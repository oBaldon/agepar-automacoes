from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import json
import tempfile
import shutil

app = FastAPI(title="Validador de Orçamento API", version="2.0")

# CORS (ajuste via env se quiser)
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/output")).resolve()
DATA_DIR   = Path(os.getenv("DATA_DIR", "/app/data")).resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


class PrecosAutoJSONIn(BaseModel):
    orc: str = Field(..., description="Caminho do Orçamento (no container)")
    sudecap: str = Field(..., description="Caminho SUDECAP (no container)")
    sinapi: str = Field(..., description="Caminho SINAPI (no container)")
    tol_rel: float = Field(0.05, description="Tolerância relativa (0.05 = 5%)")
    out_dir: Optional[str] = Field(None, description="Saída (padrão: /app/output)")


class EstruturaAutoJSONIn(BaseModel):
    orc: str
    sudecap: str
    sinapi: str
    out_dir: Optional[str] = None


def _load_worker_symbols():
    """
    Tenta importar os adapters e o aggregate do 'worker'.
    Se não estiverem na imagem da API, retornamos 501 para os endpoints de processamento.
    """
    try:
        from src.cruzar_orcamento.adapters.orcamento import load_orcamento as load_orc_precos
        from src.cruzar_orcamento.adapters.sinapi import load_sinapi_ccd_pr as load_sinapi_precos
        from src.cruzar_orcamento.adapters.sudecap import load_sudecap as load_sudecap_precos

        from src.cruzar_orcamento.adapters.estrutura_orcamento import load_estrutura_orcamento as load_orc_estr
        from src.cruzar_orcamento.adapters.estrutura_sinapi import load_estrutura_sinapi_analitico as load_sinapi_estr
        from src.cruzar_orcamento.adapters.estrutura_sudecap import load_estrutura_sudecap as load_sud_estr

        from src.cruzar_orcamento.core.aggregate import consolidar_precos, consolidar_estrutura
        from src.cruzar_orcamento.exporters.json_compacto import export_json
    except Exception as e:
        raise HTTPException(status_code=501, detail=f"Código do worker não está disponível nesta imagem: {e}")

    return {
        "load_orc_precos": load_orc_precos,
        "load_sinapi_precos": load_sinapi_precos,
        "load_sudecap_precos": load_sudecap_precos,
        "load_orc_estr": load_orc_estr,
        "load_sinapi_estr": load_sinapi_estr,
        "load_sud_estr": load_sud_estr,
        "consolidar_precos": consolidar_precos,
        "consolidar_estrutura": consolidar_estrutura,
        "export_json": export_json,
    }


@app.get("/health")
def health():
    return {"ok": True}


def _save_uploads(files: Dict[str, UploadFile]) -> Dict[str, Path]:
    tmpdir = Path(tempfile.mkdtemp(prefix="upload_", dir=str(DATA_DIR)))
    saved: Dict[str, Path] = {}
    try:
        for key, uf in files.items():
            if uf is None:
                continue
            dest = tmpdir / uf.filename
            with dest.open("wb") as f:
                shutil.copyfileobj(uf.file, f)
            saved[key] = dest
        return saved
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise


# ================= PREÇOS: duas variantes =================

@app.post("/precos/auto/json")
def precos_auto_json(body: PrecosAutoJSONIn):
    syms = _load_worker_symbols()

    orc_path = Path(body.orc).resolve()
    sud_path = Path(body.sudecap).resolve()
    sin_path = Path(body.sinapi).resolve()
    out_dir  = Path(body.out_dir or OUTPUT_DIR).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    for p in [orc_path, sud_path, sin_path]:
        if not p.exists():
            raise HTTPException(status_code=404, detail=f"arquivo não encontrado: {p}")

    a = syms["load_orc_precos"](orc_path)
    b_sud = syms["load_sudecap_precos"](sud_path)
    b_sin = syms["load_sinapi_precos"](sin_path)

    payload = syms["consolidar_precos"](a, b_sin, b_sud, tol_rel=body.tol_rel, comparar_descricao=True)
    path = syms["export_json"](payload, out_dir / "precos.json")
    return {"ok": True, "artifact": str(path), "payload": payload}


@app.post("/precos/auto/upload")
def precos_auto_upload(
    orc: UploadFile = File(...),
    sudecap: UploadFile = File(...),
    sinapi: UploadFile = File(...),
    tol_rel: float = Form(0.05),
):
    syms = _load_worker_symbols()
    saved = _save_uploads({"orc": orc, "sudecap": sudecap, "sinapi": sinapi})

    a = syms["load_orc_precos"](saved["orc"])
    b_sud = syms["load_sudecap_precos"](saved["sudecap"])
    b_sin = syms["load_sinapi_precos"](saved["sinapi"])

    payload = syms["consolidar_precos"](a, b_sin, b_sud, tol_rel=float(tol_rel), comparar_descricao=True)
    path = syms["export_json"](payload, OUTPUT_DIR / "precos.json")
    return {"ok": True, "artifact": str(path), "payload": payload}


# ================= ESTRUTURA: duas variantes =================

@app.post("/estrutura/auto/json")
def estrutura_auto_json(body: EstruturaAutoJSONIn):
    syms = _load_worker_symbols()

    orc_path = Path(body.orc).resolve()
    sud_path = Path(body.sudecap).resolve()
    sin_path = Path(body.sinapi).resolve()
    out_dir  = Path(body.out_dir or OUTPUT_DIR).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    for p in [orc_path, sud_path, sin_path]:
        if not p.exists():
            raise HTTPException(status_code=404, detail=f"arquivo não encontrado: {p}")

    a = syms["load_orc_estr"](orc_path)
    b_sud = syms["load_sud_estr"](sud_path)
    b_sin = syms["load_sinapi_estr"](sin_path)

    payload = syms["consolidar_estrutura"](a, b_sin, b_sud)
    path = syms["export_json"](payload, out_dir / "estrutura.json")
    return {"ok": True, "artifact": str(path), "payload": payload}


@app.post("/estrutura/auto/upload")
def estrutura_auto_upload(
    orc: UploadFile = File(...),
    sudecap: UploadFile = File(...),
    sinapi: UploadFile = File(...),
):
    syms = _load_worker_symbols()
    saved = _save_uploads({"orc": orc, "sudecap": sudecap, "sinapi": sinapi})

    a = syms["load_orc_estr"](saved["orc"])
    b_sud = syms["load_sud_estr"](saved["sudecap"])
    b_sin = syms["load_sinapi_estr"](saved["sinapi"])

    payload = syms["consolidar_estrutura"](a, b_sin, b_sud)
    path = syms["export_json"](payload, OUTPUT_DIR / "estrutura.json")
    return {"ok": True, "artifact": str(path), "payload": payload}


# ==================== READ-ONLY ====================

@app.get("/precos")
def get_precos():
    p = OUTPUT_DIR / "precos.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="precos.json não encontrado")
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"erro lendo {p}: {e}")


@app.get("/estrutura")
def get_estrutura():
    p = OUTPUT_DIR / "estrutura.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="estrutura.json não encontrado")
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"erro lendo {p}: {e}")


@app.get("/files")
def list_files():
    files = []
    for p in sorted(OUTPUT_DIR.glob("*.json")):
        try:
            stat = p.stat()
            files.append({
                "name": p.name,
                "path": str(p),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
            })
        except Exception:
            continue
    return {"output_dir": str(OUTPUT_DIR), "files": files}
