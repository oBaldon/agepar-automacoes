# src/cli.py
from __future__ import annotations

import sys
from pathlib import Path
import json
import typer

# permite "python src/cli.py" rodar sem instalar o pacote
sys.path.append(str(Path(__file__).resolve().parent))

# ===== PREÇOS =====
from cruzar_orcamento.adapters.orcamento import load_orcamento
from cruzar_orcamento.adapters.sudecap import load_sudecap
from cruzar_orcamento.adapters.sinapi import load_sinapi_ccd_pr
from cruzar_orcamento.validators.processor import cruzar  # cruzamento de PREÇOS

# ===== ESTRUTURA =====
from cruzar_orcamento.adapters.estrutura_orcamento import load_estrutura_orcamento
from cruzar_orcamento.adapters.estrutura_sinapi import load_estrutura_sinapi_analitico
from cruzar_orcamento.adapters.estrutura_sudecap import load_estrutura_sudecap
from cruzar_orcamento.validators.estrutura_compare import comparar_estruturas
from cruzar_orcamento.exporters.json_estrutura import (
    export_estrutura_divergencias_json,
    # export_estruturas_brutas_json,   # use se quiser depurar
)

# ---------------------------------------------------------------------
# ⚠️ FETCHERS DESLIGADOS POR PADRÃO
# Para reativar no futuro, descomente estas linhas e as chamadas
# correspondentes nos comandos indicados.
# ---------------------------------------------------------------------
# from datetime import date
# from cruzar_orcamento.fetchers.base import find_latest_available
# from cruzar_orcamento.fetchers.providers.sudecap import SUDECAP_PLAN
# from cruzar_orcamento.fetchers.providers.sinapi import fetch_latest_sinapi_referencia_xlsx
# from cruzar_orcamento.fetchers.http import download_file

app = typer.Typer(no_args_is_help=True, add_completion=False, help="""
Cruzar Orçamento x Bancos de Referência (preços e estruturas) — saída em JSON.
""")


# -----------------------------------------
# Helpers: pegar o arquivo mais recente por padrão em data/
# -----------------------------------------
def _latest_file(prefix: str, ext: str) -> Path:
    """
    Procura em data/ pelo padrão {prefix}_YYYY_MM.{ext} e retorna o mais recente
    lexicograficamente (assumindo YYYY_MM no nome).
    """
    candidates = sorted(Path("data").glob(f"{prefix}_????_??.{ext}"))
    if not candidates:
        raise FileNotFoundError(f"Nenhum arquivo encontrado: data/{prefix}_YYYY_MM.{ext}")
    return candidates[-1]


def _latest_sudecap_any() -> Path:
    """
    Tenta achar SUDECAP_YYYY_MM.xls; se não houver, tenta .xlsx.
    """
    try:
        return _latest_file("SUDECAP", "xls")
    except FileNotFoundError:
        return _latest_file("SUDECAP", "xlsx")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _add_diffs_to_cruzado(rows: list[dict]) -> list[dict]:
    """
    Calcula dif_abs e dif_rel para cada linha do 'cruzado', se possível.
    """
    out: list[dict] = []
    for r in rows:
        a = r.get("a_valor")
        b = r.get("b_valor")
        dif_abs = None
        dif_rel = None
        try:
            if a is not None and b is not None:
                fa = float(a)
                fb = float(b)
                dif_abs = abs(fa - fb)
                dif_rel = (abs(fa - fb) / fb) if fb != 0 else None
        except Exception:
            pass

        with_diffs = dict(r)
        with_diffs["dif_abs"] = dif_abs
        with_diffs["dif_rel"] = dif_rel
        out.append(with_diffs)
    return out


def _maybe_add_diffs_to_diverg(divs: list[dict]) -> list[dict]:
    """
    Se a divergência trouxer a_valor/b_valor, calcula dif_abs/dif_rel (sem sobrescrever se já existir).
    """
    out: list[dict] = []
    for d in divs:
        if ("dif_abs" in d) or ("dif_rel" in d):
            out.append(d)
            continue
        a = d.get("a_valor")
        b = d.get("b_valor")
        dif_abs = None
        dif_rel = None
        try:
            if a is not None and b is not None:
                fa = float(a)
                fb = float(b)
                dif_abs = abs(fa - fb)
                dif_rel = (abs(fa - fb) / fb) if fb != 0 else None
        except Exception:
            pass
        nd = dict(d)
        nd["dif_abs"] = dif_abs
        nd["dif_rel"] = dif_rel
        out.append(nd)
    return out


# =====================================================================
# PREÇOS
# =====================================================================

