type MutationMessageProps = {
  isPending?: boolean;
  isSuccess?: boolean;
  pending?: string;
  success?: string;
};

export function MutationMessage({ isPending, isSuccess, pending = "Working...", success = "Saved." }: MutationMessageProps) {
  if (isPending) return <div className="text-sm text-muted-foreground">{pending}</div>;
  if (isSuccess) return <div className="text-sm text-emerald-700">{success}</div>;
  return null;
}
