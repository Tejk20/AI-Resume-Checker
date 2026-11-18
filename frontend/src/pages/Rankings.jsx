import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Search, ArrowUpRight, SlidersHorizontal, Upload } from "lucide-react";
import { api } from "../services/api";
import { useLoad } from "../hooks/useLoad";
import { Heading, JobSelect, Chips, Score, State } from "../components/UI";
export default function Rankings({ jobs, selected, setSelected }) {
  const [search, setSearch] = useState(""),
    [min, setMin] = useState(0),
    [sort, setSort] = useState("score"),
    [page, setPage] = useState(0);
  useEffect(() => setPage(0), [selected, search, min, sort]);
  const { data, error, loading, reload } = useLoad(
    async () =>
      selected
        ? (
            await api.get(`/jobs/${selected}/rankings`, {
              params: {
                search,
                min_score: min,
                sort,
                offset: page * 20,
                limit: 20,
              },
            })
          ).data
        : { items: [], total: 0 },
    [selected, search, min, sort, page],
  );
  return (
    <>
      <Heading
        title="The evidence behind your shortlist."
        eyebrow="03 / CANDIDATE RANKINGS"
        action={
          <Link className="secondary" to="/upload">
            <Upload size={16} />
            Upload resumes
          </Link>
        }
      >
        Compare alignment with the job. Open any candidate to understand the
        score.
      </Heading>
      <JobSelect {...{ jobs, selected, onChange: setSelected }} />
      <section className="card">
        <div className="ranking-toolbar">
          <div className="search-field">
            <Search size={17} />
            <input
              aria-label="Search candidates"
              placeholder="Search candidates…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <label className="inline-label">
            <SlidersHorizontal size={16} />
            Minimum score
            <input
              aria-label="Minimum score"
              type="number"
              min="0"
              max="100"
              value={min}
              onChange={(e) =>
                setMin(Math.max(0, Math.min(100, Number(e.target.value))))
              }
            />
          </label>
          <select
            aria-label="Sort candidates"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="score">Highest compatibility</option>
            <option value="experience">Most relevant experience</option>
          </select>
          <button className="text-link" onClick={reload}>
            Refresh
          </button>
        </div>
        <State
          {...{ loading, error }}
          retry={reload}
          empty={!data?.items.length}
        >
          <p>
            {!selected
              ? "Select a job to view its rankings."
              : !data?.items.length
                ? "No candidates match this view. Upload resumes, run matching, or adjust your filters."
                : null}
          </p>
          {!!data?.items.length && (
            <>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Candidate</th>
                      <th>Relevant experience</th>
                      <th>Compatibility</th>
                      <th>Matched skills</th>
                      <th>Required gaps</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((r, i) => (
                      <tr key={r.candidate_id}>
                        <td>
                          <span
                            className={
                              "rank " + (page === 0 && i === 0 ? "first" : "")
                            }
                          >
                            {page * 20 + i + 1}
                          </span>
                        </td>
                        <td>
                          <div className="candidate-cell">
                            <span className="avatar">
                              {(r.candidate.name || "?")
                                .split(" ")
                                .map((x) => x[0])
                                .slice(0, 2)
                                .join("")}
                            </span>
                            <div>
                              <strong>
                                {r.candidate.name || "Name not determined"}
                              </strong>
                              <small>
                                {r.explanation.review_required
                                  ? "Review evidence"
                                  : "Evidence available"}
                              </small>
                            </div>
                          </div>
                        </td>
                        <td>
                          {r.explanation.relevant_years === null ? (
                            <span className="muted">Unverified</span>
                          ) : (
                            r.explanation.relevant_years + " years"
                          )}
                        </td>
                        <td>
                          <Score value={r.overall_score} />
                          <div className="score-track">
                            <div style={{ width: r.overall_score + "%" }} />
                          </div>
                        </td>
                        <td>
                          <Chips items={r.matched_skills.slice(0, 3)} />
                          {r.matched_skills.length > 3 && (
                            <small className="muted">
                              +{r.matched_skills.length - 3} more
                            </small>
                          )}
                        </td>
                        <td>
                          <span
                            className={
                              r.explanation.missing_required.length
                                ? "gap"
                                : "no-gap"
                            }
                          >
                            {r.explanation.missing_required.length} not
                            identified
                          </span>
                        </td>
                        <td>
                          <Link
                            className="analysis-link"
                            to={`/jobs/${selected}/candidates/${r.candidate_id}`}
                            aria-label={
                              "Analyze " + (r.candidate.name || "candidate")
                            }
                          >
                            <ArrowUpRight size={20} />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="pagination">
                <span>
                  {data.total} candidates · Compatibility is a heuristic, not a
                  hiring recommendation.
                </span>
                <div>
                  <button
                    className="secondary"
                    disabled={page === 0}
                    onClick={() => setPage(page - 1)}
                  >
                    Previous
                  </button>
                  <button
                    className="secondary"
                    disabled={(page + 1) * 20 >= data.total}
                    onClick={() => setPage(page + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </State>
      </section>
    </>
  );
}
