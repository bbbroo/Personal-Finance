import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingBlock } from "@/components/ui/loading";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Account } from "@/types";
import { PageHeader } from "./PageHeader";

export function Accounts() {
  const query = useQuery({ queryKey: ["accounts"], queryFn: () => api.get<Account[]>("/accounts") });
  if (query.isLoading) return <LoadingBlock label="Loading accounts" />;
  const accounts = query.data ?? [];
  return (
    <>
      <PageHeader title="Accounts" detail="Each account has an explicit valuation method and sign policy for net-worth correctness." />
      {!accounts.length ? (
        <EmptyState title="No accounts yet" detail="Create accounts or import a CSV to start building your local ledger." />
      ) : (
        <div className="overflow-hidden rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Institution</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Valuation</TableHead>
                <TableHead>Sign policy</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {accounts.map((account) => (
                <TableRow key={account.id}>
                  <TableCell className="font-medium">{account.name}</TableCell>
                  <TableCell>{account.institution ?? "Manual"}</TableCell>
                  <TableCell>{account.account_type}</TableCell>
                  <TableCell><Badge tone="info">{account.valuation_method}</Badge></TableCell>
                  <TableCell>{account.balance_sign_policy}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </>
  );
}
