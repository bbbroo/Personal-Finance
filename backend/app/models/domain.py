from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    institution: Mapped[str | None] = mapped_column(String(200))
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)
    account_subtype: Mapped[str | None] = mapped_column(String(100))
    valuation_method: Mapped[str] = mapped_column(String(50), nullable=False)
    balance_sign_policy: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    include_in_net_worth: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    include_in_budget: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    include_in_cash_flow: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    data_source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    freshness_threshold_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    balances: Mapped[list[AccountBalanceSnapshot]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    transactions: Mapped[list[Transaction]] = relationship(back_populates="account")
    holdings: Mapped[list[HoldingSnapshot]] = relationship(back_populates="account")


class AccountBalanceSnapshot(Base, TimestampMixin):
    __tablename__ = "account_balance_snapshots"
    __table_args__ = (
        UniqueConstraint("account_id", "snapshot_date", "balance_kind", "source_id", name="uq_balance_lineage"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    balance_cents: Mapped[int | None] = mapped_column(Integer)
    balance_kind: Mapped[str] = mapped_column(String(50), nullable=False, default="current")
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    source_id: Mapped[str | None] = mapped_column(String(100))
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    account: Mapped[Account] = relationship(back_populates="balances")


class CategoryGroup(Base):
    __tablename__ = "category_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    group_type: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    categories: Mapped[list[Category]] = relationship(back_populates="group")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    group_id: Mapped[str] = mapped_column(ForeignKey("category_groups.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category_type: Mapped[str] = mapped_column(String(50), nullable=False)
    budget_behavior: Mapped[str] = mapped_column(String(50), nullable=False, default="budgeted")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    group: Mapped[CategoryGroup] = relationship(back_populates="categories")


class TransferLink(Base):
    __tablename__ = "transfer_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    confidence_score: Mapped[str] = mapped_column(String(20), nullable=False, default="0")
    match_basis: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="suggested")
    created_by: Mapped[str] = mapped_column(String(50), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    members: Mapped[list[TransferLinkMember]] = relationship(
        back_populates="transfer_link", cascade="all, delete-orphan"
    )


class TransferLinkMember(Base):
    __tablename__ = "transfer_link_members"
    __table_args__ = (
        UniqueConstraint("transfer_link_id", "transaction_id", name="uq_transfer_link_transaction_member"),
        UniqueConstraint("transfer_link_id", "staged_row_id", name="uq_transfer_link_staged_member"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    transfer_link_id: Mapped[str] = mapped_column(ForeignKey("transfer_links.id", ondelete="CASCADE"), nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(ForeignKey("transactions.id", ondelete="SET NULL"))
    staged_row_id: Mapped[str | None] = mapped_column(ForeignKey("staged_import_rows.id", ondelete="SET NULL"))
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    side: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    transfer_link: Mapped[TransferLink] = relationship(back_populates="members")


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("account_id", "fingerprint", name="uq_transaction_fingerprint"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    posted_date: Mapped[date | None] = mapped_column(Date)
    original_description: Mapped[str] = mapped_column(Text, nullable=False)
    merchant_name: Mapped[str | None] = mapped_column(String(255))
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"))
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    transfer_status: Mapped[str] = mapped_column(String(50), nullable=False, default="not_transfer")
    transfer_link_id: Mapped[str | None] = mapped_column(ForeignKey("transfer_links.id"))
    review_status: Mapped[str] = mapped_column(String(50), nullable=False, default="needs_review")
    duplicate_status: Mapped[str] = mapped_column(String(50), nullable=False, default="unique")
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_split: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    source_id: Mapped[str | None] = mapped_column(String(100))
    created_by_import_batch_id: Mapped[str | None] = mapped_column(ForeignKey("import_batches.id"))
    updated_by_import_batch_id: Mapped[str | None] = mapped_column(ForeignKey("import_batches.id"))
    notes: Mapped[str | None] = mapped_column(Text)

    account: Mapped[Account] = relationship(back_populates="transactions")
    splits: Mapped[list[TransactionSplit]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )


class TransactionSplit(Base):
    __tablename__ = "transaction_splits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    transaction: Mapped[Transaction] = relationship(back_populates="splits")


class TransactionRule(Base, TimestampMixin):
    __tablename__ = "transaction_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    match_merchant_contains: Mapped[str | None] = mapped_column(String(200))
    match_description_contains: Mapped[str | None] = mapped_column(String(200))
    match_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"))
    match_amount_min_cents: Mapped[int | None] = mapped_column(Integer)
    match_amount_max_cents: Mapped[int | None] = mapped_column(Integer)
    match_transaction_type: Mapped[str | None] = mapped_column(String(50))
    action_category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"))
    action_merchant_name: Mapped[str | None] = mapped_column(String(200))
    action_tags_json: Mapped[dict | None] = mapped_column(JSON)
    stop_processing: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ImportMappingPreset(Base, TimestampMixin):
    __tablename__ = "import_mapping_presets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    institution: Mapped[str | None] = mapped_column(String(150))
    import_type: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    mapping_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    sign_policy: Mapped[str] = mapped_column(String(80), nullable=False, default="as_is")
    date_format: Mapped[str | None] = mapped_column(String(50))
    amount_format: Mapped[str | None] = mapped_column(String(50))


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    import_type: Mapped[str] = mapped_column(String(50), nullable=False)
    institution: Mapped[str | None] = mapped_column(String(150))
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"))
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_file_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_file_path: Mapped[str | None] = mapped_column(Text)
    mapping_preset_id: Mapped[str | None] = mapped_column(ForeignKey("import_mapping_presets.id"))
    mapping_preset_version: Mapped[int | None] = mapped_column(Integer)
    parser_version: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    committed_record_manifest_json: Mapped[dict | None] = mapped_column(JSON)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    staged_rows: Mapped[list[StagedImportRow]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )


class StagedImportRow(Base):
    __tablename__ = "staged_import_rows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    import_batch_id: Mapped[str] = mapped_column(ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    normalized_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    normalized_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(50), nullable=False, default="valid")
    duplicate_status: Mapped[str] = mapped_column(String(50), nullable=False, default="unique")
    transfer_status: Mapped[str] = mapped_column(String(50), nullable=False, default="not_transfer")
    user_action: Mapped[str] = mapped_column(String(50), nullable=False, default="import")
    final_record_type: Mapped[str | None] = mapped_column(String(50))
    final_record_id: Mapped[str | None] = mapped_column(String(36))
    errors_json: Mapped[list | None] = mapped_column(JSON)
    warnings_json: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    batch: Mapped[ImportBatch] = relationship(back_populates="staged_rows")


class AccountStatement(Base):
    __tablename__ = "account_statements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    opening_balance_cents: Mapped[int | None] = mapped_column(Integer)
    ending_balance_cents: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    import_batch_id: Mapped[str | None] = mapped_column(ForeignKey("import_batches.id"))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    account_statement_id: Mapped[str] = mapped_column(ForeignKey("account_statements.id"), nullable=False)
    calculated_ending_balance_cents: Mapped[int | None] = mapped_column(Integer)
    difference_cents: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    tolerance_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class Instrument(Base, TimestampMixin):
    __tablename__ = "instruments"
    __table_args__ = (UniqueConstraint("symbol", "instrument_type", name="uq_instrument_symbol_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    symbol: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_symbol: Mapped[str | None] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(80))
    cusip_or_isin: Mapped[str | None] = mapped_column(String(80))
    default_asset_class: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    price_provider: Mapped[str | None] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Price(Base):
    __tablename__ = "prices"
    __table_args__ = (UniqueConstraint("instrument_id", "price_date", "provider", name="uq_price_lineage"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    price_decimal: Mapped[str] = mapped_column(String(80), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    provider: Mapped[str | None] = mapped_column(String(100))
    provider_symbol: Mapped[str | None] = mapped_column(String(80))
    market_session: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="current")
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class HoldingSnapshot(Base):
    __tablename__ = "holding_snapshots"
    __table_args__ = (
        UniqueConstraint("account_id", "instrument_id", "snapshot_date", "source_id", name="uq_holding_lineage"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    valuation_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quantity_decimal: Mapped[str] = mapped_column(String(80), nullable=False)
    price_decimal: Mapped[str | None] = mapped_column(String(80))
    market_value_cents: Mapped[int | None] = mapped_column(Integer)
    cost_basis_cents: Mapped[int | None] = mapped_column(Integer)
    unrealized_gain_loss_cents: Mapped[int | None] = mapped_column(Integer)
    unrealized_gain_loss_pct: Mapped[str | None] = mapped_column(String(80))
    cost_basis_source: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown")
    cost_basis_quality: Mapped[str] = mapped_column(String(80), nullable=False, default="missing")
    market_value_source: Mapped[str] = mapped_column(String(80), nullable=False, default="manual")
    valuation_quality: Mapped[str] = mapped_column(String(80), nullable=False, default="current")
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    source_id: Mapped[str | None] = mapped_column(String(100))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    replaces_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("holding_snapshots.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    account: Mapped[Account] = relationship(back_populates="holdings")
    instrument: Mapped[Instrument] = relationship()


class SymbolAllocationOverride(Base):
    __tablename__ = "symbol_allocation_overrides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(50), nullable=False)
    allocation_percent: Mapped[str] = mapped_column(String(30), nullable=False, default="100")
    effective_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)


class BudgetPeriod(Base):
    __tablename__ = "budget_periods"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    period_type: Mapped[str] = mapped_column(String(50), nullable=False, default="monthly")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BudgetCategoryPlan(Base):
    __tablename__ = "budget_category_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    budget_period_id: Mapped[str] = mapped_column(ForeignKey("budget_periods.id"), nullable=False)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False)
    planned_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    rollover_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    plan_type: Mapped[str] = mapped_column(String(50), nullable=False, default="flexible")
    notes: Mapped[str | None] = mapped_column(Text)


class RolloverLedger(Base):
    __tablename__ = "rollover_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False)
    budget_period_id: Mapped[str] = mapped_column(ForeignKey("budget_periods.id"), nullable=False)
    starting_rollover_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    budgeted_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actual_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    adjustment_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ending_rollover_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SinkingFund(Base):
    __tablename__ = "sinking_funds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    linked_category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"))
    linked_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"))
    target_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    monthly_set_aside_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_balance_cents: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(Text)


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    merchant_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"))
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"))
    expected_amount_cents: Mapped[int | None] = mapped_column(Integer)
    amount_variability: Mapped[str] = mapped_column(String(50), nullable=False, default="fixed")
    cadence: Mapped[str] = mapped_column(String(50), nullable=False, default="monthly")
    next_expected_date: Mapped[date | None] = mapped_column(Date)
    last_seen_date: Mapped[date | None] = mapped_column(Date)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    detection_source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(Text)


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    goal_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    current_manual_cents: Mapped[int | None] = mapped_column(Integer)
    target_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    progress_method: Mapped[str] = mapped_column(String(80), nullable=False, default="manual")
    notes: Mapped[str | None] = mapped_column(Text)


class GoalAccountLink(Base):
    __tablename__ = "goal_account_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"))
    liability_id: Mapped[str | None] = mapped_column(ForeignKey("liabilities.id"))
    allocation_percent: Mapped[str | None] = mapped_column(String(30))


class Liability(Base):
    __tablename__ = "liabilities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    liability_type: Mapped[str] = mapped_column(String(80), nullable=False)
    current_balance_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    credit_limit_cents: Mapped[int | None] = mapped_column(Integer)
    minimum_payment_cents: Mapped[int | None] = mapped_column(Integer)
    due_day: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class LiabilityTermsHistory(Base):
    __tablename__ = "liability_terms_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    liability_id: Mapped[str] = mapped_column(ForeignKey("liabilities.id", ondelete="CASCADE"), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    apr_decimal: Mapped[str | None] = mapped_column(String(30))
    minimum_payment_cents: Mapped[int | None] = mapped_column(Integer)
    promo_apr_decimal: Mapped[str | None] = mapped_column(String(30))
    promo_end_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)


class DebtPaymentAllocation(Base):
    __tablename__ = "debt_payment_allocations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), nullable=False)
    liability_id: Mapped[str] = mapped_column(ForeignKey("liabilities.id"), nullable=False)
    principal_cents: Mapped[int | None] = mapped_column(Integer)
    interest_cents: Mapped[int | None] = mapped_column(Integer)
    fee_cents: Mapped[int | None] = mapped_column(Integer)
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    notes: Mapped[str | None] = mapped_column(Text)


class MonthlyReviewSnapshot(Base):
    __tablename__ = "monthly_review_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    review_month: Mapped[str] = mapped_column(String(7), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    starting_net_worth_cents: Mapped[int | None] = mapped_column(Integer)
    ending_net_worth_cents: Mapped[int | None] = mapped_column(Integer)
    net_worth_change_cents: Mapped[int | None] = mapped_column(Integer)
    income_cents: Mapped[int | None] = mapped_column(Integer)
    expenses_cents: Mapped[int | None] = mapped_column(Integer)
    savings_rate_decimal: Mapped[str | None] = mapped_column(String(50))
    investment_value_change_cents: Mapped[int | None] = mapped_column(Integer)
    top_spending_categories_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    biggest_transactions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    budget_variance_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    data_quality_summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source_data_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class DailyRefreshRun(Base):
    __tablename__ = "daily_refresh_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    run_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    refreshed_prices: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    refreshed_coinbase: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_snapshot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    errors_json: Mapped[list | None] = mapped_column(JSON)
    warnings_json: Mapped[list | None] = mapped_column(JSON)


class DailyAppSnapshot(Base):
    __tablename__ = "daily_app_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    net_worth_cents: Mapped[int | None] = mapped_column(Integer)
    assets_cents: Mapped[int | None] = mapped_column(Integer)
    liabilities_cents: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    warnings_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    fingerprint: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    before_json: Mapped[dict | None] = mapped_column(JSON)
    after_json: Mapped[dict | None] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class BackupManifest(Base):
    __tablename__ = "backup_manifests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    backup_type: Mapped[str] = mapped_column(String(50), nullable=False)
    backup_path: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_path: Mapped[str] = mapped_column(Text, nullable=False)
    app_version: Mapped[str] = mapped_column(String(50), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    database_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class AppSetting(Base, TimestampMixin):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_json: Mapped[dict] = mapped_column(JSON, nullable=False)
