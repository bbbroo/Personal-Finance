import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingBlock } from "@/components/ui/loading";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCents } from "@/lib/utils";
import type { ApiRecord } from "@/types";
import { PageHeader } from "./PageHeader";

export function Budgets() {
  const query = useQuery({ queryKey: ["budgets"], queryFn: () => api.get<ApiRecord[]>("/budgets") });
  const funds = useQuery({ queryKey: ["sinking-funds"], queryFn: () => api.get<ApiRecord[]>("/sinking-funds") });
  if (query.isLoading) return <LoadingBlock label="Loading budget" />;
  const rows = query.data ?? [];
  return (
    <>
      <PageHeader title="Budget" detail="Budget actuals exclude hidden transactions and confirmed transfers, and rollovers are ledgered when periods close." />
      {!rows.length ? <EmptyState title="No budget plans" detail="Create a budget period and category plans to see variance." /> : (
        <div className="overflow-hidden rounded-lg border bg-card">
          <Table>
            <TableHeader><TableRow><TableHead>Category</TableHead><TableHead>Available</TableHead><TableHead>Actual</TableHead><TableHead>Remaining</TableHead><TableHead>Rollover</TableHead><TableHead>Confidence</TableHead></TableRow></TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={String(row.plan_id)}>
                  <TableCell>{String(row.category_name)}</TableCell>
                  <TableCell>{formatCents(row.available_cents as number)}</TableCell>
                  <TableCell>{formatCents(row.actual_cents as number)}</TableCell>
                  <TableCell>{formatCents(row.remaining_cents as number)}</TableCell>
                  <TableCell>{formatCents(row.ending_rollover_cents as number)}</TableCell>
                  <TableCell><Badge tone="success">{String(row.confidence)}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <h2 className="mb-3 mt-8 text-lg font-semibold">Sinking Funds</h2>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {(funds.data ?? []).map((fund) => (
          <div key={String(fund.id)} className="rounded-lg border bg-card p-4">
            <div className="font-medium">{String(fund.name)}</div>
            <div className="mt-2 text-sm text-muted-foreground">Target {formatCents(fund.target_cents as number)}</div>
            <div className="text-sm">Current {formatCents(fund.current_balance_cents as number | null)}</div>
            <Badge tone={fund.confidence === "unknown" ? "warning" : "neutral"}>{String(fund.confidence)}</Badge>
          </div>
        ))}
      </div>
    </>
  );
}
