from types import SimpleNamespace
import numpy as np
import pytest
from app.services.onnx_embeddings import OnnxMPNet
from app.services import semantic
from app.core.config import settings


def test_onnx_mean_pooling_normalization_and_bounded_passages():
    model = OnnxMPNet.__new__(OnnxMPNet)
    model.tokenizer = SimpleNamespace(encode=lambda text: [0, 3, 2])
    model.inputs = {'input_ids', 'attention_mask'}
    calls = []
    def run(outputs, feed):
        calls.append(feed)
        tokens = np.zeros((1, 3, 768), dtype=np.float32)
        tokens[0, :, 0] = [1, 2, 3]
        tokens[0, :, 1] = [3, 2, 1]
        return [tokens]
    model.session = SimpleNamespace(run=run)
    vectors = model.encode(['Python APIs', 'Python APIs'], batch_size=32)
    assert vectors.shape == (2, 768)
    assert len(calls) == 2
    assert set(calls[0]) == {'input_ids', 'attention_mask'}
    assert np.all(calls[0]['attention_mask'] == 1)
    assert np.allclose(vectors[:, :2], 1 / np.sqrt(2))
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1)
    unnormalized = model.encode(['Python'], normalize_embeddings=False)
    assert np.array_equal(unnormalized[0, :2], [2, 2])


def test_onnx_deployment_never_silently_changes_model(monkeypatch):
    semantic.clear_caches()
    monkeypatch.setattr(settings, 'embedding_backend', 'onnx-int8')
    with pytest.raises(semantic.SemanticError, match='could not be loaded'):
        semantic.get_model(semantic.MINILM)
    semantic.clear_caches()
