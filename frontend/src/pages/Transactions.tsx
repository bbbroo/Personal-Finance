import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { TransactionTable } from "@/components/tables/TransactionTable";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingBlock } from "@/components/ui/loading";
import type { Transaction } from "@/types";
import { PageHeader } from "./PageHeader";

export function Transactions() {
  const query = useQuery({ queryKey: ["transactions"], queryFn: () => api.get<Transaction[]>("/transactions") });
  if (query.isLoading) return <LoadingBlock label="Loading transactions" />;
  const txns = query.data ?? [];
  return (
    <>
      <PageHeader title="Transactions" detail="Confirmed transfers remain visible but are excluded from income and expense reports." />
      {txns.length ? <TransactionTable data={txns} /> : <EmptyState title="No transactions" detail="Stage and commit a CSV import or add manual transactions." />}
    </>
  );
}
