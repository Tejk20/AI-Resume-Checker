"""Section-aware semantic retrieval with bounded, model-specific embedding reuse."""
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
import hashlib
from threading import RLock
import numpy as np
from app.core.config import settings
from app.services.extraction import sections, sentences
from app.services.privacy import scoring_text

MPNET = 'sentence-transformers/all-mpnet-base-v2'
MINILM = 'sentence-transformers/all-MiniLM-L6-v2'
PIPELINE_VERSION = 'section-evidence-v2'
MODEL_LOCK = RLock()
GROUP_WEIGHTS = {'responsibilities': .50, 'skills': .20, 'qualifications': .15, 'role': .15}
ALLOWED_SECTIONS = {
    'responsibilities': {'experience', 'projects', 'summary'},
    'skills': {'skills', 'experience', 'projects', 'summary'},
    'qualifications': {'education', 'certifications'},
    'role': {'summary', 'experience', 'projects'},
}


class SemanticError(RuntimeError):
    """Safe operational model error; no candidate content in messages."""


@lru_cache(maxsize=1)
def _load_model(identifier, cache_folder):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(identifier, cache_folder=cache_folder, device='cpu',
                               trust_remote_code=False)


def get_model(identifier=None):
    # Lock outside lru_cache prevents concurrent cache misses loading twice.
    with MODEL_LOCK:
        try:
            return _load_model(identifier or settings.embedding_model, str(settings.model_cache))
        except Exception as exc:
            raise SemanticError('Embedding model could not be loaded. Download the configured model or explicitly select the MiniLM baseline.') from exc


class EmbeddingCache:
    """LRU vector cache: hashed text keys, bounded bytes/entries, one model namespace."""
    def __init__(self, max_bytes=128 * 1024 * 1024):
        self.max_bytes = max_bytes
        self.namespace = None
        self.entries = OrderedDict()
        self.bytes = 0
        self.hits = 0
        self.misses = 0
        self.lock = RLock()

    def activate(self, namespace):
        if self.namespace != namespace:
            self.entries.clear()
            self.bytes = 0
            self.namespace = namespace

    def encode(self, model, namespace, texts):
        with self.lock:
            self.activate(namespace)
            keys = [hashlib.sha256(text.encode('utf-8')).hexdigest() for text in texts]
            missing = {}
            for key, text in zip(keys, texts):
                if key in self.entries:
                    self.hits += 1
                    self.entries.move_to_end(key)
                else:
                    self.misses += 1
                    missing[key] = text
            new = {}
            if missing:
                try:
                    matrix = np.asarray(model.encode(list(missing.values()),
                        batch_size=settings.embedding_batch_size, normalize_embeddings=True,
                        show_progress_bar=False), dtype=np.float32)
                except Exception as exc:
                    raise SemanticError('Embedding inference failed. Retry or select the MiniLM baseline.') from exc
                if matrix.ndim != 2 or matrix.shape[0] != len(missing) or not np.isfinite(matrix).all():
                    raise SemanticError('Embedding model returned invalid vectors.')
                norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                if np.any(norms < 1e-10):
                    raise SemanticError('Embedding model returned a zero vector.')
                matrix = matrix / norms
                new = {key: row.copy() for key, row in zip(missing, matrix)}
            # Assemble before eviction: a batch may be larger than the retained cache.
            rows = [self.entries[key] if key in self.entries else new[key] for key in keys]
            result = np.stack(rows)
            for key, vector in new.items():
                if vector.nbytes <= self.max_bytes:
                    self.entries[key] = vector
                    self.bytes += vector.nbytes
                    while self.bytes > self.max_bytes or len(self.entries) > 20000:
                        _, evicted = self.entries.popitem(last=False)
                        self.bytes -= evicted.nbytes
            return result


VECTOR_CACHE = EmbeddingCache(settings.embedding_cache_mb * 1024 * 1024)


def clear_caches():
    with MODEL_LOCK:
        _load_model.cache_clear()
        with VECTOR_CACHE.lock:
            VECTOR_CACHE.activate(None)
            VECTOR_CACHE.entries.clear()
            VECTOR_CACHE.bytes = 0


@dataclass(frozen=True)
class Passage:
    text: str
    section: str


