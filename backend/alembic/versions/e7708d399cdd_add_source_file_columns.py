"""add_source_file_columns

Revision ID: e7708d399cdd
Revises: 5dd82151203b
Create Date: 2026-09-23 18:55:50.989371

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7708d399cdd'
down_revision: Union[str, Sequence[str], None] = '5dd82151203b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('reports', sa.Column('source_file_name', sa.String(length=255), nullable=True))
    op.add_column('reports', sa.Column('source_file_path', sa.String(length=255), nullable=True))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('reports', 'source_file_path')
    op.drop_column('reports', 'source_file_name')
