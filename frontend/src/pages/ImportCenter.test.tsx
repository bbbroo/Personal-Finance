import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ImportCenter } from "./ImportCenter";
import { mockFetch, renderWithClient } from "@/test/utils";

describe("ImportCenter", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows staged import preview states", async () => {
    mockFetch({
      "/accounts": [{ id: "a1", name: "Checking", account_type: "cash", valuation_method: "balance_snapshot", balance_sign_policy: "asset_positive" }],
      "/imports": [{ id: "b1", original_filename: "checking.csv", status: "staged", row_count: 1, valid_row_count: 1, error_count: 0, warning_count: 1, duplicate_row_count: 0 }],
      "/imports/b1/staged-rows": [
        {
          id: "r1",
          row_number: 2,
          normalized_json: { transaction_date: "2026-06-01", merchant_name: "Coffee", amount_cents: -425 },
          validation_status: "warning",
          duplicate_status: "unique",
          transfer_status: "suggested_transfer",
          user_action: "import"
        }
      ]
    });
    renderWithClient(<ImportCenter />);
    await userEvent.click(await screen.findByText("checking.csv"));
    await waitFor(() => expect(screen.getByText("suggested_transfer")).toBeInTheDocument());
    expect(screen.getByText("warning")).toBeInTheDocument();
  });
});
