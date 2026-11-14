from prometheus_client import Counter, Gauge, Histogram

JOBS_SUBMITTED = Counter("docscan_jobs_submitted_total", "Jobs accepted by the API")
JOBS_PROCESSED = Counter("docscan_jobs_processed_total", "Jobs finished by workers", ["status"])
OCR_DURATION = Histogram(
    "docscan_ocr_duration_seconds", "OCR processing time",
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)
OCR_CONFIDENCE = Histogram(
    "docscan_ocr_confidence", "Mean word confidence", buckets=(20, 40, 60, 70, 80, 90, 95, 100)
)
QUEUE_DEPTH = Gauge("docscan_queue_depth", "Jobs waiting in the queue")
