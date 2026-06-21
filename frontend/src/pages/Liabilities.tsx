import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingBlock } from "@/components/ui/loading";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCents } from "@/lib/utils";
import type { ApiRecord } from "@/types";
import { PageHeader } from "./PageHeader";

export function Liabilities() {
  const query = useQuery({ queryKey: ["liabilities"], queryFn: () => api.get<ApiRecord[]>("/liabilities") });
  const plan = useQuery({ queryKey: ["payoff"], queryFn: () => api.get<{ rows: ApiRecord[]; warnings: string[] }>("/liabilities/payoff-plan") });
  if (query.isLoading) return <LoadingBlock label="Loading liabilities" />;
  const rows = query.data ?? [];
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
                  <TableCell><Badge tone={row.confidence === "verified" || row.confidence === "high" ? "success" : "neutral"}>{String(row.confidence)}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <h2 className="mb-3 mt-8 text-lg font-semibold">Payoff Plan</h2>
      <div className="rounded-lg border bg-card p-4 text-sm">
        {(plan.data?.warnings ?? []).map((warning) => <div key={warning} className="text-yellow-900">{warning}</div>)}
        {!plan.data?.warnings.length ? <div className="text-muted-foreground">Projection inputs are available for active liabilities.</div> : null}
        {plan.data?.rows?.length ? (
          <div className="mt-3 overflow-auto">
            <Table>
              <TableHeader><TableRow><TableHead>Balance</TableHead><TableHead>APR</TableHead><TableHead>Months</TableHead><TableHead>Interest</TableHead><TableHead>Quality</TableHead></TableRow></TableHeader>
              <TableBody>
                {plan.data.rows.map((row) => (
                  <TableRow key={String(row.liability_id)}>
                    <TableCell>{formatCents(row.balance_cents as number)}</TableCell>
                    <TableCell>{String(row.apr_decimal ?? "Missing")}</TableCell>
                    <TableCell>{String(row.projected_payoff_months ?? "Unknown")}</TableCell>
                    <TableCell>{formatCents(row.estimated_interest_cents as number | null)}</TableCell>
                    <TableCell><Badge tone={row.projection_quality === "terms_verified" ? "success" : "warning"}>{String(row.projection_quality)}</Badge></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : null}
      </div>
    </>
  );
}
