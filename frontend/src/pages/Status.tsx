import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingBlock } from "@/components/ui/loading";
import { PageHeader } from "./PageHeader";

export function Status() {
  const client = useQueryClient();
  const health = useQuery({ queryKey: ["health"], queryFn: () => api.get<Record<string, unknown>>("/health") });
  const appStatus = useQuery({ queryKey: ["app-status"], queryFn: () => api.get<Record<string, unknown>>("/app/status") });
  const refresh = useMutation({ mutationFn: () => api.post("/daily-refresh", undefined), onSuccess: () => client.invalidateQueries({ queryKey: ["dashboard"] }) });
  if (health.isLoading) return <LoadingBlock label="Loading status" />;
  return (
    <>
      <PageHeader title="Local Status" detail="The V1 refresh runs only when the app opens or when manually triggered." />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card><CardHeader><CardTitle>Backend</CardTitle></CardHeader><CardContent className="space-y-2 text-sm"><div>Status <Badge tone="success">{String(health.data?.status)}</Badge></div><div>Version {String(health.data?.version)}</div></CardContent></Card>
        <Card><CardHeader><CardTitle>Runtime Rules</CardTitle></CardHeader><CardContent className="space-y-2 text-sm">{Object.entries(appStatus.data ?? {}).map(([key, value]) => <div key={key} className="flex justify-between"><span>{key}</span><Badge tone={value === false ? "success" : "neutral"}>{String(value)}</Badge></div>)}</CardContent></Card>
      </div>
      <div className="mt-4"><Button onClick={() => refresh.mutate()}>Run Daily Refresh</Button></div>
    </>
  );
}
