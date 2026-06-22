import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "./PageHeader";

type Capability = {
  id: number;
  area: string;
  item: string;
  status: "implemented" | "partial" | "planned";
  next: string;
};

const capabilities: Capability[] = [
  { id: 8, area: "Transactions", item: "Guided transaction correction UI", status: "partial", next: "Replace normalized JSON edits with field-level date, amount, merchant, category, status, and transfer controls." },
  { id: 9, area: "Reconciliation", item: "Reconciliation Center", status: "partial", next: "Add statement ending balance/date, cleared transaction workflow, variance, finalized reconciliation, and later-change warnings." },
  { id: 10, area: "Trust", item: "Account health dashboard", status: "partial", next: "Combine last import, last reconciliation, balance source, open issues, and report inclusion per account." },
  { id: 11, area: "Onboarding", item: "First-run setup wizard", status: "planned", next: "Create guided setup: accounts, import, balances, liabilities, holdings, categories, data quality, first backup." },
  { id: 12, area: "Categories", item: "Category management", status: "planned", next: "Create parent/child category editor, merge/rename, budget flags, and hidden/excluded behavior." },
  { id: 13, area: "Transactions", item: "Bulk categorization", status: "planned", next: "Add multi-select transactions and bulk category, merchant, tag, note, and review-status actions." },
  { id: 14, area: "Rules", item: "Auto-categorization rules", status: "planned", next: "Add exact/contains/regex rules with preview and priority." },
  { id: 15, area: "Rules", item: "Rule suggestion engine", status: "planned", next: "Suggest rules from repeated manual categorization patterns." },
  { id: 16, area: "Merchants", item: "Merchant cleanup system", status: "planned", next: "Create canonical merchant mapping and merge flow." },
  { id: 17, area: "Transactions", item: "Transaction search and filters", status: "partial", next: "Expand filters for status, source, duplicate, transfer, hidden, import batch, and amount ranges." },
  { id: 18, area: "Transactions", item: "Transaction detail drawer", status: "planned", next: "Show raw import row, normalized values, splits, audit history, duplicate and transfer links." },
  { id: 19, area: "Transactions", item: "Transaction splitting", status: "planned", next: "Add split model/UI with category allocations and audit history." },
  { id: 20, area: "Transfers", item: "Transfer matching center", status: "partial", next: "Promote Import Wizard transfer review into a cross-account transfer-matching page." },
  { id: 21, area: "Transfers", item: "Transfer rules", status: "planned", next: "Create rules for credit card payments, bank transfers, brokerage transfers, Venmo, and savings transfers." },
  { id: 22, area: "Duplicates", item: "Duplicate resolution center", status: "partial", next: "Add global unresolved duplicate queue outside import batches." },
  { id: 23, area: "Imports", item: "Import mapping presets", status: "planned", next: "Save mapping templates by institution and account." },
  { id: 24, area: "Imports", item: "Import preview profiles", status: "planned", next: "Detect preset changes, missing columns, and header drift before remap." },
  { id: 25, area: "Imports", item: "Import file history", status: "partial", next: "Expose checksum, mapping, status, commit, rollback, and warnings per uploaded file." },
  { id: 26, area: "Imports", item: "Import rollback details", status: "partial", next: "Show exact removed transactions/splits/balances and pre-rollback backup reference." },
  { id: 27, area: "Imports", item: "Post-import review checklist", status: "partial", next: "Guide categorization, reconciliation, budget update, and data quality after commit." },
  { id: 28, area: "Accounts", item: "Balance snapshots", status: "partial", next: "Add richer UI for manual balances and confidence history." },
  { id: 29, area: "Accounts", item: "Balance history chart", status: "planned", next: "Chart balances by account and account group." },
  { id: 30, area: "Reports", item: "Net worth drilldown", status: "partial", next: "Break down by account group, asset/liability class, and source confidence." },
  { id: 31, area: "Reports", item: "Net worth confidence", status: "partial", next: "Make stale prices, missing balances, unreconciled accounts, and excluded accounts visible." },
  { id: 32, area: "Reports", item: "Cash-flow report", status: "partial", next: "Add recurring vs one-time, category, merchant, and confidence drilldown." },
  { id: 33, area: "Reports", item: "Spending report", status: "planned", next: "Build category, merchant, account, monthly trend, and budget relationship views." },
  { id: 34, area: "Reports", item: "Income report", status: "planned", next: "Track paychecks, refunds, reimbursements, irregular income, and transfer exclusions." },
  { id: 35, area: "Reports", item: "Refund/reimbursement handling", status: "partial", next: "Tie refunds back to original transactions and categories when possible." },
  { id: 36, area: "Budgets", item: "Budget creation workflow", status: "planned", next: "Create budget period and category-plan UI with copy-from-prior-month." },
  { id: 37, area: "Budgets", item: "Budget editing workflow", status: "planned", next: "Allow planned amount/category/rollover edits with audit history." },
  { id: 38, area: "Budgets", item: "Budget close workflow", status: "partial", next: "Expose close month, rollovers, sinking funds, and locked period behavior in UI." },
  { id: 39, area: "Budgets", item: "Budget variance explanations", status: "partial", next: "Add transaction-based explanations for over/under budget categories." },
  { id: 40, area: "Budgets", item: "Budget transaction drilldown", status: "planned", next: "Click category actuals to show underlying transactions." },
  { id: 41, area: "Planning", item: "Safe-to-spend calculation", status: "planned", next: "Estimate available cash after bills, goals, debts, and budgets." },
  { id: 42, area: "Planning", item: "Sinking fund planner", status: "partial", next: "Add contribution planning and target date projections." },
  { id: 43, area: "Recurring", item: "Bill calendar", status: "partial", next: "Show upcoming recurring bills, due dates, expected income, and debt payments." },
  { id: 44, area: "Recurring", item: "Recurring transaction review", status: "partial", next: "Confirm, ignore, rename, categorize, and set expected next date." },
  { id: 45, area: "Recurring", item: "Subscription tracker", status: "planned", next: "Track subscriptions, cancellation notes, renewal dates, and price increases." },
  { id: 46, area: "Recurring", item: "Price increase detection", status: "planned", next: "Flag recurring charges that increased compared with prior periods." },
  { id: 47, area: "Recurring", item: "Missing recurring bill warning", status: "planned", next: "Warn when expected bills or income do not appear." },
  { id: 48, area: "Goals", item: "Goal planning calculators", status: "planned", next: "Compute required monthly contribution, projected completion date, and funding gap." },
  { id: 49, area: "Goals", item: "Emergency fund calculator", status: "planned", next: "Estimate target based on monthly expenses and desired months covered." },
  { id: 50, area: "Goals", item: "Goal priority system", status: "planned", next: "Rank goals and allocate extra cash by priority." },
  { id: 51, area: "Goals", item: "Account-linked goal progress", status: "partial", next: "Use linked accounts and allocations to calculate automatic goal progress." },
  { id: 52, area: "Debt", item: "Debt payoff schedule", status: "partial", next: "Add month-by-month interest, principal, remaining balance, and payoff date." },
  { id: 53, area: "Debt", item: "Debt scenario comparison", status: "partial", next: "Add minimum-only, snowball, avalanche, custom order, and extra-payment scenarios." },
  { id: 54, area: "Debt", item: "Promo APR tracking", status: "partial", next: "Add expiration reminders and fallback APR warnings in UI." },
  { id: 55, area: "Debt", item: "Loan amortization support", status: "planned", next: "Support fixed loans with amortization schedule and acceleration scenarios." },
  { id: 56, area: "Debt", item: "Credit card utilization tracking", status: "planned", next: "Track per-card and total utilization warning thresholds." },
  { id: 57, area: "Investments", item: "Investment holdings UI", status: "partial", next: "Add lots, cost basis, current value, allocation, gain/loss, and stale price warnings." },
  { id: 58, area: "Investments", item: "Manual price update workflow", status: "partial", next: "Show affected holdings and confidence impact after price updates." },
  { id: 59, area: "Investments", item: "Asset allocation report", status: "partial", next: "Support asset class/account/tax status/custom grouping." },
  { id: 60, area: "Investments", item: "Cost basis confidence", status: "partial", next: "Flag missing/estimated cost basis and explain gain/loss uncertainty." },
  { id: 61, area: "Investments", item: "Realized gain/loss tracking", status: "planned", next: "Track sales and cost-basis method assumptions." },
  { id: 62, area: "Exports", item: "Tax export support", status: "planned", next: "Export dividends, interest, gains, giving, business/medical categories." },
  { id: 63, area: "Transactions", item: "Custom tags", status: "planned", next: "Add flexible labels for moving, vacation, reimbursable, tax, shared, apartment, car." },
  { id: 64, area: "Sharing", item: "Shared expense tracking", status: "planned", next: "Track split expenses, owed amounts, reimbursements, and outstanding balances." },
  { id: 65, area: "Sharing", item: "Reimbursement workflow", status: "planned", next: "Mark reimbursable, partial, full, or written off." },
  { id: 66, area: "Documents", item: "Attachments", status: "planned", next: "Attach local PDFs/images to transactions, statements, bills, receipts, and docs." },
  { id: 67, area: "Documents", item: "Statement storage", status: "planned", next: "Store statement metadata and local file references." },
  { id: 68, area: "Audit", item: "Audit history UI", status: "partial", next: "Add readable grouped activity feed and safety-event filters." },
  { id: 69, area: "Audit", item: "Before/after diff viewer", status: "planned", next: "Render audited JSON changes as plain-English changes." },
  { id: 70, area: "Reports", item: "Report snapshot history", status: "partial", next: "Save and compare net worth, cash flow, budgets, debt, holdings, and data quality snapshots." },
  { id: 71, area: "Reports", item: "Source-change warnings", status: "partial", next: "Show exact changed sources and impacted reports after finalization." },
  { id: 72, area: "Period Close", item: "Locked periods", status: "planned", next: "Require extra confirmation and reason for edits in finalized months." },
  { id: 73, area: "Adjustments", item: "Manual adjustment workflow", status: "planned", next: "Support balance/category/reconciliation adjustments with reason fields." },
  { id: 74, area: "Data Quality", item: "Data Quality Center v2", status: "partial", next: "Add stale imports, uncategorized spending, missing balances, unmatched transfers, and suspicious amount checks." },
  { id: 75, area: "Data Quality", item: "Data quality fix buttons", status: "partial", next: "Route each issue directly to the corrective workflow." },
  { id: 76, area: "Trust", item: "Confidence Center", status: "partial", next: "Promote trust checklist into a full page with backup/import/reconciliation/report confidence." },
  { id: 77, area: "Dashboard", item: "Dashboard next-action panel", status: "partial", next: "Wire Review Queue counts and top actions into dashboard." },
  { id: 78, area: "Dashboard", item: "Dashboard customization", status: "planned", next: "Allow hiding/reordering cards and choosing preferred summary period." },
  { id: 79, area: "Reminders", item: "Local reminders", status: "planned", next: "Track import, backup, bill, close, reconciliation, and stale-price reminders." },
  { id: 80, area: "Backups", item: "Backup picker", status: "planned", next: "Select known backups from history rather than pasting paths." },
  { id: 81, area: "Backups", item: "Backup verification", status: "partial", next: "Add verify-only action for manifest/hash/schema/integrity/app-table checks." },
  { id: 82, area: "Backups", item: "Restore preview", status: "planned", next: "Show app version, schema, date, size, hash, manifest, row counts, and warnings before restore." },
  { id: 83, area: "Backups", item: "Backup schedule recommendation", status: "planned", next: "Add local schedule recommendation/reminder UI." },
  { id: 84, area: "Exports", item: "Export system", status: "planned", next: "Export transactions, budgets, reports, audit logs, and backups to CSV/JSON." },
  { id: 85, area: "Release", item: "Clean release packaging", status: "partial", next: "Keep polishing clean ZIP exclusions and release checks." },
  { id: 86, area: "Release", item: "App versioning and changelog", status: "planned", next: "Show app version, migration version, build date, and changelog." },
  { id: 87, area: "Database", item: "Database maintenance page", status: "planned", next: "Show database size, backup count, import count, vacuum/checkpoint, and health." },
  { id: 88, area: "Settings", item: "Local settings page", status: "partial", next: "Add currency, date format, fiscal month, default account, backup path, and theme." },
  { id: 89, area: "Privacy", item: "Privacy/security page", status: "planned", next: "Explain local-only files, data paths, backups, and no external transmission." },
  { id: 90, area: "Privacy", item: "Optional app lock", status: "planned", next: "Add casual local passcode/app-lock option if desired." },
  { id: 91, area: "Storage", item: "Data directory selector", status: "planned", next: "Choose DB, backup, imports, exports, and attachment directories." },
  { id: 92, area: "Profiles", item: "Multi-profile support", status: "planned", next: "Support personal, household, demo, or archived profiles." },
  { id: 93, area: "Demo", item: "Demo mode", status: "planned", next: "Ship sample/demo data for learning without real imports." },
  { id: 94, area: "UX", item: "Empty-state action buttons", status: "partial", next: "Add direct action buttons to every empty state." },
  { id: 95, area: "UX", item: "Help/explanation tooltips", status: "planned", next: "Explain reconciliation, rollover, sinking fund, cost basis, confidence, audit, duplicate, transfer." },
  { id: 96, area: "UX", item: "Keyboard shortcuts", status: "planned", next: "Add next row, skip, import, confirm duplicate, confirm transfer, save edit." },
  { id: 97, area: "Performance", item: "Large-table performance", status: "planned", next: "Add pagination, virtualization, batch updates, and faster large import review." },
  { id: 98, area: "Recovery", item: "Error recovery UX", status: "partial", next: "Every failure should say what changed, what did not, backup status, and next action." },
  { id: 99, area: "Errors", item: "Backend error catalog", status: "planned", next: "Document error codes, meanings, and recommended user actions." },
  { id: 100, area: "API", item: "API consistency pass", status: "planned", next: "Standardize response shapes, error shapes, naming, status codes, and audit behavior." },
  { id: 101, area: "Backend", item: "Service-layer cleanup", status: "partial", next: "Move remaining business logic out of routes and into services." },
  { id: 102, area: "Tests", item: "More backend financial correctness tests", status: "partial", next: "Expand imports, transfers, refunds, budgets, reconciliation, debt, holdings, backup, and confidence tests." },
  { id: 103, area: "Tests", item: "End-to-end smoke tests", status: "planned", next: "Simulate create account → import → commit → categorize → reconcile → budget → review → backup." },
  { id: 104, area: "Tests", item: "Realistic sample CSV fixtures", status: "partial", next: "Add Chase, Amex, Capital One, Fidelity, Venmo, PayPal, and generic CSV fixtures." },
  { id: 105, area: "Imports", item: "Import parser hardening", status: "partial", next: "Handle date formats, signs, debit/credit, pending/posted, encoding, blank rows, duplicate headers." },
  { id: 106, area: "Imports", item: "Institution-specific adapters", status: "planned", next: "Add named adapters for common financial exports." },
  { id: 107, area: "Imports", item: "Pending vs posted handling", status: "planned", next: "Avoid double counting pending and posted versions of the same transaction." },
  { id: 108, area: "Accounts", item: "Account exclusion rules", status: "planned", next: "Exclude accounts from net worth, cash flow, budgets, debt payoff, or dashboard." },
  { id: 109, area: "Transactions", item: "Hidden transaction rules", status: "partial", next: "Formalize report treatment for hidden transactions." },
  { id: 110, area: "Transfers", item: "Transfer exclusion consistency", status: "partial", next: "Keep transfers consistent across cash flow, budgets, income, expenses, net worth, and reviews." },
  { id: 111, area: "Review", item: "Review queue", status: "implemented", next: "Continue adding sources: reconciliation, categories, stale imports, uncategorized, recurring warnings." },
  { id: 112, area: "Explainability", item: "Explain this number", status: "planned", next: "Make major numbers clickable with sources, formulas, confidence, and exclusions." },
  { id: 113, area: "Reports", item: "Report notes", status: "planned", next: "Add notes to reviews, budgets, goals, net worth snapshots, and debt plans." },
  { id: 114, area: "Forecasting", item: "Forecasting", status: "planned", next: "Forecast future cash from income, bills, debts, budgets, and goals." },
  { id: 115, area: "Planning", item: "Scenario planning", status: "planned", next: "Model rent increases, extra debt payments, savings changes, and moving costs." },
  { id: 116, area: "Household", item: "Household/shared finance mode", status: "planned", next: "Add personal/shared spending, partner splits, reimbursements, and shared goals." },
  { id: 117, area: "UX", item: "Mobile-friendly responsive pass", status: "partial", next: "Improve small browser/window layouts for dense tables and cards." },
  { id: 118, area: "Accessibility", item: "Accessibility pass", status: "partial", next: "Improve keyboard navigation, focus, dialogs, table labels, contrast, and screen reader labels." },
  { id: 119, area: "UX", item: "UI polish pass", status: "partial", next: "Refine spacing, cards, table density, badges, empty states, and visual hierarchy." },
  { id: 120, area: "Docs", item: "User documentation", status: "partial", next: "Document setup, imports, backups, restore, reconciliation, budgeting, and monthly close." },
  { id: 121, area: "Docs", item: "Developer documentation", status: "partial", next: "Document architecture, schema, tests, migrations, dev, packaging, and safety design." },
  { id: 122, area: "Release", item: "Safety checklist before release", status: "partial", next: "Convert checklist into a runnable/reviewable release gate." },
  { id: 123, area: "Migrations", item: "Migration rollback strategy", status: "partial", next: "Ensure each migration has downgrade or documented no-downgrade reason." },
  { id: 124, area: "Docs", item: "Schema diagram", status: "planned", next: "Generate readable schema diagram for app entities." },
  { id: 125, area: "Portability", item: "Data export/import portability", status: "planned", next: "Make moving to another machine clear and testable." },
  { id: 126, area: "Packaging", item: "Local app packaging", status: "planned", next: "Package desktop executable/installer with clear data-folder behavior." },
  { id: 127, area: "Developer", item: "Developer reliability dashboard", status: "partial", next: "Show backend status, database path, migration version, build version, and demo mode." },
  { id: 128, area: "Workflow", item: "Daily/weekly/monthly workflow", status: "partial", next: "Create polished daily review, weekly import/reconcile, monthly close, quarterly review, yearly export workflows." }
];

