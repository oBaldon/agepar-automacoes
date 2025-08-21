# src/tasks.py
from __future__ import annotations

from pathlib import Path
from typing import Union, Optional, Dict, Any
from datetime import datetime, timezone
from rq import get_current_job

# loaders (preços)
from src.cruzar_orcamento.adapters.orcamento import load_orcamento as load_orc_precos
from src.cruzar_orcamento.adapters.sinapi import load_sinapi_ccd_pr as load_sinapi_precos
from src.cruzar_orcamento.adapters.sudecap import load_sudecap as load_sudecap_precos

# loaders (estrutura)
from src.cruzar_orcamento.adapters.estrutura_orcamento import load_estrutura_orcamento as load_orc_estr
from src.cruzar_orcamento.adapters.estrutura_sinapi import load_estrutura_sinapi_analitico as load_sinapi_estr
from src.cruzar_orcamento.adapters.estrutura_sudecap import load_estrutura_sudecap as load_sud_estr

# core + export
from src.cruzar_orcamento.core.aggregate import consolidar_precos, consolidar_estrutura
from src.cruzar_orcamento.exporters.json_compacto import export_json

# ---------------------------------------------------------------------
# Normalização de caminhos
# ---------------------------------------------------------------------
APP_ROOT = Path("/app").resolve()

def _norm_in(p: Union[str, Path]) -> Path:
    """Normaliza caminho de entrada. Se relativo, resolve a partir de /app."""
    p = Path(p)
    p = p if p.is_absolute() else (APP_ROOT / p)
    return p.resolve()

def _norm_out_dir(p: Optional[Union[str, Path]]) -> Path:
    """Normaliza pasta de saída (default: /app/output) e garante que está sob /app."""
    base = APP_ROOT / "output" if p is None else (Path(p) if Path(p).is_absolute() else (APP_ROOT / Path(p)))
    out = base.resolve()
    # defensivo: impede escrever fora de /app
    out.relative_to(APP_ROOT)
    return out

def _ensure_exists(p: Path, label: str) -> None:
    if not p.exists():
        raise FileNotFoundError(f"{label} não encontrado: {p}")

def _save_meta(*, artifact: Optional[Path] = None, error: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> None:
    job = get_current_job()
    if not job:
        return
    job.meta = job.meta or {}
    if artifact is not None:
        job.meta["artifact"] = str(artifact)
    if error is not None:
        job.meta["error"] = error
    if extra:
        job.meta.update(extra)
    job.save_meta()

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ---------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------
def run_precos_auto(
    orc: str,
    sudecap: str,
    sinapi: str,
    tol_rel: float = 0.05,
    out_dir: str = "output",
    comparar_desc: bool = True,
):
    """
    Cruza preços do orçamento com SUDECAP e SINAPI.
    Aceita caminhos relativos (ex.: 'data/arquivo.xlsx') ou absolutos ('/app/data/...').
    Gera 'precos.json' em out_dir.
    """
    try:
        orc_p     = _norm_in(orc)
        sudecap_p = _norm_in(sudecap)
        sinapi_p  = _norm_in(sinapi)
        out_dir_p = _norm_out_dir(out_dir)
        out_dir_p.mkdir(parents=True, exist_ok=True)

        _ensure_exists(orc_p, "Orçamento")
        _ensure_exists(sudecap_p, "SUDECAP (preços)")
        _ensure_exists(sinapi_p, "SINAPI (preços)")

        a     = load_orc_precos(orc_p)
        b_sud = load_sudecap_precos(sudecap_p)
        b_sin = load_sinapi_precos(sinapi_p)

        payload  = consolidar_precos(a, b_sin, b_sud, tol_rel=tol_rel, comparar_descricao=comparar_desc)

        # adiciona metadados úteis
        meta = {
            "generated_at": _now_iso(),
            "inputs": {"orc": str(orc_p), "sudecap": str(sudecap_p), "sinapi": str(sinapi_p)},
            "params": {"tol_rel": tol_rel, "comparar_descricao": comparar_desc},
        }
        if isinstance(payload, dict):
            payload.setdefault("meta", meta)
        else:
            # se não for dict, embrulha (não deve acontecer com o exporter atual)
            payload = {"meta": meta, "data": payload}

        artifact = export_json(payload, out_dir_p / "precos.json")
        _save_meta(artifact=artifact, extra={"kind": "precos"})
        return {"ok": True, "artifact": str(artifact)}
    except Exception as e:
        _save_meta(error=str(e))
        raise

def run_estrutura_auto(
    orc: str,
    sudecap: str,
    sinapi: str,
    out_dir: str = "output",
):
    """
    Compara a estrutura (pai + filhos 1º nível) do orçamento com SUDECAP e SINAPI.
    Aceita caminhos relativos ou absolutos. Gera 'estrutura.json' em out_dir.
    """
    try:
        orc_p     = _norm_in(orc)
        sudecap_p = _norm_in(sudecap)
        sinapi_p  = _norm_in(sinapi)
        out_dir_p = _norm_out_dir(out_dir)
        out_dir_p.mkdir(parents=True, exist_ok=True)

        _ensure_exists(orc_p, "Estrutura do Orçamento")
        _ensure_exists(sudecap_p, "SUDECAP (estrutura)")
        _ensure_exists(sinapi_p, "SINAPI (estrutura)")

        a     = load_orc_estr(orc_p)
        b_sud = load_sud_estr(sudecap_p)
        b_sin = load_sinapi_estr(sinapi_p)

        payload  = consolidar_estrutura(a, b_sin, b_sud)

        meta = {
            "generated_at": _now_iso(),
            "inputs": {"orc": str(orc_p), "sudecap": str(sudecap_p), "sinapi": str(sinapi_p)},
            "params": {},
        }
        if isinstance(payload, dict):
            payload.setdefault("meta", meta)
        else:
            payload = {"meta": meta, "data": payload}

        artifact = export_json(payload, out_dir_p / "estrutura.json")
        _save_meta(artifact=artifact, extra={"kind": "estrutura"})
        return {"ok": True, "artifact": str(artifact)}
    except Exception as e:
        _save_meta(error=str(e))
        raise
