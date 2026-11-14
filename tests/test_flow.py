import io

import cv2
import numpy as np
import pytest
from docscan import api, worker
from docscan.db import init_db
from docscan.ocr import OcrResult, preprocess
from docscan.queue import MemoryQueue
from fastapi.testclient import TestClient


class FakeEngine:
    name = "fake"

    def __init__(self, conf=95.0, fail=False):
        self.conf, self.fail = conf, fail

    def run(self, image):
        if self.fail:
            raise RuntimeError("engine exploded")
        return OcrResult(text="hello world", confidence=self.conf, engine=self.name)


def png_bytes():
    img = np.full((60, 200, 3), 255, np.uint8)
    cv2.putText(img, "hello", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    return cv2.imencode(".png", img)[1].tobytes()


@pytest.fixture()
def client():
    init_db()
    q = MemoryQueue()
    api.app.dependency_overrides[api.get_queue] = lambda: q
    with TestClient(api.app) as c:
        yield c, q
    api.app.dependency_overrides.clear()


def submit(c):
    return c.post("/v1/jobs", files={"file": ("a.png", io.BytesIO(png_bytes()), "image/png")})


def test_health(client):
    c, _ = client
    assert c.get("/healthz").json() == {"status": "ok"}
    assert c.get("/readyz").status_code == 200


def test_happy_path(client):
    c, q = client
    r = submit(c)
    assert r.status_code == 202
    jid = q.pop()
    assert jid == r.json()["id"]
    worker.process_job(jid, FakeEngine())
    body = c.get(f"/v1/jobs/{jid}").json()
    assert body["status"] == "done" and body["text"] == "hello world"
    assert body["low_confidence"] is False


def test_low_confidence_flagged(client):
    c, q = client
    submit(c)
    jid = q.pop()
    worker.process_job(jid, FakeEngine(conf=10.0))
    assert c.get(f"/v1/jobs/{jid}").json()["low_confidence"] is True


def test_engine_failure_marks_failed(client):
    c, q = client
    submit(c)
    jid = q.pop()
    worker.process_job(jid, FakeEngine(fail=True))
    body = c.get(f"/v1/jobs/{jid}").json()
    assert body["status"] == "failed" and "exploded" in body["error"]


def test_rejects_bad_type(client):
    c, _ = client
    r = c.post("/v1/jobs", files={"file": ("a.txt", io.BytesIO(b"x"), "text/plain")})
    assert r.status_code == 415


def test_unknown_job_404(client):
    c, _ = client
    assert c.get("/v1/jobs/nope").status_code == 404


def test_metrics_exposed(client):
    c, _ = client
    assert "docscan_jobs_submitted_total" in c.get("/metrics").text


def test_preprocess_shape():
    img = np.full((50, 80, 3), 200, np.uint8)
    assert preprocess(img).shape == (50, 80)
