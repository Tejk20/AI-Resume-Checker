import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import { FileText, Sparkles, Save, ArrowRight } from "lucide-react";
import { api, errorMessage } from "../services/api";
import { Heading, Chips } from "../components/UI";
import {
  suggestedJobTitles,
  canonicalJobTitle,
} from "../components/jobOptions";
export default function CreateJob({ refreshJobs, setSelected, jobs = [] }) {
  const [title, setTitle] = useState(""),
    [text, setText] = useState(""),
    [file, setFile] = useState(null),
    [job, setJob] = useState(null),
    [busy, setBusy] = useState(false),
    [edit, setEdit] = useState({}),
    [error, setError] = useState("");
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const jobId = searchParams.get("edit");
  const requestedTitle = searchParams.get("title") || "";
  useEffect(() => {
    if (!jobId) {
      setJob(null);
      setTitle(requestedTitle);
      setText("");
      setEdit({});
      return;
    }
    let alive = true;
    setBusy(true);
    api
      .get("/jobs/" + jobId)
      .then(({ data }) => {
        if (!alive) return;
        setJob(data);
        setTitle(data.title);
        setText(data.raw_text);
        setSelected(data.id);
        setEdit({
          required_skills: data.required_skills.join(", "),
          preferred_skills: data.preferred_skills.join(", "),
          min_experience: data.min_experience ?? "",
          qualifications: data.qualifications.join("\n"),
          responsibilities: data.responsibilities.join("\n"),
        });
      })
      .catch((err) => {
        if (alive) setError(errorMessage(err));
      })
      .finally(() => {
        if (alive) setBusy(false);
      });
    return () => {
      alive = false;
    };
  }, [jobId, requestedTitle]);
  async function extract(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      let result;
      if (file) {
        const f = new FormData();
        f.append("title", title);
        f.append("file", file);
        result = await api.post("/jobs/upload", f);
      } else result = await api.post("/jobs", { title, raw_text: text });
      setJob(result.data);
      setEdit({
        required_skills: result.data.required_skills.join(", "),
        preferred_skills: result.data.preferred_skills.join(", "),
        min_experience: result.data.min_experience ?? "",
        qualifications: result.data.qualifications.join("\n"),
        responsibilities: result.data.responsibilities.join("\n"),
      });
      setSelected(result.data.id);
      await refreshJobs();
      toast.success("Job created. Review the extracted requirements.");
    } catch (err) {
      setError(errorMessage(err));
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }
  async function save() {
    setBusy(true);
    setError("");
    const split = (key, sep) =>
      edit[key]
        .split(sep)
        .map((x) => x.trim())
        .filter(Boolean);
    try {
      await api.patch("/jobs/" + job.id, {
        required_skills: split("required_skills", ","),
        preferred_skills: split("preferred_skills", ","),
        min_experience:
          edit.min_experience === "" ? null : Number(edit.min_experience),
        qualifications: split("qualifications", "\n"),
        responsibilities: split("responsibilities", "\n"),
      });
      await refreshJobs();
      toast.success("Requirements saved. Ready for resumes.");
      navigate("/upload");
    } catch (err) {
      setError(errorMessage(err));
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Heading
        title="Define what a great match looks like."
        eyebrow="01 / JOB REQUIREMENTS"
      >
        Start with a description. Review the requirements before evaluating
        candidates.
      </Heading>
      <div className="form-grid">
        <section className="card form-card">
          <div className="section-title">
            <span className="step">1</span>
            <div>
              <h2>Job description</h2>
              <p className="muted small">Paste text or upload a PDF or DOCX.</p>
            </div>
          </div>
          <form onSubmit={extract}>
            <label>
              Job title
              <input
                required
                minLength={2}
                maxLength={200}
                disabled={!!job}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Python Backend Developer"
                list="job-title-suggestions"
                aria-label="Job title"
                aria-describedby="job-title-help"
              />
              <datalist id="job-title-suggestions">
                {[
                  ...new Set([
                    ...jobs.map((item) => canonicalJobTitle(item.title)),
                    ...suggestedJobTitles,
                  ]),
                ]
                  .sort((a, b) => a.localeCompare(b))
                  .map((item) => (
                    <option key={item} value={item} />
                  ))}
              </datalist>
              <small id="job-title-help" className="muted">
                Choose a suggestion or enter any job title.
              </small>
            </label>
            <label>
              Description
              <textarea
                required={!file}
                minLength={30}
                rows={12}
                maxLength={100000}
                disabled={!!job || !!file}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Describe the role, required skills, experience, and responsibilities…"
              />
            </label>
            <label className="file-field">
              <FileText size={20} />
              <span>
                {file ? file.name : "Or choose a job description file"}
              </span>
              <input
                type="file"
                accept=".pdf,.docx"
                disabled={!!job}
                onChange={(e) => setFile(e.target.files[0] || null)}
              />
            </label>
            {file && !job && (
              <button
                type="button"
                className="text-link"
                onClick={() => setFile(null)}
              >
                Use pasted text instead
              </button>
            )}
            <div className="form-bottom">
              <span className="muted small">
                Extraction creates a saved job.
              </span>
              <button className="primary" disabled={busy || !!job}>
                <Sparkles size={17} />
                {busy ? "Extracting…" : "Extract requirements"}
              </button>
            </div>
          </form>
        </section>
        <section className="card form-card">
          <div className="section-title">
            <span className="step">2</span>
            <div>
              <h2>Review extracted requirements</h2>
              <p className="muted small">
                Edit the evidence your candidates will be scored against.
              </p>
            </div>
          </div>
          {job ? (
            <>
              <div className="notice">{job.is_demo ? 'Sample job: read-only requirements. Create a new job to customize your search.' : job.extraction_warnings.join(" ")}</div>
              {[
                [
                  "required_skills",
                  "Required skills",
                  "Separate skills with commas",
                ],
                [
                  "preferred_skills",
                  "Preferred skills",
                  "Separate skills with commas",
                ],
                [
                  "min_experience",
                  "Minimum experience (years)",
                  "Leave blank if not required",
                ],
                [
                  "qualifications",
                  "Qualifications & certifications",
                  "One requirement per line",
                ],
                [
                  "responsibilities",
                  "Responsibilities",
                  "One responsibility per line",
                ],
              ].map(([key, label, help]) => (
                <label key={key}>
                  {label}
                  {key === "min_experience" ? (
                    <input
                      type="number"
                      min="0"
                      max="60"
                      step="0.5"
                      disabled={job.is_demo}
                      value={edit[key]}
                      onChange={(e) =>
                        setEdit({ ...edit, [key]: e.target.value })
                      }
                    />
                  ) : (
                    <textarea
                      rows={key.includes("skills") ? 2 : 3}
                      disabled={job.is_demo}
                      value={edit[key]}
                      onChange={(e) =>
                        setEdit({ ...edit, [key]: e.target.value })
                      }
                    />
                  )}
                  <small className="muted">{help}</small>
                </label>
              ))}
              <button className="primary full" onClick={save} disabled={busy || job.is_demo}>
                <Save size={17} />
                {busy ? "Saving…" : "Save requirements & continue"}
                <ArrowRight size={17} />
              </button>
            </>
          ) : (
            <div className="state requirements-empty">
              <Sparkles />
              <h3>Let’s find the essentials</h3>
              <p>
                Extract a job description to review required skills, preferred
                skills, qualifications, and experience.
              </p>
              <div className="ghost-chips">
                <span>Required skills</span>
                <span>Experience</span>
                <span>Qualifications</span>
              </div>
            </div>
          )}
        </section>
      </div>
      {error && (
        <div role="alert" className="notice danger">
          {error}
        </div>
      )}
    </>
  );
}
