# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
# tesseract is only needed by workers, but one image keeps CI/CD simple
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends tesseract-ocr libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home app
COPY --from=builder /install /usr/local
WORKDIR /srv
COPY app/ /srv/
ENV OMP_THREAD_LIMIT=1 PYTHONUNBUFFERED=1 DOCSCAN_UPLOAD_DIR=/data/uploads
RUN mkdir -p /data/uploads && chown -R app /data
USER 10001
EXPOSE 8000 9100
CMD ["uvicorn", "docscan.api:app", "--host", "0.0.0.0", "--port", "8000"]
