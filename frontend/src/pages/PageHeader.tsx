export function PageHeader({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
      {detail ? <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{detail}</p> : null}
    </div>
  );
}
