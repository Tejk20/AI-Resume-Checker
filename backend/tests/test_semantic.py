from types import SimpleNamespace as NS
from unittest.mock import Mock
import numpy as np
import pytest
from pydantic import ValidationError
from app.core.config import Settings
from app.services import semantic
from app.services.extraction import parse_resume
from app.services.scoring import score_candidate


class Tokenizer:
    def num_special_tokens_to_add(self, pair=False): return 2
    def encode(self, text, **kwargs): return text.split()
    def decode(self, tokens, **kwargs): return ' '.join(tokens)


class FakeModel:
    max_seq_length = 12
    tokenizer = Tokenizer()
    def __init__(self, dimensions=3):
        self.dimensions = dimensions
        self.calls = 0
    def __getitem__(self, index): return NS(auto_model=NS(config=NS(_commit_hash='test-revision')))
    def encode(self, texts, **kwargs):
        self.calls += 1
        return np.asarray([[1 + ('Python' in t), 1 + ('degree' in t), 1 + ('API' in t)] + [1]*(self.dimensions-3) for t in texts], dtype=np.float32)


def job():
    return NS(title='Python Developer', raw_text='Build Python API services.', responsibilities=['Build Python API services.'],
              required_skills=['Python', 'FastAPI'], preferred_skills=[], qualifications=['Bachelor degree'], min_experience=2)


def candidate():
    return NS(**parse_resume('Alex Rowan\nSummary\nDevelop reliable software.\nTechnical Skills\nPython FastAPI\nExperience\nEngineer Jan 2020 - Jan 2024\nBuild Python API services.\nEducation\nBachelor degree\nProjects\nBuild useful API projects.'))


def test_model_configuration_and_weight_validation(monkeypatch):
    monkeypatch.delenv('MODEL_NAME', raising=False)
    monkeypatch.delenv('EMBEDDING_MODEL', raising=False)
    assert Settings(_env_file=None).embedding_model == semantic.MPNET
    monkeypatch.setenv('MODEL_NAME', semantic.MINILM)
    assert Settings(_env_file=None).embedding_model == semantic.MINILM
    monkeypatch.setenv('EMBEDDING_MODEL', semantic.MPNET)
    assert Settings(_env_file=None).embedding_model == semantic.MPNET
    with pytest.raises(ValidationError):
        Settings(_env_file=None, scoring_weights={'semantic': .9, 'skill': .4, 'experience': .25, 'education': .1})
    with pytest.raises(ValidationError): Settings(_env_file=None, scoring_weights={'semantic':1})


def test_model_initialized_once_cpu_and_switches_safely(monkeypatch):
    import sentence_transformers
    factory = Mock(side_effect=lambda *args, **kwargs: FakeModel())
    monkeypatch.setattr(sentence_transformers, 'SentenceTransformer', factory)
    semantic.clear_caches()
    try:
        assert semantic.get_model(semantic.MPNET) is semantic.get_model(semantic.MPNET)
        assert factory.call_count == 1
        assert factory.call_args.kwargs['device'] == 'cpu'
        assert factory.call_args.kwargs['trust_remote_code'] is False
        semantic.get_model(semantic.MINILM)
        assert factory.call_count == 2
    finally: semantic.clear_caches()


def test_long_input_covers_final_tokens_and_never_exceeds_budget():
    model = FakeModel()
    text = ' '.join(f'token{i}' for i in range(101))
    passages = semantic.token_chunks(model, text, 'experience')
    assert len(passages) > 10
    assert all(len(p.text.split()) <= 10 for p in passages)
    assert set(text.split()) == set(' '.join(p.text for p in passages).split())
    assert 'token100' in passages[-1].text


def test_cache_normalization_deduplication_model_invalidation_and_bound():
    model = FakeModel()
    cache = semantic.EmbeddingCache(max_bytes=100)
    first = cache.encode(model, ('mpnet', 1), ['Python API', 'Python API'])
    assert first.shape == (2, 3)
    assert np.allclose(np.linalg.norm(first, axis=1), 1)
    assert model.calls == 1
    cache.encode(model, ('mpnet', 1), ['Python API'])
    assert model.calls == 1
    cache.encode(model, ('minilm', 1), ['Python API'])
    assert model.calls == 2
    cache.encode(model, ('minilm', 2), ['Python API'])
    assert model.calls == 3
    cache.encode(model, ('minilm', 2), [str(i) for i in range(50)])
    assert cache.bytes <= 100


