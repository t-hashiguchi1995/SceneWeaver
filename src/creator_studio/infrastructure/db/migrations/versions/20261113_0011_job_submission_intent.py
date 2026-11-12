"""Persist submission intent + correlation key before external submit.

A crash before prompt_id save can then be reconciled instead of resubmitted.
"""
import sqlalchemy as sa
from alembic import op

revision = "20261113_0011"
down_revision = "20261113_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("submission_intent_json", sa.Text, nullable=True))
    op.add_column("jobs", sa.Column("submission_correlation_key", sa.String(256), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "submission_correlation_key")
    op.drop_column("jobs", "submission_intent_json")
