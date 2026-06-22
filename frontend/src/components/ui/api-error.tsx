type ApiErrorProps = {
  error: unknown;
  title?: string;
};

export function errorMessage(error: unknown): string {
  if (!error) return "";
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return JSON.stringify(error);
}

export function ApiError({ error, title = "Action failed" }: ApiErrorProps) {
  if (!error) return null;
  return (
    <div role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-950">
      <div className="font-medium">{title}</div>
      <div className="mt-1 break-words">{errorMessage(error)}</div>
    </div>
  );
}
