import re
import math
from app.core.config import WEIGHTS, ALGORITHM_VERSION
from app.services.skills import extract_skills, related_skills
from app.services.extraction import union_years
from app.services.privacy import scoring_text


def weighted_score(components):
    if any(value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100) for value in components.values()):
        raise ValueError('Component scores must be finite values from 0 to 100.')
    applicable = {k:w for k,w in WEIGHTS.items() if components[k] is not None}
    total = sum(applicable.values())
    if not total:
        raise ValueError('No applicable scoring component has a positive weight.')
    weights = {k:w/total for k,w in applicable.items()}
    contributions = {k:components[k]*w for k,w in weights.items()}
    return round(max(0,min(100,sum(contributions.values()))),2), weights, contributions


def skill_coverage(required, preferred, present):
    r = len(set(required) & set(present))/len(required) if required else None
    p = len(set(preferred) & set(present))/len(preferred) if preferred else None
    return 100*(.8*r+.2*p) if r is not None and p is not None else 100*r if r is not None else 100*p if p is not None else None


def relevant_experience(job, candidate):
    roles = [r for r in candidate.experience_details if not r['internship']]
    if not roles:
        return None, []
    relevant = []
    for role in roles:
        found = set(extract_skills(scoring_text(role['description'])))
        required = set(job.required_skills or job.preferred_skills)
        # Conservative and inspectable: at least one third of skills, or role title words.
        title_words = set(re.findall(r'[a-z]{4,}', job.title.lower())) - {'developer','engineer','senior','junior'}
        title_match = bool(title_words & set(re.findall(r'[a-z]{4,}', (role['title'] or '').lower())))
        if (required and len(found & required)/len(required) >= 1/3) or (not required and title_match):
            relevant.append(role)
    return union_years([(r['start_month'],r['end_month']) for r in relevant]), relevant


def degree_level(text):
    if re.search(r'ph\.?d|doctor', text, re.I): return 3
    if re.search(r'master|m\.?tech|m\.?sc|m\.s\b', text, re.I): return 2
    if re.search(r'bachelor|b\.?tech|b\.?sc|b\.s\b|b\.e\b', text, re.I): return 1
    if re.search(r'diploma|secondary|high school', text, re.I): return 0
    return None


def qualification_score(job, candidate, years):
    if not job.qualifications: return None, 'No qualification requirement stated.'
    evidence = ' '.join(candidate.education + candidate.certifications)
    values = []
    for requirement in job.qualifications:
        if re.search(r'certif',requirement,re.I):
            # Never certify a candidate from a broad degree or technology match.
            values.append(50)
            continue
        target, actual = degree_level(requirement), degree_level(evidence)
        equivalent = bool(re.search(r'equivalent experience', requirement, re.I))
        if equivalent and years is not None and job.min_experience and years >= job.min_experience:
            values.append(100); continue
        if target is not None and actual is not None:
            subject_required = bool(re.search(r'computer science|engineering|information technology', requirement, re.I))
            subject_found = bool(re.search(r'computer science|engineering|information technology', evidence, re.I))
            values.append(0 if actual < target else 100 if not subject_required or subject_found else 50)
        else:
            values.append(50)
    return sum(values)/len(values), 'Rule-based comparison of stated qualifications. A 50 indicates unverified or potential equivalence; review evidence.'


def score_candidate(job, candidate, semantic_score, semantic_evidence):
    required, preferred, present = set(job.required_skills),set(job.preferred_skills),set(candidate.skills)
    mr, mp = sorted(required & present), sorted(preferred & present)
    missing_r, missing_p = sorted(required-present), sorted(preferred-present)
    years, roles = relevant_experience(job,candidate)
    warnings = list(candidate.parsing_warnings)
    if any(item.get('section_fallback') for item in semantic_evidence):
        warnings.append('Some semantic requirements used other available sections because the expected resume section was not found; review the cited evidence.')
    experience = None
    if job.min_experience and job.min_experience > 0:
        experience = 50.0 if years is None else 100*min(1,years/job.min_experience)
        if years is None: warnings.append('Experience not reliably determined; provisional midpoint of 50, manual review required.')
    education, qualification_note = qualification_score(job,candidate,years)
    if education is not None and 0 < education < 100:
        warnings.append('Qualifications partially verified; manual review required.')
    components = dict(semantic=semantic_score, skill=skill_coverage(list(required),list(preferred),list(present)),experience=experience,education=education)
    overall, weights, contributions = weighted_score(components)
    summary = f'Estimated job-fit score {overall:.2f}/100. {len(mr)} of {len(required)} required skills identified. '
    summary += f'Estimated relevant professional experience: {years} years.' if years is not None else 'Experience not reliably determined.'
    uncertain = []
    if experience is not None and years is None:
        uncertain.append({'requirement': f'{job.min_experience} relevant professional years', 'type': 'experience', 'status': 'unverified'})
    if education is not None and 0 < education < 100:
        uncertain.extend({'requirement': q, 'type': 'qualification', 'status': 'unverified or potentially equivalent'} for q in job.qualifications)
    explanation = dict(summary=summary, components=components, weights=weights, contributions=contributions,
        uncertain_requirements=uncertain,
        matched_required=mr, matched_preferred=mp, missing_required=missing_r, missing_preferred=missing_p,
        related_skills=related_skills(missing_r+missing_p,present), relevant_years=years, required_years=job.min_experience,
        relevant_roles=roles, qualification_note=qualification_note, qualification_requirements=job.qualifications,
        qualification_evidence=candidate.education+candidate.certifications, semantic_evidence=semantic_evidence,
        skill_evidence=candidate.skill_evidence, warnings=sorted(set(warnings)), review_required=bool(warnings),
        experience_method='Union of non-internship roles with at least one third of required skills in role evidence; title overlap when no skills specified.',
        missing_label='Not identified in the resume', score_interpretation='Estimated job-fit score; not a hiring probability or an automatic rejection decision.')
    return dict(overall_score=overall, semantic_score=semantic_score, skill_score=components['skill'],experience_score=experience,
                education_score=education,matched_skills=mr+mp,missing_skills=missing_r+missing_p,explanation=explanation,algorithm_version=ALGORITHM_VERSION)
