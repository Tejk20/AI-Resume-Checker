import { Link } from "react-router-dom";
import { useEffect } from 'react';
import {
  BriefcaseBusiness,
  Files,
  Users,
  ChartNoAxesCombined,
  ArrowUpRight,
  Plus,
  ArrowRight,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { api } from "../services/api";
import { useLoad } from "../hooks/useLoad";
import { Heading, State, Status } from "../components/UI";
export default function Dashboard({ setSelected }) {
  const { data, error, loading, reload } = useLoad(async () => {
    const [stats, jobs] = await Promise.all([
      api.get("/dashboard"),
      api.get("/jobs", { params: { limit: 5 } }),
    ]);
    return { stats: stats.data, jobs: jobs.data.items };
  });
  const stats = data?.stats;
  useEffect(() => {
    if (!stats?.demo_loading) return;
    const timer = setTimeout(reload, 4000);
    return () => clearTimeout(timer);
  }, [stats?.demo_loading, data, reload]);
  return (
    <>
      <Heading
        title="A clearer view of your next hire."
        eyebrow="YOUR RECRUITMENT OVERVIEW"
        action={
          <Link className="primary" to="/jobs/new">
            <Plus size={17} />
            Create a job
          </Link>
        }
      >
        Turn resumes into evidence. Find the experience that fits.
      </Heading>
      {stats?.demo_jobs > 0 && <div className="demo-banner"><span className="pill">SAMPLE WORKSPACE</span><p>Explore fictional candidates across three hiring roles. Sample jobs are read-only; your own jobs stay in your account.</p><Link to="/rankings" className="text-link">Explore candidates <ArrowRight size={16} /></Link></div>}
      {stats?.demo_loading && <div className="notice">Preparing your sample candidates and matching results. This page will refresh automatically.</div>}
      <State {...{ loading, error }} retry={reload}>
        {data && (
          <>
            <div className="stats-grid">
              {[
                [
                  BriefcaseBusiness,
                  "Active job descriptions",
                  stats.total_jobs,
                  "Saved in your workspace",
                ],
                [
                  Files,
                  "Resumes processed",
                  stats.total_resumes,
                  "Successfully extracted",
                ],
                [
                  Users,
                  "Candidate evaluations",
                  stats.total_evaluated,
                  "Across all saved jobs",
                ],
                [
                  ChartNoAxesCombined,
                  "Average compatibility",
                  stats.average_score === null
                    ? "—"
                    : stats.average_score.toFixed(1) + "%",
                  "Based on evaluated candidates",
                ],
              ].map(([Icon, label, value, caption]) => (
                <div className="stat" key={label}>
                  <div className="stat-top">
                    {label}
                    <Icon size={19} />
                  </div>
                  <strong>{value}</strong>
                  <p>{caption}</p>
                </div>
              ))}
            </div>
            <div className="dashboard-grid">
              <section className="card">
                <div className="card-head">
                  <div>
                    <h2>Recent jobs</h2>
                    <p className="muted small">Your latest hiring priorities</p>
                  </div>
                  <Link className="text-link" to="/jobs/new">
                    New job <Plus size={14} />
                  </Link>
                </div>
                {data.jobs.length ? (
                  <div className="job-list">
                    {data.jobs.map((j) => (
                      <Link
                        key={j.id}
                        to="/rankings"
                        onClick={() => setSelected(j.id)}
                        className="job-row"
                      >
                        <span className="job-icon">
                          <BriefcaseBusiness size={19} />
                        </span>
                        <div>
                          <strong>{j.title}</strong>
                          <p>
                            {j.required_skills.slice(0, 3).join(" · ") ||
                              "Review extracted requirements"}
                          </p>
                        </div>
                        <div className="job-row-end">
                          <Status value={j.match_status} />
                          <ArrowUpRight size={18} />
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className="state compact">
                    <BriefcaseBusiness />
                    <h3>Your next search starts here</h3>
                    <p>
                      Create a job description to begin comparing candidates.
                    </p>
                    <Link to="/jobs/new" className="text-link">
                      Create your first job <ArrowRight size={15} />
                    </Link>
                  </div>
                )}
              </section>
              <section className="card">
                <div className="card-head">
                  <div>
                    <h2>Compatibility distribution</h2>
                    <p className="muted small">
                      Evaluations grouped by match score
                    </p>
                  </div>
                  <span className="pill">All jobs</span>
                </div>
                {stats.total_evaluated ? (
                  <div className="chart">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={stats.distribution}
                        margin={{ top: 15, right: 15, left: -20, bottom: 0 }}
                      >
                        <CartesianGrid vertical={false} stroke="#eef1ef" />
                        <XAxis
                          dataKey="name"
                          axisLine={false}
                          tickLine={false}
                          fontSize={12}
                        />
                        <YAxis
                          allowDecimals={false}
                          axisLine={false}
                          tickLine={false}
                          fontSize={12}
                        />
                        <Tooltip cursor={{ fill: "#f0f6f3" }} />
                        <Bar
                          dataKey="count"
                          fill="#347968"
                          radius={[6, 6, 0, 0]}
                          barSize={38}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="state compact">
                    <ChartNoAxesCombined />
                    <p>Run your first evaluation to see the distribution.</p>
                  </div>
                )}
              </section>
            </div>
            <div className="dashboard-grid lower">
              <section className="card">
                <div className="card-head">
                  <div>
                    <h2>Recent upload activity</h2>
                    <p className="muted small">
                      Document processing at a glance
                    </p>
                  </div>
                  <Link className="text-link" to="/upload">
                    Upload resumes <ArrowUpRight size={15} />
                  </Link>
                </div>
                {stats.recent_batches.length ? (
                  stats.recent_batches.map((b) => (
                    <div className="activity" key={b.id}>
                      <Files size={18} />
                      <div>
                        <strong>{b.total_files} resume batch</strong>
                        <p>
                          {b.processed_files} processed · {b.failed_files}{" "}
                          failed · {new Date(b.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <Status value={b.status} />
                    </div>
                  ))
                ) : (
                  <p className="muted padded">
                    No uploads yet. PDF and DOCX batches will appear here.
                  </p>
                )}
              </section>
              <section className="insight">
                <span className="eyebrow">BEHIND EVERY SCORE, EVIDENCE</span>
                <h2>
                  Understand the match.
                  <br />
                  Make your own call.
                </h2>
                <p>
                  Skills, relevant experience, and semantic evidence come
                  together in one explainable view.
                </p>
                <Link to="/methodology">
                  Explore application features <ArrowUpRight size={17} />
                </Link>
              </section>
            </div>
          </>
        )}
      </State>
    </>
  );
}
