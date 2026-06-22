import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { ApiError } from "@/components/ui/api-error";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { LoadingBlock } from "@/components/ui/loading";
import { MutationMessage } from "@/components/ui/mutation-message";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCents } from "@/lib/utils";
import type { Account, ApiRecord, ImportBatch, StagedRow } from "@/types";
import { PageHeader } from "./PageHeader";

const DEFAULT_MAPPING = {
  date: "Date",
  posted_date: null,
  description: "Description",
  amount: "Amount",
  debit: null,
  credit: null
};

const steps = ["Upload", "Mapping", "Validation", "Duplicates", "Transfers", "Commit", "Summary"];

type TransferCandidate = { candidate_type?: string; candidate_id?: string; reason?: string };

type ImportSummary = {
  rowsToImport: number;
  skippedRows: number;
  confirmedDuplicates: number;
  possibleDuplicates: number;
  ignoredDuplicates: number;
  confirmedTransfers: number;
  suggestedTransfers: number;
  validationErrors: number;
  validationWarnings: number;
};

function rowMessages(row: StagedRow) {
  return [...(row.errors_json ?? []), ...(row.warnings_json ?? [])];
}

function duplicateWhy(row: StagedRow) {
  const candidate = row.normalized_json.duplicate_candidate as ApiRecord | undefined;
  const reason = row.normalized_json.duplicate_reason ?? row.normalized_json.duplicate_match_reason;
  if (reason) return String(reason);
  if (candidate?.candidate_type || candidate?.candidate_id) return `Matched ${String(candidate.candidate_type ?? "candidate")} ${String(candidate.candidate_id ?? "")}`.trim();
  const messages = rowMessages(row).filter((message) => message.toLowerCase().includes("duplicate"));
  return messages[0] ?? "Similar date, amount, merchant, or imported row fingerprint.";
}

function transferCandidate(row: StagedRow): TransferCandidate | undefined {
  return row.normalized_json.transfer_candidate as TransferCandidate | undefined;
}

function transferPairProblem(row: StagedRow, staged: StagedRow[]) {
  if (row.transfer_status !== "confirmed_transfer") return null;
  if (row.user_action === "skip") return "This side is skipped.";
  if (row.validation_status === "error") return "This side has a validation error.";
  if (row.duplicate_status === "confirmed_duplicate") return "This side is marked as a duplicate.";
  const candidate = transferCandidate(row);
  if (!candidate) return "No transfer candidate is attached.";
  if (candidate.candidate_type === "transaction") return null;
  if (candidate.candidate_type !== "staged_row" || !candidate.candidate_id) return "Candidate is not another staged row.";
  const paired = staged.find((item) => item.id === candidate.candidate_id);
  if (!paired) return "The paired staged row is missing.";
  if (paired.user_action === "skip") return "The paired side is skipped.";
  if (paired.validation_status === "error") return "The paired side has a validation error.";
  if (paired.duplicate_status === "confirmed_duplicate") return "The paired side is marked as a duplicate.";
  if (paired.transfer_status !== "confirmed_transfer") return "The paired side is not confirmed as a transfer.";
  return null;
}

function buildSummary(batch: ImportBatch | undefined, staged: StagedRow[]): ImportSummary {
  return {
    rowsToImport: staged.filter((row) => row.user_action !== "skip" && row.validation_status !== "error" && row.duplicate_status !== "confirmed_duplicate").length,
    skippedRows: staged.filter((row) => row.user_action === "skip" || row.duplicate_status === "confirmed_duplicate").length,
    confirmedDuplicates: staged.filter((row) => row.duplicate_status === "confirmed_duplicate").length,
    possibleDuplicates: staged.filter((row) => row.duplicate_status === "possible_duplicate").length,
    ignoredDuplicates: staged.filter((row) => row.duplicate_status === "ignored_duplicate").length,
    confirmedTransfers: staged.filter((row) => row.transfer_status === "confirmed_transfer").length,
    suggestedTransfers: staged.filter((row) => row.transfer_status === "suggested_transfer").length,
    validationErrors: staged.filter((row) => row.validation_status === "error").length || Number(batch?.error_count ?? 0),
    validationWarnings: staged.filter((row) => row.validation_status === "warning").length || Number(batch?.warning_count ?? 0)
  };
}

