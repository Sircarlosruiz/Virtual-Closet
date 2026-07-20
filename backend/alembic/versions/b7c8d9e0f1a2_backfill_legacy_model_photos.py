"""Backfill legacy model photos into one-photo Model wrappers.

Revision ID: b7c8d9e0f1a2
Revises: f1e2d3c4b5a6
Create Date: 2026-07-18 05:26:38.000000

The migration is intentionally data-only and idempotent. A legacy row is
selected only while model_id is NULL, and model_id plus pose are linked in one
UPDATE so the coupling constraint from ADR-012 is always satisfied.
"""
from __future__ import annotations

import logging
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "f1e2d3c4b5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BATCH_SIZE = 500
logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    """Create one front-pose Model wrapper for every legacy model photo."""
    bind = op.get_bind()
    rows_backfilled = 0
    batches = 0

    while True:
        rows = bind.execute(
            sa.text(
                """
                SELECT id, mayorista_id, label
                FROM model_photos
                WHERE is_curated = false
                  AND model_id IS NULL
                  AND mayorista_id IS NOT NULL
                ORDER BY uploaded_at, id
                LIMIT :batch_size
                """
            ),
            {"batch_size": BATCH_SIZE},
        ).mappings().all()

        if not rows:
            break

        batch_count = 0
        for row in rows:
            model_id = uuid.uuid4()
            label = (row["label"] or "Legacy Model")[:255]

            bind.execute(
                sa.text(
                    """
                    INSERT INTO models (id, mayorista_id, name, created_at)
                    VALUES (:id, :mayorista_id, :name, now())
                    """
                ),
                {
                    "id": model_id,
                    "mayorista_id": row["mayorista_id"],
                    "name": label,
                },
            )

            linked = bind.execute(
                sa.text(
                    """
                    UPDATE model_photos
                    SET model_id = :model_id, pose = 'front'
                    WHERE id = :photo_id
                      AND model_id IS NULL
                    """
                ),
                {"model_id": model_id, "photo_id": row["id"]},
            )

            if linked.rowcount:
                batch_count += 1
                logger.debug(
                    "LegacyModelPhotoBackfilled photo_id=%s model_id=%s",
                    row["id"],
                    model_id,
                )
            else:
                # Another writer linked the row between selection and update.
                # Do not leave an unreferenced wrapper behind.
                bind.execute(
                    sa.text("DELETE FROM models WHERE id = :model_id"),
                    {"model_id": model_id},
                )

        batches += 1
        rows_backfilled += batch_count
        logger.info(
            "Legacy model photo backfill batch=%s rows=%s",
            batches,
            batch_count,
        )

    orphaned = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM model_photos
            WHERE is_curated = false
              AND model_id IS NULL
              AND mayorista_id IS NULL
            """
        )
    ).scalar_one()
    logger.info(
        "BackfillCompleted rows_backfilled=%s batches=%s rows_skipped_orphaned=%s",
        rows_backfilled,
        batches,
        orphaned,
    )


def downgrade() -> None:
    """Intentionally irreversible; see ADR-041."""
    # Wrapper Models are indistinguishable from user-created single-pose
    # Models. Never unlink/delete data automatically during schema rollback.
    pass
