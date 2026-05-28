import logging

import pytest

from core.config import resend_api_key_is_configured, settings, use_console_email_backend
from services import email_service


class TestEmailConfiguration:
    def test_placeholder_key_is_not_configured(self, monkeypatch):
        monkeypatch.setattr(
            settings,
            "RESEND_API_KEY",
            "re_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        )
        assert resend_api_key_is_configured() is False

    def test_real_key_prefix_is_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "RESEND_API_KEY", "re_abc123realkey")
        assert resend_api_key_is_configured() is True

    def test_console_backend_flag(self, monkeypatch):
        monkeypatch.setattr(settings, "EMAIL_BACKEND", "console")
        assert use_console_email_backend() is True


@pytest.mark.asyncio
async def test_invitation_logs_dev_link_when_console_backend(monkeypatch, caplog):
    monkeypatch.setattr(settings, "EMAIL_BACKEND", "console")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")

    caplog.set_level(logging.WARNING)
    await email_service.send_invitation_email(
        customer_email="test@buyer.com",
        customer_name="Test",
        mayorista_name="Tienda",
        invitation_token="fake.jwt.token",
    )
    assert "[EMAIL DEV]" in caplog.text
    assert "/portal/auth?token=fake.jwt.token" in caplog.text
