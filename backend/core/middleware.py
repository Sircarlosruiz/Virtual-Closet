import logging
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
