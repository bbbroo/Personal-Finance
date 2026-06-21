import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement } from "react";

export function renderWithClient(ui: ReactElement, options?: RenderOptions) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
      mutations: { retry: false }
    }
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>, options);
}

export function mockFetch(routes: Record<string, unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
      const path = url.startsWith("http") ? new URL(url).pathname : url;
      const key = Object.keys(routes)
        .sort((a, b) => b.length - a.length)
        .find((route) => path.endsWith(route) || path.includes(route));
      if (!key) {
        return new Response(JSON.stringify({ message: `No mock for ${path}` }), { status: 404 });
      }
      return new Response(JSON.stringify(routes[key]), { status: 200, headers: { "Content-Type": "application/json" } });
    })
  );
}
