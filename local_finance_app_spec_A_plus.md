# Personal Production Local Finance App — A+ Implementation Spec

**Document status:** A+ build-ready product and technical specification for a local personal finance system  
**Target user:** Single individual managing personal finances locally on Windows  
**Primary priority:** Financial accuracy, reliability, auditability, and truthful reporting  
**Target release type:** Personal production app — stable enough to rely on weekly  
**Cost constraint:** Free to run locally; optional free API keys allowed  
**Platform:** Windows, local-only  
**Architecture:** React + TypeScript frontend, FastAPI backend, SQLite database  
**Launch method:** Double-click Windows `.bat` launcher  
**Authentication:** No login in V1  
**Scheduling:** No required background scheduler in V1  

---

## 1. Executive Summary

This app is a free, local-first personal finance system designed to centralize income, expenses, budgets, recurring bills, accounts, investments, crypto, liabilities, goals, net worth, asset allocation, historical snapshots, and monthly reviews.

The app must support manual and CSV-driven workflows instead of paid financial aggregation APIs. It runs locally on Windows, stores data in SQLite, and presents a polished Monarch-like interface using React, TypeScript, Tailwind CSS, shadcn/ui, and Recharts.

The defining principle is not feature count. The defining principle is financial truth:

> Every number must be traceable, every import reversible, every stale/missing/estimated value visible, and every report honest about confidence.

The app must prefer `unknown` over a misleading value. A beautiful chart is unacceptable if the data behind it is unreconciled, stale, estimated, duplicated, or double-counted without warning.

---

## 2. Product Goals

### 2.1 Primary Goals

1. Provide one central local dashboard for all personal finances.
2. Track income, expenses, budgets, recurring bills, accounts, investments, crypto, liabilities, goals, net worth, and monthly review metrics.
3. Support drag-and-drop CSV imports from Chase, Schwab, M1 Finance, HSA providers, Coinbase, and other institutions.
4. Support optional read-only Coinbase API integration for balances, transactions, and fills.
5. Track Ledger manually by coin holdings in V1.
6. Track daily and manual historical snapshots of account balances, holdings, asset allocation, and net worth.
7. Show current value, monthly change, net worth over time, account balances over time, investment value over time, and asset allocation.
8. Track holding-level unrealized gain/loss only when cost basis is imported or manually verified.
9. Provide full staged import preview, duplicate detection, transfer detection, reconciliation, rollback, audit logging, and backups.
10. Provide a polished, local, production-quality UI suitable for long-term personal use.

### 2.2 Non-Goals for V1

1. No paid account aggregation such as Plaid, MX, Finicity, Yodlee, or Mastercard Data Connect.
2. No cloud hosting requirement.
3. No multi-user login in V1.
4. No required background scheduler in V1.
5. No tax-lot-level accounting in V1.
6. No realized gain/loss tax reporting in V1.
7. No ETF/mutual fund look-through analysis in V1.
8. No self-custody wallet address scanning in V1.
9. No real-time market data requirement.
10. No mobile app in V1.
11. No full document vault in V1.
12. No automatic trading, money movement, crypto signing, or write permissions to financial accounts.

---

## 3. A+ Quality Bar

The app must reach this quality bar before being considered a personal production finance system.

| Category | A+ Requirement |
|---|---|
| Product scope | Clear all-in-one target with strict production core and no hidden assumptions |
| Technical architecture | Explicit stack, migrations, local runtime, service boundaries, and workflow endpoints |
| Financial data model | Reconciliation, valuation methods, audit log, data provenance, confidence states, and double-count prevention |
| Import safety | Staged preview, validation, hash lineage, duplicate detection, rollback manifest, backup before commit |
| Investment accuracy | Cost basis quality/source labels; gains/losses blocked or warned when basis is incomplete |
| Crypto accuracy | Coinbase balances/fills supported; cost basis treated as incomplete unless verified/imported; Ledger manual only in V1 |
| Buildability | No vague backend choices; precise schema guidance, workflow rules, endpoints, calculations, and tests |
| Security/privacy | Local-only storage, no login in V1, read-only API keys, no seed phrases, backup/restore safety |
| UX completeness | Dashboard, imports, data quality center, reconciliation, budget, holdings, allocation, liabilities, goals, monthly review |
| Reporting honesty | Reports display freshness, confidence, reconciliation status, and missing/estimated data warnings |

---

## 4. Non-Negotiable Financial Integrity Rules

1. The app must never silently treat missing data as zero.
2. The app must distinguish verified, imported, manual, estimated, stale, incomplete, and missing values.
3. Every import must be traceable to original file, file hash, mapping preset version, parser version, and import batch.
4. Every committed import must be reversible through an import batch manifest.
5. Every manual edit to financial records must be audit-logged.
6. Net worth must prevent double-counting between account balances, cash positions, and holdings.
7. Transfers must not be excluded from cash flow unless confirmed or matched with very high confidence between owned accounts.
8. Cost basis must be labeled by source and quality.
9. Gain/loss must show a warning when cost basis is not verified or user-entered.
10. Reports must show data quality warnings when source data is stale, missing, unreconciled, duplicated, estimated, or manually overridden.
11. Backups must be created before every import commit and before restore.
12. Database restore must validate schema, hash, and backup manifest before replacing the current database.
13. The app must prefer `unknown` or `needs review` over a confident-looking but unsupported number.
14. Read-only API permissions are allowed; write permissions and money movement are prohibited.
15. The app must never request, store, or process a Ledger seed phrase or private key.

---

## 5. Key Product Decisions

| Area | Decision |
|---|---|
| App scope | All-in-one: budgeting + net worth + portfolio + crypto + reports |
| Cost | Free local app with optional free API keys |
| Platform | Windows local-only |
| Frontend | React + TypeScript |
| Backend | FastAPI |
| Database | SQLite |
| ORM/migrations | SQLAlchemy 2.x + Alembic required |
| Backend architecture | FastAPI routes + Pydantic schemas + service layer + repository layer |
| UI | Tailwind CSS + shadcn/ui |
| Charts | Recharts |
| API style | React communicates with FastAPI endpoints |
| Launch | Double-click `.bat` file |
| Auth | No login in V1 |
| Data import | Drag-and-drop CSV import with universal importer, auto-detection, and saved mapping presets |
| Import safety | All imports staged before commit |
| Import reversibility | Every import creates rollback-capable import batch |
| Duplicate detection | Strong transaction fingerprinting and likely duplicate review |
| Transfer handling | Confidence-based transfer detection; only confirmed/high-confidence owned transfers excluded |
| Budgeting | Monarch-style budgeting: income, fixed, flexible, non-monthly, rollovers, sinking funds |
| Budget periods | Monthly and annual |
| Goals | Savings, debt payoff, investment contribution, and net worth target goals |
| Investments | Imported holdings + manually entered/imported cost basis |
| Gains/losses | Holding-level unrealized gain/loss with basis-quality warnings; no tax lots in V1 |
| Stock/ETF prices | Free market data provider abstraction; manual override fallback |
| Crypto prices | Free public crypto price provider abstraction; manual override fallback |
| Coinbase | Optional read-only API for balances, transactions, and fills |
| Ledger | Manual holdings by coin |
| Snapshots | Automatically once per day when app runs, manual snapshot button, and snapshot after every import |
| Backups | Backup before every import plus daily rolling backups |
| Attachments | Store imported CSV files and import logs only |
| Currency | USD only; crypto quantities tracked separately |
| Priority tie-breaker | Data accuracy and reliability wins |

---

## 6. System Architecture

### 6.1 High-Level Architecture

```text
Windows user
   |
   | double-click launch.bat
   v
Local FastAPI backend  <---->  SQLite database
   ^                              |
   |                              |
React + TypeScript frontend       |
   |                              |
Browser at localhost              |
                                  |
Local app data directory:          |
- database                         |
- backups                          |
- imported CSV files               |
- import logs                      |
- local settings                   |
- API secret config                |
```

### 6.2 Required Stack

Backend:

1. Python 3.11+.
2. FastAPI.
3. SQLAlchemy 2.x.
4. Alembic migrations.
5. Pydantic schemas.
6. SQLite with WAL mode enabled.
7. SQLite foreign keys enabled.
8. Decimal-safe financial calculations.
9. pytest test suite.

