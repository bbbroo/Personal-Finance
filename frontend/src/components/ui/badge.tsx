import * as React from "react";

import { cn } from "@/lib/utils";

const tones: Record<string, string> = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  neutral: "border-border bg-muted text-muted-foreground",
  warning: "border-yellow-300 bg-yellow-50 text-yellow-900",
  danger: "border-red-200 bg-red-50 text-red-800",
  info: "border-teal-200 bg-teal-50 text-teal-800"
};

export function Badge({
  className,
  tone = "neutral",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: keyof typeof tones | string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-medium",
        tones[tone] ?? tones.neutral,
        className
      )}
      {...props}
    />
  );
}
