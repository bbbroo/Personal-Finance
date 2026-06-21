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

export function ImportCenter() {
  const client = useQueryClient();
  const [accountId, setAccountId] = useState("");
  const [selectedBatch, setSelectedBatch] = useState<string | null>(null);
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: () => api.get<Account[]>("/accounts") });
  const imports = useQuery({ queryKey: ["imports"], queryFn: () => api.get<ImportBatch[]>("/imports") });
  const rows = useQuery({
    queryKey: ["staged-rows", selectedBatch],
    queryFn: () => api.stagedRows(selectedBatch ?? ""),
    enabled: Boolean(selectedBatch)
  });
  const upload = useMutation({
    mutationFn: ({ file, accountId }: { file: File; accountId: string }) => api.uploadImport(file, accountId, "CSV"),
    onSuccess: (batch) => {
      setSelectedBatch(batch.id);
      client.invalidateQueries({ queryKey: ["imports"] });
    }
  });
  const commit = useMutation({
    mutationFn: (id: string) => api.post<ImportBatch>(`/imports/${id}/commit`),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["imports"] });
      client.invalidateQueries({ queryKey: ["transactions"] });
      client.invalidateQueries({ queryKey: ["dashboard"] });
      client.invalidateQueries({ queryKey: ["staged-rows", selectedBatch] });
    }
  });
  const rollback = useMutation({
    mutationFn: (id: string) => api.post<ImportBatch>(`/imports/${id}/rollback`),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["imports"] });
      client.invalidateQueries({ queryKey: ["transactions"] });
      client.invalidateQueries({ queryKey: ["dashboard"] });
    }
  });

  if (accounts.isLoading) return <LoadingBlock label="Loading import center" />;
  const accountOptions = accounts.data ?? [];
  const batch = imports.data?.find((item) => item.id === selectedBatch) ?? imports.data?.[0];
  const staged = rows.data ?? [];

  return (
    <>
      <PageHeader title="Import Center" detail="CSV rows are staged, validated, duplicate-checked, transfer-detected, previewed, and backed up before commit." />
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
      <div className="mt-6 grid gap-4 lg:grid-cols-[0.7fr_1.3fr]">
        <Card>
          <CardHeader><CardTitle>Import Batches</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {(imports.data ?? []).map((item) => (
              <button key={item.id} onClick={() => setSelectedBatch(item.id)} className="focus-ring block w-full rounded-md border p-3 text-left text-sm hover:bg-muted">
                <div className="flex justify-between gap-2"><span className="font-medium">{item.original_filename}</span><Badge tone={item.status === "committed" ? "success" : item.status === "rolled_back" ? "warning" : "neutral"}>{item.status}</Badge></div>
                <div className="mt-1 text-muted-foreground">{item.row_count} rows, {item.error_count} errors, {item.duplicate_row_count} duplicates</div>
              </button>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <CardTitle>Staged Preview</CardTitle>
              {batch ? (
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => commit.mutate(batch.id)} disabled={batch.status === "committed" || batch.error_count > 0}>Commit</Button>
                  <Button size="sm" variant="outline" onClick={() => rollback.mutate(batch.id)} disabled={batch.status !== "committed"}>Rollback</Button>
                </div>
              ) : null}
            </div>
          </CardHeader>
          <CardContent>
            {!batch ? <div className="text-sm text-muted-foreground">No import selected.</div> : null}
            {selectedBatch && rows.isLoading ? <LoadingBlock label="Loading staged rows" /> : null}
            {staged.length ? (
              <div className="overflow-auto rounded-lg border">
                <Table>
                  <TableHeader><TableRow><TableHead>Row</TableHead><TableHead>Date</TableHead><TableHead>Description</TableHead><TableHead>Amount</TableHead><TableHead>Validation</TableHead><TableHead>Duplicate</TableHead><TableHead>Transfer</TableHead></TableRow></TableHeader>
                  <TableBody>
                    {staged.map((row: StagedRow) => (
                      <TableRow key={row.id}>
                        <TableCell>{row.row_number}</TableCell>
                        <TableCell>{String(row.normalized_json.transaction_date ?? "")}</TableCell>
                        <TableCell>{String(row.normalized_json.merchant_name ?? row.normalized_json.original_description ?? "")}</TableCell>
                        <TableCell>{formatCents(row.normalized_json.amount_cents as number | null)}</TableCell>
                        <TableCell><Badge tone={row.validation_status === "error" ? "danger" : row.validation_status === "warning" ? "warning" : "success"}>{row.validation_status}</Badge></TableCell>
                        <TableCell><Badge tone={row.duplicate_status === "unique" ? "success" : "warning"}>{row.duplicate_status}</Badge></TableCell>
                        <TableCell><Badge tone={row.transfer_status === "confirmed_transfer" ? "success" : row.transfer_status === "suggested_transfer" ? "warning" : "neutral"}>{row.transfer_status}</Badge></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
