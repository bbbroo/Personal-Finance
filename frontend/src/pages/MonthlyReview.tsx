import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { WarningList } from "@/components/quality/WarningList";
import { ApiError } from "@/components/ui/api-error";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";
import { LoadingBlock } from "@/components/ui/loading";
import { MutationMessage } from "@/components/ui/mutation-message";
import { formatCents, formatPercent, yyyyMm } from "@/lib/utils";
import { PageHeader } from "./PageHeader";

type Review = {
  review_month: string;
  status: string;
  starting_net_worth_cents: number;
  ending_net_worth_cents: number;
  net_worth_change_cents: number;
  income_cents: number;
  expenses_cents: number;
  savings_rate_decimal?: string | null;
  top_spending_categories: Array<{ category_name: string; amount_cents: number }>;
  biggest_transactions: Array<{ id: string; merchant_name?: string | null; amount_cents: number }>;
  data_quality_summary: { warnings: string[] };
  source_changed_since_finalization: boolean;
};

export function MonthlyReview() {
  const month = yyyyMm();
  const client = useQueryClient();
  const { confirm, dialog } = useConfirmDialog();
  const query = useQuery({ queryKey: ["monthly-review", month], queryFn: () => api.get<Review>(`/monthly-review/${month}`) });
  const finalize = useMutation({ mutationFn: () => api.post(`/monthly-review/${month}/finalize`), onSuccess: () => client.invalidateQueries({ queryKey: ["monthly-review", month] }) });
  const regenerate = useMutation({ mutationFn: () => api.post(`/monthly-review/${month}/regenerate`), onSuccess: () => client.invalidateQueries({ queryKey: ["monthly-review", month] }) });
  if (query.isLoading) return <LoadingBlock label="Loading monthly review" />;
  const review = query.data;
  if (!review) return null;
  const confirmRegenerate = () => {
    confirm({
      title: "Regenerate this monthly review?",
      description: "Finalized numbers are preserved until you explicitly regenerate after reviewing source data changes.",
      confirmLabel: "Regenerate review",
      variant: "danger",
      onConfirm: () => regenerate.mutate()
    });
  };
  return (
    <>
      {dialog}
      <PageHeader title="Monthly Review" detail="Draft reviews recalculate; finalized reviews store source hashes and warn when source data changes." />
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Button onClick={() => finalize.mutate()} disabled={finalize.isPending}>Finalize</Button>
        <Button variant="outline" onClick={confirmRegenerate} disabled={regenerate.isPending}>Regenerate</Button>
      </div>
      <div className="mb-4 space-y-2">
        <MutationMessage isPending={finalize.isPending} isSuccess={finalize.isSuccess} pending="Finalizing review..." success="Review finalized." />
        <MutationMessage isPending={regenerate.isPending} isSuccess={regenerate.isSuccess} pending="Regenerating review..." success="Review regenerated." />
        <ApiError error={finalize.error} title="Finalize failed" />
        <ApiError error={regenerate.error} title="Regenerate failed" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card><CardHeader><CardTitle>Start</CardTitle></CardHeader><CardContent>{formatCents(review.starting_net_worth_cents)}</CardContent></Card>
        <Card><CardHeader><CardTitle>End</CardTitle></CardHeader><CardContent>{formatCents(review.ending_net_worth_cents)}</CardContent></Card>
        <Card><CardHeader><CardTitle>Change</CardTitle></CardHeader><CardContent>{formatCents(review.net_worth_change_cents)}</CardContent></Card>
        <Card><CardHeader><CardTitle>Savings Rate</CardTitle></CardHeader><CardContent>{formatPercent(review.savings_rate_decimal)}</CardContent></Card>
      </div>
      {review.source_changed_since_finalization ? (
        <div className="mt-4 rounded-md border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-950">
          <div className="font-medium">Source data has changed since finalization.</div>
          <div>Finalized numbers are preserved. Regenerate only after reviewing the changed transactions, balances, holdings, budgets, reconciliation, and data-quality issues.</div>
        </div>
      ) : null}
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card><CardHeader><CardTitle>Top Spending</CardTitle></CardHeader><CardContent className="space-y-2">{review.top_spending_categories.map((item) => <div key={item.category_name} className="flex justify-between"><span>{item.category_name}</span><span>{formatCents(item.amount_cents)}</span></div>)}</CardContent></Card>
        <Card><CardHeader><CardTitle>Data Quality</CardTitle></CardHeader><CardContent><WarningList warnings={review.data_quality_summary.warnings} /></CardContent></Card>
      </div>
    </>
  );
}
