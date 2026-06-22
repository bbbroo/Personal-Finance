import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { ApiError } from "@/components/ui/api-error";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { LoadingBlock } from "@/components/ui/loading";
import { MutationMessage } from "@/components/ui/mutation-message";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ApiRecord } from "@/types";
import { PageHeader } from "./PageHeader";

export function Backups() {
  const client = useQueryClient();
  const [restorePath, setRestorePath] = useState("");
  const { confirm, dialog } = useConfirmDialog();
  const query = useQuery({ queryKey: ["backups"], queryFn: () => api.get<ApiRecord[]>("/backups") });
  const create = useMutation({ mutationFn: () => api.post("/backups/create", { backup_type: "manual", notes: "Manual backup from UI" }), onSuccess: () => client.invalidateQueries({ queryKey: ["backups"] }) });
  const restore = useMutation({ mutationFn: () => api.post("/backups/restore", { backup_path: restorePath }) });
  if (query.isLoading) return <LoadingBlock label="Loading backups" />;
  const rows = query.data ?? [];
  const restoreResult = restore.data as ApiRecord | undefined;
  const confirmRestore = () => {
    confirm({
      title: "Restore this backup?",
      description: "The app will validate it, create a pre-restore backup, replace the active database, and require a restart.",
      confirmLabel: "Validate and restore",
      variant: "danger",
      onConfirm: () => restore.mutate()
    });
  };
  return (
    <>
      {dialog}
      <PageHeader title="Backups" detail="Backups use SQLite's backup API, include manifests and hashes, and are created before imports and restore." />
      <div className="mb-4 flex flex-wrap gap-2">
        <Button onClick={() => create.mutate()} disabled={create.isPending}>Create Manual Backup</Button>
      </div>
      <MutationMessage isPending={create.isPending} isSuccess={create.isSuccess} pending="Creating backup..." success="Manual backup created." />
      <ApiError error={create.error} title="Backup creation failed" />
      <div className="mb-6 mt-4 rounded-lg border bg-card p-4">
        <div className="mb-2 font-medium">Restore Backup</div>
        <div className="mb-3 rounded-md border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-950">
          Restore replaces the active local SQLite database after manifest, hash, schema, and integrity validation. A pre-restore backup is created first. Restart is required after a successful restore so every connection reopens on the restored file.
        </div>
        <div className="grid gap-2 md:grid-cols-[1fr_auto]">
          <Input value={restorePath} onChange={(event) => setRestorePath(event.target.value)} placeholder="Paste backup .sqlite3 path" />
          <Button variant="outline" onClick={confirmRestore} disabled={!restorePath || restore.isPending}>Validate And Restore</Button>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">Restore validates the manifest, rejects unsupported schema versions, checkpoints/removes stale WAL/SHM sidecars, and audits restore lifecycle events.</p>
        <ApiError error={restore.error} title="Restore failed" />
        <MutationMessage isPending={restore.isPending} pending="Validating backup and restoring..." />
        {restore.isSuccess ? (
          <div className="mt-2 rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-950">
            <div>{String(restoreResult?.message ?? "Restore completed. Restart the app.")}</div>
            {restoreResult?.restart_required ? <div className="font-medium">Restart required before continuing to use the app.</div> : null}
          </div>
        ) : null}
      </div>
      {!rows.length ? <EmptyState title="No backups yet" detail="Run a manual backup or commit an import to create one." /> : (
        <div className="overflow-hidden rounded-lg border bg-card">
          <Table>
            <TableHeader><TableRow><TableHead>Created</TableHead><TableHead>Type</TableHead><TableHead>Schema</TableHead><TableHead>Hash</TableHead><TableHead>Path</TableHead></TableRow></TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={String(row.id)}>
                  <TableCell>{String(row.created_at)}</TableCell>
                  <TableCell><Badge tone={row.backup_type === "pre_import" || row.backup_type === "pre_restore" ? "warning" : "info"}>{String(row.backup_type)}</Badge></TableCell>
                  <TableCell>{String(row.schema_version)}</TableCell>
                  <TableCell>{String(row.database_sha256).slice(0, 12)}</TableCell>
                  <TableCell className="max-w-md truncate">{String(row.backup_path)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </>
  );
}
