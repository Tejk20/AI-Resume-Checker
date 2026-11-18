FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_URL=/api/v1
RUN npm run build

FROM python:3.12-slim-bookworm AS application
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 USE_TF=0 TOKENIZERS_PARALLELISM=false \
    HF_HUB_DISABLE_XET=1 MODEL_CACHE=/app/.model-cache \
    EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2 \
    EMBEDDING_BATCH_SIZE=8 EMBEDDING_CACHE_MB=32 \
    FRONTEND_DIST=/app/frontend/dist UPLOAD_DIR=/app/storage/uploads \
    OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 PORT=8000
WORKDIR /app
# CPU wheels avoid installing large CUDA libraries on a CPU-only host.
RUN python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
COPY backend/requirements.txt ./backend/requirements.txt
RUN python -m pip install -r backend/requirements.txt
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY sample_data/ ./sample_data/
COPY --from=frontend /frontend/dist ./frontend/dist
RUN python scripts/download_model.py \
    && useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/storage/uploads \
    && chown -R appuser:appuser /app
ENV HF_HUB_OFFLINE=1
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=90s --retries=6 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/api/v1/health',timeout=4)"
CMD ["python", "scripts/start_hosted.py"]
