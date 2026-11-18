import React, { useState } from "react";
import {
  render,
  screen,
  fireEvent,
  within,
  cleanup,
} from "@testing-library/react";
import { MemoryRouter, Routes, Route, useSearchParams } from "react-router-dom";
import { afterEach, it, expect, vi } from "vitest";
import JobPicker from "./JobPicker";
afterEach(cleanup);

it("groups AI naming variants once and retains both saved descriptions", () => {
  const jobs = [
    {
      id: "ai",
      title: "AI Engineer",
      match_status: "idle",
      required_skills: ["Python", "NLP"],
    },
    {
      id: "ml",
      title: "AI/ML Engineer",
      match_status: "completed",
      required_skills: ["Python", "PyTorch"],
    },
  ];
  function Controlled() {
    const [selected, setSelected] = useState("");
    return <JobPicker {...{ jobs, selected }} onChange={setSelected} />;
  }
  render(
    <MemoryRouter>
      <Controlled />
    </MemoryRouter>,
  );
  fireEvent.focus(screen.getByRole("combobox", { name: "Active job" }));
  const list = screen.getByRole("listbox");
  expect(
    within(list).getAllByRole("option", { name: /^AI\/ML Engineer/ }),
  ).toHaveLength(1);
  expect(
    within(list).queryByRole("option", { name: /^AI Engineer/ }),
  ).not.toBeInTheDocument();
  fireEvent.click(
    within(list).getByRole("option", { name: /^AI\/ML Engineer/ }),
  );
  expect(screen.getByRole("combobox", { name: "Active job" })).toHaveValue(
    "AI/ML Engineer",
  );
  const descriptions = screen.getByRole("combobox", {
    name: "Saved job description",
  });
  expect(descriptions).toHaveValue("ml");
  expect(within(descriptions).getAllByRole("option")).toHaveLength(2);
  fireEvent.change(descriptions, { target: { value: "ai" } });
  expect(
    screen.getByRole("link", { name: /Review requirements/ }),
  ).toHaveAttribute("href", "/jobs/new?edit=ai");
  expect(screen.getByRole("combobox", { name: "Active job" })).toHaveValue(
    "AI/ML Engineer",
  );
});

it("lets an arbitrary typed title open a prefilled new job instead of inventing saved data", () => {
  function NewJob() {
    const [params] = useSearchParams();
    return <h1>Create {params.get("title")}</h1>;
  }
  render(
    <MemoryRouter>
      <Routes>
        <Route
          path="/"
          element={<JobPicker jobs={[]} selected="" onChange={vi.fn()} />}
        />
        <Route path="/jobs/new" element={<NewJob />} />
      </Routes>
    </MemoryRouter>,
  );
  const input = screen.getByRole("combobox", { name: "Active job" });
  fireEvent.focus(input);
  fireEvent.change(input, {
    target: { value: "Robotics Integration Architect" },
  });
  fireEvent.click(
    screen.getByRole("option", {
      name: /^Create Robotics Integration Architect/,
    }),
  );
  expect(
    screen.getByRole("heading", {
      name: "Create Robotics Integration Architect",
    }),
  ).toBeInTheDocument();
});

it("shows any saved job and supports keyboard selection", () => {
  const change = vi.fn();
  render(
    <MemoryRouter>
      <JobPicker
        jobs={[{ id: "custom", title: "Sustainability Reporting Lead" }]}
        selected=""
        onChange={change}
      />
    </MemoryRouter>,
  );
  const input = screen.getByRole("combobox", { name: "Active job" });
  fireEvent.focus(input);
  fireEvent.change(input, { target: { value: "reporting" } });
  expect(
    screen.getByRole("option", { name: /^Sustainability Reporting Lead/ }),
  ).toBeInTheDocument();
  fireEvent.keyDown(input, { key: "Enter" });
  expect(change).toHaveBeenCalledWith("custom");
});
