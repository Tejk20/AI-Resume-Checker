import React from "react";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { afterEach, it, expect, vi } from "vitest";
import Analysis from "./Analysis";
import { api } from "../services/api";
vi.mock("../services/api", () => ({
  api: { get: vi.fn() },
  errorMessage: () => "Request failed",
}));
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
  BarChart: ({ children }) => <div>{children}</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  CartesianGrid: () => null,
}));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
it("shows model provenance, the recorded formula, missing mandatory skills and separate uncertainty", async () => {
  const explanation = {
    summary: "Estimated job-fit score 80/100.",
    components: { semantic: 80, skill: 80, experience: 80, education: 80 },
    weights: { semantic: 0.25, skill: 0.4, experience: 0.25, education: 0.1 },
    contributions: { semantic: 20, skill: 32, experience: 20, education: 8 },
    matched_required: ["Python"],
    matched_preferred: [],
    missing_required: ["Docker"],
    missing_preferred: [],
    related_skills: [],
    relevant_years: 2,
    required_years: 3,
    relevant_roles: [],
    qualification_note: "Review needed",
    qualification_requirements: ["Bachelor degree"],
    qualification_evidence: [],
    experience_method: "Dated evidence",
    semantic_evidence: [
      {
        requirement: "Build APIs",
        requirement_section: "responsibilities",
        evidence: "Developed services",
        evidence_section: "experience",
        similarity: 80,
      },
    ],
    uncertain_requirements: [
      { requirement: "Bachelor degree", status: "unverified" },
    ],
    warnings: ["Review qualifications"],
    score_interpretation: "Estimated job-fit score; not a hiring probability.",
  };
  const match = {
    overall_score: 80,
    algorithm_version: "2.0.0-section-aware",
    embedding_model: "sentence-transformers/all-mpnet-base-v2",
    scoring_config: { default_weights: explanation.weights },
    explanation,
  };
  const candidate = {
    name: "Alex Rowan",
    email: null,
    phone: null,
    original_filename: "synthetic.pdf",
    projects: [],
  };
  const history = [
    {
      id: "old",
      created_at: "2026-11-17T12:00:00Z",
      embedding_model: "sentence-transformers/all-MiniLM-L6-v2",
      payload: {
        overall_score: 75,
        algorithm_version: "1.1.0-minilm-evidence",
      },
    },
  ];
  api.get.mockImplementation(async (path) => ({
    data: path.endsWith("/history")
      ? history
      : path.includes("/matches/")
        ? match
        : candidate,
  }));
  render(
    <MemoryRouter initialEntries={["/jobs/job/candidates/candidate"]}>
      <Routes>
        <Route
          path="/jobs/:jobId/candidates/:candidateId"
          element={<Analysis />}
        />
      </Routes>
    </MemoryRouter>,
  );
  expect(
    await screen.findByText("Model: sentence-transformers/all-mpnet-base-v2"),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      "25% Semantic + 40% Skills + 25% Experience + 10% Education",
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("Docker")).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Requirements needing review" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Bachelor degree: unverified")).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Previous evaluations" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/sentence-transformers\/all-MiniLM-L6-v2/),
  ).toBeInTheDocument();
});
