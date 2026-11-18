import json
import re
from pathlib import Path

TAXONOMY = json.loads((Path(__file__).parents[1] / 'data/skill_taxonomy.json').read_text())


def extract_skills(text: str) -> dict:
    """Longest phrases win: React Native must never also become React."""
    hits = []
    for canonical, entry in TAXONOMY.items():
        for phrase in [canonical, *entry['aliases']]:
            for m in re.finditer(r'(?<![\w+#])' + re.escape(phrase) + r'(?![\w+#])', text, re.I):
                if phrase.lower() == 'js' and not re.search(r'\b(skills|javascript|frontend|web|react|node)\b', text, re.I):
                    continue
                hits.append((m.start(), m.end(), canonical, m.group()))
    selected = []
    for hit in sorted(hits, key=lambda h: (-(h[1]-h[0]), h[0])):
        if not any(hit[0] < h[1] and hit[1] > h[0] for h in selected):
            selected.append(hit)
    return {h[2]: {'phrase': h[3], 'kind': 'exact' if h[2].lower() == h[3].lower() else 'alias'} for h in sorted(selected)}


def related_skills(missing, present):
    return [{'required': s, 'supporting': r} for s in missing for r in TAXONOMY.get(s, {}).get('related', []) if r in present]
