import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingBlock } from "@/components/ui/loading";
import { PageHeader } from "./PageHeader";

export function Settings() {
  const client = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api.get<Record<string, unknown>>("/settings") });
  const coinbase = useQuery({ queryKey: ["coinbase"], queryFn: () => api.get<{ configured: boolean; implemented: boolean; sync_available: boolean; message: string; cost_basis_policy: string }>("/coinbase/status") });
  const configure = useMutation({ mutationFn: () => api.post("/coinbase/configure", { api_key_configured: true, read_only_confirmed: true }), onSuccess: () => client.invalidateQueries({ queryKey: ["coinbase"] }) });
  const remove = useMutation({ mutationFn: () => api.delete("/coinbase/configure"), onSuccess: () => client.invalidateQueries({ queryKey: ["coinbase"] }) });
  if (settings.isLoading) return <LoadingBlock label="Loading settings" />;
  return (
    <>
      <PageHeader title="Settings" detail="Core app behavior is local-only. Optional external reads are explicitly labeled and disabled by default." />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Local Runtime</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between"><span>Cloud backend</span><Badge tone="success">disabled</Badge></div>
            <div className="flex justify-between"><span>Login/auth</span><Badge tone="success">not required in V1</Badge></div>
            <div className="flex justify-between"><span>Telemetry</span><Badge tone="success">off</Badge></div>
            <div className="flex justify-between"><span>Background scheduler</span><Badge tone="success">none</Badge></div>
            <div className="flex justify-between"><span>Paid APIs required</span><Badge tone="success">no</Badge></div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Privacy And Storage Boundaries</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between"><span>Primary database</span><Badge tone="neutral">local SQLite</Badge></div>
            <div className="flex justify-between"><span>Backups</span><Badge tone="neutral">local files</Badge></div>
            <div className="flex justify-between"><span>Imports/exports</span><Badge tone="neutral">local folders</Badge></div>
            <div className="flex justify-between"><span>Secrets folder</span><Badge tone="warning">never package/share</Badge></div>
            <p className="rounded-md bg-muted p-3 text-muted-foreground">Before sharing a ZIP or moving machines, use the clean release script and verify local database, backups, logs, imports, exports, and secrets are excluded unless intentionally transferring personal data.</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Default App Preferences</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {Object.entries(settings.data ?? {}).length ? Object.entries(settings.data ?? {}).map(([key, value]) => (
              <div key={key} className="flex justify-between gap-3"><span>{key}</span><Badge tone="neutral">{String(value)}</Badge></div>
            )) : <p className="text-muted-foreground">No editable user preferences are exposed yet. Planned: currency, date format, fiscal month, default account, backup location, and theme.</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Coinbase Read-Only</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between"><span>Credentialed sync</span><Badge tone="neutral">{coinbase.data?.implemented ? "implemented" : "not implemented"}</Badge></div>
            <div className="flex justify-between"><span>Configured</span><Badge tone={coinbase.data?.configured ? "success" : "neutral"}>{coinbase.data?.configured ? "configured" : "not configured"}</Badge></div>
            <p className="text-muted-foreground">{coinbase.data?.message}</p>
            <p className="text-muted-foreground">{coinbase.data?.cost_basis_policy}</p>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => configure.mutate()}>Mark Read-Only Configured</Button>
              <Button size="sm" variant="outline" onClick={() => remove.mutate()}>Delete Config</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
