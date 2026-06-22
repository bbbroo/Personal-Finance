import type { ImportBatch, StagedRow } from "@/types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

function formatApiError(error: unknown, fallback: string): string {
  if (!error || typeof error !== "object") return fallback;
  const data = error as { message?: string; detail?: unknown; error_code?: string };
  if (typeof data.message === "string") return data.message;
  if (data.error_code) return `${data.error_code}: ${fallback}`;
  if (data.detail && typeof data.detail === "object") {
    const detail = data.detail as { message?: string; error_code?: string; recommended_action?: string };
    const parts = [detail.error_code, detail.message, detail.recommended_action].filter(Boolean);
    if (parts.length) return parts.join(" — ");
  }
  if (typeof data.detail === "string") return data.detail;
  return JSON.stringify(error);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: response.statusText }));
    throw new Error(formatApiError(error, response.statusText));
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
