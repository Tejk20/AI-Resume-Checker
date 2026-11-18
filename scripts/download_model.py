"""Run once with network access; subsequent inference uses the local cache."""
import sys
import os
os.environ.setdefault('HF_HUB_DISABLE_XET','1')
from pathlib import Path
backend=Path(__file__).resolve().parents[1]/'backend'
os.chdir(backend)
sys.path.insert(0,str(backend))
from app.services.semantic import get_model
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--model', help='Optional model identifier; defaults to EMBEDDING_MODEL.')
args=parser.parse_args()
model=get_model(args.model)
vectors=model.encode(['Build reliable backend APIs.','Develop dependable web services.'],normalize_embeddings=True)
print('Model loaded:',vectors.shape[1],'dimensions;',model.max_seq_length,'maximum tokens; real cosine:',round(float(vectors[0]@vectors[1]),4))
