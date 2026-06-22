"""financial safety fingerprints

Revision ID: 0003_financial_safety
Revises: 0002_hardening
Create Date: 2026-06-21
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_financial_safety"
down_revision = "0002_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("data_quality_issues", sa.Column("fingerprint", sa.String(length=64), nullable=True))
    op.create_index("ix_data_quality_issues_fingerprint", "data_quality_issues", ["fingerprint"])


def downgrade() -> None:
    op.drop_index("ix_data_quality_issues_fingerprint", table_name="data_quality_issues")
    op.drop_column("data_quality_issues", "fingerprint")
