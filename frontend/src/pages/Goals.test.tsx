import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Goals } from "./Goals";
import { renderWithClient } from "@/test/utils";

const goals = [{ id: "g1", name: "Emergency Fund", goal_type: "savings", target_cents: 1000000, current_manual_cents: 250000, status: "active", progress_method: "manual" }];
const accounts = [{ id: "a1", name: "Checking", account_type: "cash", valuation_method: "balance_snapshot", balance_sign_policy: "asset_positive" }];
const links = [{ id: "l1", goal_id: "g1", account_id: "a1", allocation_percent: "100" }];

describe("Goals", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders linked accounts and deletes links through confirmation dialog", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
      if (url.endsWith("/api/goals")) return new Response(JSON.stringify(goals), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/accounts")) return new Response(JSON.stringify(accounts), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/goals/links")) return new Response(JSON.stringify(links), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/goals/g1/links/l1") && init?.method === "DELETE") return new Response(JSON.stringify({ deleted: true }), { status: 200, headers: { "Content-Type": "application/json" } });
      return new Response(JSON.stringify({ message: `No mock for ${url}` }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithClient(<Goals />);

    expect((await screen.findAllByText("Emergency Fund")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Checking").length).toBeGreaterThan(0);
    await userEvent.click(screen.getByText("Delete"));
    expect(await screen.findByRole("dialog", { name: "Delete this goal link?" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Delete link" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/goals/g1/links/l1"), expect.objectContaining({ method: "DELETE" })));
  });

  it("adds a goal link through the audited backend endpoint", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
      if (url.endsWith("/api/goals")) return new Response(JSON.stringify(goals), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/accounts")) return new Response(JSON.stringify(accounts), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/goals/links")) return new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/goals/g1/links") && init?.method === "POST") return new Response(JSON.stringify({ id: "l2", goal_id: "g1", account_id: "a1", allocation_percent: "100" }), { status: 200, headers: { "Content-Type": "application/json" } });
      return new Response(JSON.stringify({ message: `No mock for ${url}` }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithClient(<Goals />);

    await userEvent.selectOptions(await screen.findByDisplayValue("Choose account"), "a1");
    await userEvent.click(screen.getByText("Add Link"));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/goals/g1/links"), expect.objectContaining({ method: "POST" })));
  });
});
