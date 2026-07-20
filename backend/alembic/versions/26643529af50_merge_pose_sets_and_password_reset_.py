"""merge pose_sets and password_reset_tokens branches

Revision ID: 26643529af50
Revises: c7d8e9f0a1b2, d2e3f4a5b6c7
Create Date: 2026-07-20 11:28:58.735235

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26643529af50'
down_revision: Union[str, Sequence[str], None] = ('c7d8e9f0a1b2', 'd2e3f4a5b6c7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
