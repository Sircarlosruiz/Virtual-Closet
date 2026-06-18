import logging
import uuid
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from core.security import create_access_token, decode_access_token

logger = logging.getLogger(__name__)

REFRESH_THRESHOLD_HOURS = 24


class TokenRefreshMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        access_token = request.cookies.get("access_token")
        if not access_token:
            return response

        payload = decode_access_token(access_token)
        if not payload:
            return response

        exp = payload.get("exp")
        if not exp:
            return response

        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        time_until_expiry = exp_datetime - now

        if time_until_expiry < timedelta(hours=REFRESH_THRESHOLD_HOURS):
            mayorista_id = payload.get("sub")
            if mayorista_id:
                new_token = create_access_token(mayorista_id)
                response.set_cookie(
                    key="access_token",
                    value=new_token,
                    httponly=True,
                    samesite="lax",
                    secure=settings.COOKIE_SECURE,
                    max_age=604800,
                )
                logger.debug("Token refreshed automatically")

        return response


_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Return the current request ID, or '-' outside a request context."""
    return _request_id_var.get()


class RequestIDFilter(logging.Filter):
    """Injects the current request ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()  # type: ignore[attr-defined]
        return True


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = _request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            _request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response
