import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ImportCenter } from "./ImportCenter";
import { mockFetch, renderWithClient } from "@/test/utils";

const accounts = [{ id: "a1", name: "Checking", account_type: "cash", valuation_method: "balance_snapshot", balance_sign_policy: "asset_positive" }];

function batch(status = "staged", overrides = {}) {
  return {
    id: "b1",
    original_filename: "checking.csv",
    status,
    row_count: 4,
    valid_row_count: 2,
    error_count: 1,
    warning_count: 1,
    duplicate_row_count: 1,
    skipped_row_count: 0,
    ...overrides
  };
}

const stagedRows = [
  {
    id: "r1",
    row_number: 2,
    normalized_json: { transaction_date: "2026-06-01", merchant_name: "Coffee", amount_cents: -425 },
    validation_status: "warning",
    duplicate_status: "possible_duplicate",
    transfer_status: "not_transfer",
    user_action: "import",
    warnings_json: ["Possible duplicate from same merchant and amount"]
  },
  {
    id: "r2",
    row_number: 3,
    normalized_json: { transaction_date: "2026-06-02", merchant_name: "Bad Row", amount_cents: null },
    validation_status: "error",
    duplicate_status: "unique",
    transfer_status: "not_transfer",
    user_action: "needs_review",
    errors_json: ["Amount is required"]
  },
  {
    id: "r3",
    row_number: 4,
    normalized_json: { transaction_date: "2026-06-03", merchant_name: "Transfer Out", amount_cents: -10000, transfer_candidate: { candidate_type: "staged_row", candidate_id: "r4" } },
    validation_status: "valid",
    duplicate_status: "unique",
    transfer_status: "confirmed_transfer",
    user_action: "import"
  },
  {
    id: "r4",
    row_number: 5,
    normalized_json: { transaction_date: "2026-06-03", merchant_name: "Transfer In", amount_cents: 10000, transfer_candidate: { candidate_type: "staged_row", candidate_id: "r3" } },
    validation_status: "valid",
    duplicate_status: "unique",
    transfer_status: "suggested_transfer",
    user_action: "import"
  }
];

function setupImportMocks(rows = stagedRows, currentBatch = batch()) {
  mockFetch({
    "/accounts": accounts,
    "/imports": [currentBatch],
    "/imports/b1/staged-rows": rows
  });
}

