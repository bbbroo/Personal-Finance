import type { ImportBatch, StagedRow } from "@/types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: response.statusText }));
    throw new Error(error.message ?? error.detail?.message ?? JSON.stringify(error));
  }
  return response.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body)
    }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: "PATCH",
      body: JSON.stringify(body)
    }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  uploadImport: (file: File, accountId: string, institution?: string) => {
    const form = new FormData();
    form.append("file", file);
    const params = new URLSearchParams({ account_id: accountId, import_type: "transactions" });
    if (institution) params.set("institution", institution);
    return request<ImportBatch>(`/imports/upload?${params.toString()}`, { method: "POST", body: form });
  },
  stagedRows: (batchId: string) => request<StagedRow[]>(`/imports/${batchId}/staged-rows`)
};
