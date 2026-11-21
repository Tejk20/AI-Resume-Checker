import { AlertCircle, ArrowRight, LoaderCircle, Inbox } from "lucide-react";
import { Link } from "react-router-dom";
import JobPicker from "./JobPicker";
export function Heading({ eyebrow, title, children, action }) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow || "HIRELENS AI / TALENT INTELLIGENCE"}</p>
        <h1>{title}</h1>
        {children && <p className="muted">{children}</p>}
      </div>
      {action}
    </div>
  );
}
export function State({ loading, error, retry, empty, children }) {
  if (loading)
    return (
      <div className="state">
        <LoaderCircle className="spin" />
        Loading your workspace…
      </div>
    );
  if (error)
    return (
      <div role="alert" className="state error">
        <AlertCircle />
        {error}
        <button className="secondary" onClick={retry}>
          Retry
        </button>
      </div>
    );
  if (empty)
    return (
      <div className="state">
        <Inbox />
        <h3>Nothing here yet</h3>
        {children}
      </div>
    );
  return children;
}
export function Chips({ items = [], tone = "" }) {
  return (
    <div className="chips">
      {items.length ? (
        items.map((s) => (
          <span key={s} className={"chip " + tone}>
            {s}
          </span>
        ))
      ) : (
        <span className="muted small">None identified</span>
      )}
    </div>
  );
}
export function Score({ value }) {
  return (
    <span
      className={
        "score " + (value >= 80 ? "high" : value >= 60 ? "medium" : "low")
      }
    >
      {Number(value).toFixed(2)}
      <small> / 100</small>
    </span>
  );
}
export function JobSelect({ jobs, selected, onChange }) {
  return <JobPicker {...{ jobs, selected, onChange }} />;
}
export function NextLink({ to, children }) {
  return (
    <Link className="primary" to={to}>
      {children}
      <ArrowRight size={16} />
    </Link>
  );
}
export function Status({ value }) {
  return (
    <span className={"status " + (value.includes("fail") ? "warn" : "")}>
      {value.replaceAll("_", " ")}
    </span>
  );
}