@app.command("run-precos")
def run_precos(
    orc: Path = typer.Option(..., exists=True, readable=True, help="Arquivo de ORÇAMENTO."),
    ref: Path = typer.Option(..., exists=True, readable=True, help="Arquivo de referência (SUDECAP/SINAPI)."),
    ref_type: str = typer.Option("SUDECAP", help="Tipo da referência: SUDECAP ou SINAPI."),
    banco: str = typer.Option("", help="Filtra o orçamento por este banco (ex.: SUDECAP, SINAPI)."),
    tol_rel: float = typer.Option(0.0, help="Tolerância relativa (fração). Ex.: 0.02 = 2%%."),
    tol_abs: float = typer.Option(0.0, help="(Reservado) Tolerância absoluta."),
    valor_scale: float = typer.Option(1.0, help="Fator multiplicador nos valores do orçamento (ex.: 0.01)."),
    out: Path = typer.Option(Path("output/cruzamento_precos.json"), help="JSON de saída."),
):
    """
    Cruza PREÇOS do ORÇAMENTO contra uma referência (SUDECAP/SINAPI) — saída em JSON.
    """
    ref_type_norm = ref_type.strip().upper()

    typer.secho(">> Lendo ORÇAMENTO…", fg=typer.colors.CYAN)
    orc_dict = load_orcamento(str(orc), valor_scale=valor_scale)

    typer.secho(f">> Lendo referência: {ref_type_norm}…", fg=typer.colors.CYAN)
    if ref_type_norm == "SUDECAP":
        ref_dict = load_sudecap(str(ref))
    elif ref_type_norm == "SINAPI":
        # cidade fixa aqui; se precisar, adicione uma opção CLI
        ref_dict = load_sinapi_ccd_pr(str(ref), cidade="CURITIBA")
    else:
        raise typer.BadParameter("ref_type não suportado. Use: SUDECAP, SINAPI")

    typer.secho(">> Cruzando PREÇOS…", fg=typer.colors.CYAN)
    cruzado, diverg = cruzar(
        orcamento=orc_dict,
        referencia=ref_dict,
        banco=banco or None,
        tol_rel=float(tol_rel or 0.0),
        comparar_descricao=True,
    )

    cruzado = _add_diffs_to_cruzado(cruzado)
    diverg = _maybe_add_diffs_to_diverg(diverg)

    payload = {
        "meta": {
            "banco": banco or None,
            "ref_type": ref_type_norm,
            "tol_rel": float(tol_rel or 0.0),
            "valor_scale": valor_scale,
            "orc": str(orc),
            "ref": str(ref),
        },
        "total_cruzado": len(cruzado),
        "total_divergencias": len(diverg),
        "cruzado": cruzado,
        "divergencias": diverg,
    }

    _ensure_parent(out)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    typer.secho(f">> OK! JSON salvo em {out}", fg=typer.colors.GREEN)


