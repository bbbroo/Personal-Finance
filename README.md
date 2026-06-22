# Local Finance

Local Finance is a Windows-first, local-only personal finance app built from the A+ spec in `local_finance_app_spec_A_plus.md`.

It uses FastAPI, SQLite, SQLAlchemy 2.x, Alembic, React, TypeScript, Tailwind, shadcn-style local UI components, and Recharts. Core financial calculations live in the backend.

## Launch

Double-click:

```bat
launch.bat
```

The launcher creates `backend\.venv`, installs dependencies, runs Alembic migrations, starts FastAPI at `http://127.0.0.1:8000`, starts Vite at `http://127.0.0.1:5173`, writes logs to `data\logs`, and opens the browser.

Manual launch:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

## Tests

Backend:

```powershell
cd backend
python -m pytest
```

Frontend:

```powershell
cd frontend
npm test
npm run build
```

## Demo Data

On first backend startup, the app seeds a local demo dataset with checking, credit card, brokerage, Coinbase, Ledger, liability, budget, recurring, goal, holding, price, and reconciliation examples.

Set this before startup to disable demo seeding:

```powershell
$env:LOCAL_FINANCE_DEMO_SEED_ENABLED="false"
```

## CSV Import

Use Import Center:

1. Select a target account.
2. Choose a CSV file.
3. Edit or paste a JSON column mapping and reparse the original CSV if auto-detection is wrong.
4. Review staged rows, validation warnings, duplicate status, transfer status, and row actions.
5. Edit normalized staged rows, skip rows, confirm/ignore duplicates, and confirm/reject transfer candidates.
6. Commit only after preview.
7. Roll back committed imports from the same import batch.

Sample files are in `sample_imports\`. Import `checking_transactions.csv`, then import `duplicate_checking_transactions.csv` to see duplicate detection.

Every staged-row edit is audit logged. Every committed import creates a pre-import SQLite backup and an import rollback manifest.

## Backup And Restore

Backups are listed in the Backups screen and stored under `data\backups`.

Backup manifests include app version, schema version, timestamp, backup type, database SHA-256, source path, and notes. Restore validates the manifest, hash, and SQLite integrity before replacing the active database, creates a pre-restore backup first, blocks writes during restore, and asks for an app restart after the database is swapped.

## Prices And Coinbase

Price refresh is local-first. V1 marks stale/missing prices and supports manual prices; no external price provider is enabled by default. Coinbase sync is intentionally labeled not implemented in this build. Do not enter private keys, seed phrases, or write-enabled credentials. Coinbase cost basis remains incomplete unless verified manually or imported from a trusted tax/report export.

## Financial Integrity Notes

- USD money is stored as integer cents.
- Quantities and prices use Decimal-safe strings.
- Missing money data is never silently treated as zero.
- Net worth uses account valuation methods and avoids double-counting holdings plus balances.
- Confirmed transfers are excluded from income/expense totals; suggestions stay visible.
- Cost basis source and quality are stored on every holding.
- Coinbase API-derived basis is incomplete unless verified or imported from a tax/report export.
- Ledger is manual holdings only in V1; no private keys or seed phrases.
- Manual edits, imports, rollbacks, rules, reconciliation, and review actions are audit logged.

## Clean Distributable ZIP

Create release zips from the repository root so local databases, backups, logs, caches, virtual environments, `node_modules`, and Git metadata are excluded:

```powershell
.\scripts\create-clean-zip.ps1
```

The script writes `release\local-finance-clean.zip` by default and excludes `.git`, `.ai-bridge`, `backend\.venv`, `frontend\node_modules`, `frontend\dist`, `frontend\=`, TypeScript build cache files, generated Vite config artifacts, `data\finance.sqlite3*`, `data\backups`, `data\imports`, `data\exports`, `data\logs`, `data\secrets`, and common cache folders.

If Git is available and you only want tracked source files, this command is also safe:

```powershell
$dest = "release\local-finance-clean.zip"
New-Item -ItemType Directory -Force release | Out-Null
if (Test-Path $dest) { Remove-Item $dest }
git archive --format=zip --output=$dest HEAD
```

## Troubleshooting

- Backend errors: check `data\logs\backend.log` and `data\logs\backend-uvicorn.log`.
- Frontend errors: check `data\logs\frontend-vite.log`.
- If ports are occupied, stop the existing process or run backend/frontend manually on different ports.
- If the database is missing or invalid, run `cd backend; python -m alembic upgrade head`.
- If imports fail, fix or skip rows with fatal errors before committing.
- If frontend dependencies behave strangely because of a copied or zipped `node_modules`, delete `frontend\node_modules` and run `npm install` again.

## Current Limits

This is a working V1 local app, not a packaged installer. Optional external price/Coinbase APIs are stubbed behind explicit settings and do not fetch network data by default. Full tax-lot accounting, realized gains, paid aggregation, and mobile apps are outside V1.
