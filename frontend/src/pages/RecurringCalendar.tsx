import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingBlock } from "@/components/ui/loading";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCents } from "@/lib/utils";
import type { ApiRecord } from "@/types";
import { PageHeader } from "./PageHeader";

export function RecurringCalendar() {
  const query = useQuery({ queryKey: ["recurring"], queryFn: () => api.get<ApiRecord[]>("/recurring/calendar") });
  if (query.isLoading) return <LoadingBlock label="Loading recurring calendar" />;
  const rows = query.data ?? [];
  return (
    <>
      <PageHeader title="Recurring Calendar" detail="Expected bills and income show amount confidence and status instead of pretending forecasts are exact." />
      {!rows.length ? <EmptyState title="No recurring items" detail="Run recurring detection or add manual recurring transactions." /> : (
        <div className="overflow-hidden rounded-lg border bg-card">
          <Table>
            <TableHeader><TableRow><TableHead>Merchant</TableHead><TableHead>Next date</TableHead><TableHead>Amount</TableHead><TableHead>Cadence</TableHead><TableHead>Status</TableHead><TableHead>Confidence</TableHead></TableRow></TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={String(row.id)}>
                  <TableCell className="font-medium">{String(row.merchant_name)}</TableCell>
                  <TableCell>{String(row.next_expected_date ?? "Unknown")}</TableCell>
                  <TableCell>{formatCents(row.expected_amount_cents as number | null)}</TableCell>
                  <TableCell>{String(row.cadence)}</TableCell>
                  <TableCell><Badge tone={row.status === "active" ? "success" : "neutral"}>{String(row.status)}</Badge></TableCell>
                  <TableCell><Badge tone={row.confidence === "verified" ? "success" : "neutral"}>{String(row.confidence)}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </>
  );
}
