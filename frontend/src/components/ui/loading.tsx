export function LoadingBlock({ label = "Loading" }: { label?: string }) {
  return (
    <div className="grid min-h-40 place-items-center rounded-lg border bg-card">
      <div className="text-sm text-muted-foreground">{label}...</div>
    </div>
  );
}