def token_chunks(model, text, section):
    """Cover every token with a 32-token overlap; reserve actual special-token slots."""
    limit = int(model.max_seq_length) - model.tokenizer.num_special_tokens_to_add(pair=False)
    if limit < 2:
        raise SemanticError('Configured model has an invalid input length.')
    overlap = min(32, limit // 4)
    result = []
    for line in text.splitlines():
        for sentence in sentences(line):
            ids = model.tokenizer.encode(sentence, add_special_tokens=False, truncation=False)
            for start in range(0, len(ids), limit-overlap):
                window = ids[start:start+limit]
                content = model.tokenizer.decode(window, skip_special_tokens=True).strip()
                if content:
                    result.append(Passage(content, section))
                if start + limit >= len(ids):
                    break
    return result


def resume_passages(candidate, model):
    parts = sections(candidate.raw_text)
    identity = [candidate.name, candidate.email, candidate.phone]
    passages = []
    for section in ['summary', 'skills', 'experience', 'projects', 'education', 'certifications']:
        text = scoring_text('\n'.join(parts.get(section, [])), identity)
        passages.extend(token_chunks(model, text, section))
    if not passages:
        passages = token_chunks(model, scoring_text(candidate.raw_text, identity), 'unstructured')
    return passages


def job_passages(job, model):
    groups = {
        'responsibilities': '\n'.join(job.responsibilities),
        'skills': '\n'.join(
            (['Required technical skills: ' + ', '.join(job.required_skills)] if job.required_skills else []) +
            (['Preferred technical skills: ' + ', '.join(job.preferred_skills)] if job.preferred_skills else [])),
        'qualifications': '\n'.join(job.qualifications),
        'role': 'Role: ' + job.title,
    }
    if not job.responsibilities:
        parts = sections(job.raw_text)
        groups['responsibilities'] = '\n'.join(parts.get('summary', []))
    passages = []
    for section, text in groups.items():
        passages.extend(token_chunks(model, scoring_text(text), section))
    return passages or token_chunks(model, scoring_text(job.raw_text), 'role')


class SemanticEvaluation:
    def __init__(self, job, model_id=None):
        self.model_id = model_id or settings.embedding_model
        with MODEL_LOCK:
            self.model = get_model(self.model_id)
            config = getattr(getattr(self.model[0], 'auto_model', None), 'config', None)
            self.revision = getattr(config, '_commit_hash', None) or 'local-or-unspecified'
            self.namespace = (self.model_id, self.revision, int(self.model.max_seq_length), PIPELINE_VERSION, str(settings.model_cache), id(self.model))
            self.requirements = job_passages(job, self.model)
            self.job_vectors = self._encode(self.requirements)
        self.metadata = {
            'embedding_model': self.model_id,
            'model_revision': self.revision,
            'embedding_dimensions': int(self.job_vectors.shape[1]),
            'max_sequence_tokens': int(self.model.max_seq_length),
            'pipeline_version': PIPELINE_VERSION,
            'section_weights': GROUP_WEIGHTS,
            'aggregation': 'mean best positive cosine per requirement within section; normalized weighted section mean',
            'normalized_embeddings': True,
            'chunk_overlap_tokens': min(32, (int(self.model.max_seq_length)-2)//4),
        }

    def _encode(self, passages):
        return VECTOR_CACHE.encode(self.model, self.namespace, [p.text for p in passages])

    def prepare_many(self, candidates):
        """One batched call for all uncached passages; job vectors reused for every candidate."""
        prepared = []
        all_passages = []
        for candidate in candidates:
            passages = resume_passages(candidate, self.model)
            prepared.append((passages, len(all_passages), len(all_passages)+len(passages)))
            all_passages.extend(passages)
        with MODEL_LOCK:
            matrix = self._encode(all_passages) if all_passages else None
        return [(self.namespace, passages, matrix[a:b] if matrix is not None else None)
                for passages, a, b in prepared]

    def compare_prepared(self, prepared):
        namespace, passages, vectors = prepared
        if namespace != self.namespace:
            raise SemanticError('Incompatible embedding models; regenerate cached resume embeddings.')
        if not passages:
            return 0.0, []
        sims = np.clip(self.job_vectors @ vectors.T, 0, 1)
        group_scores, evidence = {}, []
        for row, requirement in enumerate(self.requirements):
            allowed = ALLOWED_SECTIONS[requirement.section]
            eligible = [i for i, passage in enumerate(passages) if passage.section in allowed]
            fallback = not eligible
            if fallback:
                eligible = list(range(len(passages)))
            best = max(eligible, key=lambda i: float(sims[row, i]))
            similarity = float(sims[row, best])
            group_scores.setdefault(requirement.section, []).append(similarity)
            evidence.append({
                'requirement': requirement.text, 'requirement_section': requirement.section,
                'evidence': passages[best].text, 'evidence_section': passages[best].section,
                'similarity': round(similarity*100, 2), 'section_fallback': fallback,
            })
        denominator = sum(GROUP_WEIGHTS[group] for group in group_scores)
        total = sum(GROUP_WEIGHTS[group] * float(np.mean(values))
                    for group, values in group_scores.items()) / denominator
        return round(float(np.clip(total, 0, 1))*100, 2), evidence

    def compare(self, candidate):
        return self.compare_prepared(self.prepare_many([candidate])[0])
