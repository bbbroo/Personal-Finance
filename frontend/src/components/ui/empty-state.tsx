import { AlertCircle } from "lucide-react";

export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="flex min-h-40 flex-col items-center justify-center rounded-lg border border-dashed bg-muted/40 p-8 text-center">
      <AlertCircle className="mb-3 h-6 w-6 text-muted-foreground" aria-hidden />
      <p className="font-medium">{title}</p>
      {detail ? <p className="mt-1 max-w-md text-sm text-muted-foreground">{detail}</p> : null}
    </div>
  );
}
