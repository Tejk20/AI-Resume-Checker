import { useEffect, useState } from "react";
import { NavLink, Routes, Route, useLocation, Link } from "react-router-dom";
import {
  LayoutDashboard,
  FilePlus2,
  Upload,
  Users,
  BookOpen,
  ArrowUpRight,
  PanelLeftClose,
  PanelLeftOpen,
  ScanLine,
} from "lucide-react";
import { api, errorMessage } from "./services/api";
import Dashboard from "./pages/Dashboard";
import CreateJob from "./pages/CreateJob";
import UploadResumes from "./pages/UploadResumes";
import Rankings from "./pages/Rankings";
import Analysis from "./pages/Analysis";
import Methodology from "./pages/Methodology";
import { canonicalJobTitle } from "./components/jobOptions";
const links = [
  ["/", "Overview", LayoutDashboard],
  ["/jobs/new", "Create job", FilePlus2],
  ["/upload", "Upload resumes", Upload],
  ["/rankings", "Candidate rankings", Users],
  ["/methodology", "About the application", BookOpen],
];
export default function App() {
  const [jobs, setJobs] = useState([]),
    [selected, setSelected] = useState(localStorage.getItem("avom-job") || ""),
    [open, setOpen] = useState(false),
    [jobsError, setJobsError] = useState("");
  const location = useLocation();
  const refreshJobs = async () => {
    let items = [],
      offset = 0,
      total = 1;
    while (offset < total) {
      const { data } = await api.get("/jobs", {
        params: { offset, limit: 100 },
      });
      items.push(...data.items);
      total = data.total;
      offset += 100;
    }
    setJobs(items);
    setJobsError("");
    return items;
  };
  useEffect(() => {
    const refresh = () =>
      refreshJobs().catch((e) => setJobsError(errorMessage(e)));
    refresh();
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, [location.pathname]);
  useEffect(() => {
    localStorage.setItem("avom-job", selected);
  }, [selected]);
  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);
  const context = { jobs, selected, setSelected, refreshJobs };
  return (
    <div className="app">
      <aside className={open ? "sidebar open" : "sidebar"}>
        <Link to="/" className="brand">
          <span className="brand-icon">
            <ScanLine />
          </span>
          <span>
            avom<span className="brand-dot">.</span>
            <small>RESUME INTELLIGENCE</small>
          </span>
        </Link>
        <p className="nav-label">WORKSPACE</p>
        <nav>
          {links.map(([to, label, Icon]) => (
            <NavLink end={to === "/"} to={to} key={to}>
              <Icon size={19} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="live-dot" /> Local AI engine
          <p>
            Open-source. Evidence-led.
            <br />
            Built for human decisions.
          </p>
          <Link to="/methodology">
            Explore the application <ArrowUpRight size={14} />
          </Link>
        </div>
        <div className="profile">
          <span>AC</span>
          <div>
            Avom Consultants<small>Recruiter workspace</small>
          </div>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <button
            className="menu"
            aria-label="Toggle navigation"
            onClick={() => setOpen(!open)}
          >
            {open ? <PanelLeftClose /> : <PanelLeftOpen />}
          </button>
          <span>
            Workspace <span className="slash">/</span>{" "}
            <strong>
              {links.find((x) => x[0] === location.pathname)?.[1] ||
                "Candidate analysis"}
            </strong>
          </span>
          <span className="top-tag">
            {canonicalJobTitle(
              jobs.find((j) => j.id === selected)?.title || "",
            ) || "INTERNAL DEMO"}{" "}
            <span className="live-dot" />
          </span>
        </header>
        <main>
          {jobsError && (
            <div role="alert" className="notice danger">
              {jobsError}{" "}
              <button
                className="text-link"
                onClick={() =>
                  refreshJobs().catch((e) => setJobsError(errorMessage(e)))
                }
              >
                Retry loading jobs
              </button>
            </div>
          )}
          <Routes>
            <Route path="/" element={<Dashboard {...context} />} />
            <Route path="/jobs/new" element={<CreateJob {...context} />} />
            <Route path="/upload" element={<UploadResumes {...context} />} />
            <Route path="/rankings" element={<Rankings {...context} />} />
            <Route
              path="/jobs/:jobId/candidates/:candidateId"
              element={<Analysis />}
            />
            <Route path="/methodology" element={<Methodology />} />
            <Route
              path="*"
              element={
                <div className="state">
                  Page not found. <Link to="/">Return to overview</Link>
                </div>
              }
            />
          </Routes>
        </main>
        <footer>
          AVOM CONSULTANTS{" "}
          <span>
            Compatibility is a starting point. People make the decisions.
          </span>
        </footer>
      </div>
    </div>
  );
}