Frontend:

1. React.
2. TypeScript.
3. Tailwind CSS.
4. shadcn/ui.
5. Recharts.
6. TanStack Query or equivalent for API state.
7. TanStack Table or equivalent for large tables.

Local-only runtime:

1. Backend binds to localhost only.
2. Frontend opens in local browser.
3. No cloud dependency for core app behavior.
4. Optional external read-only API calls for prices and Coinbase.

### 6.3 Backend Layers

The backend must follow these layers:

```text
api/routes      HTTP endpoints only
schemas         Pydantic request/response models
services        Business workflows and financial logic
repositories    Database persistence and query isolation
models          SQLAlchemy models
core            config, database, paths, logging, security helpers
```

Route handlers must not directly implement financial calculations. Financial calculations belong in services and must be unit tested.

### 6.4 Required Folder Structure

```text
local-finance-app/
  launch.bat
  README.md
  backend/
    app/
      main.py
      api/
        routes/
          health.py
          accounts.py
          transactions.py
          categories.py
          rules.py
          imports.py
          reconciliation.py
          holdings.py
          instruments.py
          prices.py
          budgets.py
          recurring.py
          goals.py
          liabilities.py
          snapshots.py
          reports.py
          monthly_review.py
          data_quality.py
          backups.py
          audit_log.py
          settings.py
          coinbase.py
      core/
        config.py
        database.py
        paths.py
        logging.py
        money.py
        security.py
        enums.py
      models/
      schemas/
      services/
      repositories/
      migrations/
      tests/
    pyproject.toml
    requirements.txt
  frontend/
    package.json
    src/
      main.tsx
      app/
      api/
      components/
        layout/
        cards/
        charts/
        tables/
        forms/
        import/
        quality/
      pages/
        Dashboard.tsx
        Accounts.tsx
        Transactions.tsx
        Holdings.tsx
        NetWorth.tsx
        Allocation.tsx
        MonthlyReview.tsx
        Budgets.tsx
        RecurringCalendar.tsx
        Goals.tsx
        Liabilities.tsx
        ImportCenter.tsx
        Reconciliation.tsx
        DataQuality.tsx
        Settings.tsx
  data/
    finance.sqlite3
    imports/
    logs/
    backups/
    exports/
    secrets/
```

---

## 7. Data Storage Requirements

### 7.1 SQLite Configuration

SQLite is required for V1.

Database requirements:

1. Enable WAL mode.
2. Enable foreign keys on every connection.
3. Use Alembic migrations.
4. Use transaction boundaries for multi-step workflows.
5. Use integer cents for USD money amounts.
6. Use decimal strings or scaled integers for crypto quantities and investment share quantities.
7. Use ISO 8601 timestamps stored in UTC.
8. Do not use floating-point values for money.
9. Use unique constraints to prevent duplicate snapshots where appropriate.
10. Provide migration tests for schema upgrades.

