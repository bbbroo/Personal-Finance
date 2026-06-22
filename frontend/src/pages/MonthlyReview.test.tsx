import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MonthlyReview } from "./MonthlyReview";
import { mockFetch, renderWithClient } from "@/test/utils";

const reviewPayload = {
  review_month: "2026-06",
  status: "finalized",
  starting_net_worth_cents: 100000,
  ending_net_worth_cents: 125000,
  net_worth_change_cents: 25000,
  income_cents: 50000,
  expenses_cents: 20000,
  savings_rate_decimal: "0.6",
  top_spending_categories: [],
  biggest_transactions: [],
  data_quality_summary: { warnings: [] },
  source_changed_since_finalization: true
};

describe("MonthlyReview", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("warns when finalized source data changed", async () => {
    mockFetch({ "/monthly-review/": reviewPayload });
    renderWithClient(<MonthlyReview />);
    expect(await screen.findByText("Source data has changed since finalization.")).toBeInTheDocument();
  });

  it("confirms before regenerating a review", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
      if (url.includes("/api/monthly-review/") && init?.method !== "POST") {
        return new Response(JSON.stringify(reviewPayload), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (url.includes("/api/monthly-review/") && url.endsWith("/regenerate") && init?.method === "POST") {
        return new Response(JSON.stringify({ ...reviewPayload, status: "regenerated" }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      return new Response(JSON.stringify({ message: `No mock for ${url}` }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithClient(<MonthlyReview />);
    await userEvent.click(await screen.findByText("Regenerate"));

    expect(await screen.findByRole("dialog", { name: "Regenerate this monthly review?" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Regenerate review" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/regenerate"), expect.objectContaining({ method: "POST" })));
  });
});
