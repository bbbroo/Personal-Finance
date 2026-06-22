import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { ApiError } from "@/components/ui/api-error";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingBlock } from "@/components/ui/loading";
import { MutationMessage } from "@/components/ui/mutation-message";
import type { DataQualityIssue } from "@/types";
import { PageHeader } from "./PageHeader";

export function DataQuality() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["issues"], queryFn: () => api.get<DataQualityIssue[]>("/data-quality/issues") });
  const recompute = useMutation({ mutationFn: () => api.post("/data-quality/recompute"), onSuccess: () => client.invalidateQueries({ queryKey: ["issues"] }) });
  const ignore = useMutation({ mutationFn: (id: string) => api.post(`/data-quality/issues/${id}/ignore`), onSuccess: () => client.invalidateQueries({ queryKey: ["issues"] }) });
  if (query.isLoading) return <LoadingBlock label="Loading data quality" />;
  if (query.isError) return <ApiError error={query.error} title="Data quality failed to load" />;
  const issues = query.data ?? [];
  const openIssues = issues.filter((issue) => issue.status === "open");
  const ignoredIssues = issues.filter((issue) => issue.status === "ignored");
  const visibleIssues = [...openIssues, ...ignoredIssues];
  return (
    <>
      <PageHeader title="Data Quality Center" detail="Uncertainty stays visible: stale prices, missing cost basis, unreconciled statements, duplicate risk, and double-count risks are surfaced here." />
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Button onClick={() => recompute.mutate()} disabled={recompute.isPending}>Recompute Issues</Button>
        <Badge tone={openIssues.length ? "warning" : "success"}>{openIssues.length} open issue(s)</Badge>
        {ignoredIssues.length ? <Badge tone="neutral">{ignoredIssues.length} ignored issue(s) preserved by fingerprint</Badge> : null}
      </div>
      <div className="mb-4 space-y-2">
        <MutationMessage isPending={recompute.isPending} isSuccess={recompute.isSuccess} pending="Recomputing data quality issues..." success="Data quality issues refreshed." />
        <MutationMessage isPending={ignore.isPending} isSuccess={ignore.isSuccess} pending="Ignoring issue..." success="Issue ignored by fingerprint." />
        <ApiError error={recompute.error} title="Recompute failed" />
        <ApiError error={ignore.error} title="Ignore failed" />
      </div>
      {!visibleIssues.length ? <EmptyState title="No data quality issues" detail="Current reports do not have open warnings." /> : (
        <div className="space-y-3">
          {visibleIssues.map((issue) => (
            <div key={issue.id} className={`rounded-lg border bg-card p-4 ${issue.status === "ignored" ? "opacity-60" : ""}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2"><Badge tone={issue.severity === "error" || issue.severity === "critical" ? "danger" : issue.severity === "warning" ? "warning" : "info"}>{issue.severity}</Badge><span className="font-medium">{issue.title}</span>{issue.status === "ignored" ? <Badge tone="neutral">ignored, will not reopen unless details change</Badge> : null}</div>
                  <p className="mt-2 text-sm text-muted-foreground">{issue.description}</p>
                  {issue.recommended_action ? <p className="mt-1 text-sm">{issue.recommended_action}</p> : null}
                </div>
                {issue.status === "open" ? <Button size="sm" variant="outline" onClick={() => ignore.mutate(issue.id)} disabled={ignore.isPending}>Ignore</Button> : <Badge>{issue.status}</Badge>}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
