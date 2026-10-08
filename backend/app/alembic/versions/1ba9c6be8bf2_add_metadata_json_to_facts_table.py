"""Add metadata_json to facts table

Revision ID: 1ba9c6be8bf2
Revises: ed8ab675548d
Create Date: 2026-10-09 03:23:21.843828

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '1ba9c6be8bf2'
down_revision = 'ed8ab675548d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('facts', sa.Column('metadata_json', sa.Text(), nullable=False, server_default='{}'))


def downgrade():
    op.drop_column('facts', 'metadata_json')