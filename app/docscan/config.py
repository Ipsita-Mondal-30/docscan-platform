from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./docscan.db"
    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "docscan:jobs"
    upload_dir: str = "/tmp/docscan-uploads"
    max_upload_mb: int = 10
    min_confidence: float = 60.0  # below this the job is flagged low_confidence
    worker_metrics_port: int = 9100

    class Config:
        env_prefix = "DOCSCAN_"


settings = Settings()
