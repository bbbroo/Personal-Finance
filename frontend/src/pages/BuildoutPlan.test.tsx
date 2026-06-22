import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BuildoutPlan } from "./BuildoutPlan";
import { renderWithClient } from "@/test/utils";

describe("BuildoutPlan", () => {
  it("tracks the 100-plus build-out items inside the app", () => {
    renderWithClient(<BuildoutPlan />);

    expect(screen.getByText("Build-out Plan")).toBeInTheDocument();
    expect(screen.getByText("Total Tracked")).toBeInTheDocument();
    expect(screen.getByText("Review queue")).toBeInTheDocument();
    expect(screen.getByText("Reconciliation Center")).toBeInTheDocument();
    expect(screen.getByText("Guided transaction correction UI")).toBeInTheDocument();
    expect(screen.getByText("Backend error catalog")).toBeInTheDocument();
    expect(screen.getByText("Daily/weekly/monthly workflow")).toBeInTheDocument();
  });
});
