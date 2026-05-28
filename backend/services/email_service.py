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


async def send_invitation_email(
    customer_email: str,
    customer_name: str,
    mayorista_name: str,
    invitation_token: str,
) -> None:
    """Send invitation email with signed link."""
    invitation_url = f"{settings.FRONTEND_URL}/portal/auth?token={invitation_token}"

    def _send():
        try:
            resend.Emails.send(
                {
                    "from": "Virtual Closet <onboarding@resend.dev>",
                    "to": customer_email,
                    "subject": f"{mayorista_name} te ha invitado a Virtual Closet",
                    "html": f"""
                    <h1>¡Has sido invitado!</h1>
                    <p>Hola {customer_name},</p>
                    <p>{mayorista_name} te ha invitado a ver sus catálogos en Virtual Closet.</p>
                    <p><a href="{invitation_url}">Haz clic aquí para acceder</a></p>
                    <p>Este enlace expira en 7 días.</p>
                    """,
                }
            )
            logger.info(f"Invitation email sent to {customer_email}")
        except Exception as e:
            logger.error(f"Failed to send invitation email to {customer_email}: {e}")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send)


async def send_magic_link_email(
    customer_email: str,
    customer_name: str,
    magic_link_token: str,
) -> None:
    """Send magic-link email for re-authentication."""
    magic_link_url = f"{settings.FRONTEND_URL}/portal/auth?token={magic_link_token}"

    def _send():
        try:
            resend.Emails.send(
                {
                    "from": "Virtual Closet <onboarding@resend.dev>",
                    "to": customer_email,
                    "subject": "Tu enlace de acceso a Virtual Closet",
                    "html": f"""
                    <h1>Tu enlace de acceso</h1>
                    <p>Hola {customer_name},</p>
                    <p><a href="{magic_link_url}">Haz clic aquí para acceder</a></p>
                    <p>Este enlace expira en 15 minutos.</p>
                    """,
                }
            )
            logger.info(f"Magic link email sent to {customer_email}")
        except Exception as e:
            logger.error(f"Failed to send magic link email to {customer_email}: {e}")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send)
