import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Liabilities } from "./Liabilities";
import { mockFetch, renderWithClient } from "@/test/utils";

describe("Liabilities", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows payoff confidence, snowball vs avalanche comparison, and allocation detail", async () => {
    mockFetch({
      "/liabilities/payoff-plan": {
        strategy: "avalanche",
        extra_payment_cents: 2500,
        warnings: ["Liability l1: Payment allocation history includes estimates; projection confidence is low."],
        summary: {
          confidence: "low",
          confidence_explanation: "One or more liabilities have missing or estimated payoff inputs.",
          total_projected_months: 18,
          total_estimated_interest_cents: 12345
        },
        comparison: {
          avalanche: { total_projected_months: 18, total_estimated_interest_cents: 12345 },
          snowball: { total_projected_months: 22, total_estimated_interest_cents: 16000 }
        },
        rows: [
          {
            liability_id: "l1",
            payoff_order: 1,
            balance_cents: 200000,
            apr_decimal: "0.29",
            minimum_payment_cents: 20000,
            extra_payment_cents: 2500,
            projected_payoff_months_with_extra: 11,
            estimated_interest_cents_with_extra: 3123,
            apr_source: "standard",
            projection_quality: "estimated",
            allocation_summary: { allocation_count: 2, has_estimated_allocations: true }
          }
        ]
      },
      "/liabilities": [{ id: "l1", liability_type: "credit_card", current_balance_cents: 200000, minimum_payment_cents: 20000, due_day: 15, confidence: "low" }]
    });

    renderWithClient(<Liabilities />);

    expect(await screen.findByText("Debt payoff confidence")).toBeInTheDocument();
    expect(screen.getByText("Snowball vs avalanche comparison")).toBeInTheDocument();
    expect(screen.getByText("One or more liabilities have missing or estimated payoff inputs.")).toBeInTheDocument();
    expect(screen.getByText("2 payment allocation(s), includes estimates")).toBeInTheDocument();
    expect(screen.getByText(/Liability l1/)).toBeInTheDocument();
  });

  it("shows payoff plan query errors without hiding the liabilities list", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
        if (url.endsWith("/api/liabilities")) {
          return new Response(JSON.stringify([{ id: "l1", liability_type: "loan", current_balance_cents: 50000, minimum_payment_cents: 10000, due_day: null, confidence: "medium" }]), { status: 200, headers: { "Content-Type": "application/json" } });
        }
        if (url.endsWith("/api/liabilities/payoff-plan")) {
          return new Response(JSON.stringify({ detail: { error_code: "PAYOFF_FAILED", message: "Payoff failed." } }), { status: 500, headers: { "Content-Type": "application/json" } });
        }
        return new Response(JSON.stringify({ message: `No mock for ${url}` }), { status: 404 });
      })
    );

    renderWithClient(<Liabilities />);

    expect(await screen.findByText("loan")).toBeInTheDocument();
    expect(await screen.findByText("Payoff plan failed to load")).toBeInTheDocument();
    expect(screen.getByText(/PAYOFF_FAILED/)).toBeInTheDocument();
  });
});
