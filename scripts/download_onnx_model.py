"""Download only the pinned official MPNet quantized weights and tokenizer."""
import hashlib
import json
import os
from pathlib import Path
import shutil
from huggingface_hub import hf_hub_download

MODEL = 'sentence-transformers/all-mpnet-base-v2'
REVISION = 'e8c3b32edf5434bc2275fc9bab85f82640a19130'
WEIGHTS = 'onnx/model_quint8_avx2.onnx'
SHA256 = 'aa5c27172d77bbd1cbae3628cbac4b26d7c12adabff25d2d4285d0f29159b237'


def main():
    destination = Path(os.getenv('ONNX_MODEL_DIR', '.model-cache/onnx-mpnet'))
    destination.mkdir(parents=True, exist_ok=True)
    for source, target in [(WEIGHTS, 'model.onnx'), ('tokenizer.json', 'tokenizer.json')]:
        cached = Path(hf_hub_download(MODEL, source, revision=REVISION))
        if source == WEIGHTS:
            with cached.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if digest != SHA256:
                raise RuntimeError('Official ONNX weight checksum did not match.')
        shutil.copyfile(cached, destination/target)
    (destination/'manifest.json').write_text(json.dumps({
        'model': MODEL, 'revision': REVISION, 'source': WEIGHTS,
        'precision': 'int8', 'sha256': SHA256,
    }, indent=2))
    print('Pinned MPNet ONNX model ready:', destination)


if __name__ == '__main__':
    main()
