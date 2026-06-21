import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { LoadingBlock } from "@/components/ui/loading";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCents } from "@/lib/utils";
import type { Account, ApiRecord } from "@/types";
import { PageHeader } from "./PageHeader";

function dollarsToCents(value: string) {
  return value ? Math.round(Number(value) * 100) : null;
}

export function Reconciliation() {
  const client = useQueryClient();
  const [form, setForm] = useState({
    account_id: "",
    period_start: new Date().toISOString().slice(0, 8) + "01",
    period_end: new Date().toISOString().slice(0, 10),
    opening_balance: "",
    ending_balance: ""
  });
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: () => api.get<Account[]>("/accounts") });
  const statements = useQuery({ queryKey: ["statements"], queryFn: () => api.get<ApiRecord[]>("/account-statements") });
  const createStatement = useMutation({
    mutationFn: () =>
      api.post<ApiRecord>("/account-statements", {
        account_id: form.account_id,
        period_start: form.period_start,
        period_end: form.period_end,
        opening_balance_cents: dollarsToCents(form.opening_balance),
        ending_balance_cents: dollarsToCents(form.ending_balance),
        source: "manual"
      }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["statements"] })
  });
  const run = useMutation({
    mutationFn: (statementId: string) => api.post<ApiRecord>("/reconciliation/run", { statement_id: statementId }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["statements"] });
      client.invalidateQueries({ queryKey: ["issues"] });
    }
  });
  const accept = useMutation({
    mutationFn: (runId: string) => api.post<ApiRecord>(`/reconciliation/${runId}/accept-difference`),
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
      <Card className="mb-4">
        <CardHeader><CardTitle>Create Statement</CardTitle></CardHeader>
        <CardContent className="grid gap-2 md:grid-cols-3">
          <Select value={form.account_id} onChange={(event) => setForm({ ...form, account_id: event.target.value })}>
            <option value="">Account</option>
            {(accounts.data ?? []).map((account) => <option value={account.id} key={account.id}>{account.name}</option>)}
          </Select>
          <Input type="date" value={form.period_start} onChange={(event) => setForm({ ...form, period_start: event.target.value })} />
          <Input type="date" value={form.period_end} onChange={(event) => setForm({ ...form, period_end: event.target.value })} />
          <Input placeholder="Opening balance dollars" value={form.opening_balance} onChange={(event) => setForm({ ...form, opening_balance: event.target.value })} />
          <Input placeholder="Ending balance dollars" value={form.ending_balance} onChange={(event) => setForm({ ...form, ending_balance: event.target.value })} />
          <Button onClick={() => createStatement.mutate()} disabled={!form.account_id || !form.opening_balance || !form.ending_balance}>Create</Button>
          {createStatement.error ? <div className="text-sm text-danger">{createStatement.error.message}</div> : null}
        </CardContent>
      </Card>
      {run.data ? (
        <div className="mb-4 rounded-lg border bg-card p-4 text-sm">
          <div className="font-medium">Latest run: {String(run.data.status)} with difference {formatCents(run.data.difference_cents as number | null)}</div>
          {run.data.status === "mismatch" ? <Button className="mt-2" size="sm" variant="outline" onClick={() => accept.mutate(String(run.data?.id))}>Accept Explicit Difference</Button> : null}
        </div>
      ) : null}
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
