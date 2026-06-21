import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { formatCents } from "@/lib/utils";
import type { AllocationReport } from "@/types";

const colors = ["#0f766e", "#22c55e", "#84cc16", "#14b8a6", "#06b6d4", "#64748b", "#a3a3a3", "#ef4444"];

export function AllocationChart({ allocation }: { allocation: AllocationReport }) {
  const data = allocation.slices.map((slice) => ({
    name: slice.asset_class.replaceAll("_", " "),
    value: slice.value_cents
  }));
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius={58} outerRadius={98} paddingAngle={2}>
            {data.map((entry, index) => (
              <Cell key={entry.name} fill={colors[index % colors.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => formatCents(Number(value))} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
