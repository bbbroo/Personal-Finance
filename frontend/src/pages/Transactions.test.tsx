import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Transactions } from "./Transactions";
import { mockFetch, renderWithClient } from "@/test/utils";

const transactions = [
  { id: "t1", transaction_date: "2026-06-01", merchant_name: "Kroger", original_description: "KROGER", amount_cents: -5200, transaction_type: "expense", transfer_status: "not_transfer", duplicate_status: "unique", review_status: "needs_review", category_name: "Groceries" },
  { id: "t2", transaction_date: "2026-06-02", merchant_name: "Bank Transfer", original_description: "TRANSFER", amount_cents: 10000, transaction_type: "transfer", transfer_status: "suggested_transfer", duplicate_status: "possible_duplicate", review_status: "reviewed" }
];

describe("Transactions", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows cleanup counts, status columns, and filters transactions", async () => {
    mockFetch({ "/transactions": transactions });
    renderWithClient(<Transactions />);

    expect(await screen.findByText("Needs Review")).toBeInTheDocument();
    expect(screen.getByText("Duplicate Candidates")).toBeInTheDocument();
    expect(screen.getByText("Suggested Transfers")).toBeInTheDocument();
    expect(screen.getByText("Category")).toBeInTheDocument();
    expect(screen.getByText("Review")).toBeInTheDocument();
    expect(screen.getByText("Kroger")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("Transfer status filter"), "suggested_transfer");
    expect(screen.getByText("Bank Transfer")).toBeInTheDocument();
    expect(screen.queryByText("Kroger")).not.toBeInTheDocument();
  });
});
