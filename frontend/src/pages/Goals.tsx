import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingBlock } from "@/components/ui/loading";
import { formatCents, formatPercent } from "@/lib/utils";
import type { ApiRecord } from "@/types";
import { PageHeader } from "./PageHeader";

export function Goals() {
  const query = useQuery({ queryKey: ["goals"], queryFn: () => api.get<ApiRecord[]>("/goals") });
  if (query.isLoading) return <LoadingBlock label="Loading goals" />;
  const goals = query.data ?? [];
  return (
    <>
      <PageHeader title="Goals" detail="Goal progress keeps source and confidence visible, with manual progress audit-logged by the backend." />
      {!goals.length ? <EmptyState title="No goals" detail="Add a savings, debt payoff, contribution, or net worth target." /> : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {goals.map((goal) => {
            const current = goal.current_manual_cents as number | null;
            const target = goal.target_cents as number;
            const progress = current === null || !target ? null : current / target;
            return (
              <div key={String(goal.id)} className="rounded-lg border bg-card p-5 shadow-soft">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold">{String(goal.name)}</div>
                    <div className="text-sm text-muted-foreground">{String(goal.goal_type)}</div>
                  </div>
                  <Badge tone={goal.status === "active" ? "success" : "neutral"}>{String(goal.status)}</Badge>
                </div>
                <div className="mt-4 h-2 rounded-full bg-muted">
                  <div className="h-2 rounded-full bg-primary" style={{ width: `${Math.min((progress ?? 0) * 100, 100)}%` }} />
                </div>
                <div className="mt-3 text-sm">{formatCents(current)} of {formatCents(target)}</div>
                <div className="text-sm text-muted-foreground">{formatPercent(progress)} complete via {String(goal.progress_method)}</div>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
