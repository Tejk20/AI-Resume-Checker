import { useEffect, useId, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronDown, Plus, Search } from "lucide-react";
import { canonicalJobTitle, groupJobs, suggestedJobTitles } from "./jobOptions";

export default function JobPicker({ jobs, selected, onChange }) {
  const id = useId();
  const input = useRef(null);
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const groups = groupJobs(jobs);
  const selectedGroup = groups.find((group) =>
    group.jobs.some((job) => job.id === selected),
  );
  const normalized = query.trim().toLocaleLowerCase();
  const aliasQuery = canonicalJobTitle(query).toLocaleLowerCase();
  const saved = groups.filter(
    (group) =>
      !normalized ||
      group.title.toLocaleLowerCase().includes(normalized) ||
      group.key === aliasQuery ||
      group.jobs.some((job) =>
        job.title.toLocaleLowerCase().includes(normalized),
      ),
  );
  const suggestions = suggestedJobTitles.filter(
    (title) =>
      !groups.some((group) => group.key === title.toLocaleLowerCase()) &&
      (!normalized || title.toLocaleLowerCase().includes(normalized)),
  );
  const customTitle = canonicalJobTitle(query);
  if (
    customTitle.length >= 2 &&
    !groups.some((group) => group.key === aliasQuery) &&
    !suggestions.some((title) => title.toLocaleLowerCase() === aliasQuery)
  )
    suggestions.unshift(customTitle);
  const options = [
    ...saved.map((group) => ({ type: "saved", title: group.title, group })),
    ...suggestions.map((title) => ({ type: "create", title })),
  ];
  useEffect(() => {
    if (open)
      document
        .getElementById(id + "-option-" + active)
        ?.scrollIntoView?.({ block: "nearest" });
  }, [open, active, id, query]);

  function choose(option) {
    if (!option) return;
    setOpen(false);
    if (option.type === "create") {
      navigate("/jobs/new?title=" + encodeURIComponent(option.title));
    } else {
      const job =
        option.group.jobs.find((item) => item.id === selected) ||
        option.group.jobs[0];
      onChange(job.id);
    }
    setQuery("");
  }

  function keyDown(event) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      setActive((index) =>
        options.length
          ? (index + (event.key === "ArrowDown" ? 1 : -1) + options.length) %
            options.length
          : 0,
      );
    } else if (event.key === "Enter" && open) {
      event.preventDefault();
      choose(options[active] || options[0]);
    } else if (event.key === "Escape") {
      setOpen(false);
      setQuery("");
    }
  }

  return (
    <div className="job-context job-picker-context">
      <div className="job-picker-fields">
        <div
          className="job-picker"
          onBlur={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget)) {
              setOpen(false);
              setQuery("");
            }
          }}
        >
          <label htmlFor={id}>Active job</label>
          <div className="job-picker-control">
            <Search size={16} />
            <input
              ref={input}
              id={id}
              role="combobox"
              aria-label="Active job"
              autoComplete="off"
              aria-expanded={open}
              aria-autocomplete="list"
              aria-controls={id + "-options"}
              aria-activedescendant={
                open && options[active] ? id + "-option-" + active : undefined
              }
              placeholder="Search or enter any job title"
              value={open ? query : selectedGroup?.title || ""}
              maxLength={200}
              onFocus={() => {
                setOpen(true);
                setQuery("");
                setActive(0);
              }}
              onChange={(event) => {
                setQuery(event.target.value);
                setOpen(true);
                setActive(0);
              }}
              onKeyDown={keyDown}
            />
            <button
              type="button"
              aria-label="Show job options"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => {
                if (open) {
                  setOpen(false);
                  setQuery("");
                } else {
                  setOpen(true);
                  setQuery("");
                  setActive(0);
                  input.current.focus();
                }
              }}
            >
              <ChevronDown size={16} />
            </button>
          </div>
          {open && (
            <div className="job-picker-menu">
              <ul id={id + "-options"} role="listbox" aria-label="Job titles">
                {options.map((option, index) => (
                  <li
                    key={option.type + option.title}
                    id={id + "-option-" + index}
                    role="option"
                    aria-selected={
                      option.type === "saved" &&
                      option.group.key === selectedGroup?.key
                    }
                    className={
                      (index === active ? "highlighted " : "") +
                      (option.type === "create" ? "create-option" : "")
                    }
                    onMouseDown={(event) => event.preventDefault()}
                    onMouseEnter={() => setActive(index)}
                    onClick={() => choose(option)}
                  >
                    {option.type === "create" && <Plus size={14} />}
                    <span>
                      {option.type === "create" ? "Create " : ""}
                      {option.title}
                      <small>
                        {option.type === "saved"
                          ? `${option.group.jobs.length} saved description${option.group.jobs.length === 1 ? "" : "s"}${option.group.jobs.every(j => j.is_demo) ? ' · Sample' : ''}`
                          : "Add a job description to activate this role"}
                      </small>
                    </span>
                  </li>
                ))}
              </ul>
              {!options.length && (
                <p className="muted small">
                  Enter at least two characters to create a job.
                </p>
              )}
              <p className="job-picker-hint">
                Any job title is supported. New roles become active after you
                save their job description.
              </p>
            </div>
          )}
        </div>
        {selectedGroup?.jobs.length > 1 && (
          <label className="job-description-picker">
            Saved description
            <select
              aria-label="Saved job description"
              value={selected}
              onChange={(event) => onChange(event.target.value)}
            >
              {selectedGroup.jobs.map((job, index) => (
                <option key={job.id} value={job.id}>
                  Description {index + 1} ·{" "}
                  {job.required_skills?.slice(0, 3).join(", ") ||
                    "Review requirements"}{" "}
                  ·{" "}
                  {job.match_status === "completed"
                    ? "Evaluated"
                    : "Not evaluated"}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      {selected && (
        <Link className="text-link" to={`/jobs/new?edit=${selected}`}>
          Review requirements →
        </Link>
      )}
    </div>
  );
}
