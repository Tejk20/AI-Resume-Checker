"""Exclude explicit demographic/contact lines from scoring evidence.
This conservative English rule is not a substitute for a production fairness audit.
Raw documents remain private for traceability, but these lines never feed scores.
"""
import re
from typing import Sequence

SENSITIVE_LINE = re.compile(
    r'\b(?:gender|nationality|religion|ethnicity|marital status|date of birth|dob|caste)\b'
    r'|^\s*(?:age|sex)\s*[:=]'
    r'|\b(?:male|female|non.binary|transgender|years? old)\b',re.I)


def scoring_text(text: str, identity: Sequence[str | None] = ()) -> str:
    clean='\n'.join(line for line in text.splitlines() if not SENSITIVE_LINE.search(line))
    clean=re.sub(r'[\w.+\-]+@[\w.\-]+\.[A-Za-z]{2,}', '',clean)
    for value in identity:
        if value: clean=re.sub(re.escape(value),'',clean,flags=re.I)
    return clean
