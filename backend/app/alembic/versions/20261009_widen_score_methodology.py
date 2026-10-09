"""Allow the full scoring methodology identifier."""
import sqlalchemy as sa
from alembic import op

revision = "20261009_score_width"
down_revision = "1ba9c6be8bf2"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("audits", "score_methodology", existing_type=sa.String(32), type_=sa.String(128))


def downgrade():
    # Refuse truncation rather than silently corrupt saved methodology values.
    op.alter_column("audits", "score_methodology", existing_type=sa.String(128), type_=sa.String(32))
