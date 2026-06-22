import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Budgets } from "./Budgets";
import { mockFetch, renderWithClient } from "@/test/utils";

describe("Budgets", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows refund and confirmed-transfer budget safety notes", async () => {
    mockFetch({
      "/budgets": [
        {
          plan_id: "p1",
          category_name: "Groceries",
          available_cents: 50000,
          actual_cents: -2500,
          remaining_cents: 52500,
          ending_rollover_cents: 0,
          confirmed_transfer_excluded_cents: 10000,
          confidence: "high",
          warnings: ["Suggested transfers remain included until confirmed"]
        }
      ],
      "/sinking-funds": [{ id: "s1", name: "Car Insurance", target_cents: 120000, current_balance_cents: 30000, confidence: "unknown" }]
    });

    renderWithClient(<Budgets />);

    expect(await screen.findByText("Refunds or reversals are reducing spending in 1 budget line(s).")).toBeInTheDocument();
    expect(screen.getByText("Confirmed transfers are excluded from budget actuals; suggested transfers remain visible until confirmed.")).toBeInTheDocument();
    expect(screen.getByText(/Refund\/reversal reduced spending/)).toBeInTheDocument();
    expect(screen.getByText(/Confirmed transfers excluded/)).toBeInTheDocument();
    expect(screen.getByText("Car Insurance")).toBeInTheDocument();
  });

  it("shows budget query errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
        if (url.endsWith("/api/budgets")) {
          return new Response(JSON.stringify({ detail: { error_code: "BUDGET_REPORT_FAILED", message: "Budget report failed." } }), { status: 500, headers: { "Content-Type": "application/json" } });
        }
        return new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } });
      })
    );

    renderWithClient(<Budgets />);

    expect(await screen.findByText("Budget failed to load")).toBeInTheDocument();
    expect(screen.getByText(/BUDGET_REPORT_FAILED/)).toBeInTheDocument();
  });
});