@app.command("run-precos-auto")
def run_precos_auto(
    orc: Path = typer.Option(..., exists=True, readable=True, help="Arquivo de ORÇAMENTO."),
    cidade: str = typer.Option("CURITIBA", help="Cidade para SINAPI CCD."),
    tol_rel: float = typer.Option(0.0, help="Tolerância relativa para ambos os cruzamentos."),
    out_dir: Path = typer.Option(Path("output"), "--out-dir", help="Pasta de saída"),
):
    """
    Usa os **últimos arquivos** em data/ e cruza PREÇOS:
      - ORÇAMENTO (banco=SINAPI) x SINAPI_YYYY_MM.xlsx
      - ORÇAMENTO (banco=SUDECAP) x SUDECAP_YYYY_MM.xls(.xlsx)
    Gera dois JSONs em output/.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    typer.secho(">> Lendo ORÇAMENTO…", fg=typer.colors.CYAN)
    orc_dict = load_orcamento(str(orc))

    # ===== SINAPI =====
    try:
        sinapi_file = _latest_file("SINAPI", "xlsx")
    except FileNotFoundError:
        typer.secho("[SINAPI] Nenhum arquivo encontrado em data/SINAPI_YYYY_MM.xlsx.", err=True, fg=typer.colors.YELLOW)
        sinapi_file = None

    if sinapi_file:
        try:
            typer.echo(f">> Lendo referência SINAPI: {sinapi_file.name}")
            ref_sinapi = load_sinapi_ccd_pr(str(sinapi_file), cidade=cidade)

            typer.echo(">> Cruzando PREÇOS (SINAPI)…")
            cruz_s, div_s = cruzar(
                orc_dict, ref_sinapi, banco="SINAPI",
                tol_rel=float(tol_rel or 0.0), comparar_descricao=True
            )
            cruz_s = _add_diffs_to_cruzado(cruz_s)
            div_s = _maybe_add_diffs_to_diverg(div_s)

            y, m = sinapi_file.stem.split("_")[-2:]
            out_sinapi = out_dir / f"cruzamento_precos_sinapi_{y}_{m}.json"
            payload_s = {
                "meta": {"banco": "SINAPI", "ref_type": "SINAPI", "orc": str(orc), "ref": str(sinapi_file)},
                "total_cruzado": len(cruz_s),
                "total_divergencias": len(div_s),
                "cruzado": cruz_s,
                "divergencias": div_s,
            }
            _ensure_parent(out_sinapi)
            with open(out_sinapi, "w", encoding="utf-8") as f:
                json.dump(payload_s, f, ensure_ascii=False, indent=2)

            typer.secho(f">> [SINAPI] OK → {out_sinapi}", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"[SINAPI] Falhou: {e}", err=True, fg=typer.colors.RED)

    # ===== SUDECAP =====
    try:
        sud_file = _latest_sudecap_any()
    except FileNotFoundError:
        typer.secho("[SUDECAP] Nenhum arquivo encontrado em data/SUDECAP_YYYY_MM.xls(.xlsx).", err=True, fg=typer.colors.YELLOW)
        sud_file = None

    if sud_file:
        try:
            typer.echo(f">> Lendo referência SUDECAP: {sud_file.name}")
            ref_sud = load_sudecap(str(sud_file))

            typer.echo(">> Cruzando PREÇOS (SUDECAP)…")
            cruz_u, div_u = cruzar(
                orc_dict, ref_sud, banco="SUDECAP",
                tol_rel=float(tol_rel or 0.0), comparar_descricao=True
            )
            cruz_u = _add_diffs_to_cruzado(cruz_u)
            div_u = _maybe_add_diffs_to_diverg(div_u)

            y, m = sud_file.stem.split("_")[-2:]
            out_sud = out_dir / f"cruzamento_precos_sudecap_{y}_{m}.json"
            payload_u = {
                "meta": {"banco": "SUDECAP", "ref_type": "SUDECAP", "orc": str(orc), "ref": str(sud_file)},
                "total_cruzado": len(cruz_u),
                "total_divergencias": len(div_u),
                "cruzado": cruz_u,
                "divergencias": div_u,
            }
            _ensure_parent(out_sud)
            with open(out_sud, "w", encoding="utf-8") as f:
                json.dump(payload_u, f, ensure_ascii=False, indent=2)

            typer.secho(f">> [SUDECAP] OK → {out_sud}", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"[SUDECAP] Falhou: {e}", err=True, fg=typer.colors.RED)


# =====================================================================
# ESTRUTURA
# =====================================================================

@app.command("validar-estrutura")
def validar_estrutura(
    orc: Path = typer.Option(..., exists=True, readable=True, help="Arquivo do ORÇAMENTO (aba(s) de Composições)."),
    banco_a: str = typer.Option("", help="Filtrar no ORÇAMENTO apenas pais deste banco (ex.: SINAPI, SUDECAP)."),
    base: Path = typer.Option(..., exists=True, readable=True, help="Arquivo da base (ORÇAMENTO / SINAPI / SUDECAP)."),
    base_type: str = typer.Option(..., help="Tipo da base: ORCAMENTO | SINAPI | SUDECAP."),
    sinapi_sheet: str = typer.Option("Analítico", help="Nome da aba Analítico no SINAPI."),
    out: Path = typer.Option(Path("output/diverg_estrutura.json"), help="JSON de saída."),
):
    """
    Valida a ESTRUTURA (pai + filhos 1º nível) do ORÇAMENTO contra uma BASE.
    """
    base_type_norm = base_type.strip().upper()
    banco_a = (banco_a or "").strip() or None

    typer.secho(">> Lendo ESTRUTURA do ORÇAMENTO…", fg=typer.colors.CYAN)
    A = load_estrutura_orcamento(str(orc), banco=banco_a)

    typer.secho(f">> Lendo BASE de ESTRUTURA: {base_type_norm}…", fg=typer.colors.CYAN)
    if base_type_norm == "ORCAMENTO":
        B = load_estrutura_orcamento(str(base))
    elif base_type_norm == "SINAPI":
        B = load_estrutura_sinapi_analitico(str(base), sheet_name=sinapi_sheet)
    elif base_type_norm == "SUDECAP":
        B = load_estrutura_sudecap(str(base))
    else:
        raise typer.BadParameter("base_type não suportado. Use: ORCAMENTO, SINAPI, SUDECAP.")

    typer.secho(">> Comparando ESTRUTURAS…", fg=typer.colors.CYAN)
    diverg = comparar_estruturas(A, B)

    meta = {
        "orc": str(orc),
        "banco_a": banco_a,
        "base": str(base),
        "base_type": base_type_norm,
        "sinapi_sheet": sinapi_sheet if base_type_norm == "SINAPI" else None,
    }

    _ensure_parent(out)
    export_estrutura_divergencias_json(diverg, out, meta=meta)
    typer.secho(f">> OK! JSON salvo em {out} (divergências={len(diverg)})", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app(prog_name="cli.py")
