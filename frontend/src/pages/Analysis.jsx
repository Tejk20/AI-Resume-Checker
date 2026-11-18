import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Mail, Phone, FileText, AlertTriangle } from "lucide-react";
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
import { Heading, State, Chips, Score } from "../components/UI";
export default function Analysis() {
  const { jobId, candidateId } = useParams();
  const { data, error, loading, reload } = useLoad(async () => {
    const [m, c, h] = await Promise.all([
      api.get(`/jobs/${jobId}/matches/${candidateId}`),
      api.get(`/candidates/${candidateId}`),
      api.get(`/jobs/${jobId}/matches/${candidateId}/history`),
    ]);
    return { match: m.data, candidate: c.data, history: h.data };
  }, [jobId, candidateId]);
  const e = data?.match.explanation,
    c = data?.candidate;
  return (
    <>
      <Link to="/rankings" className="text-link back">
        <ArrowLeft size={15} />
        Back to rankings
      </Link>
      <State {...{ loading, error }} retry={reload}>
        {data && (
          <>
            <Heading
              title={c.name || "Candidate name not determined"}
              eyebrow="CANDIDATE / DETAILED ANALYSIS"
              action={
                <div className="overall">
                  <Score value={data.match.overall_score} />
                  <small>Estimated job-fit score</small>
                </div>
              }
            >
              An inspectable score, grounded in extracted evidence.
            </Heading>
            <div className="contact-strip">
              {c.email && (
                <span>
                  <Mail size={15} />
                  {c.email}
                </span>
              )}
              {c.phone && (
                <span>
                  <Phone size={15} />
                  {c.phone}
                </span>
              )}
              <span>
                <FileText size={15} />
                {c.original_filename}
              </span>
              <span>Algorithm {data.match.algorithm_version}</span>
              <span>Model: {data.match.embedding_model}</span>
            </div>
            <div className="notice">{e.summary}</div>
            <div className="analysis-grid">
              <section className="card form-card">
                <h2>Score composition</h2>
                <p className="muted small">
                  Component scores out of 100; weights normalized for this job.
                </p>
                <p className="small" style={{ marginTop: 12 }}>
                  {data.match.scoring_config?.default_weights
                    ? Object.entries(data.match.scoring_config.default_weights)
                        .map(
                          ([key, value]) =>
                            `${Math.round(value * 100)}% ${{ semantic: "Semantic", skill: "Skills", experience: "Experience", education: "Education" }[key]}`,
                        )
                        .join(" + ")
                    : "Legacy evaluation: recorded component weights are shown below."}
                </p>
                <div className="chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={Object.entries(e.components)
                        .filter(([, v]) => v !== null)
                        .map(([name, value]) => ({
                          name: name[0].toUpperCase() + name.slice(1),
                          value,
                        }))}
                      margin={{ left: -20, right: 10, top: 10 }}
                    >
                      <CartesianGrid vertical={false} stroke="#edf0ee" />
                      <XAxis
                        dataKey="name"
                        fontSize={11}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        domain={[0, 100]}
                        fontSize={11}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip />
                      <Bar
                        dataKey="value"
                        fill="#347968"
                        radius={[5, 5, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="component-rows">
                  {Object.entries(e.components).map(([k, v]) => (
                    <div key={k}>
                      <span>
                        {{
                          semantic: "Semantic similarity",
                          skill: "Skill matching",
                          experience: "Relevant experience",
                          education: "Education",
                        }[k] || k}
                        <small>
                          {v === null
                            ? "Not applicable"
                            : (e.weights[k] * 100).toFixed(2) + "% weight"}
                        </small>
                      </span>
                      <strong>
                        {v === null ? "—" : v.toFixed(2)}
                        <small>
                          {v === null
                            ? ""
                            : ` +${e.contributions[k].toFixed(4)} points`}
                        </small>
                      </strong>
                    </div>
                  ))}
                </div>
                <p className="small muted">
                  Contributions are displayed to four decimals. The
                  full-precision sum is rounded once to produce the overall
                  score.
                </p>
              </section>
              <div>
                <section className="card form-card">
                  <h2>Skill alignment</h2>
                  <h3 className="small-title">Matched required skills</h3>
                  <Chips items={e.matched_required} />
                  <h3 className="small-title">Matched preferred skills</h3>
                  <Chips items={e.matched_preferred} />
                  <h3 className="small-title">
                    Required skills not identified
                  </h3>
                  <Chips items={e.missing_required} tone="missing" />
                  <h3 className="small-title">
                    Preferred skills not identified
                  </h3>
                  <Chips items={e.missing_preferred} tone="missing" />
                  {e.related_skills.length > 0 && (
                    <>
                      <h3 className="small-title">
                        Transferable evidence · no exact-match credit
                      </h3>
                      {e.related_skills.map((r, i) => (
                        <p className="muted small" key={i}>
                          {r.supporting} → related to {r.required}
                        </p>
                      ))}
                    </>
                  )}
                </section>
                <section className="card form-card">
                  <h2>Experience & qualifications</h2>
                  <div className="experience-compare">
                    <div>
                      <strong>{e.relevant_years ?? "?"}</strong>
                      <span>Relevant years</span>
                    </div>
                    <span>/</span>
                    <div>
                      <strong>{e.required_years ?? "—"}</strong>
                      <span>Required years</span>
                    </div>
                  </div>
                  <p className="small muted">{e.experience_method}</p>
                  {e.relevant_roles.map((r, i) => (
                    <div className="evidence" key={i}>
                      <strong>{r.title}</strong>
                      <p>{r.description}</p>
                    </div>
                  ))}
                  <h3 className="small-title">Qualifications</h3>
                  <p className="muted small">{e.qualification_note}</p>
                  <p className="small">
                    Required:{" "}
                    {e.qualification_requirements.join(" · ") ||
                      "No explicit requirement"}
                  </p>
                  <p className="small">
                    Evidence:{" "}
                    {e.qualification_evidence.join(" · ") || "Not identified"}
                  </p>
                </section>
              </div>
            </div>
            {!!e.uncertain_requirements?.length && (
              <section className="card form-card warning-card">
                <h2>Requirements needing review</h2>
                {e.uncertain_requirements.map((item, index) => (
                  <p key={index} className="small">
                    {item.requirement}: {item.status}
                  </p>
                ))}
              </section>
            )}
            <section className="card form-card">
              <h2>Semantic evidence</h2>
              <p className="muted small">
                Each job requirement is paired with its most similar resume
                passage. Cosine similarity is a heuristic alignment measure.
              </p>
              <div className="semantic-list">
                {e.semantic_evidence.map((s, i) => (
                  <div className="semantic-row" key={i}>
                    <div>
                      <span className="eyebrow">JOB REQUIREMENT</span>
                      {s.requirement_section && (
                        <p className="small muted">{s.requirement_section}</p>
                      )}
                      <p>{s.requirement}</p>
                    </div>
                    <div>
                      <span className="eyebrow">RESUME EVIDENCE</span>
                      {s.evidence_section && (
                        <p className="small muted">
                          {s.evidence_section}
                          {s.section_fallback
                            ? " (available-evidence fallback)"
                            : ""}
                        </p>
                      )}
                      <p>{s.evidence}</p>
                    </div>
                    <Score value={s.similarity} />
                  </div>
                ))}
              </div>
            </section>
            {c.projects.length > 0 && (
              <section className="card form-card">
                <h2>Extracted projects</h2>
                {c.projects.map((p, i) => (
                  <p className="small" key={i}>
                    {p}
                  </p>
                ))}
              </section>
            )}
            {!!data.history.length && (
              <section className="card form-card">
                <h2>Previous evaluations</h2>
                <p className="muted small">
                  Previous scores are retained when this candidate is rematched.
                </p>
                {data.history.map((item) => (
                  <div className="evidence" key={item.id}>
                    <strong>
                      {Number(item.payload.overall_score).toFixed(2)} / 100
                    </strong>
                    <p>
                      {item.embedding_model} · {item.payload.algorithm_version}{" "}
                      ·{" "}
                      {new Date(
                        item.payload.evaluated_at || item.created_at,
                      ).toLocaleString()}
                    </p>
                  </div>
                ))}
              </section>
            )}
            {e.warnings.length > 0 && (
              <section className="card form-card warning-card">
                <h2>
                  <AlertTriangle size={18} />
                  Manual review
                </h2>
                {e.warnings.map((w) => (
                  <p className="small" key={w}>
                    {w}
                  </p>
                ))}
              </section>
            )}
            <p className="muted small">
              {e.score_interpretation} Missing skills mean “not identified in
              the resume”, which may reflect incomplete parsing.
            </p>
          </>
        )}
      </State>
    </>
  );
}
