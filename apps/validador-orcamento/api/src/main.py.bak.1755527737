from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Optional, Any
import os
from redis import from_url as redis_from_url
from rq import Queue, job

app = FastAPI(title="Validador de Orçamento API")

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
    artifact: Optional[Any] = None

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
    j = _q.enqueue(fn, kwargs=payload, job_timeout="1h")
    return JobOut(id=j.id, status=j.get_status())

@app.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str):
    try:
        j = job.Job.fetch(job_id, connection=_redis)
    except Exception:
        raise HTTPException(status_code=404, detail="job not found")
    return JobOut(id=j.id, status=j.get_status(), artifact=j.meta.get("artifact"))
