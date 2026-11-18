// Suggestions are optional hints, never a fixed set of supported jobs.
export const suggestedJobTitles = [
  "AI/ML Engineer",
  "Backend Developer",
  "Business Analyst",
  "Cloud Engineer",
  "Cybersecurity Analyst",
  "Data Analyst",
  "Data Engineer",
  "Data Scientist",
  "DevOps Engineer",
  "Frontend Developer",
  "Full Stack Developer",
  "Java Developer",
  "Mobile App Developer",
  "Product Manager",
  "Project Manager",
  "Python Developer",
  "QA Engineer",
  "React Developer",
  "Software Engineer",
  "UI/UX Designer",
];

export function canonicalJobTitle(title = "") {
  const clean = title.trim().replace(/\s+/g, " ");
  const alias = clean
    .toLowerCase()
    .replace(/[\/+&_\-]+/g, " ")
    .replace(/\s+/g, " ");
  if (
    /^(ai|ml|ai ml|artificial intelligence|machine learning|artificial intelligence machine learning)( engineer)?$/.test(
      alias,
    )
  )
    return "AI/ML Engineer";
  return clean;
}

export function groupJobs(jobs) {
  const groups = new Map();
  for (const job of jobs) {
    const title = canonicalJobTitle(job.title);
    const key = title.toLocaleLowerCase();
    if (!groups.has(key)) groups.set(key, { key, title, jobs: [] });
    groups.get(key).jobs.push(job);
  }
  for (const group of groups.values()) {
    group.jobs.sort(
      (a, b) =>
        Number(b.match_status === "completed") -
          Number(a.match_status === "completed") ||
        String(b.created_at || "").localeCompare(String(a.created_at || "")) ||
        a.id.localeCompare(b.id),
    );
  }
  return [...groups.values()].sort((a, b) => a.title.localeCompare(b.title));
}