function statusTone(status: string) {
  if (["committed", "valid", "unique", "confirmed_transfer", "ignored_duplicate"].includes(status)) return "success";
  if (["error", "confirmed_duplicate", "rejected_transfer"].includes(status)) return "danger";
  if (["warning", "possible_duplicate", "suggested_transfer", "rolled_back"].includes(status)) return "warning";
  return "neutral";
}

function StepCard({ title, detail, children }: { title: string; detail: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <p className="text-sm text-muted-foreground">{detail}</p>
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  );
}

export function ImportCenter() {
  const client = useQueryClient();
  const [accountId, setAccountId] = useState("");
  const [selectedBatch, setSelectedBatch] = useState<string | null>(null);
  const [mappingText, setMappingText] = useState(JSON.stringify(DEFAULT_MAPPING, null, 2));
  const [mappingError, setMappingError] = useState<string | null>(null);
  const [editingRowId, setEditingRowId] = useState<string | null>(null);
  const [rowJsonText, setRowJsonText] = useState("");
  const [rowEditError, setRowEditError] = useState<string | null>(null);
  const { confirm, dialog } = useConfirmDialog();

  const accounts = useQuery({ queryKey: ["accounts"], queryFn: () => api.get<Account[]>("/accounts") });
  const imports = useQuery({ queryKey: ["imports"], queryFn: () => api.get<ImportBatch[]>("/imports") });
  const activeBatchId = selectedBatch ?? imports.data?.[0]?.id ?? null;
  const rows = useQuery({ queryKey: ["staged-rows", activeBatchId], queryFn: () => api.stagedRows(activeBatchId ?? ""), enabled: Boolean(activeBatchId) });

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
  const remap = useMutation({ mutationFn: ({ id, mapping }: { id: string; mapping: Record<string, unknown> }) => api.post<ImportBatch>(`/imports/${id}/map`, mapping), onSuccess: invalidateImport });
  const updateRow = useMutation({
    mutationFn: ({ rowId, payload }: { rowId: string; payload: Record<string, unknown> }) => api.patch<StagedRow>(`/imports/${activeBatchId}/staged-rows/${rowId}`, payload),
    onSuccess: () => {
      setEditingRowId(null);
      setRowJsonText("");
      setRowEditError(null);
      invalidateImport();
    }
  });
  const commit = useMutation({
    mutationFn: (id: string) => api.post<ImportBatch>(`/imports/${id}/commit`),
    onSuccess: (batch) => {
      setSelectedBatch(batch.id);
      invalidateImport();
      client.invalidateQueries({ queryKey: ["transactions"] });
      client.invalidateQueries({ queryKey: ["dashboard"] });
      client.invalidateQueries({ queryKey: ["issues"] });
    }
  });
  const rollback = useMutation({
    mutationFn: (id: string) => api.post<ImportBatch>(`/imports/${id}/rollback`),
    onSuccess: (batch) => {
      setSelectedBatch(batch.id);
      invalidateImport();
      client.invalidateQueries({ queryKey: ["transactions"] });
      client.invalidateQueries({ queryKey: ["dashboard"] });
      client.invalidateQueries({ queryKey: ["issues"] });
    }
  });

  if (accounts.isLoading) return <LoadingBlock label="Loading import wizard" />;
  const accountOptions = accounts.data ?? [];
  const batch = imports.data?.find((item) => item.id === activeBatchId) ?? imports.data?.[0] ?? (upload.data as ImportBatch | undefined) ?? (commit.data as ImportBatch | undefined) ?? (rollback.data as ImportBatch | undefined);
  const staged = rows.data ?? [];
  const validationRows = staged.filter((row) => row.validation_status === "warning" || row.validation_status === "error");
  const duplicateRows = staged.filter((row) => row.duplicate_status !== "unique");
  const transferRows = staged.filter((row) => row.transfer_status !== "not_transfer");
  const incompleteConfirmedTransfers = staged.filter((row) => transferPairProblem(row, staged));
  const commitBlockedByTransfers = incompleteConfirmedTransfers.length > 0;
  const commitBlockedByErrors = Number(batch?.error_count ?? 0) > 0 || staged.some((row) => row.validation_status === "error");
  const summary = buildSummary(batch, staged);
  const activeStepIndex = !batch ? 0 : batch.status === "committed" || batch.status === "rolled_back" ? 6 : commitBlockedByErrors ? 2 : commitBlockedByTransfers ? 4 : 5;

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

  const confirmCommit = () => {
    if (!batch) return;
    confirm({
      title: "Commit this import?",
      description: "This creates transactions after validation, duplicate review, transfer review, and a pre-import backup.",
      confirmLabel: "Commit import",
      onConfirm: () => commit.mutate(batch.id)
    });
  };

  const confirmRollback = () => {
    if (!batch) return;
    confirm({
      title: "Rollback this committed import?",
      description: "This removes records created by that import and creates a pre-rollback backup first.",
      confirmLabel: "Rollback import",
      variant: "danger",
      onConfirm: () => rollback.mutate(batch.id)
    });
  };

  return (
    <>
      {dialog}
      <PageHeader title="Import Wizard" detail="Upload, map, validate, review duplicates and transfers, then commit only after every safety check is visible." />

      <div className="mb-6 grid gap-2 md:grid-cols-7">
        {steps.map((step, index) => (
          <div key={step} className={`rounded-md border p-2 text-center text-xs ${index <= activeStepIndex ? "bg-primary/10 text-primary" : "bg-card text-muted-foreground"}`}>
            <div className="font-medium">{index + 1}. {step}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-6">
        <StepCard title="1. Upload" detail="Choose the target account and upload the CSV. The backend creates a staged import batch before any transaction is committed.">
          <div className="grid gap-3 md:grid-cols-[260px_1fr]">
            <Select value={accountId} onChange={(event) => setAccountId(event.target.value)} aria-label="Target account">
              <option value="">Choose target account</option>
              {accountOptions.map((account) => <option value={account.id} key={account.id}>{account.name}</option>)}
            </Select>
            <Input
              type="file"
              aria-label="Upload CSV"
              accept=".csv,text/csv"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file && accountId) upload.mutate({ file, accountId });
              }}
            />
          </div>
          <MutationMessage isPending={upload.isPending} isSuccess={upload.isSuccess} pending="Uploading import..." success="Import uploaded for review." />
          <ApiError error={upload.error} title="Upload failed" />
          {batch ? (
            <div className="grid gap-3 rounded-md border bg-muted/40 p-3 text-sm md:grid-cols-4">
              <div><div className="text-xs uppercase text-muted-foreground">File</div><div className="font-medium">{batch.original_filename}</div></div>
              <div><div className="text-xs uppercase text-muted-foreground">Rows</div><div className="font-medium">{batch.row_count}</div></div>
              <div><div className="text-xs uppercase text-muted-foreground">Batch ID</div><div className="font-mono text-xs">{batch.id}</div></div>
              <div><div className="text-xs uppercase text-muted-foreground">Status</div><Badge tone={statusTone(batch.status)}>{batch.status}</Badge></div>
            </div>
          ) : null}
          {(imports.data ?? []).length ? (
            <div className="space-y-2">
              <div className="text-sm font-medium">Recent import batches</div>
              {(imports.data ?? []).map((item) => (
                <button key={item.id} onClick={() => setSelectedBatch(item.id)} className="focus-ring block w-full rounded-md border p-3 text-left text-sm hover:bg-muted">
                  <div className="flex justify-between gap-2"><span className="font-medium">{item.original_filename}</span><Badge tone={statusTone(item.status)}>{item.status}</Badge></div>
                  <div className="mt-1 text-muted-foreground">{item.row_count} rows, {item.error_count} errors, {item.duplicate_row_count} duplicates, {item.skipped_row_count ?? 0} skipped</div>
                </button>
              ))}
            </div>
          ) : null}
        </StepCard>

        {batch ? (
          <StepCard title="2. Mapping" detail="Review the detected/default mapping. Invalid JSON is blocked locally before the remap request is sent.">
            <textarea className="focus-ring min-h-48 w-full rounded-md border bg-background p-3 font-mono text-xs" value={mappingText} onChange={(event) => setMappingText(event.target.value)} aria-label="Mapping JSON" />
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" variant="outline" onClick={submitRemap} disabled={batch.status === "committed" || remap.isPending}>Reparse With Mapping</Button>
              <span className="text-sm text-muted-foreground">Expected fields: date, description, amount or debit/credit.</span>
            </div>
            {mappingError ? <div role="alert" className="text-sm text-danger">{mappingError}</div> : null}
            <MutationMessage isPending={remap.isPending} isSuccess={remap.isSuccess} pending="Reparsing import..." success="Import remapped." />
            <ApiError error={remap.error} title="Remap failed" />
          </StepCard>
        ) : null}

        {batch ? (
          <StepCard title="3. Validation" detail="Errors block commit. Warnings remain visible so you can decide whether to edit, skip, or continue.">
            <div className="grid gap-3 md:grid-cols-4">
              <div className="rounded-md border p-3"><div className="text-xs uppercase text-muted-foreground">Valid rows</div><div className="text-lg font-semibold">{batch.valid_row_count}</div></div>
              <div className="rounded-md border p-3"><div className="text-xs uppercase text-muted-foreground">Warnings</div><div className="text-lg font-semibold">{summary.validationWarnings}</div></div>
              <div className="rounded-md border p-3"><div className="text-xs uppercase text-muted-foreground">Errors</div><div className="text-lg font-semibold">{summary.validationErrors}</div></div>
              <div className="rounded-md border p-3"><div className="text-xs uppercase text-muted-foreground">Commit status</div><Badge tone={commitBlockedByErrors ? "danger" : "success"}>{commitBlockedByErrors ? "blocked" : "ready"}</Badge></div>
            </div>
            {commitBlockedByErrors ? <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-950">Commit is blocked until validation errors are fixed, skipped, or remapped.</div> : null}
            {validationRows.length ? (
              <div className="space-y-2">
                {validationRows.map((row) => (
                  <div key={row.id} className="rounded-md border p-3 text-sm">
                    <div className="flex flex-wrap justify-between gap-2"><span>Row {row.row_number}: {String(row.normalized_json.merchant_name ?? row.normalized_json.original_description ?? "Unknown")}</span><Badge tone={statusTone(row.validation_status)}>{row.validation_status}</Badge></div>
                    <div className="mt-1 text-muted-foreground">{rowMessages(row).join("; ") || "Review normalized JSON for this row."}</div>
                  </div>
                ))}
              </div>
            ) : <div className="text-sm text-muted-foreground">No validation warnings or errors are currently staged.</div>}
          </StepCard>
        ) : null}

        {batch ? (
          <StepCard title="4. Duplicate Review" detail="Possible duplicates are isolated here so you can confirm duplicate, import anyway, skip, or leave for review.">
            {!duplicateRows.length ? <div className="text-sm text-muted-foreground">No duplicate candidates are currently staged.</div> : (
              <div className="overflow-auto rounded-lg border">
                <Table>
                  <TableHeader><TableRow><TableHead>Row</TableHead><TableHead>Description</TableHead><TableHead>Amount</TableHead><TableHead>Why flagged</TableHead><TableHead>Decision</TableHead></TableRow></TableHeader>
                  <TableBody>
                    {duplicateRows.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell>{row.row_number}</TableCell>
                        <TableCell>{String(row.normalized_json.merchant_name ?? row.normalized_json.original_description ?? "Unknown")}</TableCell>
                        <TableCell>{formatCents(row.normalized_json.amount_cents as number | null)}</TableCell>
                        <TableCell className="max-w-md text-xs text-muted-foreground">{duplicateWhy(row)}</TableCell>
                        <TableCell>
                          <div className="grid gap-2">
                            <Select value={row.duplicate_status} onChange={(event) => updateRow.mutate({ rowId: row.id, payload: { duplicate_status: event.target.value } })} aria-label={`Duplicate decision row ${row.row_number}`}>
                              <option value="possible_duplicate">Possible duplicate</option>
                              <option value="confirmed_duplicate">Confirm duplicate</option>
                              <option value="ignored_duplicate">Import anyway</option>
                              <option value="unique">Not duplicate</option>
                            </Select>
                            <Select value={row.user_action} onChange={(event) => updateRow.mutate({ rowId: row.id, payload: { user_action: event.target.value } })} aria-label={`Row action ${row.row_number}`}>
                              <option value="import">Import</option>
                              <option value="skip">Skip</option>
                              <option value="needs_review">Needs review</option>
                            </Select>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </StepCard>
        ) : null}

        {batch ? (
          <StepCard title="5. Transfer Review" detail="Confirmed transfers must have a complete importable pair. Suggested transfers remain included until you explicitly confirm them.">
            {commitBlockedByTransfers ? (
              <div className="rounded-md border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-950">
                Commit blocked: {incompleteConfirmedTransfers.length} confirmed transfer row(s) do not have a complete importable pair. Import both sides, or downgrade/reject the incomplete side so cash flow is not understated.
              </div>
            ) : null}
            {!transferRows.length ? <div className="text-sm text-muted-foreground">No transfer candidates are currently staged.</div> : (
              <div className="space-y-3">
                {transferRows.map((row) => {
                  const candidate = transferCandidate(row);
                  const paired = candidate?.candidate_id ? staged.find((item) => item.id === candidate.candidate_id) : undefined;
                  const problem = transferPairProblem(row, staged);
                  return (
                    <div key={row.id} className="rounded-lg border p-3 text-sm">
                      <div className="mb-2 flex flex-wrap justify-between gap-2"><span>Row {row.row_number}</span><Badge tone={statusTone(row.transfer_status)}>{row.transfer_status}</Badge></div>
                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="rounded-md border bg-muted/40 p-3">
                          <div className="text-xs uppercase text-muted-foreground">This side</div>
                          <div>{String(row.normalized_json.merchant_name ?? row.normalized_json.original_description ?? "Unknown")}</div>
                          <div>{formatCents(row.normalized_json.amount_cents as number | null)}</div>
                          <div className="text-xs text-muted-foreground">{row.validation_status} · {row.duplicate_status} · {row.user_action}</div>
                        </div>
                        <div className="rounded-md border bg-muted/40 p-3">
                          <div className="text-xs uppercase text-muted-foreground">Pair / match</div>
                          {paired ? (
                            <>
                              <div>Row {paired.row_number}: {String(paired.normalized_json.merchant_name ?? paired.normalized_json.original_description ?? "Unknown")}</div>
                              <div>{formatCents(paired.normalized_json.amount_cents as number | null)}</div>
                              <div className="text-xs text-muted-foreground">{paired.validation_status} · {paired.duplicate_status} · {paired.user_action}</div>
                            </>
                          ) : <div>{candidate?.candidate_type === "transaction" ? "Matched existing transaction" : "No paired staged row"}</div>}
                        </div>
                      </div>
                      {problem ? <div className="mt-2 rounded-md border border-yellow-300 bg-yellow-50 p-2 text-yellow-950">{problem}</div> : null}
                      <div className="mt-3 grid gap-2 md:grid-cols-2">
                        <Select value={row.transfer_status} onChange={(event) => updateRow.mutate({ rowId: row.id, payload: { transfer_status: event.target.value } })} aria-label={`Transfer decision row ${row.row_number}`}>
                          <option value="suggested_transfer">Suggested transfer</option>
                          <option value="confirmed_transfer">Confirm transfer</option>
                          <option value="rejected_transfer">Reject transfer</option>
                          <option value="not_transfer">Not transfer</option>
                        </Select>
                        <Select value={row.user_action} onChange={(event) => updateRow.mutate({ rowId: row.id, payload: { user_action: event.target.value } })} aria-label={`Transfer row action ${row.row_number}`}>
                          <option value="import">Import</option>
                          <option value="skip">Skip</option>
                          <option value="needs_review">Needs review</option>
                        </Select>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </StepCard>
        ) : null}

        {batch ? (
          <StepCard title="6. Commit" detail="Review the final pre-commit counts. Commit remains blocked when validation errors or incomplete confirmed transfers exist.">
            <div className="grid gap-3 md:grid-cols-4">
              <div className="rounded-md border p-3"><div className="text-xs uppercase text-muted-foreground">Rows to import</div><div className="text-lg font-semibold">{summary.rowsToImport}</div></div>
              <div className="rounded-md border p-3"><div className="text-xs uppercase text-muted-foreground">Skipped rows</div><div className="text-lg font-semibold">{summary.skippedRows}</div></div>
              <div className="rounded-md border p-3"><div className="text-xs uppercase text-muted-foreground">Duplicates</div><div className="text-lg font-semibold">{summary.confirmedDuplicates} confirmed · {summary.ignoredDuplicates} imported</div></div>
              <div className="rounded-md border p-3"><div className="text-xs uppercase text-muted-foreground">Transfers</div><div className="text-lg font-semibold">{summary.confirmedTransfers} confirmed · {summary.suggestedTransfers} suggested</div></div>
              <div className="rounded-md border p-3"><div className="text-xs uppercase text-muted-foreground">Validation errors</div><div className="text-lg font-semibold">{summary.validationErrors}</div></div>
              <div className="rounded-md border p-3"><div className="text-xs uppercase text-muted-foreground">Validation warnings</div><div className="text-lg font-semibold">{summary.validationWarnings}</div></div>
              <div className="rounded-md border p-3"><div className="text-xs uppercase text-muted-foreground">Possible duplicates</div><div className="text-lg font-semibold">{summary.possibleDuplicates}</div></div>
              <div className="rounded-md border p-3"><div className="text-xs uppercase text-muted-foreground">Readiness</div><Badge tone={commitBlockedByErrors || commitBlockedByTransfers ? "danger" : "success"}>{commitBlockedByErrors || commitBlockedByTransfers ? "blocked" : "ready"}</Badge></div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={confirmCommit} disabled={batch.status === "committed" || batch.status === "rolled_back" || commitBlockedByErrors || commitBlockedByTransfers || commit.isPending}>Commit import</Button>
              <Button variant="outline" onClick={confirmRollback} disabled={batch.status !== "committed" || rollback.isPending}>Rollback import</Button>
            </div>
            <MutationMessage isPending={commit.isPending} isSuccess={commit.isSuccess} pending="Committing import..." success="Import committed." />
            <MutationMessage isPending={rollback.isPending} isSuccess={rollback.isSuccess} pending="Rolling back import..." success="Import rollback completed." />
            <ApiError error={commit.error} title="Commit failed" />
            <ApiError error={rollback.error} title="Rollback failed" />
          </StepCard>
        ) : null}

        {batch && (batch.status === "committed" || batch.status === "rolled_back" || commit.isSuccess || rollback.isSuccess) ? (
          <StepCard title="7. Post-import Summary" detail="The completed import remains reviewable. A rollback is offered for committed batches and requires confirmation.">
            <div className="grid gap-3 md:grid-cols-4">
              <div><div className="text-xs uppercase text-muted-foreground">Batch</div><div className="font-mono text-xs">{batch.id}</div></div>
              <div><div className="text-xs uppercase text-muted-foreground">Transactions created</div><div className="font-medium">{String(batch.created_transaction_count ?? summary.rowsToImport)}</div></div>
              <div><div className="text-xs uppercase text-muted-foreground">Backup</div><div className="font-medium">{String(batch.backup_id ?? batch.pre_import_backup_id ?? "created before commit")}</div></div>
              <div><div className="text-xs uppercase text-muted-foreground">Status</div><Badge tone={statusTone(batch.status)}>{batch.status}</Badge></div>
            </div>
            {summary.validationWarnings || summary.possibleDuplicates || summary.suggestedTransfers ? (
              <div className="rounded-md border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-950">
                Warnings remain: {summary.validationWarnings} validation warning(s), {summary.possibleDuplicates} possible duplicate(s), and {summary.suggestedTransfers} suggested transfer(s) still included until confirmed.
              </div>
            ) : <div className="text-sm text-muted-foreground">No remaining warnings were detected in the staged rows.</div>}
            <Button variant="outline" onClick={confirmRollback} disabled={batch.status !== "committed" || rollback.isPending}>Rollback this committed import</Button>
          </StepCard>
        ) : null}

        {batch && rows.isLoading ? <LoadingBlock label="Loading staged rows" /> : null}
        {batch && staged.length ? (
          <StepCard title="Full staged row review" detail="The full table remains available for fine-grained row actions and normalized JSON edits.">
            <ApiError error={updateRow.error} title="Row update failed" />
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
                        {rowMessages(row).length ? <div className="mt-1 space-y-1 text-xs text-muted-foreground">{rowMessages(row).map((message) => <div key={message}>{message}</div>)}</div> : null}
                      </TableCell>
                      <TableCell>{formatCents(row.normalized_json.amount_cents as number | null)}</TableCell>
                      <TableCell className="space-y-1">
                        <Badge tone={statusTone(row.validation_status)}>{row.validation_status}</Badge>
                        <Badge tone={statusTone(row.duplicate_status)}>{row.duplicate_status}</Badge>
                        <Badge tone={statusTone(row.transfer_status)}>{row.transfer_status}</Badge>
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
            {editingRowId ? (
              <div className="rounded-lg border p-3">
                <div className="mb-2 font-medium">Edit Normalized Row</div>
                <textarea className="focus-ring min-h-64 w-full rounded-md border bg-background p-3 font-mono text-xs" value={rowJsonText} onChange={(event) => setRowJsonText(event.target.value)} />
                <div className="mt-2 flex gap-2">
                  <Button size="sm" onClick={saveRowJson}>Save Row Edit</Button>
                  <Button size="sm" variant="outline" onClick={() => setEditingRowId(null)}>Cancel</Button>
                </div>
                {rowEditError ? <div className="mt-2 text-sm text-danger">{rowEditError}</div> : null}
              </div>
            ) : null}
          </StepCard>
        ) : null}
      </div>
    </>
  );
}
