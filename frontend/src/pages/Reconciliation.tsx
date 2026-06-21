import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingBlock } from "@/components/ui/loading";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCents } from "@/lib/utils";
import type { ApiRecord } from "@/types";
import { PageHeader } from "./PageHeader";

export function Reconciliation() {
  const client = useQueryClient();
  const statements = useQuery({ queryKey: ["statements"], queryFn: () => api.get<ApiRecord[]>("/account-statements") });
  const run = useMutation({
    mutationFn: (statementId: string) => api.post<ApiRecord>("/reconciliation/run", { statement_id: statementId }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["statements"] });
      client.invalidateQueries({ queryKey: ["issues"] });
    }
  });
  if (statements.isLoading) return <LoadingBlock label="Loading reconciliation" />;
  const rows = statements.data ?? [];
  return (
    <>
      <PageHeader title="Reconciliation" detail="Statement mismatches create data-quality issues until fixed or explicitly accepted." />
      {!rows.length ? <EmptyState title="No statements" detail="Create or import statements before running reconciliation." /> : (
        <div className="overflow-hidden rounded-lg border bg-card">
          <Table>
            <TableHeader><TableRow><TableHead>Period</TableHead><TableHead>Opening</TableHead><TableHead>Ending</TableHead><TableHead>Status</TableHead><TableHead /></TableRow></TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={String(row.id)}>
                  <TableCell>{String(row.period_start)} to {String(row.period_end)}</TableCell>
                  <TableCell>{formatCents(row.opening_balance_cents as number | null)}</TableCell>
                  <TableCell>{formatCents(row.ending_balance_cents as number | null)}</TableCell>
                  <TableCell><Badge tone={row.status === "reconciled" ? "success" : row.status === "mismatch" ? "danger" : "warning"}>{String(row.status)}</Badge></TableCell>
                  <TableCell className="text-right"><Button size="sm" variant="outline" onClick={() => run.mutate(String(row.id))}>Run</Button></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </>
  );
}
