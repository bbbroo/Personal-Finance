import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { ApiError } from "@/components/ui/api-error";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingBlock } from "@/components/ui/loading";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCents } from "@/lib/utils";
import type { ApiRecord } from "@/types";
import { PageHeader } from "./PageHeader";

type PayoffPlan = {
  rows: ApiRecord[];
  warnings: string[];
  summary?: ApiRecord;
  comparison?: Record<string, ApiRecord>;
};

function confidenceTone(confidence: unknown) {
  return confidence === "high" || confidence === "verified" || confidence === "medium" ? "success" : confidence === "low" || confidence === "unknown" ? "warning" : "neutral";
}

export function Liabilities() {
  const query = useQuery({ queryKey: ["liabilities"], queryFn: () => api.get<ApiRecord[]>("/liabilities") });
  const plan = useQuery({ queryKey: ["payoff"], queryFn: () => api.get<PayoffPlan>("/liabilities/payoff-plan") });
  if (query.isLoading) return <LoadingBlock label="Loading liabilities" />;
  if (query.isError) return <ApiError error={query.error} title="Liabilities failed to load" />;
  const rows = query.data ?? [];
  const comparison = plan.data?.comparison ?? {};
  return (
    <>
      <PageHeader title="Liabilities" detail="Liability balances use positive debt amounts, and payoff projections disclose missing APR or payment assumptions." />
      {!rows.length ? <EmptyState title="No liabilities" detail="Add credit cards, loans, or manual debts to plan payoff." /> : (
        <div className="overflow-hidden rounded-lg border bg-card">
          <Table>
            <TableHeader><TableRow><TableHead>Type</TableHead><TableHead>Balance</TableHead><TableHead>Minimum</TableHead><TableHead>Due day</TableHead><TableHead>Confidence</TableHead></TableRow></TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={String(row.id)}>
                  <TableCell>{String(row.liability_type)}</TableCell>
                  <TableCell>{formatCents(row.current_balance_cents as number)}</TableCell>
                  <TableCell>{formatCents(row.minimum_payment_cents as number | null)}</TableCell>
                  <TableCell>{String(row.due_day ?? "Unknown")}</TableCell>
                  <TableCell><Badge tone={confidenceTone(row.confidence)}>{String(row.confidence)}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <h2 className="mb-3 mt-8 text-lg font-semibold">Payoff Plan</h2>
      <div className="rounded-lg border bg-card p-4 text-sm">
        {plan.isLoading ? <LoadingBlock label="Loading payoff plan" /> : null}
        {plan.isError ? <ApiError error={plan.error} title="Payoff plan failed to load" /> : null}
        {plan.data?.summary ? (
          <div className="mb-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-md border p-3">
              <div className="text-xs uppercase text-muted-foreground">Debt payoff confidence</div>
              <Badge tone={confidenceTone(plan.data.summary.confidence)}>{String(plan.data.summary.confidence)}</Badge>
              <div className="mt-1 text-xs text-muted-foreground">{String(plan.data.summary.confidence_explanation ?? "")}</div>
            </div>
            <div className="rounded-md border p-3">
              <div className="text-xs uppercase text-muted-foreground">Estimated months</div>
              <div className="font-semibold">{String(plan.data.summary.total_projected_months ?? "Unknown")}</div>
            </div>
            <div className="rounded-md border p-3">
              <div className="text-xs uppercase text-muted-foreground">Estimated interest</div>
              <div className="font-semibold">{formatCents(plan.data.summary.total_estimated_interest_cents as number | null)}</div>
            </div>
          </div>
        ) : null}
        {Object.keys(comparison).length ? (
          <div className="mb-4 rounded-md border border-blue-300 bg-blue-50 p-3 text-blue-950">
            <div className="font-medium">Snowball vs avalanche comparison</div>
            <div className="mt-1 grid gap-2 md:grid-cols-2">
              {Object.entries(comparison).map(([strategy, item]) => (
                <div key={strategy}>
                  <div className="capitalize">{strategy}</div>
                  <div className="text-xs">Months: {String(item.total_projected_months ?? "Unknown")} · Interest: {formatCents(item.total_estimated_interest_cents as number | null)}</div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
        {(plan.data?.warnings ?? []).map((warning) => <div key={warning} className="text-yellow-900">{warning}</div>)}
        {!plan.data?.warnings.length ? <div className="text-muted-foreground">Projection inputs are available for active liabilities.</div> : null}
        {plan.data?.rows?.length ? (
          <div className="mt-3 overflow-auto">
            <Table>
              <TableHeader><TableRow><TableHead>Order</TableHead><TableHead>Balance</TableHead><TableHead>APR</TableHead><TableHead>Minimum</TableHead><TableHead>Extra</TableHead><TableHead>Months</TableHead><TableHead>Interest</TableHead><TableHead>APR Source</TableHead><TableHead>Quality</TableHead><TableHead>Allocation</TableHead></TableRow></TableHeader>
              <TableBody>
                {plan.data.rows.map((row) => {
                  const allocation = row.allocation_summary as ApiRecord | undefined;
                  return (
                    <TableRow key={String(row.liability_id)}>
                      <TableCell>{String(row.payoff_order ?? "")}</TableCell>
                      <TableCell>{formatCents(row.balance_cents as number)}</TableCell>
                      <TableCell>{String(row.apr_decimal ?? "Missing")}</TableCell>
                      <TableCell>{formatCents(row.minimum_payment_cents as number | null)}</TableCell>
                      <TableCell>{formatCents(row.extra_payment_cents as number | null)}</TableCell>
                      <TableCell>{String(row.projected_payoff_months_with_extra ?? row.projected_payoff_months ?? "Unknown")}</TableCell>
                      <TableCell>{formatCents((row.estimated_interest_cents_with_extra ?? row.estimated_interest_cents) as number | null)}</TableCell>
                      <TableCell>{String(row.apr_source ?? "missing")}</TableCell>
                      <TableCell><Badge tone={row.projection_quality === "terms_verified" ? "success" : "warning"}>{String(row.projection_quality)}</Badge></TableCell>
                      <TableCell className="text-xs text-muted-foreground">{String(allocation?.allocation_count ?? 0)} payment allocation(s){allocation?.has_estimated_allocations ? ", includes estimates" : ""}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        ) : null}
      </div>
    </>
  );
}
