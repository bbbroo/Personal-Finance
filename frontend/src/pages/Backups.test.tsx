import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Backups } from "./Backups";
import { mockFetch, renderWithClient } from "@/test/utils";

describe("Backups", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows backup safety empty state", async () => {
    mockFetch({ "/backups": [] });
    renderWithClient(<Backups />);
    expect(await screen.findByText("No backups yet")).toBeInTheDocument();
    expect(screen.getByText(/SQLite's backup API/)).toBeInTheDocument();
  });

  it("confirms before restore and shows restart-required success", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
      if (url.endsWith("/api/backups")) {
        return new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (url.endsWith("/api/backups/restore") && init?.method === "POST") {
        return new Response(JSON.stringify({ message: "Restore completed safely.", restart_required: true }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      return new Response(JSON.stringify({ message: `No mock for ${url}` }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithClient(<Backups />);
    await userEvent.type(await screen.findByPlaceholderText("Paste backup .sqlite3 path"), "C:\\backup.sqlite3");
    await userEvent.click(screen.getByText("Validate And Restore"));

    expect(await screen.findByRole("dialog", { name: "Restore this backup?" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Validate and restore" }));
    await waitFor(() => expect(screen.getByText("Restore completed safely.")).toBeInTheDocument());
    expect(screen.getByText("Restart required before continuing to use the app.")).toBeInTheDocument();
  });

  it("shows backend error codes when restore fails", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
      if (url.endsWith("/api/backups")) {
        return new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (url.endsWith("/api/backups/restore") && init?.method === "POST") {
        return new Response(
          JSON.stringify({ detail: { error_code: "BACKUP_SCHEMA_MISMATCH", message: "Backup schema version is not supported.", recommended_action: "Choose another backup." } }),
          { status: 422, headers: { "Content-Type": "application/json" } }
        );
      }
      return new Response(JSON.stringify({ message: `No mock for ${url}` }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithClient(<Backups />);
    await userEvent.type(await screen.findByPlaceholderText("Paste backup .sqlite3 path"), "C:\\bad.sqlite3");
    await userEvent.click(screen.getByText("Validate And Restore"));
    await userEvent.click(await screen.findByRole("button", { name: "Validate and restore" }));

    expect(await screen.findByText("Restore failed")).toBeInTheDocument();
    expect(screen.getByText(/BACKUP_SCHEMA_MISMATCH/)).toBeInTheDocument();
  });
});
