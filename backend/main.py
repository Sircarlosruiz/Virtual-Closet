from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse

from api.routers.auth import router as auth_router
from api.routers.prendas import router as prendas_router
from api.routers.ws import router as ws_router
from api.routers.modelos_ia import router as modelos_ia_router
from api.routers.generaciones import router as generaciones_router
from core.config import settings
from core.limiter import limiter
from core.middleware import TokenRefreshMiddleware

app = FastAPI(title="Virtual Closet API", version="0.1.0")
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TokenRefreshMiddleware)

app.include_router(auth_router)
app.include_router(prendas_router)
app.include_router(ws_router)
app.include_router(modelos_ia_router)
app.include_router(generaciones_router)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Demasiados intentos. Inténtalo de nuevo en un minuto."},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    try:
        from aiobotocore.session import get_session
        session = get_session()
        async with session.create_client(
            "s3",
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
        ) as client:
            buckets = await client.list_buckets()
            bucket_names = [b["Name"] for b in buckets.get("Buckets", [])]
            for bucket in [
                settings.MINIO_BUCKET_ORIGINALS,
                settings.MINIO_BUCKET_GENERATED,
                settings.MINIO_BUCKET_THUMBNAILS,
                settings.MINIO_BUCKET_MODEL_THUMBNAILS,
            ]:
                if bucket not in bucket_names:
                    await client.create_bucket(Bucket=bucket)
    except Exception:
        pass
