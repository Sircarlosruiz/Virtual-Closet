"""merge media and batch job branches

Revision ID: 0c2cff14de00
Revises: a3b4c5d6e7f8, a8b9c0d1e2f3
Create Date: 2026-06-05 10:38:48.682099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c2cff14de00'
down_revision: Union[str, Sequence[str], None] = ('a3b4c5d6e7f8', 'a8b9c0d1e2f3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
