import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingBlock } from "@/components/ui/loading";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCents } from "@/lib/utils";
import type { ApiRecord } from "@/types";
import { PageHeader } from "./PageHeader";

export function Holdings() {
  const query = useQuery({ queryKey: ["holdings"], queryFn: () => api.get<ApiRecord[]>("/holdings") });
  if (query.isLoading) return <LoadingBlock label="Loading holdings" />;
  const rows = query.data ?? [];
  return (
    <>
      <PageHeader title="Holdings" detail="Cost basis quality is shown anywhere gain/loss could otherwise look more certain than it is." />
      {!rows.length ? <EmptyState title="No holdings" detail="Add manual holdings or import a brokerage holdings CSV." /> : (
        <div className="overflow-hidden rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Quantity</TableHead>
                <TableHead>Market value</TableHead>
                <TableHead>Cost basis</TableHead>
                <TableHead>Gain/Loss</TableHead>
                <TableHead>Basis quality</TableHead>
                <TableHead>Valuation</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={String(row.id)}>
                  <TableCell>{String(row.snapshot_date)}</TableCell>
                  <TableCell>{String(row.quantity_decimal)}</TableCell>
                  <TableCell>{formatCents(row.market_value_cents as number | null)}</TableCell>
                  <TableCell>{formatCents(row.cost_basis_cents as number | null)}</TableCell>
                  <TableCell>{formatCents(row.unrealized_gain_loss_cents as number | null)}</TableCell>
                  <TableCell><Badge tone={row.cost_basis_quality === "verified" || row.cost_basis_quality === "user_entered" ? "success" : "warning"}>{String(row.cost_basis_quality)}</Badge></TableCell>
                  <TableCell><Badge tone={row.valuation_quality === "current" ? "success" : "warning"}>{String(row.valuation_quality)}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </>
  );
}
