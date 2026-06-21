import { screen } from "@testing-library/react";
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
});
