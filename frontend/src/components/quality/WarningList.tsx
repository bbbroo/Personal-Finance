import { AlertTriangle } from "lucide-react";

import { Badge } from "@/components/ui/badge";

export function WarningList({ warnings, limit = 5 }: { warnings?: string[]; limit?: number }) {
  const visible = warnings?.slice(0, limit) ?? [];
  if (!visible.length) {
    return <Badge tone="success">No warnings</Badge>;
  }
  return (
    <div className="space-y-2">
      {visible.map((warning) => (
        <div key={warning} className="flex gap-2 rounded-md border border-yellow-200 bg-yellow-50 p-2 text-sm text-yellow-950">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <span>{warning}</span>
        </div>
      ))}
      {warnings && warnings.length > limit ? (
        <div className="text-xs text-muted-foreground">+{warnings.length - limit} more warnings</div>
      ) : null}
    </div>
  );
}
