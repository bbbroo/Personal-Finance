import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingBlock } from "@/components/ui/loading";
import { PageHeader } from "./PageHeader";

const releaseChecks = [
  "Frontend build passes",
  "Backend tests pass",
  "Fresh database migration passes",
  "Clean ZIP excludes local data",
  "Backup restore validation is tested",
  "Import rollback is tested",
  "No secrets are packaged",
  "Review Queue has no critical items before release"
];

export function Status() {
  const client = useQueryClient();
  const health = useQuery({ queryKey: ["health"], queryFn: () => api.get<Record<string, unknown>>("/health") });
  const appStatus = useQuery({ queryKey: ["app-status"], queryFn: () => api.get<Record<string, unknown>>("/app/status") });
  const refresh = useMutation({ mutationFn: () => api.post("/daily-refresh", undefined), onSuccess: () => client.invalidateQueries({ queryKey: ["dashboard"] }) });
  if (health.isLoading) return <LoadingBlock label="Loading status" />;
  return (
    <>
      <PageHeader title="Local Status" detail="The V1 refresh runs only when the app opens or when manually triggered. Use this page for local runtime, release-readiness, and developer health checks." />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card><CardHeader><CardTitle>Backend</CardTitle></CardHeader><CardContent className="space-y-2 text-sm"><div>Status <Badge tone="success">{String(health.data?.status)}</Badge></div><div>Version {String(health.data?.version)}</div></CardContent></Card>
        <Card><CardHeader><CardTitle>Runtime Rules</CardTitle></CardHeader><CardContent className="space-y-2 text-sm">{Object.entries(appStatus.data ?? {}).map(([key, value]) => <div key={key} className="flex justify-between"><span>{key}</span><Badge tone={value === false ? "success" : "neutral"}>{String(value)}</Badge></div>)}</CardContent></Card>
        <Card>
          <CardHeader><CardTitle>Release Readiness Checklist</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {releaseChecks.map((check) => <div key={check} className="flex justify-between gap-3"><span>{check}</span><Badge tone="warning">verify</Badge></div>)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Developer Health Notes</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>Use the verification commands before release: backend tests, fresh database migration test, frontend tests, and frontend production build.</p>
            <p>The app is local-only. Confirm the clean ZIP script excludes database, WAL/SHM files, backups, logs, imports, exports, secrets, caches, node_modules, and virtual environments.</p>
            <p>Run Review Queue before major data decisions so incomplete imports, unreconciled statements, data-quality warnings, and backup gaps are visible.</p>
          </CardContent>
        </Card>
      </div>
      <div className="mt-4"><Button onClick={() => refresh.mutate()}>Run Daily Refresh</Button></div>
    </>
  );
}
