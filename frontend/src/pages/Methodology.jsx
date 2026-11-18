import { Link } from "react-router-dom";
import { Heading } from "../components/UI";
import { BriefcaseBusiness, Files, Users, FileSearch, FolderClock, ArrowRight, ScanLine } from "lucide-react";

const features = [
  [BriefcaseBusiness, "01", "Start with the role", "Paste a job description or upload a document. Review the skills, experience, and qualifications, then adjust the requirements to reflect the role you are hiring for."],
  [Files, "02", "Bring your resumes together", "Upload up to 50 PDF and DOCX resumes in one batch. Follow processing progress and see which documents are ready for review."],
  [Users, "03", "Compare your candidate pool", "Explore a ranked table with compatibility scores, relevant experience, matched skills, and requirements not identified in each resume. Search by name or filter and sort the results."],
  [FileSearch, "04", "Explore each candidate", "Open a candidate profile to review contact details, skills, work experience, qualifications, and projects alongside the requirements of your selected job."],
  [ScanLine, "05", "See the details behind a match", "Review matching skills, experience comparisons, and supporting resume passages in one place. Candidate analysis helps you understand where a profile aligns and where a closer look is useful."],
  [FolderClock, "06", "Pick up where you left off", "Return to saved jobs and evaluations whenever you need them. Revisit candidate rankings, review a role's requirements, or upload more resumes as your search develops."],
];

export default function Methodology() {
  return (
    <>
      <Heading title="Your candidate review, all in one place." eyebrow="ABOUT / AVOM RESUME INTELLIGENCE">
        A workspace for organizing resumes, comparing candidates, and exploring the experience behind each profile.
      </Heading>
      <div className="method-hero">
        <BriefcaseBusiness size={34} />
        <div>
          <h2>From job description to candidate insights.</h2>
          <p>
            Avom Resume Intelligence brings your job requirements, resume uploads,
            and candidate evaluations into a connected workflow. Spend less time
            moving between documents and more time reviewing the people who
            could fit your team.
          </p>
        </div>
      </div>
      <div className="method-grid">
        {features.map(([Icon, number, title, description]) => (
          <section className="card form-card" key={number}>
            <div className="method-number">
              <Icon size={24} />
              <span>{number}</span>
            </div>
            <h2>{title}</h2>
            <p className="muted">{description}</p>
          </section>
        ))}
      </div>
      <section className="card form-card">
        <span className="eyebrow">A CONNECTED RECRUITMENT WORKSPACE</span>
        <h2>Keep your next step within reach.</h2>
        <p className="muted" style={{ marginTop: 14 }}>
          The overview shows your saved jobs, resume processing activity, and
          evaluation summaries. Select a job to move between uploads and
          rankings, or create a new role to begin another candidate review.
        </p>
        <div className="chips" style={{ marginTop: 22, gap: 12 }}>
          <Link className="primary" to="/jobs/new">Create a job <ArrowRight size={16} /></Link>
          <Link className="secondary" to="/rankings">Explore candidate rankings <ArrowRight size={16} /></Link>
        </div>
      </section>
    </>
  );
}
