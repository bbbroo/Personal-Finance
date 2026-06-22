import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { ApiError } from "@/components/ui/api-error";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingBlock } from "@/components/ui/loading";
import type { Account, ApiRecord, DataQualityIssue, ImportBatch, StagedRow, Transaction, TrustChecklist } from "@/types";
import { PageHeader } from "./PageHeader";

type ReviewItem = {
  id: string;
  area: string;
  title: string;
  detail: string;
  severity: "critical" | "warning" | "info" | "success";
  action: string;
  link: string;
};

function tone(severity: ReviewItem["severity"]) {
  if (severity === "critical") return "danger";
  if (severity === "warning") return "warning";
  if (severity === "success") return "success";
  return "info";
}

function issueSeverity(severity: string): ReviewItem["severity"] {
  return severity === "critical" || severity === "error" ? "critical" : severity === "warning" ? "warning" : "info";
}

function checkStatus(status: string): ReviewItem["severity"] {
  return ["ok", "committed", "verified", "high", "reconciled"].includes(status) ? "success" : status === "missing" || status === "error" || status === "mismatch" ? "critical" : "warning";
}

function trustItems(trust?: TrustChecklist): ReviewItem[] {
  if (!trust) return [];
  return Object.entries(trust.checks)
    .filter(([, check]) => !["ok", "committed"].includes(String(check.status)))
    .map(([key, check]) => ({
      id: `trust-${key}`,
      area: "Confidence",
      title: key.replaceAll("_", " "),
      detail: Object.entries(check).filter(([field]) => field !== "status").slice(0, 3).map(([field, value]) => `${field}: ${String(value)}`).join(" · ") || `Status is ${String(check.status)}`,
      severity: checkStatus(String(check.status)),
      action: "Open Confidence Center / source page",
      link: key.includes("backup") ? "#backups" : key.includes("import") ? "#import" : key.includes("quality") ? "#quality" : key.includes("debt") ? "#liabilities" : key.includes("reconciliation") ? "#reconciliation" : "#dashboard"
    }));
}

function importItems(imports: ImportBatch[], stagedRows: StagedRow[]): ReviewItem[] {
  const latest = imports[0];
  const items: ReviewItem[] = [];
  const unresolvedRows = stagedRows.filter((row) => row.validation_status === "error" || row.user_action === "needs_review" || row.duplicate_status === "possible_duplicate" || row.transfer_status === "suggested_transfer");
  if (!latest) {
    items.push({ id: "import-none", area: "Imports", title: "No imports yet", detail: "Create your first CSV import so reports are based on actual account activity.", severity: "warning", action: "Start Import Wizard", link: "#import" });
  } else if (latest.status !== "committed") {
    items.push({ id: "import-open", area: "Imports", title: `Import batch ${latest.status}`, detail: `${latest.original_filename}: ${latest.row_count} rows, ${latest.error_count} errors, ${latest.duplicate_row_count} duplicate candidates.`, severity: latest.error_count > 0 ? "critical" : "warning", action: "Finish Import Wizard", link: "#import" });
  }
  if (latest && latest.status !== "committed") {
    items.push({ id: "import-stale", area: "Imports", title: "Import is not finalized", detail: "Uncommitted imports should be committed, rolled back, or intentionally left in review so reports do not feel more complete than they are.", severity: "warning", action: "Resolve import batch", link: "#import" });
  }
  if (unresolvedRows.length) {
    items.push({ id: "import-rows", area: "Imports", title: `${unresolvedRows.length} staged row(s) need review`, detail: "Rows have validation errors, possible duplicates, suggested transfers, or needs-review actions.", severity: unresolvedRows.some((row) => row.validation_status === "error") ? "critical" : "warning", action: "Review staged rows", link: "#import" });
  }
  return items;
}

