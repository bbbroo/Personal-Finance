import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "./Dashboard";
import { mockFetch, renderWithClient } from "@/test/utils";

describe("Dashboard", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows dashboard cards, data quality warnings, and trust checklist statuses", async () => {
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
      "/reports/trust-checklist": {
        as_of: "2026-06-21",
        overall_status: "warning",
        warning_count: 2,
        checks: {
          last_successful_backup: { status: "ok" },
          last_import_commit: { status: "committed" },
          data_quality: { status: "warning", open_issue_count: 1 },
          prices: { status: "ok" },
          reconciliation: { status: "warning", unreconciled_account_count: 1 },
          monthly_review: { status: "ok" },
          debt_payoff: { status: "warning", confidence: "low" },
          net_worth: { status: "warning", confidence: "low" },
          cash_flow: { status: "ok", confidence: "high" }
        }
      },
      "/data-quality/issues": [{ id: "i1", status: "open", severity: "warning", issue_type: "missing_cost_basis", title: "Missing basis", description: "Basis missing" }],
      "/imports": [{ id: "b1", status: "staged", original_filename: "test.csv", row_count: 1, valid_row_count: 1, error_count: 0, warning_count: 0, duplicate_row_count: 0 }]
    });
    renderWithClient(<Dashboard />);
    expect(await screen.findByText("$12,345.67")).toBeInTheDocument();
    expect(screen.getByText("Coinbase: Cost basis is incomplete")).toBeInTheDocument();
    expect(screen.getByText("Trust Checklist")).toBeInTheDocument();
    expect(screen.getByText("Last successful backup")).toBeInTheDocument();
    expect(screen.getByText("Debt payoff")).toBeInTheDocument();
  });
});
