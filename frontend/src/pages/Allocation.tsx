import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { AllocationChart } from "@/components/charts/AllocationChart";
import { WarningList } from "@/components/quality/WarningList";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingBlock } from "@/components/ui/loading";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCents, formatPercent } from "@/lib/utils";
import type { AllocationReport } from "@/types";
import { PageHeader } from "./PageHeader";

export function Allocation() {
  const [mode, setMode] = useState<"investment_only" | "full_net_worth">("investment_only");
  const query = useQuery({ queryKey: ["allocation", mode], queryFn: () => api.get<AllocationReport>(`/allocation?mode=${mode}`) });
  if (query.isLoading) return <LoadingBlock label="Loading allocation" />;
  const allocation = query.data;
  if (!allocation) return null;
  return (
    <>
      <PageHeader title="Asset Allocation" detail="Unknown classifications stay visible as Other/Needs Classification." />
      <div className="mb-4 flex flex-wrap gap-2">
        <Button size="sm" variant={mode === "investment_only" ? "default" : "outline"} onClick={() => setMode("investment_only")}>Investment Only</Button>
        <Button size="sm" variant={mode === "full_net_worth" ? "default" : "outline"} onClick={() => setMode("full_net_worth")}>Full Net Worth</Button>
      </div>
      <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <Card>
          <CardHeader><CardTitle>Allocation</CardTitle></CardHeader>
          <CardContent><AllocationChart allocation={allocation} /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Slices</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <TableHeader><TableRow><TableHead>Class</TableHead><TableHead>Value</TableHead><TableHead>Percent</TableHead></TableRow></TableHeader>
              <TableBody>
                {allocation.slices.map((slice) => (
                  <TableRow key={slice.asset_class}><TableCell>{slice.asset_class}</TableCell><TableCell>{formatCents(slice.value_cents)}</TableCell><TableCell>{formatPercent(slice.percent_decimal)}</TableCell></TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
      <div className="mt-4"><WarningList warnings={allocation.warnings} /></div>
    </>
  );
}
