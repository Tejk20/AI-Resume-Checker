import time
from uuid import uuid4
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alembic.config import Config
from alembic import command
from app.core.database import get_db
from app.core.config import settings
from app import main
from app.services import workers
from app.services.workers import process_batch


@pytest.fixture
def client(tmp_path,monkeypatch):
    url='sqlite:///'+str(tmp_path/'api.db')
    engine=create_engine(url,connect_args={'check_same_thread':False})
    # Exercise the committed migration, not metadata.create_all.
    monkeypatch.setattr('app.core.database.engine',engine)
    command.upgrade(Config('alembic.ini'),'head')
    factory=sessionmaker(engine,expire_on_commit=False)
    monkeypatch.setattr(workers,'SessionLocal',factory)
    monkeypatch.setattr(main,'engine',engine)
    monkeypatch.setattr(settings,'upload_dir',tmp_path/'uploads')
    def db():
        with factory() as session:yield session
    main.app.dependency_overrides[get_db]=db
    # Synchronous unit worker avoids races; real executor tested in integration script.
    def submit(fn,*args):
        try:return fn(*args)
        finally:workers.SLOTS.release()
    monkeypatch.setattr('app.api.routes.submit_reserved',submit)
    with TestClient(main.app) as test_client:yield test_client
    main.app.dependency_overrides.clear()
    engine.dispose()


def create(client):
    return client.post('/api/v1/jobs',json={'title':'Python Backend Developer','raw_text':'Required Python FastAPI. Build reliable backend services with at least 2 years of experience.'}).json()


def test_job_crud_and_validation(client):
    j=create(client); assert 'id' in j
    assert client.get('/api/v1/jobs/'+j['id']).status_code==200
    assert client.get('/api/v1/jobs').json()['total']==1
    assert client.patch('/api/v1/jobs/'+j['id'],json={'required_skills':['Python'],'min_experience':None}).json()['min_experience'] is None
    assert client.get('/api/v1/jobs/not-a-uuid').status_code==422
    assert client.get('/api/v1/jobs/'+str(uuid4())).status_code==404
    assert client.post('/api/v1/jobs',json={'title':'','raw_text':'x'}).status_code==422
    assert client.get('/api/v1/health').json()['database']=='connected'


def test_partial_batch_and_candidate_detail(client):
    j=create(client)
    root=Path(__file__).resolve().parents[2]/'sample_data/synthetic_resumes'
    paths=sorted([*root.glob('*.pdf'),*root.glob('*.docx')])
    assert len(paths)==12,'Generate synthetic samples before tests.'
    files=[('files',(p.name,p.read_bytes())) for p in paths]+[('files',('invalid.pdf',b'not a pdf'))]
    response=client.post('/api/v1/jobs/'+j['id']+'/resumes',files=files)
    assert response.status_code==202
    batch=client.get('/api/v1/batches/'+response.json()['id']).json()
    assert batch['processed_files']==12 and batch['failed_files']==1
    assert batch['status']=='partially_completed'
    candidates=client.get('/api/v1/jobs/'+j['id']+'/candidates').json()
    assert candidates['total']==12
    detail=client.get('/api/v1/candidates/'+candidates['items'][0]['id']).json()
    assert detail['original_filename'] and 'raw_text' not in detail
    assert 'email' not in candidates['items'][0]
    assert client.get('/api/v1/jobs/'+j['id']+'/rankings').json()['total']==0


def test_limits_and_missing_matches(client):
    j=create(client)
    assert client.post('/api/v1/jobs/'+j['id']+'/match').status_code==422
    assert client.get('/api/v1/jobs/'+j['id']+'/matches/'+str(uuid4())).status_code==404
    assert client.get('/api/v1/jobs/'+j['id']+'/rankings?sort=unsafe').status_code==422
    assert client.get('/api/v1/jobs?offset=-1').status_code==422
    response=client.post('/api/v1/jobs/'+j['id']+'/resumes',files=[('files',('a.exe',b'bad'))]*51)
    assert response.status_code==422


def test_rematching_provenance_history_and_atomic_failure(client,monkeypatch):
    from app.services.semantic import SemanticError
    class Evaluation:
        model_id = 'sentence-transformers/all-mpnet-base-v2'
        metadata = {'embedding_dimensions':768,'pipeline_version':'section-evidence-v2'}
        def __init__(self, job): pass
        def prepare_many(self, candidates): return [None]*len(candidates)
        def compare_prepared(self, prepared): return 80, [{'requirement':'Build APIs','evidence':'Built APIs','similarity':80}]
    monkeypatch.setattr(workers,'SemanticEvaluation',Evaluation)
    j=create(client)
    path=next((Path(__file__).resolve().parents[2]/'sample_data/synthetic_resumes').glob('*.pdf'))
    upload=client.post('/api/v1/jobs/'+j['id']+'/resumes',files=[('files',(path.name,path.read_bytes()))])
    assert client.get('/api/v1/batches/'+upload.json()['id']).json()['processed_files']==1
    endpoint='/api/v1/jobs/'+j['id']
    for _ in range(2):
        response=client.post(endpoint+'/match')
        assert response.status_code==202 and response.json()['run_id']
    results=client.get(endpoint+'/rankings').json()
    assert results['total']==1
    result=results['items'][0]
    assert result['embedding_model']==Evaluation.model_id
    assert result['scoring_config']['default_weights']=={'semantic':.25,'skill':.4,'experience':.25,'education':.1}
    assert result['run_id']
    history=client.get(endpoint+'/matches/'+result['candidate_id']+'/history').json()
    assert len(history)==1 and history[0]['payload']['overall_score']==result['overall_score']
    runs=client.get(endpoint+'/runs').json()
    assert len(runs)==2 and all(r['status']=='completed' for r in runs)
    Evaluation.compare_prepared=lambda *args: (_ for _ in ()).throw(SemanticError('Embedding inference failed.'))
    assert client.post(endpoint+'/match').status_code==202
    assert client.get(endpoint).json()['match_status']=='failed'
    assert client.get(endpoint+'/rankings').json()['items'][0]['run_id']==result['run_id']
    assert len(client.get(endpoint+'/runs').json())==3
    client.patch(endpoint,json={'required_skills':['Python']})
    assert client.get(endpoint+'/rankings').json()['total']==0
    assert len(client.get(endpoint+'/matches/'+result['candidate_id']+'/history').json())==2
