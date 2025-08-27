# apps/validador-orcamento/worker/src/tasks.py
from __future__ import annotations

from pathlib import Path
from typing import Union, Optional, Dict, Any
from datetime import datetime, timezone
from time import perf_counter
from rq import get_current_job

# loaders (preços)
from src.cruzar_orcamento.adapters.orcamento import load_orcamento as load_orc_precos
from src.cruzar_orcamento.adapters.sinapi import load_sinapi_ccd_pr as load_sinapi_precos
from src.cruzar_orcamento.adapters.sudecap import load_sudecap as load_sudecap_precos
from src.cruzar_orcamento.adapters.secid import load_secid_precos

# loaders (estrutura)
from src.cruzar_orcamento.adapters.estrutura_orcamento import load_estrutura_orcamento as load_orc_estr
from src.cruzar_orcamento.adapters.estrutura_sinapi import load_estrutura_sinapi_analitico as load_sinapi_estr
from src.cruzar_orcamento.adapters.estrutura_sudecap import load_estrutura_sudecap as load_sud_estr
from src.cruzar_orcamento.adapters.estrutura_secid import load_estrutura_secid

# core + export (sempre usar as versões multi)
from src.cruzar_orcamento.core.aggregate import (
    consolidar_precos_multi,
    consolidar_estrutura_multi,
)
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

def _artifact_path(out_dir: Path, kind: str) -> Path:
    """Gera nome único para o artefato: <kind>_<jobid>_<YYYYMMDDHHMMSS>.json"""
    job = get_current_job()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    jid = (job.id if job else "nojid")[:8]
    fname = f"{kind}_{jid}_{ts}.json"
    return (out_dir / fname).resolve()


# ---------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------
def run_precos_auto(
    orc: str,
    sudecap: Optional[str] = None,
    sinapi: Optional[str] = None,
    secid: Optional[str] = None,
    tol_rel: float = 0.0,
    out_dir: str = "output",
    comparar_desc: bool = True,
):
    """
    Cruza preços do orçamento com quaisquer bancos informados (SINAPI/SUDECAP/SECID).
    Requer: 'orc' + ao menos 1 banco. Gera '<precos>_<job>_<ts>.json' em out_dir.
    """
    started_at = _now_iso()
    t0 = perf_counter()
    try:
        tol_rel = float(tol_rel)
    except Exception:
        tol_rel = 0.0
    tol_rel = max(0.0, min(1.0, tol_rel))

    try:
        orc_p     = _norm_in(orc)
        out_dir_p = _norm_out_dir(out_dir)
        out_dir_p.mkdir(parents=True, exist_ok=True)

        _ensure_exists(orc_p, "Orçamento")
        a = load_orc_precos(orc_p)

        banks: Dict[str, Dict[str, Any]] = {}
        meta_inputs: Dict[str, Any] = {"orc": str(orc_p)}

        if sinapi:
            sinapi_p = _norm_in(sinapi)
            _ensure_exists(sinapi_p, "SINAPI (preços)")
            banks["SINAPI"] = load_sinapi_precos(sinapi_p)
            meta_inputs["sinapi"] = str(sinapi_p)

        if sudecap:
            sudecap_p = _norm_in(sudecap)
            _ensure_exists(sudecap_p, "SUDECAP (preços)")
            banks["SUDECAP"] = load_sudecap_precos(sudecap_p)
            meta_inputs["sudecap"] = str(sudecap_p)

        if secid:
            secid_p = _norm_in(secid)
            _ensure_exists(secid_p, "SECID (preços)")
            banks["SECID"] = load_secid_precos(secid_p)
            meta_inputs["secid"] = str(secid_p)

        if not banks:
            raise ValueError("Informe ao menos um banco: SINAPI, SUDECAP ou SECID.")

        # Consolidação via 'multi'
        payload = consolidar_precos_multi(a, banks, tol_rel=tol_rel, comparar_descricao=comparar_desc)

        meta = {
            "kind": "precos",
            "generated_at": _now_iso(),
            "started_at": started_at,
            "inputs": meta_inputs,
            "params": {
                "tol_rel": tol_rel,
                "comparar_descricao": comparar_desc,
                "bancos": sorted(banks.keys()),
            },
        }
        if isinstance(payload, dict):
            payload.setdefault("meta", meta)
        else:
            payload = {"meta": meta, "data": payload}

        artifact = _artifact_path(out_dir_p, "precos")
        artifact = export_json(payload, artifact)

        _save_meta(
            artifact=artifact,
            extra={
                "kind": "precos",
                "finished_at": _now_iso(),
                "duration_s": round(perf_counter() - t0, 3),
            },
        )
        return {"ok": True, "artifact": str(artifact)}
    except Exception as e:
        _save_meta(
            error=str(e),
            extra={
                "kind": "precos",
                "finished_at": _now_iso(),
                "duration_s": round(perf_counter() - t0, 3),
            },
        )
        raise