function accountItems(accounts: Account[]): ReviewItem[] {
  if (!accounts.length) {
    return [{ id: "account-none", area: "Setup", title: "No accounts configured", detail: "Create accounts before importing transactions, balances, liabilities, or holdings.", severity: "critical", action: "Create accounts", link: "#accounts" }];
  }
  return accounts
    .filter((account) => account.valuation_method === "manual" || account.valuation_method === "unknown")
    .slice(0, 5)
    .map((account) => ({ id: `account-${account.id}`, area: "Accounts", title: `${account.name} needs balance confidence`, detail: `Valuation method is ${account.valuation_method}. Add/import balance snapshots or reconcile statements.`, severity: "warning", action: "Review account", link: "#accounts" }));
}

function qualityItems(issues: DataQualityIssue[]): ReviewItem[] {
  return issues
    .filter((issue) => issue.status === "open")
    .map((issue) => ({ id: `quality-${issue.id}`, area: "Data Quality", title: issue.title, detail: issue.recommended_action || issue.description, severity: issueSeverity(issue.severity), action: "Fix issue", link: "#quality" }));
}

function transactionItems(transactions: Transaction[]): ReviewItem[] {
  const needsReview = transactions.filter((txn) => txn.review_status !== "reviewed");
  const possibleDuplicates = transactions.filter((txn) => txn.duplicate_status !== "unique");
  const suggestedTransfers = transactions.filter((txn) => txn.transfer_status === "suggested_transfer");
  const uncategorized = transactions.filter((txn) => !txn.category_id && !txn.category_name && txn.transaction_type !== "transfer");
  const items: ReviewItem[] = [];
  if (needsReview.length) items.push({ id: "txn-review", area: "Transactions", title: `${needsReview.length} transaction(s) need review`, detail: "Transactions are not marked reviewed yet. Confirm category, transfer, duplicate, and report treatment.", severity: "warning", action: "Review transactions", link: "#transactions" });
  if (uncategorized.length) items.push({ id: "txn-uncategorized", area: "Transactions", title: `${uncategorized.length} uncategorized transaction(s)`, detail: "Uncategorized transactions reduce budget, cash-flow, and spending report confidence.", severity: "warning", action: "Categorize transactions", link: "#transactions" });
  if (possibleDuplicates.length) items.push({ id: "txn-duplicates", area: "Duplicates", title: `${possibleDuplicates.length} duplicate candidate transaction(s)`, detail: "Resolve duplicate candidates so cash flow and budgets are not overstated.", severity: "warning", action: "Resolve duplicates", link: "#transactions" });
  if (suggestedTransfers.length) items.push({ id: "txn-transfers", area: "Transfers", title: `${suggestedTransfers.length} suggested transfer(s)`, detail: "Suggested transfers are still included until confirmed, so income/expense reports may be noisy.", severity: "warning", action: "Confirm or reject transfers", link: "#transactions" });
  return items;
}

function reconciliationItems(statements: ApiRecord[], accounts: Account[]): ReviewItem[] {
  if (!accounts.length) return [];
  const items: ReviewItem[] = [];
  if (!statements.length) {
    items.push({ id: "reconcile-none", area: "Reconciliation", title: "No statements reconciled", detail: "Add statement ending balances to prove app balances match real accounts.", severity: "warning", action: "Create statement", link: "#reconciliation" });
    return items;
  }
  const unresolved = statements.filter((statement) => !["reconciled", "accepted_difference"].includes(String(statement.status)));
  if (unresolved.length) {
    items.push({ id: "reconcile-unresolved", area: "Reconciliation", title: `${unresolved.length} statement(s) not reconciled`, detail: "Run reconciliation, fix differences, or explicitly accept known differences with audit history.", severity: unresolved.some((row) => row.status === "mismatch") ? "critical" : "warning", action: "Open Reconciliation", link: "#reconciliation" });
  }
  return items;
}

function backupItems(backups: ApiRecord[]): ReviewItem[] {
  if (backups.length) return [];
  return [{ id: "backup-none", area: "Backups", title: "No successful backup recorded", detail: "Create a manual backup before major imports, restore tests, or month close.", severity: "critical", action: "Create backup", link: "#backups" }];
}

