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
import { Select } from "@/components/ui/select";
import { formatCents, formatPercent } from "@/lib/utils";
import type { Account, ApiRecord } from "@/types";
import { PageHeader } from "./PageHeader";

type GoalLink = ApiRecord & {
  goal_id: string;
  account_id?: string | null;
  liability_id?: string | null;
  allocation_percent?: string | null;
};

export function Goals() {
  const client = useQueryClient();
  const { confirm, dialog } = useConfirmDialog();
  const [selectedGoalId, setSelectedGoalId] = useState("");
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [allocationPercent, setAllocationPercent] = useState("100");

  const query = useQuery({ queryKey: ["goals"], queryFn: () => api.get<ApiRecord[]>("/goals") });
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: () => api.get<Account[]>("/accounts") });
  const links = useQuery({ queryKey: ["goal-links"], queryFn: () => api.get<GoalLink[]>("/goals/links") });

  const addLink = useMutation({
    mutationFn: () => api.post(`/goals/${selectedGoalId || String((query.data ?? [])[0]?.id ?? "")}/links`, { account_id: selectedAccountId, allocation_percent: allocationPercent }),
    onSuccess: () => {
      setSelectedAccountId("");
      client.invalidateQueries({ queryKey: ["goal-links"] });
    }
  });
  const deleteLink = useMutation({
    mutationFn: ({ goalId, linkId }: { goalId: string; linkId: string }) => api.delete(`/goals/${goalId}/links/${linkId}`),
    onSuccess: () => client.invalidateQueries({ queryKey: ["goal-links"] })
  });

  if (query.isLoading) return <LoadingBlock label="Loading goals" />;
  if (query.isError) return <ApiError error={query.error} title="Goals failed to load" />;
  const goals = query.data ?? [];
  const accountRows = accounts.data ?? [];
  const linkRows = links.data ?? [];
  const goalOptions = goals.map((goal) => ({ id: String(goal.id), name: String(goal.name) }));
  const selectedGoal = selectedGoalId || goalOptions[0]?.id || "";

  const confirmDeleteLink = (link: GoalLink) => {
    confirm({
      title: "Delete this goal link?",
      description: "This removes the account/liability connection from the goal. The backend audit log records the deleted link details.",
      confirmLabel: "Delete link",
      variant: "danger",
      onConfirm: () => deleteLink.mutate({ goalId: String(link.goal_id), linkId: String(link.id) })
    });
  };

  return (
    <>
      {dialog}
      <PageHeader title="Goals" detail="Goal progress keeps source and confidence visible, with manual progress and link changes audit-logged by the backend." />
      {!goals.length ? <EmptyState title="No goals" detail="Add a savings, debt payoff, contribution, or net worth target." /> : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {goals.map((goal) => {
            const current = goal.current_manual_cents as number | null;
            const target = goal.target_cents as number;
            const progress = current === null || !target ? null : current / target;
            const goalLinks = linkRows.filter((link) => link.goal_id === goal.id);
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
                <div className="mt-4 space-y-2 border-t pt-3 text-sm">
                  <div className="font-medium">Linked accounts/liabilities</div>
                  {!goalLinks.length ? <div className="text-muted-foreground">No links yet.</div> : null}
                  {goalLinks.map((link) => {
                    const account = accountRows.find((item) => item.id === link.account_id);
                    return (
                      <div key={String(link.id)} className="flex items-center justify-between gap-2 rounded-md border p-2">
                        <div>
                          <div>{account?.name ?? String(link.account_id ?? link.liability_id ?? "Unknown link")}</div>
                          <div className="text-xs text-muted-foreground">Allocation {String(link.allocation_percent ?? "100")}%</div>
                        </div>
                        <Button size="sm" variant="outline" onClick={() => confirmDeleteLink(link)} disabled={deleteLink.isPending}>Delete</Button>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
      {goals.length ? (
        <div className="mt-6 rounded-lg border bg-card p-4">
          <div className="mb-3 font-medium">Add audited goal link</div>
          <div className="grid gap-2 md:grid-cols-[1fr_1fr_120px_auto]">
            <Select value={selectedGoalId} onChange={(event) => setSelectedGoalId(event.target.value)}>
              {goalOptions.map((goal) => <option key={goal.id} value={goal.id}>{goal.name}</option>)}
            </Select>
            <Select value={selectedAccountId} onChange={(event) => setSelectedAccountId(event.target.value)}>
              <option value="">Choose account</option>
              {accountRows.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}
            </Select>
            <Input value={allocationPercent} onChange={(event) => setAllocationPercent(event.target.value)} placeholder="100" />
            <Button onClick={() => addLink.mutate()} disabled={!selectedGoal || !selectedAccountId || addLink.isPending}>Add Link</Button>
          </div>
          <div className="mt-2 text-sm text-muted-foreground">Goal link create/delete actions are audit-logged by the backend.</div>
          <MutationMessage isPending={addLink.isPending} isSuccess={addLink.isSuccess} pending="Adding goal link..." success="Goal link added." />
          <MutationMessage isPending={deleteLink.isPending} isSuccess={deleteLink.isSuccess} pending="Deleting goal link..." success="Goal link deleted." />
          <ApiError error={accounts.error} title="Accounts failed to load" />
          <ApiError error={links.error} title="Goal links failed to load" />
          <ApiError error={addLink.error} title="Add goal link failed" />
          <ApiError error={deleteLink.error} title="Delete goal link failed" />
        </div>
      ) : null}
    </>
  );
}
