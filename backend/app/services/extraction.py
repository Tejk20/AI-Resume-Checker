import re
from datetime import date
from functools import lru_cache
from app.services.skills import extract_skills
from app.services.privacy import scoring_text

HEADINGS = {'summary':'summary','profile':'summary','skills':'skills','technical skills':'skills',
 'work experience':'experience','professional experience':'experience','experience':'experience','employment':'experience',
 'education':'education','qualifications':'education','projects':'projects','certifications':'certifications','internships':'internships'}


@lru_cache(maxsize=1)
def nlp():
    import spacy
    try:
        return spacy.load('en_core_web_sm', disable=['ner', 'tagger', 'lemmatizer'])
    except OSError:
        model = spacy.blank('en')
        model.add_pipe('sentencizer')
        return model


def sentences(text):
    return [s.text.strip() for s in nlp()(text[:200000]).sents if s.text.strip()]


def parse_job(text: str) -> dict:
    text = scoring_text(text)
    required, preferred = set(), set()
    context = 'required'
    responsibilities, qualifications = [], []
    for line in text.splitlines():
        for sentence in sentences(line):
            for clause in re.split(r';|(?<=\.)\s+|\bbut\b', sentence):
                is_pref = bool(re.search(r'preferred|nice.to.have|bonus|optional|desirable', clause, re.I))
                is_req = bool(re.search(r'must|required|essential|minimum', clause, re.I))
                if len(clause.strip().split()) <= 4 and (is_pref or is_req):
                    context = 'preferred' if is_pref else 'required'
                target = preferred if is_pref or (context == 'preferred' and not is_req) else required
                target.update(extract_skills(clause))
            if re.search(r'degree|bachelor|master|b\.tech|bsc|phd|certifi', sentence, re.I):
                qualifications.append(sentence)
            if re.search(r'build|develop|design|maintain|implement|deploy|responsib|collaborat|train|optimiz', sentence, re.I):
                responsibilities.append(sentence)
    exp = re.search(r'(\d+(?:\.\d+)?)\s*(?:\+|[-–]\s*\d+)?\s*years?\s*(?:of\s*)?(?:\w+\s+){0,3}experience', text, re.I)
    preferred -= required
    warnings = ['Extraction is rule-based. Review requirements before matching.']
    if not required and not preferred:
        warnings.append('No recognized skills; add requirements manually.')
    return dict(required_skills=sorted(required), preferred_skills=sorted(preferred),
                min_experience=float(exp[1]) if exp else None, qualifications=qualifications,
                responsibilities=responsibilities, extraction_warnings=warnings)


def sections(text):
    result = {'header': []}
    current = 'header'
    for line in text.splitlines():
        line = line.strip().strip('•')
        prefix, sep, remainder = line.partition(':')
        heading = HEADINGS.get((prefix if sep else line).lower().strip())
        if heading:
            current = heading
            result.setdefault(current, [])
            if sep and remainder.strip():
                result[current].append(remainder.strip())
        elif line:
            result.setdefault(current, []).append(line)
    return result


MONTHS = {m: i+1 for i, m in enumerate(['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'])}
DATE = r'(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|\d{1,2}[/\-]\d{4}|\d{4}|Present|Current|Now)'
RANGE = re.compile(r'(' + DATE + r')\s*(?:[-–—]|\bto\b)\s*(' + DATE + r')', re.I)


def month_index(value, today=None):
    today = today or date.today()
    if value.lower() in ['present','current','now']:
        return today.year*12+today.month-1, False
    if re.fullmatch(r'\d{4}', value):
        return int(value)*12, True
    m = re.fullmatch(r'(\d{1,2})[/\-](\d{4})', value)
    if m:
        if not 1 <= int(m[1]) <= 12:
            raise ValueError('Invalid month')
        return int(m[2])*12+int(m[1])-1, False
    mon, year = value.split()
    return int(year)*12+MONTHS[mon[:3].lower()]-1, False


def union_years(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return round(sum(b-a for a,b in merged)/12, 2)


def employment(lines):
    text = '\n'.join(lines)
    matches = list(RANGE.finditer(text))
    roles, warnings = [], []
    for i, m in enumerate(matches):
        start_line = text.rfind('\n', 0, m.start())+1
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        if i+1 < len(matches):
            end = text.rfind('\n', m.end(), end)+1 or end
        evidence = text[start_line:end].strip()
        try:
            start, a = month_index(m[1]); finish, b = month_index(m[2])
            if finish < start or finish > month_index('Present')[0] or start < 1950*12:
                raise ValueError('Invalid range')
            title_line = evidence.splitlines()[0]
            title_text = RANGE.sub('',title_line).strip(' |,-')
            pieces = re.split(r'\s*\|\s*|\s+at\s+',title_text,flags=re.I)
            title = pieces[0].strip() or None
            company = pieces[1].strip() if len(pieces)>1 and pieces[1].strip() else None
            roles.append(dict(title=title, company=company, start=m[1], end=m[2],
                        start_month=start, end_month=finish, description=evidence,
                        internship=bool(re.search(r'\bintern(?:ship)?\b', evidence.splitlines()[0], re.I)), uncertain=a or b))
            if a or b:
                warnings.append('Year-only employment dates are approximate; review required.')
        except (ValueError, KeyError):
            warnings.append('Unrecognized or invalid employment dates; experience not reliably determined.')
    if not roles:
        warnings.append('Experience not reliably determined from dated employment history.')
    return roles, warnings


def parse_resume(text):
    parts = sections(text)
    warnings = []
    header = parts['header']
    name = None
    if header:
        possible = header[0]
        if re.fullmatch(r"[A-Za-z][A-Za-z .'\-]{2,70}", possible) and 2 <= len(possible.split()) <= 4 and not re.search(r'resume|curriculum|developer|engineer', possible, re.I):
            name = possible
    if not name:
        warnings.append('Candidate name could not be confidently extracted.')
    email = re.search(r'[\w.+\-]+@[\w.\-]+\.[A-Za-z]{2,}', text)
    phone = re.search(r'(?<!\w)(?:\+\d{1,3}[ -]?)?(?:\(?\d{3}\)?[ -])\d{3}[ -]\d{4}(?!\d)', text)
    roles, exp_warnings = employment(parts.get('experience', []))
    warnings.extend(exp_warnings)
    details = extract_skills(scoring_text(text,[name,email[0] if email else None,phone[0] if phone else None]))
    professional = [r for r in roles if not r['internship']]
    return dict(name=name, email=email[0] if email else None, phone=phone[0] if phone else None,
                skills=list(details), skill_evidence=details,
                experience_years=union_years([(r['start_month'], r['end_month']) for r in professional]) if professional else None,
                experience_details=roles, education=parts.get('education', []), projects=parts.get('projects', []),
                certifications=parts.get('certifications', []), raw_text=text, parsing_warnings=warnings)
