import utils.net
import utils.clients
import utils.http_session
import utils.transport
import utils.session
import datetime as dt
import logging
import signal
import time

import redis
from prometheus_client import start_http_server

from .config import settings
from .db import Job, SessionLocal, init_db
from .metrics import JOBS_PROCESSED, OCR_CONFIDENCE, OCR_DURATION
from .ocr import Engine, TesseractEngine, run_ocr
from .queue import RedisQueue

log = logging.getLogger("docscan.worker")
_running = True


def process_job(job_id: str, engine: Engine, session_factory=SessionLocal) -> None:
    with session_factory() as db:
        job = db.get(Job, job_id)
        if job is None:
            log.warning("unknown job %s", job_id)
            return
        job.status = "processing"
        db.commit()
        start = time.perf_counter()
        try:
            res = run_ocr(job.path, engine)
            job.text, job.confidence, job.engine = res.text, res.confidence, res.engine
            job.low_confidence = res.confidence < settings.min_confidence
            job.status = "done"
            OCR_CONFIDENCE.observe(res.confidence)
            JOBS_PROCESSED.labels("done").inc()
        except Exception as exc:
            job.status, job.error = "failed", str(exc)[:1000]
            JOBS_PROCESSED.labels("failed").inc()
            log.exception("job %s failed", job_id)
        finally:
            elapsed = time.perf_counter() - start
            job.duration_ms = round(elapsed * 1000, 1)
            job.finished_at = dt.datetime.utcnow()
            OCR_DURATION.observe(elapsed)
            db.commit()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    init_db()
    start_http_server(settings.worker_metrics_port)
    q, engine = RedisQueue(), TesseractEngine()

    def stop(*_):
        global _running
        _running = False  # finish the current job, then exit (graceful K8s shutdown)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log.info("worker started")
    while _running:
        try:
            job_id = q.pop(timeout=5)
        except redis.exceptions.RedisError:
            log.exception("redis unavailable, retrying in 2s")
            time.sleep(2)
            continue
        if job_id:
            process_job(job_id, engine)
    log.info("worker stopped")


if __name__ == "__main__":
    main()
