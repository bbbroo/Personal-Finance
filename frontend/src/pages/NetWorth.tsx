import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { NetWorthChart } from "@/components/charts/NetWorthChart";
import { WarningList } from "@/components/quality/WarningList";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingBlock } from "@/components/ui/loading";
import { formatCents } from "@/lib/utils";
import { PageHeader } from "./PageHeader";

type NetWorthResponse = {
  current: { net_worth_cents: number; assets_cents: number; liabilities_cents: number; confidence: string; metadata: { warnings: string[] } };
  history: Array<{ date: string; net_worth_cents: number; assets_cents: number; liabilities_cents: number; confidence: string }>;
};

export function NetWorth() {
  const query = useQuery({ queryKey: ["net-worth"], queryFn: () => api.get<NetWorthResponse>("/reports/net-worth") });
  if (query.isLoading) return <LoadingBlock label="Loading net worth" />;
  if (!query.data) return null;
  return (
    <>
      <PageHeader title="Net Worth" detail="Historical points come from stored account, holding, and liability snapshots." />
      <div className="grid gap-4 lg:grid-cols-[1.3fr_0.7fr]">
        <Card>
          <CardHeader><CardTitle>History</CardTitle></CardHeader>
          <CardContent><NetWorthChart data={query.data.history} /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Current Valuation</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="text-3xl font-semibold">{formatCents(query.data.current.net_worth_cents)}</div>
            <div className="flex gap-2"><Badge tone="info">Assets {formatCents(query.data.current.assets_cents)}</Badge><Badge tone="warning">Liabilities {formatCents(query.data.current.liabilities_cents)}</Badge></div>
            <Badge tone={query.data.current.confidence === "high" ? "success" : "warning"}>{query.data.current.confidence}</Badge>
            <WarningList warnings={query.data.current.metadata.warnings} />
          </CardContent>
        </Card>
      </div>
    </>
  );
}
