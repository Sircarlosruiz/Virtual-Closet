"""create publication_selections, sync_deliveries, and product_images

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-18 16:18:29.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "publication_selections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "product_link_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_links.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "generation_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generation_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "composition_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("composition_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decision", sa.Text, nullable=False),
        sa.Column(
            "selected_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mayorista.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "mayorista_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mayorista.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "decision IN ('selected', 'discarded')",
            name="ck_publication_selections_decision",
        ),
    )
    op.create_index(
        "idx_publication_selections_link",
        "publication_selections",
        ["product_link_id"],
    )
    op.create_index(
        "idx_publication_selections_job",
        "publication_selections",
        ["generation_job_id"],
    )
    op.create_index(
        "idx_publication_selections_tenant",
        "publication_selections",
        ["tenant_id"],
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_publication_selections_candidate
        ON publication_selections (
            product_link_id, generation_job_id, composition_version_id
        )
        NULLS NOT DISTINCT
        """
    )

    op.create_table(
        "sync_deliveries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "publication_selection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("publication_selections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("destination", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column(
            "retryable", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("external_ref", sa.Text, nullable=True),
        sa.Column("durable_object_key", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "publication_selection_id",
            "destination",
            name="uq_sync_deliveries_selection_destination",
        ),
        sa.CheckConstraint(
            "destination IN ('virtual_closet', 'bfashion')",
            name="ck_sync_deliveries_destination",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'synced', 'failed')",
            name="ck_sync_deliveries_status",
        ),
    )
    op.create_index(
        "idx_sync_deliveries_selection",
        "sync_deliveries",
        ["publication_selection_id"],
    )
    op.create_index("idx_sync_deliveries_status", "sync_deliveries", ["status"])

    op.create_table(
        "product_images",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "product_link_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_links.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prenda_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("prenda.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "publication_selection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("publication_selections.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "generation_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generation_jobs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "composition_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("composition_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "mayorista_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mayorista.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("minio_key", sa.Text, nullable=False),
        sa.Column("configuration", postgresql.JSONB, nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "publication_selection_id",
            name="uq_product_images_publication_selection",
        ),
    )
    op.create_index("idx_product_images_link", "product_images", ["product_link_id"])
    op.create_index("idx_product_images_tenant", "product_images", ["tenant_id"])
    op.create_index(
        "idx_product_images_link_created",
        "product_images",
        ["product_link_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_product_images_link_created", table_name="product_images")
    op.drop_index("idx_product_images_tenant", table_name="product_images")
    op.drop_index("idx_product_images_link", table_name="product_images")
    op.drop_table("product_images")
    op.drop_index("idx_sync_deliveries_status", table_name="sync_deliveries")
    op.drop_index("idx_sync_deliveries_selection", table_name="sync_deliveries")
    op.drop_table("sync_deliveries")
    op.execute("DROP INDEX IF EXISTS uq_publication_selections_candidate")
    op.drop_index(
        "idx_publication_selections_tenant", table_name="publication_selections"
    )
    op.drop_index("idx_publication_selections_job", table_name="publication_selections")
    op.drop_index(
        "idx_publication_selections_link", table_name="publication_selections"
    )
    op.drop_table("publication_selections")
