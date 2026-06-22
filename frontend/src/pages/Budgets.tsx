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

function confidenceTone(confidence: unknown) {
  return confidence === "high" || confidence === "verified" || confidence === "exact" ? "success" : confidence === "low" || confidence === "unknown" ? "warning" : "neutral";
}

export function Budgets() {
  const query = useQuery({ queryKey: ["budgets"], queryFn: () => api.get<ApiRecord[]>("/budgets") });
  const funds = useQuery({ queryKey: ["sinking-funds"], queryFn: () => api.get<ApiRecord[]>("/sinking-funds") });
  if (query.isLoading) return <LoadingBlock label="Loading budget" />;
  if (query.isError) return <ApiError error={query.error} title="Budget failed to load" />;
  const rows = query.data ?? [];
  const refundRows = rows.filter((row) => Number(row.actual_cents ?? 0) < 0);
  const transferNote = rows.some((row) => Number(row.transfer_excluded_cents ?? 0) !== 0 || Number(row.confirmed_transfer_excluded_cents ?? 0) !== 0);
  return (
    <>
      <PageHeader title="Budget" detail="Budget actuals exclude hidden transactions and confirmed transfers, and rollovers are ledgered when periods close." />
      {refundRows.length ? (
        <div className="mb-3 rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-950">
          Refunds or reversals are reducing spending in {refundRows.length} budget line(s).
        </div>
      ) : null}
      {transferNote ? (
        <div className="mb-3 rounded-md border border-blue-300 bg-blue-50 p-3 text-sm text-blue-950">
          Confirmed transfers are excluded from budget actuals; suggested transfers remain visible until confirmed.
        </div>
      ) : null}
      {!rows.length ? <EmptyState title="No budget plans" detail="Create a budget period and category plans to see variance." /> : (
        <div className="overflow-hidden rounded-lg border bg-card">
          <Table>
            <TableHeader><TableRow><TableHead>Category</TableHead><TableHead>Available</TableHead><TableHead>Actual</TableHead><TableHead>Remaining</TableHead><TableHead>Rollover</TableHead><TableHead>Confidence</TableHead><TableHead>Notes</TableHead></TableRow></TableHeader>
            <TableBody>
              {rows.map((row) => {
                const warnings = (row.warnings as string[] | undefined) ?? [];
                const notes = [
                  Number(row.actual_cents ?? 0) < 0 ? "Refund/reversal reduced spending" : null,
                  Number(row.confirmed_transfer_excluded_cents ?? row.transfer_excluded_cents ?? 0) !== 0 ? "Confirmed transfers excluded" : null,
                  ...warnings
                ].filter(Boolean);
                return (
                  <TableRow key={String(row.plan_id)}>
                    <TableCell>{String(row.category_name)}</TableCell>
                    <TableCell>{formatCents(row.available_cents as number)}</TableCell>
                    <TableCell>{formatCents(row.actual_cents as number)}</TableCell>
                    <TableCell>{formatCents(row.remaining_cents as number)}</TableCell>
                    <TableCell>{formatCents(row.ending_rollover_cents as number)}</TableCell>
                    <TableCell><Badge tone={confidenceTone(row.confidence)}>{String(row.confidence)}</Badge></TableCell>
                    <TableCell className="max-w-md text-xs text-muted-foreground">{notes.length ? notes.join("; ") : "No warnings"}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
      <h2 className="mb-3 mt-8 text-lg font-semibold">Sinking Funds</h2>
      {funds.isError ? <ApiError error={funds.error} title="Sinking funds failed to load" /> : null}
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {(funds.data ?? []).map((fund) => (
          <div key={String(fund.id)} className="rounded-lg border bg-card p-4">
            <div className="font-medium">{String(fund.name)}</div>
            <div className="mt-2 text-sm text-muted-foreground">Target {formatCents(fund.target_cents as number)}</div>
            <div className="text-sm">Current {formatCents(fund.current_balance_cents as number | null)}</div>
            <Badge tone={confidenceTone(fund.confidence)}>{String(fund.confidence)}</Badge>
          </div>
        ))}
      </div>
    </>
  );
}
