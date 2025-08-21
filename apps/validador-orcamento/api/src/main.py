# apps/validador-orcamento/api/src/main.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

APP_ROOT = Path("/app")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", APP_ROOT / "output"))
DATA_DIR = Path(os.getenv("DATA_DIR", APP_ROOT / "data"))

app = FastAPI(title="Validador API (read-only)")

# CORS liberal p/ dev; ajuste conforme necessário
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def _read_json(path: Path):
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{path.name} não encontrado")
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao ler {path.name}: {e}")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/files")
def list_files():
    files: List[dict] = []
    if OUTPUT_DIR.exists():
        for p in sorted(OUTPUT_DIR.glob("*.json")):
            st = p.stat()
            files.append({
                "name": p.name,
                "path": str(p),
                "size": st.st_size,
                "mtime": st.st_mtime,
            })
    return {"output_dir": str(OUTPUT_DIR), "files": files}

@app.get("/precos")
def get_precos():
    return _read_json(OUTPUT_DIR / "precos.json")

@app.get("/estrutura")
def get_estrutura():
    return _read_json(OUTPUT_DIR / "estrutura.json")

# ---- rotas legadas removidas/aposentadas ----
@app.post("/jobs")
def jobs_disabled():
    raise HTTPException(status_code=410, detail="Endpoint de jobs foi descontinuado. Use /precos e /estrutura.")

@app.get("/jobs/{_id}")
def job_status_disabled(_id: str):
    raise HTTPException(status_code=410, detail="Endpoint de jobs foi descontinuado. Use /precos e /estrutura.")

@app.get("/jobs/{_id}/result")
def job_result_disabled(_id: str):
    raise HTTPException(status_code=410, detail="Endpoint de jobs foi descontinuado. Use /precos e /estrutura.")
