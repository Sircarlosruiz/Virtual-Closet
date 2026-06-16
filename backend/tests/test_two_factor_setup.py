"""Unit tests for TwoFactorSetupService.

Tests TOTP setup, SMS setup, backup code generation, and confirmation flows.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from services.two_factor_setup_service import (
    TwoFactorSetupService,
    TwoFactorAlreadyConfiguredError,
    InvalidOtpCodeError,
    InvalidPhoneNumberError,
)
from models.two_factor import TwoFactorConfig


@pytest.fixture
def mock_two_factor_repo():
    repo = AsyncMock()
    repo.get_by_mayorista_id = AsyncMock(return_value=None)
    repo.create = AsyncMock(side_effect=lambda c: c)
    repo.update = AsyncMock(side_effect=lambda c: c)
    repo.mark_configured = AsyncMock()
    return repo


@pytest.fixture
def mock_backup_code_repo():
    repo = AsyncMock()
    repo.create_batch = AsyncMock()
    return repo


@pytest.fixture
def mock_sms_otp_service():
    service = AsyncMock()
    service.send_otp = AsyncMock(return_value=True)
    service.verify_otp = AsyncMock(return_value=True)
    return service


@pytest.fixture
def service(mock_two_factor_repo, mock_backup_code_repo, mock_sms_otp_service):
    return TwoFactorSetupService(
        two_factor_repo=mock_two_factor_repo,
        backup_code_repo=mock_backup_code_repo,
        sms_otp_service=mock_sms_otp_service,
    )


class TestInitiateTotpSetup:
    @pytest.mark.asyncio
    async def test_returns_totp_secret_and_backup_codes(self, service, mock_two_factor_repo):
        mayorista_id = uuid.uuid4()
        result = await service.initiate_totp_setup(mayorista_id, "test@example.com")

        assert "totp_secret" in result
        assert "otpauth_uri" in result
        assert "backup_codes" in result
        assert len(result["backup_codes"]) == 8
        assert "otpauth://totp/" in result["otpauth_uri"]
        assert "Virtual Closet" in result["otpauth_uri"]

    @pytest.mark.asyncio
    async def test_raises_if_already_configured(self, service, mock_two_factor_repo):
        mock_two_factor_repo.get_by_mayorista_id = AsyncMock(
            return_value=TwoFactorConfig(mayorista_id=uuid.uuid4(), is_configured=True)
        )
        with pytest.raises(TwoFactorAlreadyConfiguredError):
            await service.initiate_totp_setup(uuid.uuid4(), "test@example.com")

    @pytest.mark.asyncio
    async def test_stores_encrypted_secret(self, service, mock_two_factor_repo):
        mayorista_id = uuid.uuid4()
        await service.initiate_totp_setup(mayorista_id, "test@example.com")

        mock_two_factor_repo.create.assert_called_once()
        config = mock_two_factor_repo.create.call_args[0][0]
        assert config.mayorista_id == mayorista_id
        assert config.totp_secret_encrypted is not None
        assert config.method == "totp"


class TestConfirmTotpSetup:
    @pytest.mark.asyncio
    async def test_confirms_with_valid_code(self, service, mock_two_factor_repo):
        mayorista_id = uuid.uuid4()
        # First initiate to store secret
        init_result = await service.initiate_totp_setup(mayorista_id, "test@example.com")
        totp_secret = init_result["totp_secret"]

        # Mock get to return the config with secret
        import pyotp

        totp = pyotp.TOTP(totp_secret)
        valid_code = totp.now()

        from core.security import encrypt_value

        mock_two_factor_repo.get_by_mayorista_id = AsyncMock(
            return_value=TwoFactorConfig(
                mayorista_id=mayorista_id,
                totp_secret_encrypted=encrypt_value(totp_secret),
                is_configured=False,
            )
        )

        result = await service.confirm_totp_setup(mayorista_id, valid_code)

        assert result["configured"] is True
        assert result["method"] == "totp"
        assert result["backup_codes_remaining"] == 8

    @pytest.mark.asyncio
    async def test_raises_if_already_configured(self, service, mock_two_factor_repo):
        from core.security import encrypt_value

        mock_two_factor_repo.get_by_mayorista_id = AsyncMock(
            return_value=TwoFactorConfig(
                mayorista_id=uuid.uuid4(),
                totp_secret_encrypted=encrypt_value("JBSWY3DPEHPK3PXP"),
                is_configured=True,
            )
        )
        with pytest.raises(TwoFactorAlreadyConfiguredError):
            await service.confirm_totp_setup(uuid.uuid4(), "123456")


class TestInitiateSmsSetup:
    @pytest.mark.asyncio
    async def test_sends_otp_with_valid_phone(self, service, mock_two_factor_repo, mock_sms_otp_service):
        mayorista_id = uuid.uuid4()
        result = await service.initiate_sms_setup(mayorista_id, "+50588881234")

        assert result["otp_sent"] is True
        assert "****" in result["phone_number"]
        mock_sms_otp_service.send_otp.assert_called_once_with(mayorista_id, "+50588881234")

    @pytest.mark.asyncio
    async def test_raises_on_invalid_phone(self, service):
        with pytest.raises(InvalidPhoneNumberError):
            await service.initiate_sms_setup(uuid.uuid4(), "invalid-phone")

    @pytest.mark.asyncio
    async def test_raises_if_already_configured(self, service, mock_two_factor_repo):
        mock_two_factor_repo.get_by_mayorista_id = AsyncMock(
            return_value=TwoFactorConfig(mayorista_id=uuid.uuid4(), is_configured=True)
        )
        with pytest.raises(TwoFactorAlreadyConfiguredError):
            await service.initiate_sms_setup(uuid.uuid4(), "+50588881234")


class TestBackupCodeGeneration:
    def test_generates_8_codes(self, service):
        codes = service._generate_backup_codes()
        assert len(codes) == 8

    def test_codes_are_8_chars(self, service):
        codes = service._generate_backup_codes()
        for code in codes:
            assert len(code) == 8

    def test_codes_are_unique(self, service):
        codes = service._generate_backup_codes()
        assert len(set(codes)) == 8  # all unique

    def test_codes_use_safe_chars(self, service):
        codes = service._generate_backup_codes()
        safe_chars = set("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        for code in codes:
            assert all(c in safe_chars for c in code)


class TestPhoneMasking:
    def test_masks_last_4_digits(self, service):
        assert service._mask_phone("+50588881234") == "+5058888****"

    def test_handles_short_numbers(self, service):
        assert service._mask_phone("+1234") == "+1****"
