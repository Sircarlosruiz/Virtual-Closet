"""Repository for BackupCode persistence."""

import uuid
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.two_factor import BackupCode


class BackupCodeRepository:
    """Data access for BackupCode entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_batch(
        self, mayorista_id: uuid.UUID, code_plaintexts: list[str]
    ) -> list[BackupCode]:
        """Create multiple backup codes, hashing each with bcrypt."""
        codes = []
        for plaintext in code_plaintexts:
            code_hash = bcrypt.hashpw(
                plaintext.encode("utf-8"), bcrypt.gensalt(rounds=12)
            ).decode("utf-8")
            codes.append(
                BackupCode(
                    mayorista_id=mayorista_id,
                    code_hash=code_hash,
                )
            )
        self.session.add_all(codes)
        await self.session.commit()
        for code in codes:
            await self.session.refresh(code)
        return codes

    async def verify_and_consume(
        self, mayorista_id: uuid.UUID, code_plaintext: str
    ) -> bool:
        """Verify a backup code and mark it as used if valid.

        Returns True if the code was valid and consumed, False otherwise.
        """
        unused = await self._get_unused_codes(mayorista_id)
        for backup_code in unused:
            if bcrypt.checkpw(
                code_plaintext.encode("utf-8"),
                backup_code.code_hash.encode("utf-8"),
            ):
                # Mark as used
                await self.session.execute(
                    update(BackupCode)
                    .where(BackupCode.id == backup_code.id)
                    .values(
                        used=True,
                        used_at=datetime.now(timezone.utc),
                    )
                )
                await self.session.commit()
                return True
        return False

    async def count_remaining(self, mayorista_id: uuid.UUID) -> int:
        """Count unused backup codes for a user."""
        result = await self.session.execute(
            select(BackupCode)
            .where(
                BackupCode.mayorista_id == mayorista_id,
                BackupCode.used.is_(False),
            )
        )
        return len(result.scalars().all())

    async def get_all_unused(
        self, mayorista_id: uuid.UUID
    ) -> list[BackupCode]:
        """Get all unused backup codes for a user."""
        result = await self.session.execute(
            select(BackupCode)
            .where(
                BackupCode.mayorista_id == mayorista_id,
                BackupCode.used.is_(False),
            )
        )
        return list(result.scalars().all())

    async def _get_unused_codes(
        self, mayorista_id: uuid.UUID
    ) -> list[BackupCode]:
        """Internal: get unused codes for verification."""
        result = await self.session.execute(
            select(BackupCode)
            .where(
                BackupCode.mayorista_id == mayorista_id,
                BackupCode.used.is_(False),
            )
        )
        return list(result.scalars().all())
