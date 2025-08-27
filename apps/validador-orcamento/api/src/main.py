# apps/validador-orcamento/api/src/main.py
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Body, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# RQ / Redis
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

# limite opcional para upload (MB)
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "200"))

CORS_ORIGINS = (
    [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
    if os.getenv("CORS_ORIGINS")
    else ["*"]
)

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

def _latest_by_prefix(prefix: str) -> Optional[Path]:
    if not OUTPUT_DIR.exists():
        return None
    cands = sorted(
        OUTPUT_DIR.glob(f"{prefix}_*.json"),
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
        reverse=True,
    )
    if cands:
        return cands[0]
    legacy = OUTPUT_DIR / f"{prefix}.json"
    return legacy if legacy.exists() else None

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
def _safe_filename(name: str) -> str:
    # remove paths e normaliza
    name = name.replace("\\", "/").split("/")[-1]
    name = name.strip()
    if not name:
        return "upload.bin"
    name = _SAFE_NAME_RE.sub("_", name)
    # evita nomes ocultos vazios
    return name or "upload.bin"

def _ensure_under(base: Path, p: Path) -> None:
    try:
        p.resolve().relative_to(base.resolve())
    except Exception:
        raise HTTPException(400, detail="Destino inválido (fora da área permitida).")
    
def _resolve_subdir(subdir: Optional[str]) -> Path:
    """
    Constrói DATA_DIR/<subdir-sanitizada-preservando-subpastas>.
    - Divide por / ou \, sanitiza cada segmento.
    - Impede '..' / traversal.
    """
    base = DATA_DIR
    if not subdir:
        return base
    parts = [p for p in subdir.replace("\\", "/").split("/") if p]
    clean_parts: List[str] = []
    for part in parts:
        clean = _SAFE_NAME_RE.sub("_", part).strip("._-")
        if not clean or clean in {".", ".."}:
            continue
        clean_parts.append(clean)
    dest = (base.joinpath(*clean_parts)).resolve()
    _ensure_under(base, dest)
    return dest


# ---------------------------------------------------------------------
# Rotas simples
# ---------------------------------------------------------------------
@app.get("/health")
def health():
    info = {
        "ok": True,
        "output_dir": str(OUTPUT_DIR),
        "data_dir": str(DATA_DIR),
        "queue": QUEUE_NAME,
        "max_upload_mb": MAX_UPLOAD_MB,
    }
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

# --- Legado/compat: devolvem o artefato mais recente do tipo ---
@app.get("/precos")
def get_precos():
    p = _latest_by_prefix("precos")
    if not p:
        raise HTTPException(404, detail="Nenhum arquivo de preços encontrado.")
    return _read_json(p)

@app.get("/estrutura")
def get_estrutura():
    p = _latest_by_prefix("estrutura")
    if not p:
        raise HTTPException(404, detail="Nenhum arquivo de estrutura encontrado.")
    return _read_json(p)

# ---------------------------------------------------------------------
# UPLOADS para shared/data
# ---------------------------------------------------------------------
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    subdir: Optional[str] = Form(None),      # opcional: ex. "2025-08"
    overwrite: bool = Form(False),
):
    """
    Recebe um arquivo (multipart/form-data) e salva em DATA_DIR[/subdir]/<nome>.
    Retorna o caminho relativo para usar nos jobs, ex.: "data/orcamento.xlsx".
    """
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    # pasta destino
    dest_dir = _resolve_subdir(subdir)
    dest_dir.mkdir(parents=True, exist_ok=True)


    # nome destino
    fname = _safe_filename(file.filename or "upload.bin")
    dest_path = (dest_dir / fname).resolve()
    _ensure_under(DATA_DIR, dest_path)

    if dest_path.exists() and not overwrite:
        # gera nome único simples
        stem = dest_path.stem
        suffix = dest_path.suffix
        i = 1
        while True:
            alt = dest_path.with_name(f"{stem}({i}){suffix}")
            if not alt.exists():
                dest_path = alt
                break
            i += 1

    # grava em chunks com limite de tamanho
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    written = 0
    with dest_path.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)  # 1 MiB
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                try:
                    dest_path.unlink(missing_ok=True)
                except Exception:
                    pass
                raise HTTPException(413, detail=f"Arquivo excede {MAX_UPLOAD_MB} MB.")
            out.write(chunk)

    # caminho relativo ao /app para usar na chamada de job
    rel_for_jobs = str(dest_path.relative_to(APP_ROOT))

    await file.close()  # boa prática: fecha explicitamente o UploadFile

    return JSONResponse(
        status_code=201,
        content={
            "ok": True,
            "filename": fname,
            "bytes": written,
            "saved_at": str(dest_path),
            "path_for_job": rel_for_jobs,   # ex.: "data/arquivo.xlsx"
        },
        headers={"Location": f"/data/list?subdir={dest_dir.relative_to(DATA_DIR)}"},
    )

@app.get("/data/list")
def list_data(subdir: Optional[str] = Query(None, description="Subpasta em /app/data")):
    """Lista arquivos em /app/data (ou subdir)."""
    base = _resolve_subdir(subdir)

    if not base.exists():
        return {"dir": str(base), "files": []}

    out: List[Dict[str, Any]] = []
    for p in sorted(base.glob("*")):
        if p.is_file():
            st = p.stat()
            out.append({
                "name": p.name,
                "size": st.st_size,
                "mtime": st.st_mtime,
                "mtime_iso": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                "path_for_job": str(p.relative_to(APP_ROOT)),  # "data/..."
            })
    return {"dir": str(base), "files": out}

# ---------------------------------------------------------------------
# JOBS (via Redis/RQ)
# ---------------------------------------------------------------------

@app.post("/jobs")
def create_job(payload: Dict[str, Any] = Body(...)):
    """
    Cria um job (RQ) para o worker processar e gerar JSONs em `out_dir`.

    Operações suportadas:
      - "precos_auto"
      - "estrutura_auto"

    Observações:
      - Caminhos podem ser relativos ao /app do worker (ex.: "data/...", "output")
        ou absolutos ("/app/...").
      - Agora apenas 'orc' é obrigatório; SINAPI/SUDECAP/SECID são opcionais,
        mas é necessário informar **ao menos um** deles.
    """
    op = (payload.get("op") or "").strip().lower()
    q = _queue()

    # obrigatório
    orc = payload.get("orc")
    if not orc:
        raise HTTPException(400, detail="Campo obrigatório ausente: orc")

    # bancos opcionais (precisa ter pelo menos 1)
    sinapi   = payload.get("sinapi") or None
    sudecap  = payload.get("sudecap") or None
    secid    = payload.get("secid") or None
    bancos_informados = [b for b in (sinapi, sudecap, secid) if b]
    if not bancos_informados:
        raise HTTPException(400, detail="Informe ao menos um banco: sinapi, sudecap ou secid.")

    # base kwargs comuns
    base_kwargs = dict(
        orc=orc,
        out_dir=payload.get("out_dir", str(OUTPUT_DIR)),
    )
    if sinapi:
        base_kwargs["sinapi"] = sinapi
    if sudecap:
        base_kwargs["sudecap"] = sudecap
    if secid:
        base_kwargs["secid"] = secid

    if op == "precos_auto":
        kwargs = dict(
            **base_kwargs,
            tol_rel=float(payload.get("tol_rel", 0.0)),
            comparar_desc=bool(payload.get("comparar_desc", True)),
        )
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
        kwargs = dict(**base_kwargs)
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