export function ReviewQueue() {
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: () => api.get<Account[]>("/accounts") });
  const issues = useQuery({ queryKey: ["issues"], queryFn: () => api.get<DataQualityIssue[]>("/data-quality/issues") });
  const imports = useQuery({ queryKey: ["imports"], queryFn: () => api.get<ImportBatch[]>("/imports") });
  const activeBatchId = imports.data?.[0]?.id;
  const stagedRows = useQuery({ queryKey: ["review-staged-rows", activeBatchId], queryFn: () => api.stagedRows(activeBatchId ?? ""), enabled: Boolean(activeBatchId) });
  const backups = useQuery({ queryKey: ["backups"], queryFn: () => api.get<ApiRecord[]>("/backups") });
  const trust = useQuery({ queryKey: ["trust-checklist"], queryFn: () => api.get<TrustChecklist>("/reports/trust-checklist") });
  const transactions = useQuery({ queryKey: ["transactions"], queryFn: () => api.get<Transaction[]>("/transactions") });
  const statements = useQuery({ queryKey: ["statements"], queryFn: () => api.get<ApiRecord[]>("/account-statements") });

  if (accounts.isLoading || issues.isLoading || imports.isLoading || backups.isLoading || trust.isLoading || stagedRows.isLoading || transactions.isLoading || statements.isLoading) return <LoadingBlock label="Building review queue" />;
  const errors = [accounts.error, issues.error, imports.error, stagedRows.error, backups.error, trust.error, transactions.error, statements.error].filter(Boolean);
  const accountRows = accounts.data ?? [];
  const items = [
    ...accountItems(accountRows),
    ...importItems(imports.data ?? [], stagedRows.data ?? []),
    ...qualityItems(issues.data ?? []),
    ...transactionItems(transactions.data ?? []),
    ...reconciliationItems(statements.data ?? [], accountRows),
    ...backupItems(backups.data ?? []),
    ...trustItems(trust.data)
  ].sort((a, b) => ({ critical: 0, warning: 1, info: 2, success: 3 }[a.severity] - { critical: 0, warning: 1, info: 2, success: 3 }[b.severity]));
  const counts = items.reduce<Record<string, number>>((acc, item) => ({ ...acc, [item.severity]: (acc[item.severity] ?? 0) + 1 }), {});

  return (
    <>
      <PageHeader title="Review Queue" detail="One place for import rows, transaction cleanup, reconciliation, stale data, missing backups, account confidence, and report trust warnings." />
      {errors.map((error, index) => <ApiError key={index} error={error} title="Review queue source failed" />)}
      <div className="mb-4 grid gap-3 md:grid-cols-4">
        <Card><CardHeader><CardTitle>Critical</CardTitle></CardHeader><CardContent><span className="text-2xl font-semibold">{counts.critical ?? 0}</span></CardContent></Card>
        <Card><CardHeader><CardTitle>Warnings</CardTitle></CardHeader><CardContent><span className="text-2xl font-semibold">{counts.warning ?? 0}</span></CardContent></Card>
        <Card><CardHeader><CardTitle>Info</CardTitle></CardHeader><CardContent><span className="text-2xl font-semibold">{counts.info ?? 0}</span></CardContent></Card>
        <Card><CardHeader><CardTitle>Total</CardTitle></CardHeader><CardContent><span className="text-2xl font-semibold">{items.length}</span></CardContent></Card>
      </div>
      {!items.length ? <EmptyState title="No review items" detail="Imports, transactions, reconciliation, backups, data quality, and trust checks are currently clear." /> : (
        <div className="space-y-3">
          {items.map((item) => (
            <a key={item.id} href={item.link} className="focus-ring block rounded-lg border bg-card p-4 hover:bg-muted/50">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2"><Badge tone={tone(item.severity)}>{item.severity}</Badge><Badge tone="neutral">{item.area}</Badge><span className="font-medium">{item.title}</span></div>
                  <p className="mt-2 text-sm text-muted-foreground">{item.detail}</p>
                </div>
                <span className="text-sm font-medium text-primary">{item.action}</span>
              </div>
            </a>
          ))}
        </div>
      )}
    </>
  );
}
