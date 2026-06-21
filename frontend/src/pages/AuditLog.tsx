import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingBlock } from "@/components/ui/loading";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ApiRecord } from "@/types";
import { PageHeader } from "./PageHeader";

export function AuditLog() {
  const query = useQuery({ queryKey: ["audit"], queryFn: () => api.get<ApiRecord[]>("/audit-log") });
  if (query.isLoading) return <LoadingBlock label="Loading audit log" />;
  const rows = query.data ?? [];
  return (
    <>
      <PageHeader title="Audit Log" detail="Manual edits, import commits, rollbacks, rules, reconciliation, budgets, and review finalization are recorded here." />
      {!rows.length ? <EmptyState title="No audit entries" detail="Financial changes will appear here." /> : (
        <div className="overflow-hidden rounded-lg border bg-card">
          <Table>
            <TableHeader><TableRow><TableHead>Time</TableHead><TableHead>Entity</TableHead><TableHead>Action</TableHead><TableHead>Source</TableHead></TableRow></TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={String(row.id)}>
                  <TableCell>{String(row.created_at)}</TableCell>
                  <TableCell>{String(row.entity_type)} / {String(row.entity_id).slice(0, 8)}</TableCell>
                  <TableCell><Badge tone="info">{String(row.action)}</Badge></TableCell>
                  <TableCell>{String(row.source)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </>
  );
}
