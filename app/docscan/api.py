import logging
import os
import uuid

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from .config import settings
from .db import Job, SessionLocal, init_db
from .metrics import JOBS_SUBMITTED, QUEUE_DEPTH
from .queue import RedisQueue

log = logging.getLogger("docscan.api")
ALLOWED = {"image/png", "image/jpeg", "image/tiff", "image/bmp"}

app = FastAPI(title="DocScan", version="0.1.0")
_queue = None


def get_queue():
    global _queue
    if _queue is None:
        _queue = RedisQueue()
    return _queue


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup():
    os.makedirs(settings.upload_dir, exist_ok=True)
    init_db()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz(db: Session = Depends(get_db), q=Depends(get_queue)):
    try:
        db.execute(sql_text("SELECT 1"))
        q.ping()
    except Exception as exc:  # readiness must fail closed when a dependency is down
        raise HTTPException(503, f"dependency unavailable: {exc}")
    return {"status": "ready"}


@app.get("/metrics")
def metrics(q=Depends(get_queue)):
    try:
        QUEUE_DEPTH.set(q.depth())
    except Exception:
        pass
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/jobs", status_code=202)
async def submit(file: UploadFile = File(...), db: Session = Depends(get_db), q=Depends(get_queue)):
    if file.content_type not in ALLOWED:
        raise HTTPException(415, f"unsupported type {file.content_type}")
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "file too large")
    job_id = str(uuid.uuid4())
    path = os.path.join(settings.upload_dir, job_id)  # never trust the client filename for paths
    with open(path, "wb") as fh:
        fh.write(data)
    db.add(Job(id=job_id, filename=(file.filename or "upload")[:255], path=path))
    db.commit()
    q.push(job_id)
    JOBS_SUBMITTED.inc()
    log.info("job queued", extra={"job_id": job_id})
    return {"id": job_id, "status": "queued"}


@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return {
        "id": job.id, "status": job.status, "text": job.text, "confidence": job.confidence,
        "low_confidence": job.low_confidence, "engine": job.engine, "error": job.error,
        "duration_ms": job.duration_ms,
    }
