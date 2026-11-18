from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from app.core.config import Settings
from app.services.frontend import mount_frontend


def test_hosted_frontend_routes_assets_and_api_boundaries(tmp_path):
    (tmp_path/'index.html').write_text('<html>Resume Checker</html>')
    (tmp_path/'assets').mkdir()
    (tmp_path/'assets/app.js').write_text('console.log("app")')
    app=FastAPI()
    @app.get('/api/v1/health')
    def health():return {'status':'ok'}
    mount_frontend(app,tmp_path)
    with TestClient(app) as client:
        assert 'Resume Checker' in client.get('/').text
        assert 'Resume Checker' in client.get('/rankings').text
        assert client.get('/assets/app.js').status_code==200
        assert client.get('/api/v1/health').json()=={'status':'ok'}
        assert client.get('/api/v1/nonexistent').status_code==404
        assert client.get('/missing.js').status_code==404
        assert client.get('/%2e%2e/secret.txt').status_code==404


def test_hosted_config_and_missing_build(tmp_path):
    assert Settings(_env_file=None,database_url='postgres://user:pass@db/app').database_url=='postgresql+psycopg://user:pass@db/app'
    assert Settings(_env_file=None,database_url='postgresql://user:pass@db/app').database_url=='postgresql+psycopg://user:pass@db/app'
    with pytest.raises(RuntimeError,match='compiled frontend'):
        mount_frontend(FastAPI(),tmp_path)
