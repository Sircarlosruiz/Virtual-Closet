"""create_prenda_table

Revision ID: 4d14008659c2
Revises: de3f021d6d3c
Create Date: 2026-05-20 09:58:54.310338

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d14008659c2'
down_revision: Union[str, Sequence[str], None] = 'de3f021d6d3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('prenda',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('mayorista_id', sa.UUID(), nullable=False),
    sa.Column('nombre', sa.String(length=80), nullable=False),
    sa.Column('imagen_original_url', sa.Text(), nullable=False),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['mayorista_id'], ['mayorista.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_prenda_mayorista_created', 'prenda', ['mayorista_id', 'created_at'], unique=False)
    op.create_index('idx_prenda_mayorista_id', 'prenda', ['mayorista_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_prenda_mayorista_id', table_name='prenda')
    op.drop_index('idx_prenda_mayorista_created', table_name='prenda')
    op.drop_table('prenda')
