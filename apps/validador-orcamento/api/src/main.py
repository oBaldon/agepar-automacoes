from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional, Any
import os, json
from redis import from_url as redis_from_url
from rq import Queue, job

app = FastAPI(title="Validador de Orçamento API")

# CORS (dev)
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/1")
QUEUE_NAME = os.getenv("QUEUE_NAME", "validador")
_redis = redis_from_url(REDIS_URL)
_q = Queue(QUEUE_NAME, connection=_redis)

class PrecosManual(BaseModel):
    op: Literal["precos_manual"]
    orc: str
    ref: str
    ref_type: Literal["SINAPI","SUDECAP"]
    banco: Literal["SINAPI","SUDECAP"]
    tol_rel: float = Field(0)
    out: str

class PrecosAuto(BaseModel):
    op: Literal["precos_auto"]
    orc: str
    tol_rel: float = Field(0)
    out_dir: str

class Estrutura(BaseModel):
    op: Literal["estrutura"]
    orc: str
    banco_a: Literal["SINAPI","SUDECAP"]
    base: str
    base_type: Literal["SINAPI","SUDECAP"]
    out: str

JobCreate = PrecosManual | PrecosAuto | Estrutura

class JobOut(BaseModel):
    id: str
    status: str
    artifact: Optional[Any] = None  # reservado p/ futuro (MinIO)

@app.get("/health")
def health():
    return {"status":"ok","env": os.getenv("ENV","dev")}

@app.post("/jobs", response_model=JobOut)
def create_job(body: JobCreate):
    target_map = {
        "precos_manual": "src.tasks.run_precos_manual",
        "precos_auto":   "src.tasks.run_precos_auto",
        "estrutura":     "src.tasks.validar_estrutura",
    }
    fn = target_map[body.op]
    payload = body.model_dump(exclude={"op"})  # não enviar 'op' ao worker
    j = _q.enqueue(
        fn,
        kwargs=payload,
        job_timeout="1h",
        result_ttl=24*3600,
        failure_ttl=7*24*3600,
    )
    # guardar caminhos úteis para leitura depois
    if "out" in payload:
        j.meta["out"] = payload["out"]
    if "out_dir" in payload:
        j.meta["out_dir"] = payload["out_dir"]
    j.save_meta()
    return JobOut(id=j.id, status=j.get_status())

@app.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str):
    try:
        j = job.Job.fetch(job_id, connection=_redis)
    except Exception:
        raise HTTPException(status_code=404, detail="job not found")
    return JobOut(id=j.id, status=j.get_status(), artifact=j.meta.get("artifact"))

@app.get("/jobs/{job_id}/result")
def get_job_result(job_id: str):
    """
    Retorna o(s) JSON(s) de resultado.
    - Se o job tiver meta 'out': devolve o JSON único.
    - Se tiver meta 'out_dir': procura os JSONs gerados (SINAPI/SUDECAP) e
      retorna um pacote consolidado.
    """
    try:
        j = job.Job.fetch(job_id, connection=_redis)
    except Exception:
        raise HTTPException(status_code=404, detail="job not found")

    meta = j.meta or {}

    # Caso 1: resultado único em 'out'
    out = meta.get("out")
    if out:
        if not os.path.exists(out):
            raise HTTPException(status_code=404, detail=f"result file not found: {out}")
        try:
            with open(out, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"failed to read result: {e}")

    # Caso 2: modo automático: múltiplos arquivos em 'out_dir'
    out_dir = meta.get("out_dir")
    if out_dir:
        if not os.path.isdir(out_dir):
            raise HTTPException(status_code=404, detail=f"result directory not found: {out_dir}")

        # Lista todos .json e escolhe os mais recentes de SINAPI/SUDECAP
        try:
            json_files = []
            for name in os.listdir(out_dir):
                if name.lower().endswith(".json"):
                    full = os.path.join(out_dir, name)
                    try:
                        mtime = os.path.getmtime(full)
                    except Exception:
                        continue
                    json_files.append((mtime, name, full))

            if not json_files:
                raise HTTPException(status_code=404, detail="no JSON results found in out_dir")

            # mais recentes primeiro
            json_files.sort(key=lambda x: x[0], reverse=True)

            sinapi_json = None
            sudecap_json = None
            files_list = []

            for _mt, nm, path in json_files:
                files_list.append({"name": nm, "path": path})
                ln = nm.lower()
                try:
                    if "sinapi" in ln and sinapi_json is None:
                        with open(path, "r", encoding="utf-8") as f:
                            sinapi_json = json.load(f)
                    elif "sudecap" in ln and sudecap_json is None:
                        with open(path, "r", encoding="utf-8") as f:
                            sudecap_json = json.load(f)
                except Exception:
                    # ignora leitura problemática de algum arquivo avulso
                    pass

            return {
                "mode": "precos_auto",
                "sinapi": sinapi_json,
                "sudecap": sudecap_json,
                "files": files_list
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"failed to collect auto results: {e}")

    # Sem 'out' e sem 'out_dir'
    raise HTTPException(status_code=404, detail="no 'out' or 'out_dir' registered for this job")
