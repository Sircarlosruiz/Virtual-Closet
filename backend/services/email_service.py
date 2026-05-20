import asyncio
import logging

import resend

from core.config import settings

logger = logging.getLogger(__name__)

resend.api_key = settings.RESEND_API_KEY


async def send_welcome_email(email: str, nombre_negocio: str) -> None:
    """Send welcome email to new mayorista. Non-blocking."""

    def _send():
        try:
            resend.Emails.send(
                {
                    "from": "Virtual Closet <onboarding@resend.dev>",
                    "to": email,
                    "subject": f"Bienvenido a Virtual Closet, {nombre_negocio}!",
                    "html": f"""
                    <h1>Bienvenido a Virtual Closet!</h1>
                    <p>Hola {nombre_negocio},</p>
                    <p>Tu cuenta ha sido creada exitosamente. Tienes 30 días de prueba gratis.</p>
                    <p>Comienza subiendo tu primera prenda y genera fotos profesionales con IA.</p>
                    """,
                }
            )
            logger.info(f"Welcome email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {e}")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send)
