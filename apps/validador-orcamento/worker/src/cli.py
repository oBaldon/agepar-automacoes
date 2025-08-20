# src/cli.py
import typer
from pathlib import Path

from .cruzar_orcamento.adapters.orcamento import load_orcamento as load_orc_precos
from .cruzar_orcamento.adapters.sinapi import load_sinapi_ccd_pr as load_sinapi_precos
from .cruzar_orcamento.adapters.sudecap import load_sudecap as load_sudecap_precos

from .cruzar_orcamento.adapters.estrutura_orcamento import load_estrutura_orcamento as load_orc_estr
from .cruzar_orcamento.adapters.estrutura_sinapi import load_estrutura_sinapi_analitico as load_sinapi_estr
from .cruzar_orcamento.adapters.estrutura_sudecap import load_estrutura_sudecap as load_sud_estr

from .cruzar_orcamento.core.aggregate import consolidar_precos, consolidar_estrutura
from .cruzar_orcamento.exporters.json_compacto import export_json

app = typer.Typer(no_args_is_help=True)

@app.command("precos-auto")
def precos_auto(
    orc: Path = typer.Option(..., "--orc", help="Arquivo do Orçamento"),
    sudecap: Path = typer.Option(..., "--sudecap", help="Arquivo de preços SUDECAP"),
    sinapi: Path = typer.Option(..., "--sinapi", help="Arquivo de preços SINAPI"),
    tol_rel: float = typer.Option(0.05, "--tol-rel", help="Tolerância relativa (ex.: 0.05 = 5%)"),
    comparar_desc: bool = typer.Option(
        True,
        "--comparar-desc/--no-comparar-desc",
        help="Compara descrições entre orçamento e referência"
    ),
    out_dir: Path = typer.Option(Path("output"), "--out-dir", help="Pasta de saída"),
):
    out_dir.mkdir(parents=True, exist_ok=True)

    typer.echo(">> Lendo ORÇAMENTO (preços)…")
    a = load_orc_precos(orc)

    typer.echo(">> Lendo SUDECAP (preços)…")
    b_sud = load_sudecap_precos(sudecap)

    typer.echo(">> Lendo SINAPI (preços)…")
    b_sin = load_sinapi_precos(sinapi)

    payload = consolidar_precos(
        a, b_sin, b_sud,
        tol_rel=tol_rel,
        comparar_descricao=comparar_desc
    )
    path = export_json(payload, out_dir / "precos.json")
    typer.secho(f"OK: {path}", fg=typer.colors.GREEN)


@app.command("estrutura-auto")
def estrutura_auto(
    orc: Path = typer.Option(..., "--orc", help="Arquivo do Orçamento (composições)"),
    sudecap: Path = typer.Option(..., "--sudecap", help="Arquivo de composições SUDECAP"),
    sinapi: Path = typer.Option(..., "--sinapi", help="Arquivo de composições SINAPI"),
    out_dir: Path = typer.Option(Path("output"), "--out-dir", help="Pasta de saída"),
):
    out_dir.mkdir(parents=True, exist_ok=True)

    typer.echo(">> Lendo ESTRUTURA do ORÇAMENTO…")
    a = load_orc_estr(orc)

    typer.echo(">> Lendo ESTRUTURA SUDECAP…")
    b_sud = load_sud_estr(sudecap)

    typer.echo(">> Lendo ESTRUTURA SINAPI…")
    b_sin = load_sinapi_estr(sinapi)

    payload = consolidar_estrutura(a, b_sin, b_sud)
    path = export_json(payload, out_dir / "estrutura.json")
    typer.secho(f"OK: {path}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
