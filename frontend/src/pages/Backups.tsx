import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { LoadingBlock } from "@/components/ui/loading";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ApiRecord } from "@/types";
import { PageHeader } from "./PageHeader";

export function Backups() {
  const client = useQueryClient();
  const [restorePath, setRestorePath] = useState("");
  const query = useQuery({ queryKey: ["backups"], queryFn: () => api.get<ApiRecord[]>("/backups") });
  const create = useMutation({ mutationFn: () => api.post("/backups/create", { backup_type: "manual", notes: "Manual backup from UI" }), onSuccess: () => client.invalidateQueries({ queryKey: ["backups"] }) });
  const restore = useMutation({ mutationFn: () => api.post("/backups/restore", { backup_path: restorePath }) });
  if (query.isLoading) return <LoadingBlock label="Loading backups" />;
  const rows = query.data ?? [];
  return (
    <>
      <PageHeader title="Backups" detail="Backups use SQLite's backup API, include manifests and hashes, and are created before imports and restore." />
      <div className="mb-4 flex flex-wrap gap-2">
        <Button onClick={() => create.mutate()}>Create Manual Backup</Button>
      </div>
      <div className="mb-6 rounded-lg border bg-card p-4">
        <div className="mb-2 font-medium">Restore Backup</div>
        <div className="grid gap-2 md:grid-cols-[1fr_auto]">
          <Input value={restorePath} onChange={(event) => setRestorePath(event.target.value)} placeholder="Paste backup .sqlite3 path" />
          <Button variant="outline" onClick={() => restore.mutate()} disabled={!restorePath}>Validate And Restore</Button>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">Restore validates the manifest and creates a pre-restore backup before replacing the active database.</p>
        {restore.isError ? <p className="mt-2 text-sm text-danger">{restore.error.message}</p> : null}
        {restore.isSuccess ? <p className="mt-2 text-sm text-emerald-700">{String((restore.data as ApiRecord).message ?? "Restore completed. Restart the app.")}</p> : null}
      </div>
      {!rows.length ? <EmptyState title="No backups yet" detail="Run a manual backup or commit an import to create one." /> : (
        <div className="overflow-hidden rounded-lg border bg-card">
          <Table>
            <TableHeader><TableRow><TableHead>Created</TableHead><TableHead>Type</TableHead><TableHead>Schema</TableHead><TableHead>Hash</TableHead><TableHead>Path</TableHead></TableRow></TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={String(row.id)}>
                  <TableCell>{String(row.created_at)}</TableCell>
                  <TableCell><Badge tone={row.backup_type === "pre_import" ? "warning" : "info"}>{String(row.backup_type)}</Badge></TableCell>
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
