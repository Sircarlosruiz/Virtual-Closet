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


settings = Settings()
