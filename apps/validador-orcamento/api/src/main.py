# apps/validador-orcamento/api/src/main.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# RQ / Redis (somente na API cliente do Redis; o código do worker é carregado lá)
from redis import Redis
from rq import Queue
from rq.job import Job

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
APP_ROOT = Path("/app")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR") or (APP_ROOT / "output"))
DATA_DIR = Path(os.getenv("DATA_DIR") or (APP_ROOT / "data"))

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/1")
QUEUE_NAME = os.getenv("QUEUE_NAME", "validador")

CORS_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")
] if os.getenv("CORS_ORIGINS") else ["*"]

app = FastAPI(title="Validador API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _read_json(path: Path):
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{path.name} não encontrado")
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao ler {path.name}: {e}")


def _queue() -> Queue:
    conn = Redis.from_url(
        REDIS_URL,
        socket_timeout=5,
        health_check_interval=30,
        retry_on_timeout=True,
    )
    return Queue(name=QUEUE_NAME, connection=conn)


# ---------------------------------------------------------------------
# Rotas simples (read-only atuais)
# ---------------------------------------------------------------------
# em apps/validador-orcamento/api/src/main.py
@app.get("/health")
def health():
    info = {"ok": True, "output_dir": str(OUTPUT_DIR), "queue": QUEUE_NAME}
    try:
        conn = Redis.from_url(REDIS_URL, socket_timeout=2)
        conn.ping()
        info["redis"] = {"url": REDIS_URL, "status": "up"}
    except Exception as e:
        info["redis"] = {"url": REDIS_URL, "status": "down", "error": str(e)}
        info["ok"] = False
    return info


@app.get("/files")
def list_files():
    """Lista os JSONs gerados em OUTPUT_DIR, mais recentes primeiro."""
    def _size_human(n: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        f = float(n)
        for u in units:
            if f < 1024.0 or u == units[-1]:
                return f"{f:.0f} {u}" if u == "B" else f"{f:.1f} {u}"
            f /= 1024.0

    files: List[dict] = []
    if OUTPUT_DIR.exists():
        for p in OUTPUT_DIR.glob("*.json"):
            try:
                st = p.stat()
            except FileNotFoundError:
                continue
            files.append({
                "name": p.name,
                "path": str(p),
                "size": st.st_size,
                "size_human": _size_human(st.st_size),
                "mtime": st.st_mtime,
                "mtime_iso": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
            })

    files.sort(key=lambda f: f["mtime"], reverse=True)
    return {"output_dir": str(OUTPUT_DIR), "count": len(files), "files": files}



@app.get("/precos")
def get_precos():
    return _read_json(OUTPUT_DIR / "precos.json")

@app.get("/estrutura")
def get_estrutura():
    return _read_json(OUTPUT_DIR / "estrutura.json")


# ---------------------------------------------------------------------
# JOBS (via Redis/RQ)
#   - API APENAS enfileira por string ("src.tasks.func"),
#     o código roda no container do worker.
# ---------------------------------------------------------------------
@app.post("/jobs")
def create_job(payload: Dict[str, Any] = Body(...)):
    """
    Cria um job (RQ) para o worker processar e gerar JSONs em `out_dir`.

    Operações suportadas:
    - "precos_auto"
    - "estrutura_auto"

    Caminhos:
    - Você pode enviar caminhos **relativos** (recomendado), como "data/..." e "output".
    - Caminhos relativos são resolvidos **dentro do container do worker** (raiz = /app).
    - Caminhos absolutos ("/app/...") também funcionam.

    Exemplos de payload:

    # PREÇOS (automático)
    {
    "op": "precos_auto",
    "orc": "data/orcamento.xlsx",
    "sudecap": "data/sudecap_preco.xls",
    "sinapi": "data/sinapi_ccd.xlsx",
    "tol_rel": 0.05,
    "comparar_desc": true,   // opcional (default = true)
    "out_dir": "output"      // gera "output/precos.json"
    }

    # ESTRUTURA (automático)
    {
    "op": "estrutura_auto",
    "orc": "data/orcamento.xlsx",
    "sudecap": "data/sudecap_comp.xls",
    "sinapi": "data/sinapi_estrutura.xlsx",
    "out_dir": "output"      // gera "output/estrutura.json"
    }

    Resposta:
    - 201/200: { "id": "<job_id>", "status": "queued" }
    - Consulte o status em /jobs/{id} e o resultado em /jobs/{id}/result
    """

    op = (payload.get("op") or "").strip().lower()
    q = _queue()

    if op == "precos_auto":
        for k in ("orc", "sudecap", "sinapi"):
            if not payload.get(k):
                raise HTTPException(400, detail=f"Campo obrigatório ausente: {k}")

        kwargs = dict(
            orc=payload["orc"],
            sudecap=payload["sudecap"],
            sinapi=payload["sinapi"],
            tol_rel=float(payload.get("tol_rel", 0.05)),
            out_dir=payload.get("out_dir", str(OUTPUT_DIR)),
        )
        if "comparar_desc" in payload:
            kwargs["comparar_desc"] = bool(payload["comparar_desc"])

        job = q.enqueue(
            "src.tasks.run_precos_auto",
            kwargs=kwargs,
            job_timeout=60 * 60,        # 1h
            result_ttl=60 * 60 * 24,    # 1d
            failure_ttl=60 * 60 * 24,   # 1d
        )
        return JSONResponse(
            status_code=201,
            content={"id": job.id, "status": job.get_status()},
            headers={"Location": f"/jobs/{job.id}"},
        )

    elif op == "estrutura_auto":
        for k in ("orc", "sudecap", "sinapi"):
            if not payload.get(k):
                raise HTTPException(400, detail=f"Campo obrigatório ausente: {k}")

        kwargs = dict(
            orc=payload["orc"],
            sudecap=payload["sudecap"],
            sinapi=payload["sinapi"],
            out_dir=payload.get("out_dir", str(OUTPUT_DIR)),
        )
        job = q.enqueue(
            "src.tasks.run_estrutura_auto",
            kwargs=kwargs,
            job_timeout=60 * 60,
            result_ttl=60 * 60 * 24,
            failure_ttl=60 * 60 * 24,
        )
        return JSONResponse(
            status_code=201,
            content={"id": job.id, "status": job.get_status()},
            headers={"Location": f"/jobs/{job.id}"},
        )

    else:
        raise HTTPException(400, detail="op inválida. Use: precos_auto ou estrutura_auto")


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    q = _queue()
    try:
        job = Job.fetch(job_id, connection=q.connection)
    except Exception:
        raise HTTPException(404, detail="Job não encontrado")
    return {"id": job.id, "status": job.get_status()}


@app.get("/jobs/{job_id}/result")
def get_job_result(job_id: str):
    q = _queue()
    try:
        job = Job.fetch(job_id, connection=q.connection)
    except Exception:
        raise HTTPException(404, detail="Job não encontrado")

    status = job.get_status()
    if status != "finished":
        raise HTTPException(409, detail=f"Job ainda não finalizado (status={status})")

    artifact = (job.meta or {}).get("artifact")
    if not artifact:
        raise HTTPException(500, detail="Job finalizado mas sem 'artifact' nos metadados")

    artifact_path = Path(artifact)
    if not artifact_path.is_absolute():
        artifact_path = (APP_ROOT / artifact_path).resolve()

    try:
        artifact_path.resolve().relative_to(OUTPUT_DIR.resolve())
    except Exception:
        raise HTTPException(400, detail="Artifact fora do OUTPUT_DIR")

    try:
        with artifact_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(404, detail=f"Arquivo de resultado não encontrado: {artifact_path}")
    except Exception as e:
        raise HTTPException(500, detail=f"Falha lendo resultado: {e}")
