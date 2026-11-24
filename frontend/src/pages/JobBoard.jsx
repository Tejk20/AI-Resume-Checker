import { useEffect, useState } from "react";
import { api, errorMessage } from "../services/api";

const pageSize = 20;

export default function JobBoard() {
  const [offset, setOffset] = useState(0);
  const [jobs, setJobs] = useState([]);
  const [state, setState] = useState({ loading: true, error: "" });

  useEffect(() => {
    const controller = new AbortController();
    setState({ loading: true, error: "" });
    api.get("/public-jobs", {
      params: { offset, limit: pageSize + 1 },
      signal: controller.signal,
    }).then(({ data }) => {
      if (controller.signal.aborted) return;
      setJobs(data);
      setState({ loading: false, error: "" });
    }).catch(error => {
      if (!controller.signal.aborted) setState({ loading: false, error: errorMessage(error) });
    });
    return () => controller.abort();
  }, [offset]);

  return <section className="profile-settings">
    <h1>Job board</h1>
    {state.loading && <p role="status">Loading openings…</p>}
    {state.error && <p role="alert">{state.error}</p>}
    {!state.loading && !state.error && <>
      {jobs.length === 0 && <p className="muted">No published openings on this page.</p>}
      {jobs.slice(0, pageSize).map(job => <article className="card profile-settings-card" key={job.id}>
        <details>
          <summary>{job.title}</summary>
          <p className="job-board-description">{job.raw_text}</p>
        </details>
      </article>)}
      <nav className="job-board-pagination" aria-label="Job board pages">
        {offset > 0 && <button className="text-link" onClick={() => setOffset(offset - pageSize)}>Previous</button>}
        {jobs.length > pageSize && <button className="text-link" onClick={() => setOffset(offset + pageSize)}>Next</button>}
      </nav>
    </>}
  </section>;
}
