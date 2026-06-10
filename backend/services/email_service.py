import asyncio
import logging

import resend

from core.config import resend_api_key_is_configured, settings, use_console_email_backend

logger = logging.getLogger(__name__)

resend.api_key = settings.RESEND_API_KEY


def _should_use_resend() -> bool:
    if not resend_api_key_is_configured():
        return False
    if use_console_email_backend():
        logger.warning(
            "EMAIL_BACKEND=console — emails are NOT sent via Resend. "
            "Set EMAIL_BACKEND=resend in backend/.env to deliver to inbox."
        )
        return False
    return True


def _log_dev_email(kind: str, to: str, url: str) -> None:
    """Print invitation/magic-link URLs when email is not sent via Resend."""
    logger.warning(
        "[EMAIL DEV] %s not sent via Resend (backend=%s, resend_key=%s). "
        "Open this link as %s:\n  %s",
        kind,
        settings.EMAIL_BACKEND,
        "configured" if resend_api_key_is_configured() else "missing/placeholder",
        to,
        url,
    )


async def _run_send(fn) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, fn)


async def send_welcome_email(email: str, nombre_negocio: str) -> None:
    """Send welcome email to new mayorista. Non-blocking."""

    def _send():
        if not _should_use_resend():
            logger.info(
                "[EMAIL DEV] Welcome email skipped for %s (%s)",
                email,
                nombre_negocio,
            )
            return
        try:
            resend.Emails.send(
                {
                    "from": settings.RESEND_FROM_EMAIL,
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
            logger.info("Welcome email sent to %s", email)
        except Exception as e:
            logger.error("Failed to send welcome email to %s: %s", email, e)

    await _run_send(_send)


async def send_invitation_email(
    customer_email: str,
    customer_name: str,
    mayorista_name: str,
    invitation_token: str,
) -> None:
    """Send invitation email with signed link."""
    invitation_url = f"{settings.FRONTEND_URL}/portal/auth?token={invitation_token}"

    def _send():
        if not _should_use_resend():
            _log_dev_email("Invitation", customer_email, invitation_url)
            return
        try:
            resend.Emails.send(
                {
                    "from": settings.RESEND_FROM_EMAIL,
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
            logger.info("Invitation email sent to %s", customer_email)
        except Exception as e:
            logger.error(
                "Failed to send invitation email to %s: %s — dev link: %s",
                customer_email,
                e,
                invitation_url,
            )

    await _run_send(_send)


async def send_magic_link_email(
    customer_email: str,
    customer_name: str,
    magic_link_token: str,
) -> None:
    """Send magic-link email for re-authentication."""
    magic_link_url = f"{settings.FRONTEND_URL}/portal/auth?token={magic_link_token}"

    def _send():
        if not _should_use_resend():
            _log_dev_email("Magic link", customer_email, magic_link_url)
            return
        try:
            resend.Emails.send(
                {
                    "from": settings.RESEND_FROM_EMAIL,
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
            logger.info("Magic link email sent to %s", customer_email)
        except Exception as e:
            logger.error(
                "Failed to send magic link email to %s: %s — dev link: %s",
                customer_email,
                e,
                magic_link_url,
            )

    await _run_send(_send)


async def send_admin_invitation_email(
    email: str,
    tenant_name: str,
    invitation_token: str,
) -> None:
    """Send admin invitation email with registration link."""
    invitation_url = (
        f"{settings.FRONTEND_URL}/auth/accept-invitation?token={invitation_token}"
    )

    def _send():
        if not _should_use_resend():
            _log_dev_email("Admin invitation", email, invitation_url)
            return
        try:
            resend.Emails.send(
                {
                    "from": settings.RESEND_FROM_EMAIL,
                    "to": email,
                    "subject": f"Has sido invitado como administrador a {tenant_name}",
                    "html": f"""
                    <h1>Invitación de administrador</h1>
                    <p>Has sido invitado como administrador de <strong>{tenant_name}</strong> en Virtual Closet.</p>
                    <p><a href="{invitation_url}">Haz clic aquí para aceptar la invitación y crear tu cuenta</a></p>
                    <p>Este enlace expira en 7 días.</p>
                    """,
                }
            )
            logger.info("Admin invitation email sent to %s", email)
        except Exception as e:
            logger.error(
                "Failed to send admin invitation email to %s: %s — dev link: %s",
                email,
                e,
                invitation_url,
            )

    await _run_send(_send)


async def send_verification_email(
    email: str,
    business_name: str,
    verification_url: str,
) -> None:
    """Send email verification link."""

    def _send():
        if not _should_use_resend():
            _log_dev_email("Verification", email, verification_url)
            return
        try:
            resend.Emails.send(
                {
                    "from": settings.RESEND_FROM_EMAIL,
                    "to": email,
                    "subject": "Verifica tu email en Virtual Closet",
                    "html": f"""
                    <h1>Verifica tu email</h1>
                    <p>Hola {business_name},</p>
                    <p>Gracias por registrarte en Virtual Closet. Para activar tu cuenta, haz clic en el siguiente enlace:</p>
                    <p><a href="{verification_url}">Verificar mi email</a></p>
                    <p>Este enlace expira en 24 horas.</p>
                    <p>Si no creaste esta cuenta, puedes ignorar este email.</p>
                    """,
                }
            )
            logger.info("Verification email sent to %s", email)
        except Exception as e:
            logger.error(
                "Failed to send verification email to %s: %s — dev link: %s",
                email,
                e,
                verification_url,
            )

    await _run_send(_send)


async def send_unlock_email(
    email: str,
    unlock_url: str,
) -> None:
    """Send account unlock link after lockout."""

    def _send():
        if not _should_use_resend():
            _log_dev_email("Unlock", email, unlock_url)
            return
        try:
            resend.Emails.send(
                {
                    "from": settings.RESEND_FROM_EMAIL,
                    "to": email,
                    "subject": "Tu cuenta ha sido bloqueada — Instrucciones de desbloqueo",
                    "html": f"""
                    <h1>Cuenta bloqueada</h1>
                    <p>Tu cuenta ha sido bloqueada debido a múltiples intentos fallidos de inicio de sesión.</p>
                    <p>Para desbloquear tu cuenta, haz clic en el siguiente enlace:</p>
                    <p><a href="{unlock_url}">Desbloquear mi cuenta</a></p>
                    <p>Este enlace expira en 24 horas.</p>
                    <p>Si no intentaste iniciar sesión, tu contraseña podría estar comprometida. Considera cambiarla después de desbloquear.</p>
                    """,
                }
            )
            logger.info("Unlock email sent to %s", email)
        except Exception as e:
            logger.error(
                "Failed to send unlock email to %s: %s — dev link: %s",
                email,
                e,
                unlock_url,
            )

    await _run_send(_send)