Recommended SQLite pragmas:

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=5000;
```

### 7.2 Money and Quantity Representation

USD fields:

```text
*_cents integer NOT NULL or nullable when unknown
```

Price fields:

```text
price_decimal string or Decimal-compatible numeric representation
```

Quantity fields:

```text
quantity_decimal string
```

Rules:

1. `0` means a known value of zero.
2. `NULL` means unknown or not applicable.
3. Reports must never coerce `NULL` to zero without displaying a warning.
4. Currency is USD only in V1.
5. Crypto quantities are not fiat currencies and must be stored separately from USD value.

### 7.3 Local File Storage

Required folders:

| Folder | Purpose |
|---|---|
| `data/imports/originals/` | Original uploaded CSVs |
| `data/imports/normalized/` | Normalized CSV previews or JSON row records |
| `data/imports/logs/` | Import logs |
| `data/backups/pre_import/` | Backups before import commits |
| `data/backups/daily/` | Daily rolling backups |
| `data/backups/pre_restore/` | Backups before restore |
| `data/exports/` | User exports |
| `data/secrets/` | Local API secret config, ignored by git |

The app must store original imported CSV files and compute SHA-256 hashes for provenance.

### 7.4 Backup Policy

Backups are mandatory.

Required backups:

1. Backup before every import commit.
2. Daily rolling backup when the app is opened, if no backup exists for that local date.
3. Backup before any restore operation.
4. Manual backup button in Settings.

Backup method:

1. Use SQLite Online Backup API or controlled backend backup routine.
2. Do not blindly copy an active SQLite database file without accounting for WAL state.
3. Include database, backup manifest, and optionally import metadata.
4. Validate backup after creation.

Backup manifest:

```json
{
  "app_version": "1.0.0",
  "schema_version": "alembic_revision_id",
  "created_at": "2026-06-21T00:00:00Z",
  "backup_type": "pre_import | daily | manual | pre_restore",
  "database_sha256": "...",
  "source_database_path": "...",
  "notes": "optional"
}
```

Restore requirements:

1. Restore only while backend is in maintenance mode or while database connections are safely closed.
2. Create a pre-restore backup before replacing the current database.
3. Validate backup manifest and database integrity before restore.
4. Run migration compatibility check.
5. Run `PRAGMA integrity_check` after restore.
6. Show clear success/failure result to user.

---

## 8. Security and Privacy Requirements

### 8.1 Local-Only Requirement

1. Backend must bind to `127.0.0.1` by default.
2. No cloud account is required.
3. No telemetry is allowed by default.
4. No financial data leaves the machine except optional user-enabled calls to price APIs or Coinbase.
5. Any optional external API use must be explicitly labeled in Settings.

### 8.2 Secrets

Secrets include optional Coinbase API keys and optional market data API keys.

Requirements:

1. Store secrets locally only.
2. Do not commit secrets to git.
3. Prefer Windows Credential Manager if implemented.
4. If using a local `.env` file, store it in `data/secrets/`, not in source folders.
5. Display whether a secret is configured, not the full secret.
6. Provide a delete-secret action.
7. Only read-only Coinbase API permissions are allowed.

### 8.3 Crypto Safety

1. Never request Ledger seed phrases.
2. Never store private keys.
3. Never sign transactions.
4. Never request Coinbase write/trade permissions.
5. Ledger is manual holdings only in V1.
6. Coinbase integration is read-only balances, transactions, and fills only.

---

## 9. Financial Integrity Model

### 9.1 Data Confidence

Every major financial value must have a confidence level.

Confidence enum:

```text
verified
high
medium
low
unknown
```

Quality/source enums must feed confidence. Example:

| Source condition | Confidence |
|---|---|
| Reconciled account statement | verified |
| Fresh imported balance from trusted CSV | high |
| Manual value entered recently | medium/high depending user flag |
| Stale price older than threshold | medium/low |
| Cost basis inferred from incomplete data | low |
| Missing cost basis | unknown |

Confidence must be shown on:

1. Account balances.
2. Holdings.
3. Cost basis.
4. Prices.
5. Net worth.
6. Asset allocation.
7. Monthly review.
8. Budget actuals.
9. Liabilities.
10. Goals.

### 9.2 Data Provenance

Any imported, calculated, or manual financial value must track provenance.

Required provenance fields where applicable:

```text
source_type = manual | csv_import | api | calculated | system
source_id = import_batch_id | api_run_id | user_entry_id | calculation_run_id
source_timestamp
source_quality
notes
```

### 9.3 Audit Log

All important changes must create audit records.

AuditLog fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| entity_type | string | transaction, account, holding, price, budget, goal, liability, rule, import, etc. |
| entity_id | UUID/string | Changed record |
| action | enum | create, update, delete, import_commit, rollback, rule_apply, reconcile, finalize |
| before_json | JSON nullable | Previous state |
| after_json | JSON nullable | New state |
| source | enum | manual, import, rule, system, api |
| source_id | nullable | Import batch, rule id, API run, etc. |
| created_at | datetime | UTC timestamp |

Must audit:

1. Manual transaction edits.
2. Category changes.
3. Split changes.
4. Account balance changes.
5. Holding and cost basis changes.
6. Import commit and rollback.
7. Rule application.
8. Transfer confirmation/rejection.
9. Reconciliation actions.
10. Monthly review finalization/regeneration.
11. Budget changes.
12. Liability terms and payment allocation changes.

### 9.4 Account Valuation Method

Every account must define how it contributes to net worth.

Valuation method enum:

```text
balance_snapshot
holdings_sum
holdings_plus_cash
liability_balance
manual
excluded
```

Balance sign policy enum:

```text
asset_positive
liability_positive
imported_as_signed
invert_imported
```

Rules:

1. Cash accounts use `balance_snapshot`.
2. Credit cards and debts use `liability_balance`.
3. Brokerages/IRAs/HSAs normally use `holdings_plus_cash`.
4. Coinbase normally uses `holdings_sum` or `holdings_plus_cash` if USD cash exists.
5. Ledger normally uses `holdings_sum`.
6. If an account has both account balance and holdings, the app must prevent double-counting.
7. If valuation method is ambiguous, dashboard must show a data quality issue.

### 9.5 Net Worth Calculation Policy

Net worth for date `D`:

```text
net_worth(D) = sum(asset account valuations as of D) - sum(liability account valuations as of D)
```

For each account, choose latest eligible valuation at or before date `D`, subject to stale-data thresholds.

Valuation hierarchy:

| Account type | Preferred valuation | Fallback | Warning condition |
|---|---|---|---|
| Cash | Latest balance snapshot | Manual balance | Stale/missing balance |
| Credit card | Latest liability balance | Manual balance | Ambiguous sign |
| Brokerage | Holdings market value + cash position | Account balance snapshot | Double-count risk |
| Retirement | Holdings market value + cash position | Account balance snapshot | Missing holdings/cash split |
| HSA | Holdings market value + cash position | Account balance snapshot | Missing holdings/cash split |
| Coinbase | API/imported holdings value + cash | Manual holdings | Missing/incomplete API data |
| Ledger | Manual holdings value | Manual total | Stale manual entry |
| Manual debt | Liability balance | Manual balance | Missing APR/payment terms |

The net worth report must display:

1. Data as-of date.
2. Number of stale accounts.
3. Number of unreconciled accounts.
4. Number of missing valuations.
5. Overall confidence.

---

## 10. Core Domain Model

This section defines implementation-level entities. Exact SQLAlchemy model names may differ, but all fields and concepts must be represented.

### 10.1 Account

Represents a financial account, manual asset, brokerage, wallet, debt, or other balance container.

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| name | string | User-visible name |
| institution | string nullable | Chase, Schwab, Coinbase, Ledger, etc. |
| account_type | enum | cash, credit_card, brokerage, retirement, hsa, crypto_exchange, crypto_wallet, liability, manual_asset, other |
| account_subtype | string nullable | checking, savings, roth_ira, taxable, etc. |
| valuation_method | enum | See Section 9.4 |
| balance_sign_policy | enum | See Section 9.4 |
| currency | string | USD in V1 |
| is_active | bool | Active/inactive |
| include_in_net_worth | bool | Default true |
| include_in_budget | bool | Whether transactions affect budgets |
| include_in_cash_flow | bool | Whether account transactions affect cash flow |
| data_source | enum | manual, csv, api, mixed |
| freshness_threshold_days | integer | Default per account type |
| created_at | datetime | UTC |
| updated_at | datetime | UTC |
| notes | text nullable | User notes |

### 10.2 Account Balance Snapshot

Represents known account balance at a point in time.

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| account_id | FK | Account |
| snapshot_date | date | Local date |
| balance_cents | integer nullable | Known balance; null if unknown |
| balance_kind | enum | current, statement, manual, imported, calculated |
| source_type | enum | manual, csv_import, api, calculated |
| source_id | nullable | Import batch/API run |
| confidence | enum | verified/high/medium/low/unknown |
| is_reconciled | bool | True when tied to reconciled statement |
| created_at | datetime | UTC |
| updated_at | datetime | UTC |

Constraints:

1. Unique account + snapshot_date + balance_kind + source_id where appropriate.
2. Manual snapshots must not be overwritten silently by imports.
3. Same-date imported snapshots require user confirmation to replace.

### 10.3 Category Group

Groups categories for budgeting and reporting.

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| name | string | Income, Fixed, Flexible, Non-Monthly, Transfers, Investing, Other |
| group_type | enum | income, fixed_expense, flexible_expense, non_monthly, transfer, investment, liability, other |
| sort_order | integer | Display order |
| is_system | bool | Protected default group |
| is_active | bool | Soft hide |

### 10.4 Category

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| group_id | FK | CategoryGroup |
| name | string | Groceries, Rent, Paycheck, etc. |
| category_type | enum | income, expense, transfer, investment, liability_payment, other |
| budget_behavior | enum | budgeted, ignored, transfer, sinking_fund, income |
| is_system | bool | Default categories protected |
| is_active | bool | Soft hide |
| sort_order | integer | Display order |

Default category groups and categories must exist on first launch and be user-editable except protected system behavior categories.

### 10.5 Transaction

Represents income, expense, transfer, debt payment, or investment-related cash movement imported from bank/credit card CSVs or entered manually.

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| account_id | FK | Account |
| transaction_date | date | Posted or effective date |
| posted_date | date nullable | If different |
| original_description | text | Raw imported description |
| merchant_name | string nullable | Cleaned merchant |
| amount_cents | integer | Positive inflow, negative outflow by normalized app convention |
| category_id | FK nullable | User/rule category |
| transaction_type | enum | income, expense, transfer, investment, liability_payment, adjustment, unknown |
| transfer_status | enum | not_transfer, suggested_transfer, confirmed_transfer, rejected_transfer |
| transfer_link_id | FK nullable | Links matched transfers |
| review_status | enum | needs_review, reviewed, ignored |
| duplicate_status | enum | unique, possible_duplicate, confirmed_duplicate, ignored_duplicate |
| is_hidden | bool | Exclude from reports if true |
| is_split | bool | True if split rows exist |
| fingerprint | string | Normalized duplicate detection hash |
| source_type | enum | manual, csv_import, api |
| source_id | nullable | Import batch/API run |
| created_by_import_batch_id | FK nullable | Import provenance |
| updated_by_import_batch_id | FK nullable | Import provenance |
| notes | text nullable | User notes |
| created_at | datetime | UTC |
| updated_at | datetime | UTC |

Rules:

1. App convention: positive = inflow, negative = outflow.
2. CSV mapping must normalize source-specific sign conventions.
3. Confirmed transfers are excluded from income/expense totals but still visible in transfer reports.
4. Liability payments may have debt payment allocation records.
5. Hidden transactions are excluded from standard reports but remain auditable.

### 10.6 Transaction Split

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| transaction_id | FK | Parent transaction |
| category_id | FK | Split category |
| amount_cents | integer | Signed amount |
| notes | text nullable | Optional |
| created_at | datetime | UTC |

Rules:

1. Sum of split amounts must equal parent transaction amount.
2. Split transactions report by split rows, not parent category.
3. Splits must be audit-logged.

### 10.7 Transfer Link

Connects one or more transactions representing movement between owned accounts.

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| confidence_score | decimal/string | 0-1 score |
| match_basis | string | exact_amount_date, date_window, manual, etc. |
| status | enum | suggested, confirmed, rejected |
| created_by | enum | system, user |
| created_at | datetime | UTC |
| confirmed_at | datetime nullable | UTC |

Rules:

1. Exact matched transfers between owned accounts may be auto-confirmed only when amount, date window, and account ownership rules are very high confidence.
2. Suggested transfers do not affect reports as excluded transfers until confirmed.
3. User can reject false matches.

### 10.8 Transaction Rule

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| name | string | User-visible rule name |
| priority | integer | Lower or higher priority must be defined consistently |
| is_active | bool | Rule enabled |
| match_merchant_contains | string nullable | Merchant pattern |
| match_description_contains | string nullable | Raw description pattern |
| match_account_id | FK nullable | Optional account constraint |
| match_amount_min_cents | integer nullable | Optional min |
| match_amount_max_cents | integer nullable | Optional max |
| match_transaction_type | enum nullable | Optional |
| action_category_id | FK nullable | Category assignment |
| action_merchant_name | string nullable | Merchant cleanup |
| action_tags_json | JSON nullable | Tags if implemented |
| stop_processing | bool | Stop after match |
| created_at | datetime | UTC |
| updated_at | datetime | UTC |

Rules:

1. Rule preview must be available before applying to historical data.
2. Rule application must be audit-logged.
3. Rules can be applied to staged rows before import commit and existing transactions after confirmation.

### 10.9 Import Batch

Represents one imported file or API import run.

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| import_type | enum | transactions, holdings, balances, prices, coinbase_api, other |
| institution | string nullable | Chase, Schwab, etc. |
| account_id | FK nullable | Account target when known |
| original_filename | string | User file name |
| original_file_path | string | Local stored path |
| original_file_sha256 | string | File hash |
| normalized_file_path | string nullable | Normalized preview path |
| mapping_preset_id | FK nullable | Preset used |
| mapping_preset_version | integer nullable | Version at import time |
| parser_version | string | App parser version |
| status | enum | uploaded, staged, validated, committed, rolled_back, failed |
| row_count | integer | Total rows |
| valid_row_count | integer | Valid staged rows |
| skipped_row_count | integer | Skipped rows |
| duplicate_row_count | integer | Duplicates detected |
| warning_count | integer | Validation warnings |
| error_count | integer | Validation errors |
| committed_record_manifest_json | JSON nullable | Records created/updated |
| committed_at | datetime nullable | UTC |
| rolled_back_at | datetime nullable | UTC |
| created_at | datetime | UTC |
| notes | text nullable | User notes |

Rules:

1. Import batch must not commit with unresolved fatal errors.
2. Import batch commit must be atomic.
3. Import batch rollback must use the committed record manifest.
4. Import batch must create a backup before commit.

### 10.10 Import Mapping Preset

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| name | string | Chase Checking CSV, Schwab Holdings CSV, etc. |
| institution | string nullable | Institution |
| import_type | enum | transactions, holdings, balances, prices |
| version | integer | Increment on edit |
| mapping_json | JSON | Source columns to canonical fields |
| sign_policy | enum | as_is, invert, credits_positive_debits_negative, etc. |
| date_format | string nullable | User-specified if needed |
| amount_format | string nullable | User-specified if needed |
| created_at | datetime | UTC |
| updated_at | datetime | UTC |

Rules:

1. Auto-detect common columns first.
2. User can edit and save a preset.
3. Import batches must record the preset version used.

### 10.11 Staged Import Row

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| import_batch_id | FK | Import batch |
| row_number | integer | Original file row number |
| raw_json | JSON | Raw row values |
| normalized_json | JSON | Canonical mapped row |
| normalized_hash | string | Row-level hash |
| validation_status | enum | valid, warning, error, skipped |
| duplicate_status | enum | unique, possible_duplicate, duplicate |
| transfer_status | enum | not_transfer, suggested_transfer, confirmed_transfer, rejected_transfer |
| user_action | enum | import, skip, edit, needs_review |
| final_record_type | string nullable | transaction, holding, balance, price |
| final_record_id | UUID/string nullable | After commit |
| errors_json | JSON nullable | Validation errors |
| warnings_json | JSON nullable | Warnings |
| created_at | datetime | UTC |

### 10.12 Import Record Manifest

A committed import batch must record exact created/updated/deleted records for rollback.

Manifest structure:

```json
{
  "created": [
    {"entity_type": "transaction", "entity_id": "..."}
  ],
  "updated": [
    {"entity_type": "transaction", "entity_id": "...", "before": {}, "after": {}}
  ],
  "deleted": []
}
```

Rollback rules:

1. Created records may be deleted during rollback if not externally modified after commit.
2. Updated records must be restored from `before` state.
3. If a record was modified after import commit, rollback must require user confirmation.
4. Rollback must be audit-logged.

### 10.13 Account Statement

Represents statement/import period balances for reconciliation.

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| account_id | FK | Account |
| period_start | date | Start date |
| period_end | date | End date |
| opening_balance_cents | integer nullable | Statement opening |
| ending_balance_cents | integer nullable | Statement ending |
| source | enum | manual, csv, statement, calculated |
| import_batch_id | FK nullable | Related import |
| status | enum | draft, ready, reconciled, mismatch, accepted_difference |
| created_at | datetime | UTC |
| notes | text nullable | User notes |

### 10.14 Reconciliation Run

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| account_statement_id | FK | Statement |
| calculated_ending_balance_cents | integer nullable | Opening + transactions |
| difference_cents | integer nullable | Calculated minus statement |
| status | enum | matched, mismatch, accepted_difference, failed |
| tolerance_cents | integer | Usually 0 for bank accounts |
| run_at | datetime | UTC |
| notes | text nullable | User notes |

Rule:

```text
opening balance + normalized transactions during period must equal ending balance, unless the user explicitly accepts the difference.
```

Unreconciled or mismatched periods must create data quality issues.

### 10.15 Instrument / Security

Represents stock, ETF, mutual fund, bond, crypto asset, or cash-like instrument.

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| symbol | string | Display ticker or crypto symbol |
| provider_symbol | string nullable | Provider-specific symbol |
| name | string | Asset name |
| instrument_type | enum | stock, etf, mutual_fund, bond, crypto, cash, option, other |
| exchange | string nullable | NYSE, NASDAQ, etc. |
| cusip_or_isin | string nullable | Optional |
| default_asset_class | enum | cash, us_stock, international_stock, bond, crypto, real_estate, alternatives, liability, other |
| price_provider | enum nullable | manual, csv_import, free_api_primary, free_api_secondary |
| is_active | bool | Active/inactive |
| created_at | datetime | UTC |
| updated_at | datetime | UTC |

Rules:

1. Ticker symbol alone is not enough for long-term identity.
2. Provider symbols must be stored when using external price APIs.
3. Mutual funds/ETFs are classified as a single asset class in V1 unless manually overridden.

### 10.16 Price

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| instrument_id | FK | Instrument |
| price_date | date | Date of price |
| price_decimal | string | Decimal-safe price |
| currency | string | USD |
| source_type | enum | manual, csv_import, api |
| provider | string nullable | Provider name |
| provider_symbol | string nullable | Provider symbol |
| market_session | enum | intraday, close, historical, crypto_spot, manual |
| status | enum | current, stale, missing, failed, manual_override |
| confidence | enum | verified/high/medium/low/unknown |
| fetched_at | datetime nullable | UTC |
| created_at | datetime | UTC |

Rules:

1. Price history must be stored, not just latest price.
2. Manual overrides must not be overwritten silently.
3. Stale thresholds differ by asset type.
4. Crypto can update on weekends; stock market prices may not.

### 10.17 Holding Snapshot

Represents holdings by account, symbol, and snapshot date.

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| account_id | FK | Account |
| instrument_id | FK | Instrument |
| snapshot_date | date | Date holdings are valid |
| valuation_timestamp | datetime nullable | Exact timestamp if known |
| quantity_decimal | string | Decimal-safe quantity |
| price_decimal | string nullable | Price used |
| market_value_cents | integer nullable | Current value |
| cost_basis_cents | integer nullable | Total basis for current holding |
| unrealized_gain_loss_cents | integer nullable | Market value - cost basis |
| unrealized_gain_loss_pct | string nullable | Decimal-safe percent |
| cost_basis_source | enum | brokerage_import, coinbase_tax_export, coinbase_api_inferred, manual, calculated, unknown |
| cost_basis_quality | enum | verified, user_entered, estimated, incomplete, missing |
| market_value_source | enum | imported, calculated_from_price, manual |
| valuation_quality | enum | current, stale, estimated, missing |
| confidence | enum | verified/high/medium/low/unknown |
| source_type | enum | manual, csv_import, api, calculated |
| source_id | nullable | Import/API run |
| is_current | bool | Latest current row for account/instrument |
| replaces_snapshot_id | FK nullable | Replacement history |
| notes | text nullable | User notes |
| created_at | datetime | UTC |

Rules:

1. Same account + instrument + snapshot date imports require replacement policy.
2. Imported snapshot may replace previous imported snapshot from the same source after confirmation.
3. Manual snapshots must not be overwritten silently.
4. API snapshots must not overwrite manually verified cost basis.
5. Gain/loss must warn unless cost_basis_quality is `verified` or `user_entered`.
6. If cost basis is missing, gain/loss is unknown, not zero.

### 10.18 Symbol Allocation Override

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| instrument_id | FK | Instrument |
| asset_class | enum | cash, us_stock, international_stock, bond, crypto, real_estate, alternatives, liability, other |
| allocation_percent | string | 100.0 in V1 for single-class override |
| effective_date | date nullable | Optional |
| notes | text nullable | User notes |

V1 supports single-class symbol overrides. ETF/fund look-through is future functionality.

### 10.19 Budget Period

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| period_type | enum | monthly, annual |
| start_date | date | Period start |
| end_date | date | Period end |
| status | enum | draft, active, closed |
| created_at | datetime | UTC |
| closed_at | datetime nullable | UTC |

### 10.20 Budget Category Plan

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| budget_period_id | FK | BudgetPeriod |
| category_id | FK | Category |
| planned_cents | integer | Budget target |
| rollover_enabled | bool | Category rollover |
| plan_type | enum | fixed, flexible, non_monthly, income, sinking_fund |
| notes | text nullable | User notes |

### 10.21 Rollover Ledger

Rollovers must be computed and stored as ledger entries, not only mutable category fields.

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| category_id | FK | Category |
| budget_period_id | FK | BudgetPeriod |
| starting_rollover_cents | integer | Start value |
| budgeted_cents | integer | Planned amount |
| actual_cents | integer | Actual amount |
| adjustment_cents | integer | Manual adjustment |
| ending_rollover_cents | integer | Result |
| locked_at | datetime nullable | Locked when month closed |

### 10.22 Sinking Fund

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| name | string | Insurance, annual fee, etc. |
| linked_category_id | FK nullable | Spending category |
| linked_account_id | FK nullable | Account holding funds |
| target_cents | integer | Target amount |
| due_date | date nullable | Goal date |
| monthly_set_aside_cents | integer | Planned contribution |
| current_balance_cents | integer nullable | Manual/derived balance |
| status | enum | active, paused, completed, archived |
| notes | text nullable | User notes |

### 10.23 Recurring Transaction

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| merchant_name | string | Merchant/source |
| account_id | FK nullable | Account if known |
| category_id | FK nullable | Category |
| expected_amount_cents | integer nullable | Expected amount |
| amount_variability | enum | fixed, variable, unknown |
| cadence | enum | weekly, biweekly, monthly, quarterly, annual, custom |
| next_expected_date | date nullable | Forecast date |
| last_seen_date | date nullable | Last transaction date |
| confidence | enum | verified/high/medium/low/unknown |
| detection_source | enum | system_detected, manual |
| status | enum | active, paused, ignored |
| notes | text nullable | User notes |

Recurring detection must support a full calendar in V1, but confidence must be visible.

### 10.24 Goal

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| name | string | Goal name |
| goal_type | enum | savings, debt_payoff, investment_contribution, net_worth_target |
| target_cents | integer | Target |
| current_manual_cents | integer nullable | Manual progress |
| target_date | date nullable | Optional |
| status | enum | active, paused, completed, archived |
| progress_method | enum | linked_accounts, manual, hybrid |
| notes | text nullable | User notes |

### 10.25 Goal Account Link

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| goal_id | FK | Goal |
| account_id | FK nullable | Account contribution |
| liability_id | FK nullable | Debt payoff goal |
| allocation_percent | string nullable | Optional percent |

Goals may be linked to multiple accounts or manual progress.

### 10.26 Liability

Represents credit card debt, loans, or manual debts.

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| account_id | FK | Account of type liability/credit_card |
| liability_type | enum | credit_card, student_loan, auto_loan, mortgage, personal_loan, medical_debt, other |
| current_balance_cents | integer | Positive liability amount |
| credit_limit_cents | integer nullable | For revolving credit |
| minimum_payment_cents | integer nullable | Current minimum |
| due_day | integer nullable | 1-31 |
| status | enum | active, paid_off, archived |
| source_type | enum | manual, csv_import, calculated |
| confidence | enum | verified/high/medium/low/unknown |
| updated_at | datetime | UTC |

### 10.27 Liability Terms History

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| liability_id | FK | Liability |
| effective_date | date | Terms begin |
| apr_decimal | string nullable | APR as decimal string |
| minimum_payment_cents | integer nullable | Minimum payment |
| promo_apr_decimal | string nullable | Promo APR |
| promo_end_date | date nullable | Promo end |
| notes | text nullable | User notes |

### 10.28 Debt Payment Allocation

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| transaction_id | FK | Payment transaction |
| liability_id | FK | Liability |
| principal_cents | integer nullable | Principal |
| interest_cents | integer nullable | Interest |
| fee_cents | integer nullable | Fee |
| is_estimated | bool | True if not exact |
| confidence | enum | verified/high/medium/low/unknown |
| notes | text nullable | User notes |

Debt payoff projections must label estimated allocations clearly.

### 10.29 Monthly Review Snapshot

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| review_month | string | YYYY-MM |
| status | enum | draft, finalized, regenerated |
| starting_net_worth_cents | integer nullable | Start |
| ending_net_worth_cents | integer nullable | End |
| net_worth_change_cents | integer nullable | Change |
| income_cents | integer nullable | Income |
| expenses_cents | integer nullable | Expenses |
| savings_rate_decimal | string nullable | Savings rate |
| investment_value_change_cents | integer nullable | Investment change |
| top_spending_categories_json | JSON | Top categories |
| biggest_transactions_json | JSON | Biggest transactions |
| budget_variance_json | JSON | Budget variance |
| data_quality_summary_json | JSON | Warnings/confidence |
| source_data_hash | string | Hash of inputs |
| finalized_at | datetime nullable | UTC |
| created_at | datetime | UTC |

Rules:

1. Draft reviews can recalculate dynamically.
2. Finalized reviews must not silently change.
3. If source data changes after finalization, show warning and allow regeneration.

### 10.30 Daily Refresh Run

Tracks user-triggered/app-open refresh attempts.

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| run_date | date | Local date |
| started_at | datetime | UTC |
| completed_at | datetime nullable | UTC |
| status | enum | running, completed, partial, failed |
| refreshed_prices | bool | Prices updated |
| refreshed_coinbase | bool | Coinbase updated |
| created_snapshot | bool | Daily snapshot created |
| errors_json | JSON nullable | Errors |
| warnings_json | JSON nullable | Warnings |

### 10.31 Data Quality Issue

Required fields:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| severity | enum | info, warning, error, critical |
| issue_type | enum | stale_data, missing_data, unreconciled, duplicate, ambiguous_transfer, missing_cost_basis, stale_price, double_count_risk, backup_failed, import_error, other |
| entity_type | string nullable | Related entity |
| entity_id | string nullable | Related id |
| title | string | User-facing title |
| description | text | User-facing detail |
| recommended_action | text nullable | What to do |
| status | enum | open, ignored, resolved |
| created_at | datetime | UTC |
| resolved_at | datetime nullable | UTC |

Data quality issues may be computed dynamically and/or persisted for user resolution.

---

## 11. Import and Reconciliation Workflows

### 11.1 Supported Import Types

V1 must support:

1. Bank/credit card transactions CSV.
2. Account balance CSV or manual balance entry.
3. Brokerage holdings CSV.
4. Manual holdings entry.
5. Coinbase CSV import where available.
6. Optional Coinbase API import.
7. Price CSV/manual price import.

### 11.2 Universal CSV Import Flow

Required flow:

1. User opens Import Center.
2. User drags/drops CSV.
3. App stores original CSV and computes SHA-256 hash.
4. App detects institution/import type if possible.
5. App suggests mapping preset or starts auto-detection.
6. User confirms account/import type/mapping.
7. App creates Import Batch with status `uploaded`.
8. App parses into Staged Import Rows.
9. App validates required fields.
10. App normalizes sign/date/amount/quantity formats.
11. App computes row hashes/fingerprints.
12. App runs duplicate detection.
13. App applies transaction rules to staged rows if user requests.
14. App runs transfer detection.
15. App shows staged preview with warnings/errors.
16. User edits/skips/imports rows.
17. App creates pre-import backup.
18. App commits import atomically.
19. App writes committed record manifest.
20. App audit-logs commit.
21. App optionally creates post-import snapshot.
22. App offers reconciliation if statement balances are available.

Fatal errors block commit. Warnings allow commit only after visible user acknowledgement.

### 11.3 Duplicate Detection

Transaction fingerprint inputs:

1. Account id.
2. Normalized date or date window.
3. Normalized amount.
4. Normalized merchant/description.
5. Optional check/reference id if present.

Duplicate statuses:

```text
unique
possible_duplicate
duplicate
```

Required behavior:

1. Exact fingerprint match is duplicate candidate.
2. Similar merchant + same amount + date window is possible duplicate.
3. User can import, skip, or mark as not duplicate.
4. Duplicate decisions must be stored in staged rows and audit log.

### 11.4 Transfer Detection

Transfer detection must be confidence-based.

Matching signals:

1. Equal and opposite amounts.
2. Dates within configurable window.
3. Both accounts are owned accounts.
4. Merchant/description suggests payment/transfer.
5. Account types make sense for transfer.

Statuses:

```text
not_transfer
suggested_transfer
confirmed_transfer
rejected_transfer
```

Rules:

1. Only `confirmed_transfer` is excluded from income/expense totals.
2. Auto-confirm is allowed only for very high-confidence exact matches.
3. Credit card payments must reduce liability but not count as expense, while interest/fees remain expenses.
4. Brokerage contributions should be excluded from spending but visible in contribution/investment reports.
5. Loan payments must support principal/interest/fee allocation.

### 11.5 Reconciliation Workflow

Reconciliation is required for trust.

Flow:

1. User creates or imports Account Statement with period start/end and opening/ending balance.
2. App calculates ending balance from opening balance + normalized transactions.
3. App compares calculated ending balance to statement ending balance.
4. If matched, account period becomes reconciled.
5. If mismatch, user sees difference and candidate causes.
6. User can fix transactions, add missing transactions, change sign policy, or accept difference.
7. Accepted differences must be explicit and audit-logged.

Acceptance rule:

```text
A transaction import is not considered fully clean until its relevant account period reconciles or the user explicitly accepts the difference.
```

### 11.6 Import Rollback Workflow

Required flow:

1. User opens import batch.
2. User selects rollback.
3. App displays records created/updated by batch.
4. App checks whether any records changed after commit.
5. App creates pre-rollback backup.
6. App deletes created records and restores updated records from manifest.
7. App marks import batch `rolled_back`.
8. App audit-logs rollback.
9. App recomputes data quality issues and snapshots as needed.

Rollback must be blocked or require confirmation when later manual edits depend on imported records.

---

## 12. Accounts, Net Worth, and Snapshots

### 12.1 Account Types

Required account types:

1. Checking.
2. Savings.
3. Credit card.
4. Brokerage.
5. Roth IRA.
6. Traditional retirement.
7. HSA.
8. Coinbase crypto exchange.
9. Ledger crypto wallet.
10. Manual asset.
11. Loan/debt/liability.
12. Other.

### 12.2 Snapshot Rules

Snapshots are created:

1. Automatically once per day when app runs, if no snapshot exists for that day.
2. Manually via button.
3. After import commit if user confirms or setting is enabled.

No background scheduler is required. If the app is not opened for several days, no automatic snapshots occur for those days unless the user backfills manually.

### 12.3 Historical Net Worth

Historical net worth must be computed from stored account/holding/liability snapshots, not from current values alone.

Each point in a net worth chart must display:

1. Date.
2. Net worth.
3. Assets.
4. Liabilities.
5. Confidence.
6. Number of stale/missing accounts.
7. Any data quality warnings.

---

## 13. Transactions and Cash Flow

### 13.1 Cash Flow Calculation

Income:

```text
sum positive transactions categorized as income
excluding hidden transactions
excluding confirmed transfers
within selected date range
```

Expenses:

```text
absolute value of negative transactions categorized as expense
excluding hidden transactions
excluding confirmed transfers
within selected date range
```

Savings rate:

```text
(income - expenses) / income
```

If income is zero or unknown, savings rate is unknown.

### 13.2 Transaction Editing

User must be able to edit:

1. Merchant.
2. Category.
3. Transaction type.
4. Transfer status.
5. Notes.
6. Hidden status.
7. Review status.
8. Split rows.

All edits must create audit log entries.

### 13.3 Split Transactions

Requirements:

1. User can split one transaction across multiple categories.
2. Split total must equal parent total.
3. Reports use split rows for category totals.
4. Parent transaction remains source of truth for account balance impact.
5. Splits are audit-logged.

---

## 14. Budgeting

### 14.1 Budgeting Model

The app must support Monarch-style budgeting:

1. Income.
2. Fixed expenses.
3. Flexible expenses.
4. Non-monthly expenses.
5. Annual budgets.
6. Category rollovers.
7. Sinking-fund style set-asides.

### 14.2 Budget Calculations

For each budget period/category:

```text
available = planned + starting_rollover + adjustment
actual = reportable spending/income for category in period
remaining = available - actual
ending_rollover = remaining if rollover_enabled else 0
```

Rules:

1. Confirmed transfers are excluded from expense budgets unless category behavior says otherwise.
2. Hidden transactions are excluded.
3. Split transactions report by split category.
4. Closed periods lock rollover ledger values.
5. If data changes after close, show data quality warning.

### 14.3 Annual Budgets

Annual budgets may either:

1. Allocate annual amount evenly across months.
2. Track against annual period directly.
3. Use sinking funds for non-monthly expenses.

UI must make the behavior explicit.

---

## 15. Recurring Calendar

### 15.1 Detection

Recurring detection should identify repeated income/bills using:

1. Merchant/source name.
2. Amount pattern.
3. Date cadence.
4. Account.
5. Category.

Each detected recurring item must have a confidence level and user review status.

### 15.2 Calendar Requirements

The recurring calendar must show:

1. Upcoming expected bills.
2. Upcoming expected income.
3. Amount confidence.
4. Due/expected date.
5. Last seen date.
6. Category.
7. Account.
8. Status: active, paused, ignored.

---

## 16. Investments and Holdings

### 16.1 Holdings Scope

V1 tracks:

1. Current holdings by account and instrument.
2. Historical holding snapshots.
3. Market value.
4. Holding-level cost basis when imported or manually entered.
5. Holding-level unrealized gain/loss when basis is sufficient.
6. Asset allocation by class.
7. Investment value over time.

V1 does not track:

1. Tax lots.
2. Realized gains/losses.
3. Complete performance attribution.
4. ETF/fund look-through.

### 16.2 Gain/Loss Rules

```text
unrealized_gain_loss = market_value - cost_basis
unrealized_gain_loss_pct = unrealized_gain_loss / cost_basis
```

Rules:

1. If cost basis is missing, gain/loss is unknown.
2. If cost basis is incomplete or estimated, gain/loss must show warning.
3. If market value is stale, gain/loss must show warning.
4. Gain/loss must not be shown as exact when source is inferred.
5. Retirement accounts can show economic gain/loss, but not tax basis unless explicitly supported by source.

### 16.3 Price Updates

Price refresh behavior:

1. Runs when app opens if daily refresh has not completed for local date.
2. Can be triggered manually.
3. Uses provider abstraction.
4. Stores price history.
5. Supports manual override.
6. Marks stale/missing/failed prices.

Provider abstraction:

```text
manual
csv_import
free_api_primary
free_api_secondary
```

### 16.4 Asset Allocation

Default asset classes:

1. Cash.
2. US stocks.
3. International stocks.
4. Bonds.
5. Crypto.
6. Real estate.
7. Alternatives.
8. Liabilities.
9. Other.

Rules:

1. Symbol-level override supported in V1.
2. ETF/mutual fund look-through not supported in V1.
3. Unknown asset class must show as Other/Needs Classification.
4. Allocation chart must show stale/missing classification warnings.

---

## 17. Crypto

### 17.1 Coinbase

Optional read-only Coinbase API integration may import:

1. Account balances.
2. Crypto quantities.
3. Fiat value where available or calculable.
4. Transactions/activity where available.
5. Fills/trades where available.

Strict cost basis rule:

```text
Coinbase API data may populate balances, transactions, and fills. Cost basis must be treated as incomplete unless explicitly imported from a Coinbase tax/report export or manually verified by the user.
```

Rules:

1. Fills are not the same as full taxable transaction history.
2. Transfers, deposits, withdrawals, staking rewards, conversions, and fees may require separate handling.
3. Coinbase cost basis from API-inferred data must default to `incomplete` unless verified.
4. The UI must label Coinbase gain/loss confidence.
5. API permissions must be read-only.

### 17.2 Ledger

V1 Ledger support is manual holdings by coin.

Required fields per Ledger holding:

1. Coin symbol.
2. Quantity.
3. Manual cost basis optional.
4. Manual notes optional.
5. Last updated date.

Rules:

1. No seed phrase.
2. No private key.
3. No signing.
4. No address scanning in V1.
5. Stale manual Ledger values must show warning.

---

## 18. Liabilities and Debt Payoff

### 18.1 Liability Tracking

The app must support manual liabilities and debt payoff tracking.

Required capabilities:

1. Current balance.
2. APR.
3. Minimum payment.
4. Due day.
5. Credit limit for credit cards.
6. Payment history via linked transactions.
7. Principal/interest/fee allocation where known.
8. Estimated allocation where exact data is unavailable.

### 18.2 Payoff Strategies

V1 must support debt payoff views:

1. Avalanche order by APR.
2. Snowball order by balance.
3. Minimum payment summary.
4. Extra payment scenario.

Projection warnings:

1. If APR missing, projection confidence is low.
2. If payment allocation missing, projection is estimated.
3. If minimum payment missing, projection is incomplete.
4. Promotional APR end dates must be considered when present.

---

## 19. Goals

Goal types:

1. Savings goal.
2. Debt payoff goal.
3. Investment contribution goal.
4. Net worth target.

Progress methods:

1. Linked accounts.
2. Linked liabilities.
3. Manual progress.
4. Hybrid.

Rules:

1. Goal progress must show source and confidence.
2. Manual progress edits must be audit-logged.
3. Goals may link to multiple accounts or manual progress.

---

## 20. Monthly Review

### 20.1 Required Metrics

Monthly review must include:

1. Starting net worth.
2. Ending net worth.
3. Net worth change.
4. Income.
5. Expenses.
6. Savings rate.
7. Investment value change.
8. Top spending categories.
9. Biggest transactions.
10. Budget variance.
11. Data quality summary.
12. Reconciliation status.

### 20.2 Draft vs Finalized Reviews

Rules:

1. Draft review recalculates dynamically.
2. Finalized review stores snapshot metrics and source data hash.
3. Finalized review must not silently change.
4. If source data changes, show warning: `Source data has changed since finalization.`
5. User can regenerate a review, which creates audit log entry.

---

## 21. Dashboard and Required Screens

### 21.1 Global UX Requirements

1. Polished Monarch-like dashboard.
2. Desktop-first layout.
3. Clear cards, tabs, filters, tables, and charts.
4. Data freshness badges.
5. Confidence badges.
6. Empty states with clear next actions.
7. Data quality warnings surfaced prominently.
8. No hidden financial assumptions.

### 21.2 Required Screens

1. Dashboard.
2. Accounts.
3. Transactions.
4. Holdings.
5. Net Worth History.
6. Asset Allocation.
7. Monthly Review.
8. Budget.
9. Recurring Calendar.
10. Goals.
11. Liabilities.
12. Import Center.
13. Reconciliation.
14. Data Quality Center.
15. Settings.
16. Audit Log.

### 21.3 Dashboard Cards

Dashboard must show:

1. Net worth.
2. Net worth monthly change.
3. Cash balance.
4. Investments total.
5. Crypto total.
6. Liabilities total.
7. Monthly income.
8. Monthly expenses.
9. Savings rate.
10. Budget status.
11. Upcoming recurring bills/income.
12. Open data quality issues.
13. Latest import status.
14. Latest backup status.

### 21.4 Charts

Required charts:

1. Net worth over time.
2. Monthly income vs expenses.
3. Asset allocation pie chart.
4. Account balances over time.
5. Investment value over time.
6. Crypto allocation.
7. Contributions over time.
8. Spending by category.

Every chart must expose data as-of date and warnings when source data is incomplete.

---

## 22. API Requirements

All endpoints are local FastAPI endpoints under `/api`.

### 22.1 Health and App

```text
GET  /api/health
GET  /api/app/status
POST /api/daily-refresh
```

### 22.2 Accounts

```text
GET    /api/accounts
POST   /api/accounts
GET    /api/accounts/{account_id}
PATCH  /api/accounts/{account_id}
DELETE /api/accounts/{account_id}
GET    /api/accounts/{account_id}/balances
POST   /api/accounts/{account_id}/balances
GET    /api/accounts/{account_id}/valuation
```

### 22.3 Transactions

```text
GET   /api/transactions
POST  /api/transactions
GET   /api/transactions/{transaction_id}
PATCH /api/transactions/{transaction_id}
DELETE /api/transactions/{transaction_id}
POST  /api/transactions/{transaction_id}/split
POST  /api/transactions/{transaction_id}/mark-reviewed
POST  /api/transactions/{transaction_id}/hide
POST  /api/transactions/{transaction_id}/unhide
```

### 22.4 Categories and Rules

```text
GET   /api/category-groups
POST  /api/category-groups
GET   /api/categories
POST  /api/categories
PATCH /api/categories/{category_id}
GET   /api/rules
POST  /api/rules
PATCH /api/rules/{rule_id}
POST  /api/rules/{rule_id}/preview
POST  /api/rules/{rule_id}/apply
```

### 22.5 Imports

```text
POST /api/imports/upload
GET  /api/imports
GET  /api/imports/{import_batch_id}
POST /api/imports/{import_batch_id}/map
POST /api/imports/{import_batch_id}/validate
POST /api/imports/{import_batch_id}/apply-rules
POST /api/imports/{import_batch_id}/detect-duplicates
POST /api/imports/{import_batch_id}/detect-transfers
GET  /api/imports/{import_batch_id}/staged-rows
PATCH /api/imports/{import_batch_id}/staged-rows/{row_id}
POST /api/imports/{import_batch_id}/commit
POST /api/imports/{import_batch_id}/rollback
GET  /api/import-mapping-presets
POST /api/import-mapping-presets
PATCH /api/import-mapping-presets/{preset_id}
```

### 22.6 Reconciliation

```text
GET  /api/account-statements
POST /api/account-statements
GET  /api/account-statements/{statement_id}
PATCH /api/account-statements/{statement_id}
POST /api/reconciliation/run
GET  /api/reconciliation/{reconciliation_run_id}
POST /api/reconciliation/{reconciliation_run_id}/accept-difference
```

### 22.7 Holdings, Instruments, and Prices

```text
GET  /api/instruments
POST /api/instruments
PATCH /api/instruments/{instrument_id}
GET  /api/holdings
POST /api/holdings/manual-snapshot
GET  /api/holdings/history
GET  /api/prices
POST /api/prices/refresh
POST /api/prices/manual
GET  /api/allocation
POST /api/allocation/overrides
PATCH /api/allocation/overrides/{override_id}
```

### 22.8 Coinbase

```text
GET  /api/coinbase/status
POST /api/coinbase/configure
DELETE /api/coinbase/configure
POST /api/coinbase/sync
GET  /api/coinbase/sync-runs
```

### 22.9 Budgets

```text
GET  /api/budget-periods
POST /api/budget-periods
PATCH /api/budget-periods/{period_id}
POST /api/budget-periods/{period_id}/close
GET  /api/budgets
POST /api/budgets
PATCH /api/budgets/{budget_plan_id}
GET  /api/rollovers
POST /api/rollovers/adjust
GET  /api/sinking-funds
POST /api/sinking-funds
PATCH /api/sinking-funds/{fund_id}
```

### 22.10 Recurring

```text
GET  /api/recurring
POST /api/recurring/detect
POST /api/recurring
PATCH /api/recurring/{recurring_id}
GET  /api/recurring/calendar
```

### 22.11 Goals

```text
GET  /api/goals
POST /api/goals
PATCH /api/goals/{goal_id}
POST /api/goals/{goal_id}/links
DELETE /api/goals/{goal_id}/links/{link_id}
GET  /api/goals/{goal_id}/progress
```

### 22.12 Liabilities

```text
GET  /api/liabilities
POST /api/liabilities
PATCH /api/liabilities/{liability_id}
GET  /api/liabilities/{liability_id}/terms
POST /api/liabilities/{liability_id}/terms
GET  /api/liabilities/payoff-plan
POST /api/liabilities/payment-allocation
```

### 22.13 Reports and Monthly Review

```text
GET  /api/reports/net-worth
GET  /api/reports/cash-flow
GET  /api/reports/spending-by-category
GET  /api/reports/account-balances
GET  /api/reports/investment-value
GET  /api/reports/allocation
GET  /api/monthly-review/{yyyy_mm}
POST /api/monthly-review/{yyyy_mm}/finalize
POST /api/monthly-review/{yyyy_mm}/regenerate
```

### 22.14 Data Quality, Backups, Audit, Settings

```text
GET  /api/data-quality/issues
POST /api/data-quality/issues/{issue_id}/ignore
POST /api/data-quality/recompute
GET  /api/backups
POST /api/backups/create
POST /api/backups/restore
GET  /api/audit-log
GET  /api/settings
PATCH /api/settings
POST /api/maintenance/vacuum
```

---

## 23. Data Freshness and Daily Update Behavior

Because V1 has no required background scheduler:

1. The app checks daily refresh status when opened.
2. If no refresh has run today, the dashboard prompts or runs configured safe refreshes.
3. Safe refreshes include price refresh, Coinbase read-only sync, and daily snapshot creation.
4. User can manually run refresh anytime.
5. If app is closed, no background work is expected.
6. Missed days can be manually backfilled only where data is available.

Freshness thresholds:

| Data type | Default stale threshold |
|---|---|
| Cash balances | 7 days |
| Credit card balances | 7 days |
| Brokerage holdings | 7 days |
| Prices for stocks/ETFs | 3 market days |
| Crypto prices | 2 days |
| Ledger manual holdings | 14 days |
| Liabilities | 14 days |
| Cost basis | No stale threshold, but quality matters |

Stale data must create warnings, not silent assumptions.

---

## 24. Reporting and Calculation Rules

### 24.1 Net Worth

Net worth must use account valuation methods and must prevent double counting.

Required report metadata:

1. As-of date.
2. Account count included/excluded.
3. Stale account count.
4. Missing account valuation count.
5. Unreconciled account count.
6. Confidence.

### 24.2 Asset Allocation

```text
allocation_value(asset_class) = sum(market_value for holdings classified in asset_class)
allocation_percent = allocation_value / total_allocated_assets
```

Rules:

1. Liabilities are not included in asset allocation unless explicitly showing balance sheet allocation.
2. Unknown asset classes appear as Other/Needs Classification.
3. Stale holdings/prices must show warnings.

### 24.3 Investment Value

```text
holding_market_value = quantity * price
```

or imported market value if provided and trusted.

If imported market value differs significantly from calculated value, show data quality issue.

### 24.4 Budget Variance

```text
variance = available_budget - actual_spending
```

For income categories:

```text
income_variance = actual_income - planned_income
```

### 24.5 Debt Payoff

Debt payoff projections must identify:

1. Exact vs estimated values.
2. APR assumptions.
3. Payment allocation assumptions.
4. Missing terms.
5. Confidence.

---

## 25. Testing Requirements

### 25.1 Backend Unit Tests

Must test:

1. Money math uses cents/Decimal and avoids float errors.
2. Net worth valuation methods.
3. Double-count prevention.
4. Cash flow transfer exclusion.
5. Split transaction totals.
6. Budget rollover calculations.
7. Sinking fund calculations.
8. Gain/loss with verified basis.
9. Gain/loss blocked/warned with missing/incomplete basis.
10. Debt payoff projections with missing APR/payment warnings.
11. Data confidence aggregation.

### 25.2 Import Tests

Must test:

1. CSV mapping auto-detection.
2. Mapping preset versioning.
3. Sign normalization.
4. Date parsing.
5. Duplicate detection.
6. Transfer detection.
7. Staged row edits.
8. Commit atomicity.
9. Rollback manifest correctness.
10. Backup before commit.
11. Reconciliation matched/mismatch cases.

### 25.3 API Tests

Must test:

1. CRUD endpoints for core entities.
2. Workflow endpoints for imports/reconciliation/monthly review/backups.
3. Error handling.
4. Validation errors.
5. No external network calls during core tests.

### 25.4 Frontend Tests

Must test:

1. Import preview states.
2. Data quality warnings.
3. Dashboard cards.
4. Empty states.
5. Transaction split form.
6. Transfer confirmation flow.
7. Monthly review finalize/regenerate warnings.
8. Backup/restore UI warnings.

### 25.5 Acceptance Test Dataset

The project must include a small synthetic dataset with:

1. Checking account transactions.
2. Credit card transactions and payment transfer.
3. Brokerage holdings with cost basis.
4. Crypto holding with incomplete cost basis.
5. Manual Ledger holding.
6. Liability with APR.
7. Budget categories.
8. Recurring bill.
9. Reconciliation match and mismatch examples.
10. Duplicate import example.

---

## 26. Error Handling Requirements

1. Errors must be specific and actionable.
2. Import errors must identify row and field.
3. Backup failures must block import commit.
4. Restore failures must not corrupt current database.
5. API failures must not erase existing data.
6. Price refresh failure must mark stale/failed prices, not zero them.
7. Coinbase sync failure must preserve previous data and show last successful sync.
8. Validation errors must use consistent response schema.

Standard error response:

```json
{
  "error_code": "IMPORT_VALIDATION_FAILED",
  "message": "3 rows are missing required amount values.",
  "details": {},
  "recommended_action": "Review staged rows and either fix or skip them."
}
```

---

## 27. Windows Launcher Requirements

`launch.bat` must:

1. Check for Python environment.
2. Check/install backend dependencies if configured.
3. Check for Node dependencies if configured.
4. Run database migrations.
5. Start FastAPI backend bound to localhost.
6. Start or serve React frontend.
7. Open browser to local app URL.
8. Write logs to `data/logs/`.
9. Avoid exposing the app on the network by default.
10. Display helpful errors if dependencies are missing.

Production-style local serving is preferred over development servers once packaged locally.

---

## 28. Definition of Done

The app is not personal-production ready until all of these are true:

1. Launches locally on Windows from `launch.bat`.
2. Database migrations run cleanly from an empty database.
3. SQLite WAL, foreign keys, and backup safety are implemented.
4. Accounts can be created with valuation methods and sign policies.
5. Transaction CSV import is staged, validated, committed, and rollback-capable.
6. Duplicate detection works on repeated imports.
7. Transfer candidates are detected and excluded only when confirmed/high confidence.
8. Manual/imported account balances can be reconciled.
9. Reconciliation mismatch warnings appear on dashboard/data quality screen.
10. Holdings can be imported or manually entered.
11. Cost basis source/quality appears everywhere gain/loss appears.
12. Net worth avoids double-counting and shows freshness/confidence.
13. Dashboard shows data quality warnings.
14. Budget actuals correctly handle hidden transactions, splits, and confirmed transfers.
15. Monthly review supports draft/finalized/regenerated states.
16. Manual edits are audit-logged.
17. Backup before import works and restore is tested.
18. Price refresh failures do not corrupt values.
19. Coinbase sync is read-only and labels cost basis as incomplete unless verified/imported.
20. Ledger support is manual only and never asks for private data.
21. Financial calculations have unit tests.
22. Synthetic acceptance dataset passes.
23. No core feature requires paid APIs or cloud hosting.
24. No login is required in V1.
25. No background scheduler is required in V1.

---

## 29. Future Enhancements

Future enhancements are explicitly outside V1 unless later requested:

1. Paid aggregation APIs.
2. Mobile app.
3. Packaged Windows `.exe` installer.
4. Full database encryption.
5. Windows Credential Manager integration if not implemented initially.
6. Tax lots.
7. Realized gains/losses.
8. Coinbase tax report import parser.
9. Ledger public wallet address scanning.
10. ETF/mutual fund look-through.
11. Document vault for statements/receipts.
12. Multi-user household mode.
13. Local password/app lock.
14. Scheduled Windows Task Scheduler integration.
15. AI-assisted categorization.
