"""Repository for SmsOtpRecord persistence."""

import uuid

import bcrypt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.oauth import SmsOtpRecord


class SmsOtpRepository:
    """Data access for SmsOtpRecord entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, mayorista_id: uuid.UUID, otp_hash: str, expires_at
    ) -> SmsOtpRecord:
        """Create a new SMS OTP record, invalidating any existing one."""
        # Invalidate existing OTP for this user
        await self.invalidate(mayorista_id)

        record = SmsOtpRecord(
            mayorista_id=mayorista_id,
            otp_hash=otp_hash,
            expires_at=expires_at,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_active(self, mayorista_id: uuid.UUID) -> SmsOtpRecord | None:
        """Get the active (non-expired) OTP for a user."""
        result = await self.session.execute(
            select(SmsOtpRecord).where(
                SmsOtpRecord.mayorista_id == mayorista_id
            )
        )
        record = result.scalar_one_or_none()
        return record

    async def invalidate(self, mayorista_id: uuid.UUID) -> None:
        """Delete any existing OTP for this user."""
        from sqlalchemy import delete

        stmt = delete(SmsOtpRecord).where(
            SmsOtpRecord.mayorista_id == mayorista_id
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def verify_and_delete(
        self, mayorista_id: uuid.UUID, otp_plaintext: str
    ) -> bool:
        """Verify an OTP and delete it if valid.

        Returns True if the OTP was valid and consumed, False otherwise.
        Increments attempt counter on failure.
        """
        record = await self.get_active(mayorista_id)
        if record is None:
            return False

        # Check attempts limit
        if record.attempts >= 3:
            await self.invalidate(mayorista_id)
            return False

        if bcrypt.checkpw(
            otp_plaintext.encode("utf-8"),
            record.otp_hash.encode("utf-8"),
        ):
            # Valid — delete the record
            await self.invalidate(mayorista_id)
            return True

        # Invalid — increment attempts
        await self.session.execute(
            update(SmsOtpRecord)
            .where(SmsOtpRecord.mayorista_id == mayorista_id)
            .values(attempts=SmsOtpRecord.attempts + 1)
        )
        await self.session.commit()
        return False
