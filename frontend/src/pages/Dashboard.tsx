import { useQuery } from "@tanstack/react-query";

import { MetricCard } from "@/components/cards/MetricCard";
import { AllocationChart } from "@/components/charts/AllocationChart";
import { NetWorthChart } from "@/components/charts/NetWorthChart";
import { WarningList } from "@/components/quality/WarningList";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingBlock } from "@/components/ui/loading";
import { api } from "@/api/client";
import { formatCents, formatPercent } from "@/lib/utils";
import type { DashboardReport, DataQualityIssue, ImportBatch, TrustChecklist } from "@/types";
import { PageHeader } from "./PageHeader";

const trustLabels: Record<string, string> = {
  last_successful_backup: "Last successful backup",
  last_import_commit: "Last import commit",
  data_quality: "Data quality",
  prices: "Prices",
  reconciliation: "Reconciliation",
  monthly_review: "Monthly review",
  debt_payoff: "Debt payoff",
  net_worth: "Net worth",
  cash_flow: "Cash flow"
};

type ActionItem = { label: string; detail: string; href: string; severity: "danger" | "warning" | "info" | "success" };

function buildNextActions(openIssues: DataQualityIssue[], latestImport: ImportBatch | undefined, trust: TrustChecklist | undefined): ActionItem[] {
  const actions: ActionItem[] = [];
  if (latestImport && latestImport.status !== "committed") actions.push({ label: "Finish current import", detail: `${latestImport.original_filename} is ${latestImport.status}.`, href: "#import", severity: latestImport.error_count > 0 ? "danger" : "warning" });
  if (!latestImport) actions.push({ label: "Start first import", detail: "Import transactions so reports use real activity.", href: "#import", severity: "warning" });
  if (openIssues.length) actions.push({ label: "Fix data quality issues", detail: `${openIssues.length} open issue(s) affect report confidence.`, href: "#quality", severity: "warning" });
  const backupStatus = trust?.checks.last_successful_backup?.status;
  if (backupStatus && backupStatus !== "ok") actions.push({ label: "Create or verify backup", detail: `Backup status is ${String(backupStatus)}.`, href: "#backups", severity: "danger" });
  const reconciliationStatus = trust?.checks.reconciliation?.status;
  if (reconciliationStatus && reconciliationStatus !== "ok") actions.push({ label: "Reconcile accounts", detail: `Reconciliation status is ${String(reconciliationStatus)}.`, href: "#reconciliation", severity: "warning" });
  actions.push({ label: "Open Review Queue", detail: "See the full prioritized list across imports, transactions, backups, and reports.", href: "#review", severity: "info" });
  return actions.slice(0, 5);
}

export function Dashboard() {
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: () => api.get<DashboardReport>("/reports/dashboard") });
  const trust = useQuery({ queryKey: ["trust-checklist"], queryFn: () => api.get<TrustChecklist>("/reports/trust-checklist") });
  const issues = useQuery({ queryKey: ["issues"], queryFn: () => api.get<DataQualityIssue[]>("/data-quality/issues") });
  const imports = useQuery({ queryKey: ["imports"], queryFn: () => api.get<ImportBatch[]>("/imports") });

  if (dashboard.isLoading) return <LoadingBlock label="Loading dashboard" />;
  if (dashboard.isError || !dashboard.data) return <div>Dashboard failed to load.</div>;

  const report = dashboard.data;
  const latestImport = imports.data?.[0];
  const openIssues = issues.data?.filter((issue) => issue.status === "open") ?? [];
  const trustChecks = trust.data?.checks ?? {};
  const nextActions = buildNextActions(openIssues, latestImport, trust.data);

  return (
    <>
      <PageHeader
        title="Dashboard"
        detail="Every major number comes from backend calculations and carries confidence or warnings when the source data is incomplete."
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Net Worth" value={formatCents(report.net_worth.net_worth_cents)} confidence={report.net_worth.confidence} detail="Double-count protected" />
        <MetricCard title="Monthly Income" value={formatCents(report.cash_flow.income_cents)} confidence={report.cash_flow.confidence} detail="Transfers excluded only when confirmed" />
        <MetricCard title="Monthly Expenses" value={formatCents(report.cash_flow.expenses_cents)} confidence={report.cash_flow.confidence} />
        <MetricCard title="Savings Rate" value={formatPercent(report.cash_flow.savings_rate_decimal)} confidence={report.cash_flow.confidence} />
        <MetricCard title="Cash" value={formatCents(Number(report.cards.cash_balance_cents ?? 0))} />
        <MetricCard title="Investments" value={formatCents(Number(report.cards.investments_total_cents ?? 0))} />
        <MetricCard title="Crypto" value={formatCents(Number(report.cards.crypto_total_cents ?? 0))} />
        <MetricCard title="Liabilities" value={formatCents(Number(report.cards.liabilities_total_cents ?? 0))} />
      </div>
      <div className="mt-6 grid gap-4 xl:grid-cols-[1.4fr_0.8fr]">
        <Card>
          <CardHeader>
            <CardTitle>Net Worth History</CardTitle>
          </CardHeader>
          <CardContent>
            <NetWorthChart data={report.history} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Asset Allocation</CardTitle>
          </CardHeader>
          <CardContent>
            <AllocationChart allocation={report.allocation} />
          </CardContent>
        </Card>
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Next Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {nextActions.map((action) => (
              <a key={action.label} href={action.href} className="focus-ring block rounded-md border p-3 hover:bg-muted/50">
                <div className="flex items-center justify-between gap-2"><span className="font-medium">{action.label}</span><Badge tone={action.severity}>{action.severity}</Badge></div>
                <p className="mt-1 text-muted-foreground">{action.detail}</p>
              </a>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Trust Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between"><span>Overall status</span><Badge tone={trust.data?.overall_status === "ok" ? "success" : "warning"}>{trust.data?.overall_status ?? "unknown"}</Badge></div>
            <div className="flex justify-between"><span>Warning count</span><Badge tone={(trust.data?.warning_count ?? 0) ? "warning" : "success"}>{trust.data?.warning_count ?? 0}</Badge></div>
            <a href="#review" className="block rounded-md bg-muted p-3 text-primary">Open full Review Queue</a>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Trust Checklist</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {Object.entries(trustLabels).map(([key, label]) => {
              const check = trustChecks[key];
              return (
                <div key={key} className="flex items-center justify-between gap-3">
                  <span>{label}</span>
                  <Badge tone={check?.status === "ok" || check?.status === "committed" ? "success" : check ? "warning" : "neutral"}>{String(check?.status ?? "unknown")}</Badge>
                </div>
              );
            })}
            <div className="rounded-md bg-muted p-3 text-muted-foreground">
              Local-only mode is active. Optional external APIs are disabled unless configured in Settings.
            </div>
          </CardContent>
        </Card>
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Visible Data Quality Warnings</CardTitle>
          </CardHeader>
          <CardContent>
            <WarningList warnings={[...report.net_worth.metadata.warnings, ...report.allocation.warnings, ...report.cash_flow.warnings]} />
          </CardContent>
        </Card>
      </div>
      <div className="sr-only">Open quality issues {openIssues.length}</div>
      <div className="sr-only">Latest import {latestImport?.status ?? "none"}</div>
    </>
  );
}
