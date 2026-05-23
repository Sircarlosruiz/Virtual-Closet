from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7

    # Email
    RESEND_API_KEY: str = ""

    # URLs
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    # Cookie security (False for local HTTP dev, True for production)
    COOKIE_SECURE: bool = False

    # MinIO
    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_PUBLIC_ENDPOINT: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_ORIGINALS: str = "originals"
    MINIO_BUCKET_GENERATED: str = "generated"
    MINIO_BUCKET_THUMBNAILS: str = "thumbnails"
    MINIO_BUCKET_MODEL_THUMBNAILS: str = "model-thumbnails"

    # VTON / IA
    VTON_PROVIDER: str = "replicate"
    REPLICATE_API_KEY: str = ""
    LMSTUDIO_BASE_URL: str = "http://localhost:1234"
    LMSTUDIO_MODEL: str = ""
    LMSTUDIO_API_KEY: str = "lm-studio"
    LMSTUDIO_SYSTEM_PROMPT: str = ""
    LMSTUDIO_USE_PLACEMENT: bool = False
    VTON_LOCAL_URL: str = "http://idm-vton-gpu:8000"

    # CatVTON-Flux
    # Replicate model: find the exact version at https://replicate.com — search "catvton"
    # Verify input schema (human_image, cloth_image, cloth_type) matches the deployed version.
    CATVTON_REPLICATE_MODEL: str = "zhengchong/catvton"
    # Self-hosted inference server (docker compose --profile gpu up catvton)
    CATVTON_LOCAL_URL: str = "http://catvton:8000"
    # Type of garment: upper | lower | overall
    CATVTON_CLOTH_TYPE: str = "upper"
    # HuggingFace token — required to download gated FLUX.1-Fill-dev weights
    HF_TOKEN: str = ""

    # RabbitMQ / Celery
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"


settings = Settings()
