from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse

from api.routers.auth import router as auth_router
from api.routers.auth_2fa import router as auth_2fa_router
from api.routers.auth_oauth import router as auth_oauth_router
from api.routers.auth_reset import router as auth_reset_router
from api.routers.auth_session import router as auth_session_router
from api.routers.prendas import router as prendas_router
from api.routers.ws import router as ws_router
from api.routers.modelos_ia import router as modelos_ia_router
from api.routers.generaciones import router as generaciones_router
from api.routers.media import router as media_router
from api.routers.pose_sets import router as pose_sets_router
from api.routers.models import router as models_router
from api.routers.vton import router as vton_router
from api.routers.tryoff import router as tryoff_router
from api.routers.catalogo import router as catalogo_router
from api.routers.customers import router as customers_router
from api.routers.portal import router as portal_router
from api.routers.batches import router as batches_router
from api.routers.tenant import router as tenant_router
from api.routers.admin import router as admin_router
from api.routers.buyer_links import router as buyer_links_router, validate_router as buyer_links_validate_router
import logging

from core.config import email_backend_status, resend_api_key_is_configured, settings, use_console_email_backend
from core.limiter import limiter
from core.middleware import RequestIDFilter, RequestIDMiddleware, TokenRefreshMiddleware

_log_handler = logging.StreamHandler()
_log_handler.setFormatter(logging.Formatter(
    fmt="%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
))
_log_handler.addFilter(RequestIDFilter())
logging.root.setLevel(logging.INFO)
logging.root.addHandler(_log_handler)

logger = logging.getLogger(__name__)

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
app.add_middleware(RequestIDMiddleware)

app.include_router(auth_router)
app.include_router(auth_2fa_router)
app.include_router(auth_oauth_router)
app.include_router(auth_reset_router)
app.include_router(auth_session_router)
app.include_router(prendas_router)
app.include_router(ws_router)
app.include_router(modelos_ia_router)
app.include_router(generaciones_router)
app.include_router(media_router)
app.include_router(pose_sets_router)
app.include_router(models_router)
app.include_router(vton_router)
app.include_router(tryoff_router)
app.include_router(catalogo_router)
app.include_router(customers_router)
app.include_router(portal_router)
app.include_router(batches_router)
app.include_router(tenant_router)
app.include_router(admin_router)
app.include_router(buyer_links_router)
app.include_router(buyer_links_validate_router)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Demasiados intentos. Inténtalo de nuevo en un minuto."},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/.well-known/jwks.json", tags=["auth"])
async def jwks_endpoint():
    """Public JWKS endpoint for RS256 public key distribution.

    Returns the active public key in JWK format for downstream
    service token verification (ADR-026).
    """
    from services.jwks_manager import get_jwks_response

    return get_jwks_response()


@app.on_event("startup")
async def startup_event():
    logger.info("Email backend: %s", email_backend_status())
    if resend_api_key_is_configured() and use_console_email_backend():
        logger.warning(
            "RESEND_API_KEY is set but EMAIL_BACKEND=console — no emails will reach inboxes."
        )
    try:
        from core.minio_buckets import ensure_minio_buckets

        await ensure_minio_buckets()
    except Exception:
        pass
