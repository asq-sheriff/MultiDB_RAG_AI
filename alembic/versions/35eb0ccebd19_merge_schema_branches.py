"""merge schema branches

Revision ID: 35eb0ccebd19
Revises: 001_query_embeddings, da4078a66da6
Create Date: 2025-09-03 19:37:52.155245

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35eb0ccebd19'
down_revision: Union[str, Sequence[str], None] = ('001_query_embeddings', 'da4078a66da6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
