import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { TransactionTable } from "@/components/tables/TransactionTable";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { LoadingBlock } from "@/components/ui/loading";
import { Select } from "@/components/ui/select";
import type { Transaction } from "@/types";
import { PageHeader } from "./PageHeader";

function matchesSearch(txn: Transaction, search: string) {
  if (!search.trim()) return true;
  const text = [txn.merchant_name, txn.original_description, txn.transaction_type, txn.transfer_status, txn.duplicate_status, txn.review_status, txn.category_name]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return text.includes(search.toLowerCase());
}

export function Transactions() {
  const [search, setSearch] = useState("");
  const [reviewStatus, setReviewStatus] = useState("all");
  const [duplicateStatus, setDuplicateStatus] = useState("all");
  const [transferStatus, setTransferStatus] = useState("all");
  const query = useQuery({ queryKey: ["transactions"], queryFn: () => api.get<Transaction[]>("/transactions") });
  const txns = query.data ?? [];
  const filtered = useMemo(
    () =>
      txns.filter((txn) => {
        if (!matchesSearch(txn, search)) return false;
        if (reviewStatus !== "all" && txn.review_status !== reviewStatus) return false;
        if (duplicateStatus !== "all" && txn.duplicate_status !== duplicateStatus) return false;
        if (transferStatus !== "all" && txn.transfer_status !== transferStatus) return false;
        return true;
      }),
    [txns, search, reviewStatus, duplicateStatus, transferStatus]
  );
  const needsReview = txns.filter((txn) => txn.review_status !== "reviewed").length;
  const duplicateCandidates = txns.filter((txn) => txn.duplicate_status !== "unique").length;
  const suggestedTransfers = txns.filter((txn) => txn.transfer_status === "suggested_transfer").length;
  const uncategorized = txns.filter((txn) => !txn.category_id && !txn.category_name && txn.transaction_type !== "transfer").length;
  if (query.isLoading) return <LoadingBlock label="Loading transactions" />;

  return (
    <>
      <PageHeader title="Transactions" detail="Filter transactions by review, duplicate, transfer, category, and search terms. Confirmed transfers remain visible but are excluded from income and expense reports." />
      <div className="mb-4 grid gap-3 md:grid-cols-4">
        <Card><CardHeader><CardTitle>Needs Review</CardTitle></CardHeader><CardContent><div className="text-2xl font-semibold">{needsReview}</div></CardContent></Card>
        <Card><CardHeader><CardTitle>Duplicate Candidates</CardTitle></CardHeader><CardContent><div className="text-2xl font-semibold">{duplicateCandidates}</div></CardContent></Card>
        <Card><CardHeader><CardTitle>Suggested Transfers</CardTitle></CardHeader><CardContent><div className="text-2xl font-semibold">{suggestedTransfers}</div></CardContent></Card>
        <Card><CardHeader><CardTitle>Uncategorized</CardTitle></CardHeader><CardContent><div className="text-2xl font-semibold">{uncategorized}</div></CardContent></Card>
      </div>
      <div className="mb-4 grid gap-2 md:grid-cols-4">
        <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search merchant, description, category..." aria-label="Search transactions" />
        <Select value={reviewStatus} onChange={(event) => setReviewStatus(event.target.value)} aria-label="Review status filter">
          <option value="all">All review statuses</option>
          <option value="needs_review">Needs review</option>
          <option value="reviewed">Reviewed</option>
          <option value="auto_reviewed">Auto reviewed</option>
        </Select>
        <Select value={duplicateStatus} onChange={(event) => setDuplicateStatus(event.target.value)} aria-label="Duplicate status filter">
          <option value="all">All duplicate statuses</option>
          <option value="unique">Unique</option>
          <option value="possible_duplicate">Possible duplicate</option>
          <option value="confirmed_duplicate">Confirmed duplicate</option>
          <option value="ignored_duplicate">Imported anyway</option>
        </Select>
        <Select value={transferStatus} onChange={(event) => setTransferStatus(event.target.value)} aria-label="Transfer status filter">
          <option value="all">All transfer statuses</option>
          <option value="not_transfer">Not transfer</option>
          <option value="suggested_transfer">Suggested transfer</option>
          <option value="confirmed_transfer">Confirmed transfer</option>
          <option value="rejected_transfer">Rejected transfer</option>
        </Select>
      </div>
      <div className="mb-3 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <Badge tone="neutral">Showing {filtered.length} of {txns.length}</Badge>
        {uncategorized ? <Badge tone="warning">Categorization needed</Badge> : null}
        {suggestedTransfers ? <Badge tone="warning">Transfer review needed</Badge> : null}
      </div>
      {filtered.length ? <TransactionTable data={filtered} /> : <EmptyState title="No matching transactions" detail={txns.length ? "Adjust filters or search to see more transactions." : "Stage and commit a CSV import or add manual transactions."} />}
    </>
  );
}
