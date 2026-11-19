"""CPU MPNet inference without importing PyTorch or Sentence Transformers.

Uses the official quantized Transformer, attention-mask mean pooling and L2
normalization. Quantization is approximate and is recorded in result metadata.
"""
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np


class TokenizerAdapter:
    def __init__(self, path):
        from tokenizers import Tokenizer
        self.tokenizer = Tokenizer.from_file(str(path))
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()

    def encode(self, text, add_special_tokens=True, **kwargs):
        return self.tokenizer.encode(text, add_special_tokens=add_special_tokens).ids

    def decode(self, ids, skip_special_tokens=True):
        return self.tokenizer.decode(ids, skip_special_tokens=skip_special_tokens)

    def num_special_tokens_to_add(self, pair=False):
        return self.tokenizer.num_special_tokens_to_add(pair)


class OnnxMPNet:
    max_seq_length = 384

    def __init__(self, directory):
        import onnxruntime as ort
        directory = Path(directory)
        manifest = json.loads((directory/'manifest.json').read_text())
        self.revision = manifest['revision']
        self.tokenizer = TokenizerAdapter(directory/'tokenizer.json')
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.enable_cpu_mem_arena = False
        options.enable_mem_pattern = False
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        options.add_session_config_entry('session.disable_prepacking', '1')
        self.session = ort.InferenceSession(str(directory/'model.onnx'), options,
                                           providers=['CPUExecutionProvider'])
        self.inputs = {item.name for item in self.session.get_inputs()}

    def __getitem__(self, index):
        if index != 0:
            raise IndexError(index)
        return SimpleNamespace(auto_model=SimpleNamespace(config=SimpleNamespace(_commit_hash=self.revision)))

    def encode(self, texts, batch_size=1, normalize_embeddings=True, **kwargs):
        # One passage at a time bounds transient attention memory even for 50 resumes.
        rows = []
        for text in texts:
            ids = self.tokenizer.encode(text)[:self.max_seq_length]
            values = np.asarray([ids], dtype=np.int64)
            mask = np.ones_like(values)
            feed = {'input_ids': values, 'attention_mask': mask,
                    'token_type_ids': np.zeros_like(values)}
            tokens = self.session.run(None, {k:v for k,v in feed.items() if k in self.inputs})[0]
            vector = tokens[0].mean(axis=0, dtype=np.float32)
            if normalize_embeddings:
                vector /= max(float(np.linalg.norm(vector)), 1e-12)
            rows.append(vector)
        return np.asarray(rows, dtype=np.float32).reshape(-1, 768)
