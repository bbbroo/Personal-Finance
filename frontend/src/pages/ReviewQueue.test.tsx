import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ReviewQueue } from "./ReviewQueue";
import { mockFetch, renderWithClient } from "@/test/utils";

describe("ReviewQueue", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("combines import, transaction, account, reconciliation, backup, data-quality, and trust warnings into one queue", async () => {
    mockFetch({
      "/accounts": [{ id: "a1", name: "Checking", account_type: "cash", valuation_method: "manual", balance_sign_policy: "asset_positive" }],
      "/data-quality/issues": [{ id: "dq1", severity: "warning", issue_type: "stale_price", title: "Price is stale", description: "Update price.", recommended_action: "Enter a current price.", status: "open" }],
      "/imports": [{ id: "b1", original_filename: "checking.csv", status: "staged", row_count: 2, valid_row_count: 1, error_count: 1, warning_count: 0, duplicate_row_count: 1 }],
      "/imports/b1/staged-rows": [{ id: "r1", row_number: 2, normalized_json: {}, validation_status: "error", duplicate_status: "possible_duplicate", transfer_status: "not_transfer", user_action: "needs_review" }],
      "/transactions": [{ id: "t1", transaction_date: "2026-06-01", original_description: "Kroger", amount_cents: -2000, transaction_type: "expense", transfer_status: "suggested_transfer", duplicate_status: "possible_duplicate", review_status: "needs_review" }],
      "/account-statements": [{ id: "s1", status: "mismatch" }],
      "/backups": [],
      "/reports/trust-checklist": { as_of: "2026-06-21", overall_status: "warning", warning_count: 1, checks: { last_successful_backup: { status: "missing" }, debt_payoff: { status: "warning", confidence: "low" } } }
    });

    renderWithClient(<ReviewQueue />);

    expect(await screen.findByText("Review Queue")).toBeInTheDocument();
    expect(screen.getByText("Checking needs balance confidence")).toBeInTheDocument();
    expect(screen.getByText("Import batch staged")).toBeInTheDocument();
    expect(screen.getByText("Import is not finalized")).toBeInTheDocument();
    expect(screen.getByText("1 staged row(s) need review")).toBeInTheDocument();
    expect(screen.getByText("1 transaction(s) need review")).toBeInTheDocument();
    expect(screen.getByText("1 uncategorized transaction(s)")).toBeInTheDocument();
    expect(screen.getByText("1 duplicate candidate transaction(s)")).toBeInTheDocument();
    expect(screen.getByText("1 suggested transfer(s)")).toBeInTheDocument();
    expect(screen.getByText("1 statement(s) not reconciled")).toBeInTheDocument();
    expect(screen.getByText("Price is stale")).toBeInTheDocument();
    expect(screen.getByText("No successful backup recorded")).toBeInTheDocument();
    expect(screen.getByText("debt payoff")).toBeInTheDocument();
  });

  it("shows an empty state when all review sources are clear", async () => {
    mockFetch({
      "/accounts": [{ id: "a1", name: "Checking", account_type: "cash", valuation_method: "imported", balance_sign_policy: "asset_positive" }],
      "/data-quality/issues": [],
      "/imports": [{ id: "b1", original_filename: "checking.csv", status: "committed", row_count: 2, valid_row_count: 2, error_count: 0, warning_count: 0, duplicate_row_count: 0 }],
      "/imports/b1/staged-rows": [],
      "/transactions": [{ id: "t1", transaction_date: "2026-06-01", original_description: "Reviewed", amount_cents: -2000, transaction_type: "expense", transfer_status: "not_transfer", duplicate_status: "unique", review_status: "reviewed", category_name: "Groceries" }],
      "/account-statements": [{ id: "s1", status: "reconciled" }],
      "/backups": [{ id: "backup1" }],
      "/reports/trust-checklist": { as_of: "2026-06-21", overall_status: "ok", warning_count: 0, checks: { last_successful_backup: { status: "ok" }, last_import_commit: { status: "committed" } } }
    });

    renderWithClient(<ReviewQueue />);

    expect(await screen.findByText("No review items")).toBeInTheDocument();
  });
});
