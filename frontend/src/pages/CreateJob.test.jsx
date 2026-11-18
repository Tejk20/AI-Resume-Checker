import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, it, expect, vi } from "vitest";
import CreateJob from "./CreateJob";
import { api } from "../services/api";
vi.mock("../services/api", () => ({
  api: { post: vi.fn(), patch: vi.fn() },
  errorMessage: () => "Request failed",
}));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
it("prefills any title selected from Active job without restricting it to suggestions", () => {
  render(
    <MemoryRouter
      initialEntries={["/jobs/new?title=Robotics%20Integration%20Architect"]}
    >
      <CreateJob refreshJobs={vi.fn()} setSelected={vi.fn()} />
    </MemoryRouter>,
  );
  expect(screen.getByLabelText("Job title")).toHaveValue(
    "Robotics Integration Architect",
  );
});
it("creates an API request, allows correction and persists reviewed requirements", async () => {
  const job = {
    id: "fictional-job",
    required_skills: ["Python"],
    preferred_skills: [],
    min_experience: 3,
    qualifications: [],
    responsibilities: ["Build APIs"],
    extraction_warnings: ["Review extraction"],
  };
  api.post.mockResolvedValue({ data: job });
  api.patch.mockResolvedValue({ data: job });
  const refreshJobs = vi.fn().mockResolvedValue([]),
    setSelected = vi.fn();
  render(
    <MemoryRouter>
      <CreateJob {...{ refreshJobs, setSelected }} />
    </MemoryRouter>,
  );
  fireEvent.change(screen.getByLabelText("Job title"), {
    target: { value: "Backend Developer" },
  });
  fireEvent.change(screen.getByLabelText("Description"), {
    target: {
      value:
        "Python backend developer with at least three years experience building APIs.",
    },
  });
  fireEvent.click(screen.getByRole("button", { name: "Extract requirements" }));
  await screen.findByText("Review extraction");
  expect(api.post).toHaveBeenCalledWith(
    "/jobs",
    expect.objectContaining({ title: "Backend Developer" }),
  );
  expect(setSelected).toHaveBeenCalledWith("fictional-job");
  fireEvent.change(screen.getByLabelText(/Required skills/), {
    target: { value: "Python, FastAPI" },
  });
  fireEvent.click(screen.getByRole("button", { name: /Save requirements/ }));
  await waitFor(() =>
    expect(api.patch).toHaveBeenCalledWith(
      "/jobs/fictional-job",
      expect.objectContaining({
        required_skills: ["Python", "FastAPI"],
        min_experience: 3,
      }),
    ),
  );
});
