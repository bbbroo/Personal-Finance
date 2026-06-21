import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DataQuality } from "./DataQuality";
import { mockFetch, renderWithClient } from "@/test/utils";

describe("DataQuality", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("surfaces actionable warnings", async () => {
    mockFetch({
      "/data-quality/issues": [
        {
          id: "i1",
          severity: "warning",
          issue_type: "missing_cost_basis",
          title: "Holding cost basis is incomplete",
          description: "Gain/loss is unknown.",
          recommended_action: "Import a verified export.",
          status: "open"
        }
      ]
    });
    renderWithClient(<DataQuality />);
    expect(await screen.findByText("Holding cost basis is incomplete")).toBeInTheDocument();
    expect(screen.getByText("Import a verified export.")).toBeInTheDocument();
  });
});
