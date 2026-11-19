import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import {
  UploadCloud,
  FileText,
  X,
  CheckCircle2,
  Play,
  LoaderCircle,
} from "lucide-react";
import toast from "react-hot-toast";
import { api, errorMessage } from "../services/api";
import { Heading, JobSelect, Status } from "../components/UI";
export default function UploadResumes({
  jobs,
  selected,
  setSelected,
  refreshJobs,
}) {
  const [files, setFiles] = useState([]),
    [batch, setBatch] = useState(null),
    [busy, setBusy] = useState(false),
    [progress, setProgress] = useState(0),
    [drag, setDrag] = useState(false),
    [error, setError] = useState(""),
    [matching, setMatching] = useState(false),
    [matchStatus, setMatchStatus] = useState(""),
    [count, setCount] = useState(0);
  const input = useRef();
  const sampleJob = jobs.find(job => job.id === selected)?.is_demo;
  useEffect(() => {
    setFiles([]);
    setBatch(null);
    setError("");
    setMatching(false);
    setMatchStatus("");
    setCount(0);
    if (selected) {
      api
        .get(`/jobs/${selected}/candidates`)
        .then((r) => setCount(r.data.total))
        .catch((e) => setError(errorMessage(e)));
      api
        .get("/jobs/" + selected)
        .then((r) => {
          setMatching(r.data.match_status === "processing");
          setMatchStatus(r.data.match_status);
        })
        .catch((e) => setError(errorMessage(e)));
    } else setCount(0);
  }, [selected]);
  useEffect(() => {
    if (!batch || !["pending", "processing"].includes(batch.status)) return;
    let alive = true;
    const timer = setInterval(async () => {
      try {
        const { data } = await api.get("/batches/" + batch.id);
        if (alive) {
          setBatch(data);
          if (!["pending", "processing"].includes(data.status)) {
            const r = await api.get(`/jobs/${selected}/candidates`);
            setCount(r.data.total);
            toast(
              data.failed_files
                ? "Batch finished with some errors."
                : "Resumes ready for matching.",
            );
          }
        }
      } catch (e) {
        if (alive) setError(errorMessage(e));
      }
    }, 1200);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [batch?.id, batch?.status, selected]);
  useEffect(() => {
    if (!matching || !selected) return;
    let alive = true;
    const timer = setInterval(async () => {
      try {
        const { data } = await api.get("/jobs/" + selected);
        if (alive) {
          setMatchStatus(data.match_status);
          if (data.match_status !== "processing") {
            setMatching(false);
            refreshJobs().catch((e) => setError(errorMessage(e)));
            if (data.match_status === "failed") setError(data.match_error);
            else toast.success("Evaluation complete. Open candidate rankings.");
          }
        }
      } catch (e) {
        if (alive) setError(errorMessage(e));
      }
    }, 1800);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [matching, selected]);
  const processing =
    busy || matching || ["pending", "processing"].includes(batch?.status);
  function add(incoming) {
    const all = [...files, ...Array.from(incoming)];
    if (all.length > 50) {
      toast.error("Choose up to 50 files per batch.");
      return;
    }
    const valid = all.filter(
      (f) => /\.(pdf|docx)$/i.test(f.name) && f.size <= 10 * 1024 * 1024,
    );
    if (valid.length < all.length)
      toast.error("Only PDF/DOCX files up to 10 MB are accepted.");
    setFiles(valid);
  }
  async function upload() {
    setBusy(true);
    setError("");
    setProgress(0);
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    try {
      const { data } = await api.post(`/jobs/${selected}/resumes`, form, {
        onUploadProgress: (e) =>
          setProgress(Math.round((e.loaded / (e.total || 1)) * 100)),
      });
      setBatch(data);
      setMatchStatus("idle");
      setFiles([]);
    } catch (e) {
      setError(errorMessage(e));
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  async function run() {
    setError("");
    setMatching(true);
    try {
      await api.post(`/jobs/${selected}/match`);
      setMatchStatus("processing");
    } catch (e) {
      setMatching(false);
      setError(errorMessage(e));
      toast.error(errorMessage(e));
    }
  }
  return (
    <>
      <Heading
        title="Bring your candidate pool into focus."
        eyebrow="02 / RESUME PROCESSING"
      >
        Upload up to 50 resumes. Every document is parsed individually, so one
        failure won’t stop the batch.
      </Heading>
      <JobSelect {...{ jobs, selected, onChange: setSelected }} />
      {sampleJob && <div className="notice">This sample job is read-only. <Link className="text-link" to="/jobs/new">Create your own job</Link> to upload resumes and run matching.</div>}
      {!jobs.length && (
        <div className="notice">
          Create a job first.{" "}
          <Link className="text-link" to="/jobs/new">
            Add a job description →
          </Link>
        </div>
      )}
      <div className="upload-grid">
        <section className="card form-card">
          <h2>Candidate documents</h2>
          <p className="muted small">PDF & DOCX · Maximum 10 MB per file</p>
          <div
            role="button"
            tabIndex={0}
            aria-label="Select resumes"
            className={"dropzone " + (drag ? "drag" : "")}
            onClick={() => !processing && selected && input.current.click()}
            onKeyDown={(e) => {
              if (["Enter", " "].includes(e.key) && !processing && selected)
                input.current.click();
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              if (!processing && selected) add(e.dataTransfer.files);
            }}
          >
            <span className="upload-symbol">
              <UploadCloud size={30} />
            </span>
            <h3>Drop resumes here</h3>
            <p>
              or <span className="text-link">browse your files</span>
            </p>
            <small>Private local storage · Multiple files supported</small>
            <input
              ref={input}
              hidden
              multiple
              type="file"
              accept=".pdf,.docx"
              onChange={(e) => {
                add(e.target.files);
                e.target.value = "";
              }}
            />
          </div>
          {files.length > 0 && (
            <>
              <div className="list-head">
                <strong>{files.length} files selected</strong>
                <button
                  disabled={processing}
                  className="text-link"
                  onClick={() => setFiles([])}
                >
                  Clear all
                </button>
              </div>
              <div className="selected-files">
                {files.map((f, i) => (
                  <div className="selected-file" key={f.name + i}>
                    <FileText size={18} />
                    <span>
                      {f.name}
                      <small>{(f.size / 1024).toFixed(1)} KB</small>
                    </span>
                    <button
                      disabled={processing}
                      aria-label={"Remove " + f.name}
                      onClick={() => setFiles(files.filter((_, n) => n !== i))}
                    >
                      <X size={16} />
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
          <button
            className="primary full"
            disabled={sampleJob || !selected || !files.length || processing}
            onClick={upload}
          >
            <UploadCloud size={17} />
            {busy ? `Uploading ${progress}%` : "Upload & process resumes"}
          </button>
          {busy && <progress value={progress} max="100" />}
        </section>
        <div>
          <section className="card form-card">
            <h2>Processing status</h2>
            {batch ? (
              <>
                <div className="batch-status">
                  <Status value={batch.status} />
                  <strong>
                    {batch.processed_files + batch.failed_files} /{" "}
                    {batch.total_files}
                  </strong>
                </div>
                <progress
                  value={batch.processed_files + batch.failed_files}
                  max={batch.total_files}
                />
                <div className="batch-counts">
                  <div>
                    <strong>{batch.processed_files}</strong>
                    <span>Successful</span>
                  </div>
                  <div>
                    <strong>{batch.failed_files}</strong>
                    <span>Failed</span>
                  </div>
                </div>
                {batch.errors.map((e, i) => (
                  <div className="notice danger" key={i}>
                    <strong>{e.filename}</strong>
                    <p>{e.error}</p>
                  </div>
                ))}
              </>
            ) : (
              <div className="state compact">
                <CheckCircle2 />
                <p>Upload a batch to see live processing progress.</p>
              </div>
            )}
          </section>
          <section className="card form-card match-card">
            <span className="eyebrow">READY FOR THE NEXT STEP?</span>
            <h2>Find the strongest alignment.</h2>
            <p className="muted">
              {count} parsed candidates in this job. Matching uses local
              sentence embeddings, skill coverage, and evidence.
            </p>
            <button
              className="primary full"
              disabled={sampleJob || !selected || !count || processing}
              onClick={run}
            >
              {matching ? (
                <LoaderCircle className="spin" size={17} />
              ) : (
                <Play size={17} />
              )}{" "}
              {matching ? "Evaluating candidates…" : "Run matching"}
            </button>
            {matching && (
              <p className="small muted">
                The first run may download the open-source model. The API stays
                responsive.
              </p>
            )}
            {matchStatus === "completed" && (
              <Link className="text-link" to="/rankings">
                View candidate rankings →
              </Link>
            )}
          </section>
        </div>
      </div>
      {error && (
        <div className="notice danger" role="alert">
          {error}
          <button
            className="text-link"
            onClick={() => {
              setError("");
              refreshJobs().catch((e) => setError(errorMessage(e)));
            }}
          >
            Refresh jobs
          </button>
        </div>
      )}
    </>
  );
}
