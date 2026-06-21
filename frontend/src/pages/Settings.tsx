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
  const coinbase = useQuery({ queryKey: ["coinbase"], queryFn: () => api.get<{ configured: boolean; cost_basis_policy: string }>("/coinbase/status") });
  const configure = useMutation({ mutationFn: () => api.post("/coinbase/configure", { api_key_configured: true, read_only_confirmed: true }), onSuccess: () => client.invalidateQueries({ queryKey: ["coinbase"] }) });
  const remove = useMutation({ mutationFn: () => fetch("/api/coinbase/configure", { method: "DELETE" }), onSuccess: () => client.invalidateQueries({ queryKey: ["coinbase"] }) });
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
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Coinbase Read-Only</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between"><span>Status</span><Badge tone={coinbase.data?.configured ? "success" : "neutral"}>{coinbase.data?.configured ? "configured" : "not configured"}</Badge></div>
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
