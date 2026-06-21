import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { LoadingBlock } from "@/components/ui/loading";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCents } from "@/lib/utils";
import type { Account, ImportBatch, StagedRow } from "@/types";
import { PageHeader } from "./PageHeader";

const DEFAULT_MAPPING = {
  date: "Date",
  posted_date: null,
  description: "Description",
  amount: "Amount",
  debit: null,
  credit: null
};

export function ImportCenter() {
  const client = useQueryClient();
  const [accountId, setAccountId] = useState("");
  const [selectedBatch, setSelectedBatch] = useState<string | null>(null);
  const [mappingText, setMappingText] = useState(JSON.stringify(DEFAULT_MAPPING, null, 2));
  const [mappingError, setMappingError] = useState<string | null>(null);
  const [editingRowId, setEditingRowId] = useState<string | null>(null);
  const [rowJsonText, setRowJsonText] = useState("");
  const [rowEditError, setRowEditError] = useState<string | null>(null);

  const accounts = useQuery({ queryKey: ["accounts"], queryFn: () => api.get<Account[]>("/accounts") });
  const imports = useQuery({ queryKey: ["imports"], queryFn: () => api.get<ImportBatch[]>("/imports") });
  const activeBatchId = selectedBatch ?? imports.data?.[0]?.id ?? null;
  const rows = useQuery({
    queryKey: ["staged-rows", activeBatchId],
    queryFn: () => api.stagedRows(activeBatchId ?? ""),
    enabled: Boolean(activeBatchId)
  });
  const invalidateImport = () => {
    client.invalidateQueries({ queryKey: ["imports"] });
    client.invalidateQueries({ queryKey: ["staged-rows", activeBatchId] });
  };
  const upload = useMutation({
    mutationFn: ({ file, accountId }: { file: File; accountId: string }) => api.uploadImport(file, accountId, "CSV"),
    onSuccess: (batch) => {
      setSelectedBatch(batch.id);
      client.invalidateQueries({ queryKey: ["imports"] });
    }
  });
  const remap = useMutation({
    mutationFn: ({ id, mapping }: { id: string; mapping: Record<string, unknown> }) => api.post<ImportBatch>(`/imports/${id}/map`, mapping),
    onSuccess: invalidateImport
  });
  const updateRow = useMutation({
    mutationFn: ({ rowId, payload }: { rowId: string; payload: Record<string, unknown> }) =>
      api.patch<StagedRow>(`/imports/${activeBatchId}/staged-rows/${rowId}`, payload),
    onSuccess: () => {
      setEditingRowId(null);
      setRowJsonText("");
      setRowEditError(null);
      invalidateImport();
    }
  });
  const commit = useMutation({
    mutationFn: (id: string) => api.post<ImportBatch>(`/imports/${id}/commit`),
    onSuccess: () => {
      invalidateImport();
      client.invalidateQueries({ queryKey: ["transactions"] });
      client.invalidateQueries({ queryKey: ["dashboard"] });
      client.invalidateQueries({ queryKey: ["issues"] });
    }
  });
  const rollback = useMutation({
    mutationFn: (id: string) => api.post<ImportBatch>(`/imports/${id}/rollback`),
    onSuccess: () => {
      invalidateImport();
      client.invalidateQueries({ queryKey: ["transactions"] });
      client.invalidateQueries({ queryKey: ["dashboard"] });
      client.invalidateQueries({ queryKey: ["issues"] });
    }
  });

  if (accounts.isLoading) return <LoadingBlock label="Loading import center" />;
  const accountOptions = accounts.data ?? [];
  const batch = imports.data?.find((item) => item.id === activeBatchId) ?? imports.data?.[0];
  const staged = rows.data ?? [];

  const submitRemap = () => {
    if (!batch) return;
    try {
      setMappingError(null);
      remap.mutate({ id: batch.id, mapping: JSON.parse(mappingText) });
    } catch (error) {
      setMappingError(error instanceof Error ? error.message : "Mapping must be valid JSON.");
    }
  };

  const editRow = (row: StagedRow) => {
    setEditingRowId(row.id);
    setRowJsonText(JSON.stringify(row.normalized_json, null, 2));
    setRowEditError(null);
  };

  const saveRowJson = () => {
    if (!editingRowId) return;
    try {
      setRowEditError(null);
      updateRow.mutate({ rowId: editingRowId, payload: { normalized_json: JSON.parse(rowJsonText) } });
    } catch (error) {
      setRowEditError(error instanceof Error ? error.message : "Row JSON must be valid.");
    }
  };

  return (
    <>
      <PageHeader title="Import Center" detail="CSV rows are staged, mapped, validated, duplicate-checked, transfer-detected, reviewed, backed up, and only then committed." />
      <Card>
        <CardHeader><CardTitle>Upload CSV</CardTitle></CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-[260px_1fr]">
          <Select value={accountId} onChange={(event) => setAccountId(event.target.value)}>
            <option value="">Choose target account</option>
            {accountOptions.map((account) => <option value={account.id} key={account.id}>{account.name}</option>)}
          </Select>
          <Input
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file && accountId) upload.mutate({ file, accountId });
            }}
          />
          {upload.error ? <div className="text-sm text-danger">{upload.error.message}</div> : null}
        </CardContent>
      </Card>
      <div className="mt-6 grid gap-4 lg:grid-cols-[0.65fr_1.35fr]">
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Import Batches</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {(imports.data ?? []).map((item) => (
                <button key={item.id} onClick={() => setSelectedBatch(item.id)} className="focus-ring block w-full rounded-md border p-3 text-left text-sm hover:bg-muted">
                  <div className="flex justify-between gap-2"><span className="font-medium">{item.original_filename}</span><Badge tone={item.status === "committed" ? "success" : item.status === "rolled_back" ? "warning" : "neutral"}>{item.status}</Badge></div>
                  <div className="mt-1 text-muted-foreground">{item.row_count} rows, {item.error_count} errors, {item.duplicate_row_count} duplicates, {item.skipped_row_count ?? 0} skipped</div>
                </button>
              ))}
            </CardContent>
          </Card>
          {batch ? (
            <Card>
              <CardHeader><CardTitle>Edit Mapping</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <textarea className="focus-ring min-h-52 w-full rounded-md border bg-background p-3 font-mono text-xs" value={mappingText} onChange={(event) => setMappingText(event.target.value)} />
                <Button size="sm" variant="outline" onClick={submitRemap} disabled={batch.status === "committed" || remap.isPending}>Reparse With Mapping</Button>
                {mappingError ? <div className="text-sm text-danger">{mappingError}</div> : null}
                {remap.error ? <div className="text-sm text-danger">{remap.error.message}</div> : null}
              </CardContent>
            </Card>
          ) : null}
        </div>
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <CardTitle>Staged Review</CardTitle>
              {batch ? (
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => commit.mutate(batch.id)} disabled={batch.status === "committed" || batch.error_count > 0 || commit.isPending}>Commit</Button>
                  <Button size="sm" variant="outline" onClick={() => rollback.mutate(batch.id)} disabled={batch.status !== "committed" || rollback.isPending}>Rollback</Button>
                </div>
              ) : null}
            </div>
          </CardHeader>
          <CardContent>
            {!batch ? <div className="text-sm text-muted-foreground">No import selected.</div> : null}
            {activeBatchId && rows.isLoading ? <LoadingBlock label="Loading staged rows" /> : null}
            {staged.length ? (
              <div className="overflow-auto rounded-lg border">
                <Table>
                  <TableHeader><TableRow><TableHead>Row</TableHead><TableHead>Date</TableHead><TableHead>Description</TableHead><TableHead>Amount</TableHead><TableHead>Status</TableHead><TableHead>Review</TableHead><TableHead /></TableRow></TableHeader>
                  <TableBody>
                    {staged.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell>{row.row_number}</TableCell>
                        <TableCell>{String(row.normalized_json.transaction_date ?? "")}</TableCell>
                        <TableCell className="min-w-64">
                          <div>{String(row.normalized_json.merchant_name ?? row.normalized_json.original_description ?? "")}</div>
                          {[...(row.errors_json ?? []), ...(row.warnings_json ?? [])].length ? (
                            <div className="mt-1 space-y-1 text-xs text-muted-foreground">
                              {[...(row.errors_json ?? []), ...(row.warnings_json ?? [])].map((message) => <div key={message}>{message}</div>)}
                            </div>
                          ) : null}
                        </TableCell>
                        <TableCell>{formatCents(row.normalized_json.amount_cents as number | null)}</TableCell>
                        <TableCell className="space-y-1">
                          <Badge tone={row.validation_status === "error" ? "danger" : row.validation_status === "warning" ? "warning" : row.validation_status === "skipped" ? "neutral" : "success"}>{row.validation_status}</Badge>
                          <Badge tone={row.duplicate_status === "unique" || row.duplicate_status === "ignored_duplicate" ? "success" : "warning"}>{row.duplicate_status}</Badge>
                          <Badge tone={row.transfer_status === "confirmed_transfer" ? "success" : row.transfer_status === "suggested_transfer" ? "warning" : row.transfer_status === "rejected_transfer" ? "danger" : "neutral"}>{row.transfer_status}</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="grid gap-2">
                            <Select value={row.user_action} onChange={(event) => updateRow.mutate({ rowId: row.id, payload: { user_action: event.target.value } })}>
                              <option value="import">Import</option>
                              <option value="skip">Skip</option>
                              <option value="needs_review">Needs review</option>
                            </Select>
                            <Select value={row.duplicate_status} onChange={(event) => updateRow.mutate({ rowId: row.id, payload: { duplicate_status: event.target.value } })}>
                              <option value="unique">Unique</option>
                              <option value="possible_duplicate">Possible duplicate</option>
                              <option value="confirmed_duplicate">Confirm duplicate</option>
                              <option value="ignored_duplicate">Import anyway</option>
                            </Select>
                            <Select value={row.transfer_status} onChange={(event) => updateRow.mutate({ rowId: row.id, payload: { transfer_status: event.target.value } })}>
                              <option value="not_transfer">Not transfer</option>
                              <option value="suggested_transfer">Suggested</option>
                              <option value="confirmed_transfer">Confirm transfer</option>
                              <option value="rejected_transfer">Reject transfer</option>
                            </Select>
                          </div>
                        </TableCell>
                        <TableCell className="text-right"><Button size="sm" variant="outline" onClick={() => editRow(row)}>Edit JSON</Button></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : null}
            {editingRowId ? (
              <div className="mt-4 rounded-lg border p-3">
                <div className="mb-2 font-medium">Edit Normalized Row</div>
                <textarea className="focus-ring min-h-64 w-full rounded-md border bg-background p-3 font-mono text-xs" value={rowJsonText} onChange={(event) => setRowJsonText(event.target.value)} />
                <div className="mt-2 flex gap-2">
                  <Button size="sm" onClick={saveRowJson}>Save Row Edit</Button>
                  <Button size="sm" variant="outline" onClick={() => setEditingRowId(null)}>Cancel</Button>
                </div>
                {rowEditError ? <div className="mt-2 text-sm text-danger">{rowEditError}</div> : null}
                {updateRow.error ? <div className="mt-2 text-sm text-danger">{updateRow.error.message}</div> : null}
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
