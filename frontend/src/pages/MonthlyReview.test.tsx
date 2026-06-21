import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MonthlyReview } from "./MonthlyReview";
import { mockFetch, renderWithClient } from "@/test/utils";

describe("MonthlyReview", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("warns when finalized source data changed", async () => {
    mockFetch({
      "/monthly-review/": {
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
      }
    });
    renderWithClient(<MonthlyReview />);
    expect(await screen.findByText("Source data has changed since finalization.")).toBeInTheDocument();
  });
});
