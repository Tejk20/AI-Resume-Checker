import { useEffect, useState, useRef } from "react";
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
  Settings,
} from "lucide-react";
import { api, errorMessage } from "./services/api";
import Dashboard from "./pages/Dashboard";
import CreateJob from "./pages/CreateJob";
import UploadResumes from "./pages/UploadResumes";
import Rankings from "./pages/Rankings";
import Analysis from "./pages/Analysis";
import Methodology from "./pages/Methodology";
import { canonicalJobTitle } from "./components/jobOptions";
import { AuthProvider, useAuth, RequireAccount } from './components/AuthContext';
import Auth from './pages/Auth';
import PasswordRecovery from './pages/PasswordRecovery';
import Brand from './components/Brand';
import Profile from './pages/Profile';
const links = [
  ["/", "Overview", LayoutDashboard],
  ["/jobs/new", "Create job", FilePlus2],
  ["/upload", "Upload resumes", Upload],
  ["/rankings", "Candidate rankings", Users],
  ["/methodology", "About the application", BookOpen],
  ["/profile", "Profile settings", Settings],
];
function Workspace() {
  const { user, ready, required, error: authError, refresh: refreshAuth, logout } = useAuth();
  const jobRequest = useRef(0);
  const [jobs, setJobs] = useState([]),
    [selected, setSelected] = useState(localStorage.getItem("avom-job") || ""),
    [open, setOpen] = useState(false),
    [jobsError, setJobsError] = useState("");
  const location = useLocation();
  const refreshJobs = async () => {
    const request = ++jobRequest.current;
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
    if (request === jobRequest.current) {
      setJobs(items);
      setSelected(previous => items.some(item => item.id === previous) ? previous : items[0]?.id || '');
      setJobsError("");
    }
    return items;
  };
  useEffect(() => {
    if (!ready) return;
    const refresh = () =>
      refreshJobs().catch((e) => setJobsError(errorMessage(e)));
    refresh();
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, [location.pathname, ready, user?.id]);
  useEffect(() => {
    setJobs([]); setSelected('');
  }, [user?.id]);
  useEffect(() => {
    localStorage.setItem("avom-job", selected);
  }, [selected]);
  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);
  const context = { jobs, selected, setSelected, refreshJobs };
  if (location.pathname === '/signup' || location.pathname === '/login')
    return <Auth key={location.pathname} signup={location.pathname === '/signup'} />;
  if (location.pathname === '/forgot-password' || location.pathname === '/reset-password')
    return <PasswordRecovery key={location.pathname} reset={location.pathname === '/reset-password'} />;
  return (
    <div className="app">
      <aside className={open ? "sidebar open" : "sidebar"}>
        <Brand />
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
          <span>{user ? user.name.split(' ').map(x => x[0]).slice(0,2).join('').toUpperCase() : 'AC'}</span>
          <div>
            {user?.name || 'Sample workspace'}<small>{user ? 'Recruiter account' : 'Explore fictional candidates'}</small>
          </div>
        </div>
        {user ? <button className="text-link account-signout" onClick={() => logout().catch(e => setJobsError(errorMessage(e)))}>Sign out</button> : <div className="sidebar-auth"><Link className="primary" to="/signup">Create account</Link><Link className="text-link" to="/login">Sign in</Link></div>}
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
          {authError && <div role="alert" className="notice danger">{authError} <button className="text-link" onClick={refreshAuth}>Retry account connection</button></div>}
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
          <Routes key={user?.id || 'visitor'}>
            <Route path="/profile" element={<RequireAccount><Profile /></RequireAccount>} />
            <Route path="/" element={<Dashboard {...context} />} />
            <Route path="/jobs/new" element={<RequireAccount><CreateJob {...context} /></RequireAccount>} />
            <Route path="/upload" element={<RequireAccount><UploadResumes {...context} /></RequireAccount>} />
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
          HIRELENS AI{" "}
          <span>
            Compatibility is a starting point. People make the decisions.
          </span>
        </footer>
      </div>
    </div>
  );
}

export default function App() {
  return <AuthProvider><Workspace /></AuthProvider>;
}
