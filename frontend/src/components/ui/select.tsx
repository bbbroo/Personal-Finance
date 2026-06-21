import * as React from "react";

import { cn } from "@/lib/utils";

export function Select({ className, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn("focus-ring h-10 rounded-md border bg-background px-3 py-2 text-sm", className)}
      {...props}
    />
  );
}
