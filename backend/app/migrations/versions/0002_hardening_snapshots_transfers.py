"""hardening snapshots and transfer members

Revision ID: 0002_hardening
Revises: 0001_initial
Create Date: 2026-06-21
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_hardening"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_app_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("net_worth_cents", sa.Integer(), nullable=True),
        sa.Column("assets_cents", sa.Integer(), nullable=True),
        sa.Column("liabilities_cents", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("warnings_json", sa.JSON(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("snapshot_date", name="uq_daily_app_snapshot_date"),
    )
    op.create_table(
        "transfer_link_members",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("transfer_link_id", sa.String(length=36), sa.ForeignKey("transfer_links.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_id", sa.String(length=36), sa.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("staged_row_id", sa.String(length=36), sa.ForeignKey("staged_import_rows.id", ondelete="SET NULL"), nullable=True),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("side", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("transfer_link_id", "transaction_id", name="uq_transfer_link_transaction_member"),
        sa.UniqueConstraint("transfer_link_id", "staged_row_id", name="uq_transfer_link_staged_member"),
    )

    # The original scaffold accidentally made staged normalized hashes unique.
    # Rebuild the table without that constraint so true duplicate rows can be staged and reviewed.
    op.create_table(
        "staged_import_rows_rebuild",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("import_batch_id", sa.String(length=36), sa.ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_json", sa.JSON(), nullable=False),
        sa.Column("normalized_json", sa.JSON(), nullable=False),
        sa.Column("normalized_hash", sa.String(length=64), nullable=False),
        sa.Column("validation_status", sa.String(length=50), nullable=False),
        sa.Column("duplicate_status", sa.String(length=50), nullable=False),
        sa.Column("transfer_status", sa.String(length=50), nullable=False),
        sa.Column("user_action", sa.String(length=50), nullable=False),
        sa.Column("final_record_type", sa.String(length=50), nullable=True),
        sa.Column("final_record_id", sa.String(length=36), nullable=True),
        sa.Column("errors_json", sa.JSON(), nullable=True),
        sa.Column("warnings_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        """
        INSERT INTO staged_import_rows_rebuild (
            id, import_batch_id, row_number, raw_json, normalized_json, normalized_hash,
            validation_status, duplicate_status, transfer_status, user_action,
            final_record_type, final_record_id, errors_json, warnings_json, created_at
        )
        SELECT
            id, import_batch_id, row_number, raw_json, normalized_json, normalized_hash,
            validation_status, duplicate_status, transfer_status, user_action,
            final_record_type, final_record_id, errors_json, warnings_json, created_at
        FROM staged_import_rows
        """
    )
    op.drop_table("staged_import_rows")
    op.rename_table("staged_import_rows_rebuild", "staged_import_rows")


def downgrade() -> None:
    op.drop_table("transfer_link_members")
    op.drop_table("daily_app_snapshots")
