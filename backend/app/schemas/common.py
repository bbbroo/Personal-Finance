from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiError(BaseModel):
    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    recommended_action: str | None = None


class AccountCreate(BaseModel):
    name: str
    institution: str | None = None
    account_type: str = "cash"
    account_subtype: str | None = None
    valuation_method: str = "balance_snapshot"
    balance_sign_policy: str = "asset_positive"
    include_in_net_worth: bool = True
    include_in_budget: bool = True
    include_in_cash_flow: bool = True
    freshness_threshold_days: int = 7
    notes: str | None = None


class AccountUpdate(BaseModel):
    name: str | None = None
    institution: str | None = None
    account_type: str | None = None
    account_subtype: str | None = None
    valuation_method: str | None = None
    balance_sign_policy: str | None = None
    is_active: bool | None = None
    include_in_net_worth: bool | None = None
    include_in_budget: bool | None = None
    include_in_cash_flow: bool | None = None
    freshness_threshold_days: int | None = None
    notes: str | None = None


class BalanceCreate(BaseModel):
    snapshot_date: date
    balance_cents: int | None
    balance_kind: str = "manual"
    source_type: str = "manual"
    confidence: str = "medium"
    is_reconciled: bool = False
    notes: str | None = None


class CategoryGroupCreate(BaseModel):
    name: str
    group_type: str
    sort_order: int = 0
    is_system: bool = False


class CategoryCreate(BaseModel):
    group_id: str
    name: str
    category_type: str = "expense"
    budget_behavior: str = "budgeted"
    sort_order: int = 0
    is_system: bool = False


class TransactionCreate(BaseModel):
    account_id: str
    transaction_date: date
    posted_date: date | None = None
    original_description: str
    merchant_name: str | None = None
    amount_cents: int
    category_id: str | None = None
    transaction_type: str = "unknown"
    transfer_status: str = "not_transfer"
    notes: str | None = None


class TransactionUpdate(BaseModel):
    merchant_name: str | None = None
    category_id: str | None = None
    transaction_type: str | None = None
    transfer_status: str | None = None
    review_status: str | None = None
    duplicate_status: str | None = None
    is_hidden: bool | None = None
    notes: str | None = None


class SplitCreate(BaseModel):
    splits: list[dict[str, Any]]


class RuleCreate(BaseModel):
    name: str
    priority: int = 100
    is_active: bool = True
    match_merchant_contains: str | None = None
    match_description_contains: str | None = None
    match_account_id: str | None = None
    match_amount_min_cents: int | None = None
    match_amount_max_cents: int | None = None
    match_transaction_type: str | None = None
    action_category_id: str | None = None
    action_merchant_name: str | None = None
    stop_processing: bool = True


class ImportMappingPresetCreate(BaseModel):
    name: str
    institution: str | None = None
    import_type: str = "transactions"
    mapping_json: dict[str, Any]
    sign_policy: str = "as_is"
    date_format: str | None = None
    amount_format: str | None = None


class StagedRowUpdate(BaseModel):
    normalized_json: dict[str, Any] | None = None
    user_action: str | None = None
    transfer_status: str | None = None
    duplicate_status: str | None = None


class StatementCreate(BaseModel):
    account_id: str
    period_start: date
    period_end: date
    opening_balance_cents: int | None
    ending_balance_cents: int | None
    source: str = "manual"
    notes: str | None = None


class InstrumentCreate(BaseModel):
    symbol: str
    name: str
    instrument_type: str = "stock"
    default_asset_class: str = "other"
    provider_symbol: str | None = None
    exchange: str | None = None
    price_provider: str | None = None


class HoldingCreate(BaseModel):
    account_id: str
    instrument_id: str
    snapshot_date: date
    quantity_decimal: str
    price_decimal: str | None = None
    market_value_cents: int | None = None
    cost_basis_cents: int | None = None
    cost_basis_source: str = "manual"
    cost_basis_quality: str = "user_entered"
    replace_existing: bool = False
    notes: str | None = None


class ManualPriceCreate(BaseModel):
    instrument_id: str
    price_date: date
    price_decimal: str
    provider: str = "manual"
    provider_symbol: str | None = None
    market_session: str = "manual"
    status: str = "manual_override"
    confidence: str = "medium"


class BudgetPeriodCreate(BaseModel):
    period_type: str = "monthly"
    start_date: date
    end_date: date
    status: str = "active"


class BudgetPlanCreate(BaseModel):
    budget_period_id: str
    category_id: str
    planned_cents: int
    rollover_enabled: bool = False
    plan_type: str = "flexible"
    notes: str | None = None


class RolloverAdjust(BaseModel):
    category_id: str
    budget_period_id: str
    adjustment_cents: int


class SinkingFundCreate(BaseModel):
    name: str
    target_cents: int
    monthly_set_aside_cents: int = 0
    current_balance_cents: int | None = None
    linked_category_id: str | None = None
    linked_account_id: str | None = None
    due_date: date | None = None


class RecurringCreate(BaseModel):
    merchant_name: str
    account_id: str | None = None
    category_id: str | None = None
    expected_amount_cents: int | None = None
    amount_variability: str = "fixed"
    cadence: str = "monthly"
    next_expected_date: date | None = None
    confidence: str = "medium"


class GoalCreate(BaseModel):
    name: str
    goal_type: str
    target_cents: int
    current_manual_cents: int | None = None
    target_date: date | None = None
    progress_method: str = "manual"
    notes: str | None = None


class LiabilityCreate(BaseModel):
    account_id: str
    liability_type: str = "other"
    current_balance_cents: int
    credit_limit_cents: int | None = None
    minimum_payment_cents: int | None = None
    due_day: int | None = None
    confidence: str = "medium"


class LiabilityTermsCreate(BaseModel):
    effective_date: date
    apr_decimal: str | None = None
    minimum_payment_cents: int | None = None
    promo_apr_decimal: str | None = None
    promo_end_date: date | None = None
    notes: str | None = None


class DebtPaymentAllocationCreate(BaseModel):
    transaction_id: str
    liability_id: str
    principal_cents: int | None = None
    interest_cents: int | None = None
    fee_cents: int | None = None
    is_estimated: bool = True
    confidence: str = "low"


class BackupCreate(BaseModel):
    backup_type: str = "manual"
    notes: str | None = None


class RestoreRequest(BaseModel):
    backup_path: str


class SettingsPatch(BaseModel):
    settings: dict[str, Any]


class CoinbaseConfigure(BaseModel):
    api_key_configured: bool = True
    read_only_confirmed: bool = True


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
