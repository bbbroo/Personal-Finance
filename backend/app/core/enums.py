from __future__ import annotations

from enum import StrEnum


class Confidence(StrEnum):
    VERIFIED = "verified"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class SourceType(StrEnum):
    MANUAL = "manual"
    CSV_IMPORT = "csv_import"
    API = "api"
    CALCULATED = "calculated"
    SYSTEM = "system"
    RULE = "rule"


class AccountType(StrEnum):
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    BROKERAGE = "brokerage"
    RETIREMENT = "retirement"
    HSA = "hsa"
    CRYPTO_EXCHANGE = "crypto_exchange"
    CRYPTO_WALLET = "crypto_wallet"
    LIABILITY = "liability"
    MANUAL_ASSET = "manual_asset"
    OTHER = "other"


class ValuationMethod(StrEnum):
    BALANCE_SNAPSHOT = "balance_snapshot"
    HOLDINGS_SUM = "holdings_sum"
    HOLDINGS_PLUS_CASH = "holdings_plus_cash"
    LIABILITY_BALANCE = "liability_balance"
    MANUAL = "manual"
    EXCLUDED = "excluded"


class BalanceSignPolicy(StrEnum):
    ASSET_POSITIVE = "asset_positive"
    LIABILITY_POSITIVE = "liability_positive"
    IMPORTED_AS_SIGNED = "imported_as_signed"
    INVERT_IMPORTED = "invert_imported"


class TransactionType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    INVESTMENT = "investment"
    LIABILITY_PAYMENT = "liability_payment"
    ADJUSTMENT = "adjustment"
    UNKNOWN = "unknown"


class TransferStatus(StrEnum):
    NOT_TRANSFER = "not_transfer"
    SUGGESTED_TRANSFER = "suggested_transfer"
    CONFIRMED_TRANSFER = "confirmed_transfer"
    REJECTED_TRANSFER = "rejected_transfer"


class DuplicateStatus(StrEnum):
    UNIQUE = "unique"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    DUPLICATE = "duplicate"
    CONFIRMED_DUPLICATE = "confirmed_duplicate"
    IGNORED_DUPLICATE = "ignored_duplicate"


class ReviewStatus(StrEnum):
    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"
    IGNORED = "ignored"


class ImportStatus(StrEnum):
    UPLOADED = "uploaded"
    STAGED = "staged"
    VALIDATED = "validated"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class StagedRowStatus(StrEnum):
    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


class UserAction(StrEnum):
    IMPORT = "import"
    SKIP = "skip"
    EDIT = "edit"
    NEEDS_REVIEW = "needs_review"


class IssueSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IssueStatus(StrEnum):
    OPEN = "open"
    IGNORED = "ignored"
    RESOLVED = "resolved"


class CostBasisQuality(StrEnum):
    VERIFIED = "verified"
    USER_ENTERED = "user_entered"
    ESTIMATED = "estimated"
    INCOMPLETE = "incomplete"
    MISSING = "missing"


CONFIDENCE_ORDER: dict[str, int] = {
    Confidence.VERIFIED: 5,
    Confidence.HIGH: 4,
    Confidence.MEDIUM: 3,
    Confidence.LOW: 2,
    Confidence.UNKNOWN: 1,
}


def weakest_confidence(values: list[str | None]) -> Confidence:
    concrete = [v for v in values if v]
    if not concrete:
        return Confidence.UNKNOWN
    return min((Confidence(v) for v in concrete), key=lambda item: CONFIDENCE_ORDER[item])
