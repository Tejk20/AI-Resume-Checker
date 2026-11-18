"""One-process hosted startup: migrate before starting the same-origin web app."""
import os
from pathlib import Path
import sys

backend = Path(__file__).resolve().parents[1] / 'backend'
os.chdir(backend)
sys.path.insert(0, str(backend))

from alembic import command
from alembic.config import Config
import uvicorn

command.upgrade(Config('alembic.ini'), 'head')
uvicorn.run('app.main:app', host='0.0.0.0', port=int(os.environ.get('PORT', '8000')), workers=1)
