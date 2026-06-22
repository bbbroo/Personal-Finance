import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { ApiError } from "@/components/ui/api-error";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { LoadingBlock } from "@/components/ui/loading";
import { MutationMessage } from "@/components/ui/mutation-message";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCents } from "@/lib/utils";
import type { Account, ApiRecord } from "@/types";
import { PageHeader } from "./PageHeader";

function dollarsToCents(value: string) {
  return value ? Math.round(Number(value) * 100) : null;
}

function statusTone(status: unknown) {
  const value = String(status);
  if (["reconciled", "accepted_difference"].includes(value)) return "success";
  if (value === "mismatch") return "danger";
  return "warning";
}

export function Reconciliation() {
  const client = useQueryClient();
  const { confirm, dialog } = useConfirmDialog();
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
      client.invalidateQueries({ queryKey: ["trust-checklist"] });
    }
  });
  const accept = useMutation({
    mutationFn: (runId: string) => api.post<ApiRecord>(`/reconciliation/${runId}/accept-difference`),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["statements"] });
      client.invalidateQueries({ queryKey: ["issues"] });
      client.invalidateQueries({ queryKey: ["trust-checklist"] });
    }
  });
  if (statements.isLoading) return <LoadingBlock label="Loading reconciliation" />;
  const rows = statements.data ?? [];
  const reconciled = rows.filter((row) => ["reconciled", "accepted_difference"].includes(String(row.status))).length;
  const mismatches = rows.filter((row) => row.status === "mismatch").length;
  const openStatements = rows.filter((row) => !["reconciled", "accepted_difference"].includes(String(row.status))).length;
  const confirmAcceptDifference = () => {
    if (!run.data?.id) return;
    confirm({
      title: "Accept this reconciliation difference?",
      description: "This should only be used when you reviewed the variance and want the app to record an explicit accepted difference with audit history.",
      confirmLabel: "Accept difference",
      variant: "danger",
      onConfirm: () => accept.mutate(String(run.data?.id))
    });
  };
  return (
    <>
      {dialog}
      <PageHeader title="Reconciliation" detail="Statement mismatches create data-quality issues until fixed or explicitly accepted. Reconciliation proves app balances against real statements." />
      <div className="mb-4 grid gap-3 md:grid-cols-4">
        <Card><CardHeader><CardTitle>Total Statements</CardTitle></CardHeader><CardContent><div className="text-2xl font-semibold">{rows.length}</div></CardContent></Card>
        <Card><CardHeader><CardTitle>Reconciled</CardTitle></CardHeader><CardContent><div className="text-2xl font-semibold">{reconciled}</div></CardContent></Card>
        <Card><CardHeader><CardTitle>Open</CardTitle></CardHeader><CardContent><div className="text-2xl font-semibold">{openStatements}</div></CardContent></Card>
        <Card><CardHeader><CardTitle>Mismatches</CardTitle></CardHeader><CardContent><div className="text-2xl font-semibold">{mismatches}</div></CardContent></Card>
      </div>
      <Card className="mb-4">
        <CardHeader><CardTitle>Create Statement</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-2 md:grid-cols-3">
            <Select value={form.account_id} onChange={(event) => setForm({ ...form, account_id: event.target.value })}>
              <option value="">Account</option>
              {(accounts.data ?? []).map((account) => <option value={account.id} key={account.id}>{account.name}</option>)}
            </Select>
            <Input type="date" value={form.period_start} onChange={(event) => setForm({ ...form, period_start: event.target.value })} />
            <Input type="date" value={form.period_end} onChange={(event) => setForm({ ...form, period_end: event.target.value })} />
            <Input placeholder="Opening balance dollars" value={form.opening_balance} onChange={(event) => setForm({ ...form, opening_balance: event.target.value })} />
            <Input placeholder="Ending balance dollars" value={form.ending_balance} onChange={(event) => setForm({ ...form, ending_balance: event.target.value })} />
            <Button onClick={() => createStatement.mutate()} disabled={!form.account_id || !form.opening_balance || !form.ending_balance || createStatement.isPending}>Create</Button>
          </div>
          <MutationMessage isPending={createStatement.isPending} isSuccess={createStatement.isSuccess} pending="Creating statement..." success="Statement created." />
          <ApiError error={createStatement.error} title="Statement creation failed" />
        </CardContent>
      </Card>
      {run.data ? (
        <div className="mb-4 rounded-lg border bg-card p-4 text-sm">
          <div className="font-medium">Latest run: {String(run.data.status)} with difference {formatCents(run.data.difference_cents as number | null)}</div>
          {run.data.status === "mismatch" ? <Button className="mt-2" size="sm" variant="outline" onClick={confirmAcceptDifference} disabled={accept.isPending}>Accept Explicit Difference</Button> : null}
          <MutationMessage isPending={accept.isPending} isSuccess={accept.isSuccess} pending="Accepting reconciliation difference..." success="Difference accepted with audit trail." />
          <ApiError error={accept.error} title="Accept difference failed" />
        </div>
      ) : null}
      <MutationMessage isPending={run.isPending} isSuccess={run.isSuccess} pending="Running reconciliation..." success="Reconciliation run complete." />
      <ApiError error={run.error} title="Reconciliation run failed" />
      {!rows.length ? <EmptyState title="No statements" detail="Create or import statements before running reconciliation." /> : (
        <div className="overflow-hidden rounded-lg border bg-card">
          <Table>
            <TableHeader><TableRow><TableHead>Period</TableHead><TableHead>Opening</TableHead><TableHead>Ending</TableHead><TableHead>Status</TableHead><TableHead>Guidance</TableHead><TableHead /></TableRow></TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={String(row.id)}>
                  <TableCell>{String(row.period_start)} to {String(row.period_end)}</TableCell>
                  <TableCell>{formatCents(row.opening_balance_cents as number | null)}</TableCell>
                  <TableCell>{formatCents(row.ending_balance_cents as number | null)}</TableCell>
                  <TableCell><Badge tone={statusTone(row.status)}>{String(row.status)}</Badge></TableCell>
                  <TableCell className="text-sm text-muted-foreground">{row.status === "mismatch" ? "Fix variance or accept explicitly." : row.status === "reconciled" ? "Statement matches app balance." : "Run reconciliation."}</TableCell>
                  <TableCell className="text-right"><Button size="sm" variant="outline" onClick={() => run.mutate(String(row.id))} disabled={run.isPending}>Run</Button></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </>
  );
}