def test_section_evidence_bounded_scores_and_warm_cache(monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(semantic, 'get_model', lambda *_: model)
    monkeypatch.setattr(semantic, 'VECTOR_CACHE', semantic.EmbeddingCache())
    evaluation = semantic.SemanticEvaluation(job(), semantic.MPNET)
    prepared = evaluation.prepare_many([candidate(), candidate()])
    score, evidence = evaluation.compare_prepared(prepared[0])
    assert 0 <= score <= 100
    assert {'responsibilities', 'skills', 'qualifications', 'role'} == {e['requirement_section'] for e in evidence}
    assert next(e for e in evidence if e['requirement_section']=='qualifications')['evidence_section']=='education'
    before = model.calls
    again = evaluation.compare(candidate())
    assert model.calls == before
    assert again == (score, evidence)
    assert float(evaluation.job_vectors[0] @ evaluation.job_vectors[0]) == pytest.approx(1)
    with pytest.raises(semantic.SemanticError, match='Incompatible'):
        evaluation.compare_prepared((('other-model',), *prepared[0][1:]))


def test_semantic_similarity_never_proves_missing_mandatory_skill():
    result = score_candidate(job(), NS(**parse_resume('Finley Grey\nSkills\nPython\nProjects\nPersonal API project.')), 100, [])
    assert 'FastAPI' in result['explanation']['missing_required']
    assert result['explanation']['uncertain_requirements']
    assert result['experience_score'] == 50


def test_inference_failure_is_explicit():
    model = FakeModel()
    model.encode = Mock(side_effect=RuntimeError('private internal diagnostic'))
    with pytest.raises(semantic.SemanticError, match='inference failed') as error:
        semantic.EmbeddingCache().encode(model, ('mpnet',), ['Python'])
    assert 'private internal' not in str(error.value)


def test_load_failure_does_not_silently_fall_back(monkeypatch):
    import sentence_transformers
    factory=Mock(side_effect=OSError('private diagnostic'))
    monkeypatch.setattr(sentence_transformers,'SentenceTransformer',factory)
    semantic.clear_caches()
    try:
        with pytest.raises(semantic.SemanticError,match='could not be loaded') as error:
            semantic.get_model(semantic.MPNET)
        assert factory.call_count==1
        assert factory.call_args.args[0]==semantic.MPNET
        assert 'private diagnostic' not in str(error.value)
    finally: semantic.clear_caches()


@pytest.mark.integration
@pytest.mark.skipif(__import__('os').environ.get('RUN_MODEL_TESTS') != '1', reason='Opt in to real cached-model inference with RUN_MODEL_TESTS=1')
@pytest.mark.parametrize('identifier,dimensions', [(semantic.MPNET,768),(semantic.MINILM,384)])
def test_real_model_dimensions_normalization_and_similarity(identifier,dimensions):
    model = semantic.get_model(identifier)
    vectors = model.encode(['Build Python backend APIs.', 'Build Python backend APIs.', 'Design watercolor landscape paintings.'], normalize_embeddings=True)
    assert vectors.shape == (3,dimensions)
    assert np.allclose(np.linalg.norm(vectors,axis=1),1,atol=1e-5)
    assert float(vectors[0] @ vectors[1]) == pytest.approx(1,abs=1e-5)
    assert float(vectors[0] @ vectors[1]) > float(vectors[0] @ vectors[2])
    passages = semantic.token_chunks(model, 'Python backend APIs. '*400+'zebra', 'experience')
    assert len(passages)>1
    assert all(len(model.tokenizer.encode(p.text, add_special_tokens=True)) <= model.max_seq_length for p in passages)
    assert 'zebra' in passages[-1].text.lower()
