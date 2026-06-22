import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DataQuality } from "./DataQuality";
import { mockFetch, renderWithClient } from "@/test/utils";

const issues = [
  {
    id: "i1",
    severity: "warning",
    issue_type: "missing_cost_basis",
    title: "Holding cost basis is incomplete",
    description: "Gain/loss is unknown.",
    recommended_action: "Import a verified export.",
    status: "open"
  },
  {
    id: "i2",
    severity: "info",
    issue_type: "ignored_stale_price",
    title: "Ignored stale price",
    description: "This issue was ignored.",
    recommended_action: "It will reopen if details change.",
    status: "ignored"
  }
];

describe("DataQuality", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("surfaces actionable warnings and ignored issues separately", async () => {
    mockFetch({ "/data-quality/issues": issues });
    renderWithClient(<DataQuality />);
    expect(await screen.findByText("Holding cost basis is incomplete")).toBeInTheDocument();
    expect(screen.getByText("Import a verified export.")).toBeInTheDocument();
    expect(screen.getByText("Ignored stale price")).toBeInTheDocument();
    expect(screen.getByText("ignored, will not reopen unless details change")).toBeInTheDocument();
    expect(screen.getByText("1 ignored issue(s) preserved by fingerprint")).toBeInTheDocument();
  });

  it("calls recompute and ignore endpoints", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
      if (url.endsWith("/api/data-quality/issues") && init?.method !== "POST") {
        return new Response(JSON.stringify(issues), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (url.endsWith("/api/data-quality/recompute") && init?.method === "POST") {
        return new Response(JSON.stringify({ recomputed: true }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (url.endsWith("/api/data-quality/issues/i1/ignore") && init?.method === "POST") {
        return new Response(JSON.stringify({ ignored: true }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      return new Response(JSON.stringify({ message: `No mock for ${url}` }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithClient(<DataQuality />);
    await userEvent.click(await screen.findByText("Recompute Issues"));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/data-quality/recompute"), expect.objectContaining({ method: "POST" })));

    await userEvent.click(screen.getByText("Ignore"));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/data-quality/issues/i1/ignore"), expect.objectContaining({ method: "POST" })));
  });
});
