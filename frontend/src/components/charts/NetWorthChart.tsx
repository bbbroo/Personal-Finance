import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatCents } from "@/lib/utils";

export function NetWorthChart({
  data
}: {
  data: Array<{ date: string; net_worth_cents: number; assets_cents?: number; liabilities_cents?: number }>;
}) {
  if (import.meta.env.MODE === "test") {
    return <div aria-label="Net worth chart" className="h-72 w-full" />;
  }
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer minWidth={1} minHeight={1}>
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(180 8% 86%)" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis tickFormatter={(value) => `$${Math.round(Number(value) / 1000) / 100}k`} tick={{ fontSize: 12 }} />
          <Tooltip formatter={(value) => formatCents(Number(value))} />
          <Area type="monotone" dataKey="net_worth_cents" stroke="hsl(173 80% 30%)" fill="hsl(173 80% 30% / 0.18)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