def run_estrutura_auto(
    orc: str,
    sudecap: Optional[str] = None,
    sinapi: Optional[str] = None,
    secid: Optional[str] = None,
    out_dir: str = "output",
):
    """
    Compara estrutura (pai + filhos 1º nível) do orçamento com quaisquer bancos (SINAPI/SUDECAP/SECID).
    Requer: 'orc' + ao menos 1 banco. Gera '<estrutura>_<job>_<ts>.json' em out_dir.
    """
    started_at = _now_iso()
    t0 = perf_counter()

    try:
        orc_p     = _norm_in(orc)
        out_dir_p = _norm_out_dir(out_dir)
        out_dir_p.mkdir(parents=True, exist_ok=True)

        _ensure_exists(orc_p, "Estrutura do Orçamento")
        a = load_orc_estr(orc_p)

        banks: Dict[str, Dict[str, Any]] = {}
        meta_inputs: Dict[str, Any] = {"orc": str(orc_p)}

        if sinapi:
            sinapi_p = _norm_in(sinapi)
            _ensure_exists(sinapi_p, "SINAPI (estrutura)")
            banks["SINAPI"] = load_sinapi_estr(sinapi_p)
            meta_inputs["sinapi"] = str(sinapi_p)

        if sudecap:
            sudecap_p = _norm_in(sudecap)
            _ensure_exists(sudecap_p, "SUDECAP (estrutura)")
            banks["SUDECAP"] = load_sud_estr(sudecap_p)
            meta_inputs["sudecap"] = str(sudecap_p)

        if secid:
            secid_p = _norm_in(secid)
            _ensure_exists(secid_p, "SECID (estrutura)")
            banks["SECID"] = load_estrutura_secid(secid_p)
            meta_inputs["secid"] = str(secid_p)

        if not banks:
            raise ValueError("Informe ao menos um banco: SINAPI, SUDECAP ou SECID.")

        # Consolidação via 'multi'
        payload = consolidar_estrutura_multi(a, banks)

        meta = {
            "kind": "estrutura",
            "generated_at": _now_iso(),
            "started_at": started_at,
            "inputs": meta_inputs,
            "params": {"bancos": sorted(banks.keys())},
        }
        if isinstance(payload, dict):
            payload.setdefault("meta", meta)
        else:
            payload = {"meta": meta, "data": payload}

        artifact = _artifact_path(out_dir_p, "estrutura")
        artifact = export_json(payload, artifact)

        _save_meta(
            artifact=artifact,
            extra={
                "kind": "estrutura",
                "finished_at": _now_iso(),
                "duration_s": round(perf_counter() - t0, 3),
            },
        )
        return {"ok": True, "artifact": str(artifact)}
    except Exception as e:
        _save_meta(
            error=str(e),
            extra={
                "kind": "estrutura",
                "finished_at": _now_iso(),
                "duration_s": round(perf_counter() - t0, 3),
            },
        )
        raise
