"""partial unique index for photoshoot idempotency keys

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-09-19 17:02:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY product_link_id, idempotency_key
                       ORDER BY created_at ASC, id ASC
                   ) AS rn
            FROM photoshoots
            WHERE idempotency_key IS NOT NULL
        )
        UPDATE photoshoots AS p
        SET idempotency_key = NULL,
            payload_fingerprint = NULL
        FROM ranked
        WHERE p.id = ranked.id
          AND ranked.rn > 1
        """
    )
    op.create_index(
        "uq_photoshoots_link_idempotency",
        "photoshoots",
        ["product_link_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_photoshoots_link_idempotency",
        table_name="photoshoots",
    )
