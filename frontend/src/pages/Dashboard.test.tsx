import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "./Dashboard";
import { mockFetch, renderWithClient } from "@/test/utils";

describe("Dashboard", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows dashboard cards and data quality warnings", async () => {
    mockFetch({
      "/reports/dashboard": {
        net_worth: {
          net_worth_cents: 1234567,
          assets_cents: 1500000,
          liabilities_cents: 265433,
          confidence: "low",
          metadata: { warnings: ["Coinbase: Cost basis is incomplete"] }
        },
        cash_flow: {
          income_cents: 500000,
          expenses_cents: 250000,
          savings_rate_decimal: "0.5",
          confidence: "high",
          warnings: []
        },
        allocation: { total_cents: 100000, confidence: "low", warnings: [], slices: [{ asset_class: "cash", value_cents: 100000, percent_decimal: "1" }] },
        cards: {
          cash_balance_cents: 100000,
          investments_total_cents: 200000,
          crypto_total_cents: 30000,
          liabilities_total_cents: 265433
        },
        history: [{ date: "2026-06-21", net_worth_cents: 1234567, assets_cents: 1500000, liabilities_cents: 265433, confidence: "low" }]
      },
      "/data-quality/issues": [{ id: "i1", status: "open", severity: "warning", issue_type: "missing_cost_basis", title: "Missing basis", description: "Basis missing" }],
      "/imports": [{ id: "b1", status: "staged", original_filename: "test.csv", row_count: 1, valid_row_count: 1, error_count: 0, warning_count: 0, duplicate_row_count: 0 }]
    });
    renderWithClient(<Dashboard />);
    expect(await screen.findByText("$12,345.67")).toBeInTheDocument();
    expect(screen.getByText("Coinbase: Cost basis is incomplete")).toBeInTheDocument();
    expect(screen.getByText("Open quality issues")).toBeInTheDocument();
  });
});
