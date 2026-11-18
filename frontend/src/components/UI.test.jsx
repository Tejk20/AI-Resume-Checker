import React from "react";
import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, it, expect, vi } from "vitest";
import { State, Score, Chips, JobSelect } from "./UI";
import { MemoryRouter } from "react-router-dom";
afterEach(cleanup);
describe("recruiter feedback", () => {
  it("does not display stale content when API fails", () => {
    render(
      <State error="Database unavailable" retry={vi.fn()}>
        <span>Stale ranking</span>
      </State>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Database unavailable");
    expect(screen.queryByText("Stale ranking")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
  it("shows scores with two decimal places", () => {
    render(<Score value={84.5} />);
    expect(screen.getByText("84.50")).toBeInTheDocument();
  });
  it("labels missing evidence and offers job context", () => {
    render(
      <MemoryRouter>
        <Chips items={[]} />
        <JobSelect
          jobs={[{ id: "a", title: "Backend" }]}
          selected="a"
          onChange={vi.fn()}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText("None identified")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Active job" })).toHaveValue(
      "Backend",
    );
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "/jobs/new?edit=a",
    );
  });
});
