import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingBlock } from "@/components/ui/loading";
import type { DataQualityIssue } from "@/types";
import { PageHeader } from "./PageHeader";

export function DataQuality() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["issues"], queryFn: () => api.get<DataQualityIssue[]>("/data-quality/issues") });
  const recompute = useMutation({ mutationFn: () => api.post("/data-quality/recompute"), onSuccess: () => client.invalidateQueries({ queryKey: ["issues"] }) });
  const ignore = useMutation({ mutationFn: (id: string) => api.post(`/data-quality/issues/${id}/ignore`), onSuccess: () => client.invalidateQueries({ queryKey: ["issues"] }) });
  if (query.isLoading) return <LoadingBlock label="Loading data quality" />;
  const issues = query.data ?? [];
  return (
    <>
      <PageHeader title="Data Quality Center" detail="Uncertainty stays visible: stale prices, missing cost basis, unreconciled statements, duplicate risk, and double-count risks are surfaced here." />
      <div className="mb-4"><Button onClick={() => recompute.mutate()}>Recompute Issues</Button></div>
      {!issues.length ? <EmptyState title="No data quality issues" detail="Current reports do not have open warnings." /> : (
        <div className="space-y-3">
          {issues.map((issue) => (
            <div key={issue.id} className="rounded-lg border bg-card p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2"><Badge tone={issue.severity === "error" || issue.severity === "critical" ? "danger" : issue.severity === "warning" ? "warning" : "info"}>{issue.severity}</Badge><span className="font-medium">{issue.title}</span></div>
                  <p className="mt-2 text-sm text-muted-foreground">{issue.description}</p>
                  {issue.recommended_action ? <p className="mt-1 text-sm">{issue.recommended_action}</p> : null}
                </div>
                {issue.status === "open" ? <Button size="sm" variant="outline" onClick={() => ignore.mutate(issue.id)}>Ignore</Button> : <Badge>{issue.status}</Badge>}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
