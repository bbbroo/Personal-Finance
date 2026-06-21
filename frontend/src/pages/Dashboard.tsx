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
import type { DashboardReport, DataQualityIssue, ImportBatch } from "@/types";
import { PageHeader } from "./PageHeader";

export function Dashboard() {
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: () => api.get<DashboardReport>("/reports/dashboard") });
  const issues = useQuery({ queryKey: ["issues"], queryFn: () => api.get<DataQualityIssue[]>("/data-quality/issues") });
  const imports = useQuery({ queryKey: ["imports"], queryFn: () => api.get<ImportBatch[]>("/imports") });

  if (dashboard.isLoading) return <LoadingBlock label="Loading dashboard" />;
  if (dashboard.isError || !dashboard.data) return <div>Dashboard failed to load.</div>;

  const report = dashboard.data;
  const latestImport = imports.data?.[0];
  const openIssues = issues.data?.filter((issue) => issue.status === "open") ?? [];

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
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Visible Data Quality Warnings</CardTitle>
          </CardHeader>
          <CardContent>
            <WarningList warnings={[...report.net_worth.metadata.warnings, ...report.allocation.warnings, ...report.cash_flow.warnings]} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Workflow Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between gap-3">
              <span>Open quality issues</span>
              <Badge tone={openIssues.length ? "warning" : "success"}>{openIssues.length}</Badge>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span>Latest import</span>
              <Badge tone={latestImport?.status === "committed" ? "success" : "neutral"}>{latestImport?.status ?? "none"}</Badge>
            </div>
            <div className="rounded-md bg-muted p-3 text-muted-foreground">
              Local-only mode is active. Optional external APIs are disabled unless configured in Settings.
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