const statusRank = { implemented: 0, partial: 1, planned: 2 } as const;

function tone(status: Capability["status"]) {
  return status === "implemented" ? "success" : status === "partial" ? "warning" : "neutral";
}

export function BuildoutPlan() {
  const counts = capabilities.reduce<Record<string, number>>((acc, capability) => ({ ...acc, [capability.status]: (acc[capability.status] ?? 0) + 1 }), {});
  const groups = [...new Set(capabilities.map((capability) => capability.area))];
  return (
    <>
      <PageHeader title="Build-out Plan" detail="A living implementation tracker for the 100+ finance-app capabilities, with honest status and the next concrete step for each item." />
      <div className="mb-4 grid gap-3 md:grid-cols-4">
        <Card><CardHeader><CardTitle>Implemented</CardTitle></CardHeader><CardContent><div className="text-2xl font-semibold">{counts.implemented ?? 0}</div></CardContent></Card>
        <Card><CardHeader><CardTitle>Partial</CardTitle></CardHeader><CardContent><div className="text-2xl font-semibold">{counts.partial ?? 0}</div></CardContent></Card>
        <Card><CardHeader><CardTitle>Planned</CardTitle></CardHeader><CardContent><div className="text-2xl font-semibold">{counts.planned ?? 0}</div></CardContent></Card>
        <Card><CardHeader><CardTitle>Total Tracked</CardTitle></CardHeader><CardContent><div className="text-2xl font-semibold">{capabilities.length}</div></CardContent></Card>
      </div>
      <div className="space-y-6">
        {groups.map((group) => {
          const rows = capabilities.filter((capability) => capability.area === group).sort((a, b) => statusRank[a.status] - statusRank[b.status] || a.id - b.id);
          return (
            <Card key={group}>
              <CardHeader><CardTitle>{group}</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {rows.map((capability) => (
                  <div key={capability.id} className="rounded-md border p-3">
                    <div className="flex flex-wrap items-center gap-2"><Badge tone="neutral">#{capability.id}</Badge><Badge tone={tone(capability.status)}>{capability.status}</Badge><span className="font-medium">{capability.item}</span></div>
                    <p className="mt-2 text-sm text-muted-foreground">{capability.next}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </>
  );
}