describe("ImportCenter wizard", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders the upload step with selected batch file, row count, and batch id", async () => {
    setupImportMocks();
    renderWithClient(<ImportCenter />);

    expect(await screen.findByText("Import Wizard")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "1. Upload" })).toBeInTheDocument();
    expect(screen.getAllByText("checking.csv").length).toBeGreaterThan(0);
    expect(screen.getByText("b1")).toBeInTheDocument();
    expect(screen.getByText("Rows")).toBeInTheDocument();
  });

  it("uploads a CSV through the upload step", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.pathname + input.search : input.url;
      if (url.endsWith("/api/accounts")) return new Response(JSON.stringify(accounts), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/imports")) return new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.includes("/api/imports/upload") && init?.method === "POST") return new Response(JSON.stringify(batch("staged")), { status: 200, headers: { "Content-Type": "application/json" } });
      return new Response(JSON.stringify({ message: `No mock for ${url}` }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithClient(<ImportCenter />);
    await userEvent.selectOptions(await screen.findByLabelText("Target account"), "a1");
    const file = new File(["Date,Description,Amount\n2026-06-01,Coffee,-4.25"], "checking.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText("Upload CSV"), file);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/imports/upload"), expect.objectContaining({ method: "POST" })));
  });

  it("validates mapping JSON locally and shows remap API errors", async () => {
    setupImportMocks();
    renderWithClient(<ImportCenter />);

    const mapping = await screen.findByLabelText("Mapping JSON");
    fireEvent.change(mapping, { target: { value: "{bad json" } });
    await userEvent.click(screen.getByText("Reparse With Mapping"));
    expect(await screen.findByRole("alert")).toHaveTextContent(/JSON/);
  });

  it("shows validation errors and blocks commit", async () => {
    setupImportMocks();
    renderWithClient(<ImportCenter />);

    expect(await screen.findByRole("heading", { name: "3. Validation" })).toBeInTheDocument();
    expect((await screen.findAllByText("Amount is required")).length).toBeGreaterThan(0);
    expect(screen.getByText("Commit is blocked until validation errors are fixed, skipped, or remapped.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Commit import" })).toBeDisabled();
  });

  it("shows duplicate review and sends row decisions", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
      if (url.endsWith("/api/accounts")) return new Response(JSON.stringify(accounts), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/imports")) return new Response(JSON.stringify([batch()]), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/imports/b1/staged-rows")) return new Response(JSON.stringify(stagedRows), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/imports/b1/staged-rows/r1") && init?.method === "PATCH") return new Response(JSON.stringify({ ...stagedRows[0], duplicate_status: "ignored_duplicate" }), { status: 200, headers: { "Content-Type": "application/json" } });
      return new Response(JSON.stringify({ message: `No mock for ${url}` }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithClient(<ImportCenter />);
    expect(await screen.findByRole("heading", { name: "4. Duplicate Review" })).toBeInTheDocument();
    expect(await screen.findByLabelText("Duplicate decision row 2")).toBeInTheDocument();
    expect(screen.getAllByText("Coffee").length).toBeGreaterThan(0);
    await userEvent.selectOptions(screen.getByLabelText("Duplicate decision row 2"), "ignored_duplicate");

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/staged-rows/r1"), expect.objectContaining({ method: "PATCH" })));
  });

  it("shows transfer pairs and blocks incomplete confirmed transfers", async () => {
    setupImportMocks();
    renderWithClient(<ImportCenter />);

    expect(await screen.findByRole("heading", { name: "5. Transfer Review" })).toBeInTheDocument();
    expect(await screen.findByLabelText("Transfer decision row 4")).toBeInTheDocument();
    expect(screen.getByText(/The paired side is not confirmed as a transfer/)).toBeInTheDocument();
    expect(screen.getByText(/Commit blocked: 1 confirmed transfer row/)).toBeInTheDocument();
  });

  it("shows final commit summary and confirms commit when ready", async () => {
    const readyRows = stagedRows.map((row) =>
      row.id === "r2" ? { ...row, validation_status: "valid", errors_json: [] } : row.id === "r4" ? { ...row, transfer_status: "confirmed_transfer" } : row
    );
    const readyBatch = batch("staged", { error_count: 0, valid_row_count: 4, warning_count: 1 });
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
      if (url.endsWith("/api/accounts")) return new Response(JSON.stringify(accounts), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/imports")) return new Response(JSON.stringify([readyBatch]), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/imports/b1/staged-rows")) return new Response(JSON.stringify(readyRows), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/imports/b1/commit") && init?.method === "POST") return new Response(JSON.stringify(batch("committed", { error_count: 0, created_transaction_count: 4, pre_import_backup_id: "backup1" })), { status: 200, headers: { "Content-Type": "application/json" } });
      return new Response(JSON.stringify({ message: `No mock for ${url}` }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithClient(<ImportCenter />);
    expect(await screen.findByRole("heading", { name: "6. Commit" })).toBeInTheDocument();
    expect(screen.getByText("Rows to import")).toBeInTheDocument();
    const commitButton = screen.getByRole("button", { name: "Commit import" });
    await waitFor(() => expect(commitButton).not.toBeDisabled());
    await userEvent.click(commitButton);
    const dialog = await screen.findByRole("dialog", { name: "Commit this import?" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Commit import" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/commit"), expect.objectContaining({ method: "POST" })));
  });

  it("shows post-import summary and confirms rollback", async () => {
    const committedBatch = batch("committed", { error_count: 0, created_transaction_count: 4, pre_import_backup_id: "backup1" });
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
      if (url.endsWith("/api/accounts")) return new Response(JSON.stringify(accounts), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/imports")) return new Response(JSON.stringify([committedBatch]), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/imports/b1/staged-rows")) return new Response(JSON.stringify(stagedRows), { status: 200, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/api/imports/b1/rollback") && init?.method === "POST") return new Response(JSON.stringify(batch("rolled_back", { error_count: 0 })), { status: 200, headers: { "Content-Type": "application/json" } });
      return new Response(JSON.stringify({ message: `No mock for ${url}` }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithClient(<ImportCenter />);
    expect(await screen.findByRole("heading", { name: "7. Post-import Summary" })).toBeInTheDocument();
    expect(screen.getByText("backup1")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Rollback this committed import" }));
    const dialog = await screen.findByRole("dialog", { name: "Rollback this committed import?" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Rollback import" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/rollback"), expect.objectContaining({ method: "POST" })));
  });
});
