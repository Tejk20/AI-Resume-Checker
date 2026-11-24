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
    endpoint='/api/v1/jobs/'+j['id']
    upload = client.post(endpoint + '/resumes?rank_after_upload=true', files=[
        ('files', (path.name, path.read_bytes())),
        ('files', ('invalid.pdf', b'not a pdf')),
    ])
    assert upload.status_code == 202
    batch = client.get('/api/v1/batches/' + upload.json()['id']).json()
    assert batch['status'] == 'partially_completed'
    assert client.get(endpoint + '/rankings').json()['total'] == 1
    response = client.post(endpoint + '/match')
    assert response.status_code == 202 and response.json()['run_id']
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


def signup_account(client, label='recruiter'):
    response=client.post('/api/v1/auth/signup',json={'name':'Test Recruiter',
        'email':f'{label}-{uuid4().hex}@example.test','password':'Fictional-Test-Passphrase-42'})
    assert response.status_code==201,response.text
    assert 'password' not in response.text
    assert 'httponly' in response.headers['set-cookie'].lower()
    return response.json()['user']


def test_signup_login_logout_expiry_and_password_storage(client,monkeypatch):
    from datetime import timedelta
    from sqlalchemy import select
    from app.models import User, AuthSession
    from app.models.entities import now
    monkeypatch.setattr(settings,'auth_required',True)
    account=signup_account(client)
    assert client.get('/api/v1/auth/me').json()['user']['id']==account['id']
    with workers.SessionLocal() as db:
        stored=db.scalar(select(User).where(User.email==account['email']))
        assert stored.password_hash.startswith('pbkdf2_sha256$600000$')
        assert 'Fictional-Test-Passphrase' not in stored.password_hash
    assert client.post('/api/v1/auth/signup',json={'name':'Other Name','email':account['email'].upper(),
        'password':'Different-Passphrase-42'}).status_code==409
    assert client.post('/api/v1/auth/logout').status_code==204
    assert client.get('/api/v1/auth/me').json()['user'] is None
    credentials={'email':account['email'],'password':'Incorrect-Passphrase-42'}
    assert client.post('/api/v1/auth/login',json=credentials).status_code==401
    credentials['password']='Fictional-Test-Passphrase-42'
    assert client.post('/api/v1/auth/login',json=credentials).status_code==200
    with workers.SessionLocal() as db:
        for session in db.scalars(select(AuthSession)):
            session.expires_at=now()-timedelta(seconds=1)
        db.commit()
    assert client.get('/api/v1/auth/me').json()['user'] is None


def test_account_isolation_covers_jobs_batches_candidates_and_dashboard(client,monkeypatch):
    monkeypatch.setattr(settings,'auth_required',True)
    assert client.post('/api/v1/jobs',json={'title':'Private job','raw_text':'Build reliable Python backend services.'}).status_code==401
    owner = signup_account(client,'first')
    job=create(client); endpoint='/api/v1/jobs/'+job['id']
    path=next((Path(__file__).resolve().parents[2]/'sample_data/synthetic_resumes').glob('*.pdf'))
    batch=client.post(endpoint+'/resumes',files=[('files',(path.name,path.read_bytes()))]).json()
    cid=client.get(endpoint+'/candidates').json()['items'][0]['id']
    assert client.get('/api/v1/dashboard').json()['total_resumes']==1
    board = '/api/v1/public-jobs'
    publication = endpoint + '/publication'
    assert client.get(board).json() == []
    assert client.put(publication, json={'is_published': True}).json()['is_published'] is True
    public_listing = {'id': job['id'], 'title': job['title'], 'raw_text': job['raw_text']}
    assert client.post('/api/v1/auth/logout').status_code==204
    assert client.get(board).json() == [public_listing]
    assert client.put(publication, json={'is_published': False}).status_code == 401
    signup_account(client,'second')
    assert client.get(board).json() == [public_listing]
    assert client.put(publication, json={'is_published': False}).status_code == 404
    assert client.get('/api/v1/jobs').json()['total']==0
    assert client.get('/api/v1/dashboard').json()['total_resumes']==0
    for route in [endpoint,endpoint+'/candidates',endpoint+'/rankings',endpoint+'/runs',
                  endpoint+'/matches/'+cid,endpoint+'/matches/'+cid+'/history',
                  '/api/v1/candidates/'+cid,'/api/v1/batches/'+batch['id']]:
        assert client.get(route).status_code==404,route
    assert client.patch(endpoint,json={'required_skills':['SQL']}).status_code==404
    assert client.post(endpoint+'/match').status_code==404
    assert client.post(endpoint+'/resumes',files=[('files',(path.name,path.read_bytes()))]).status_code==404
    assert client.post('/api/v1/auth/logout').status_code == 204
    assert client.post('/api/v1/auth/login', json={
        'email': owner['email'], 'password': 'Fictional-Test-Passphrase-42',
    }).status_code == 200
    assert client.put(publication, json={'is_published': False}).json()['is_published'] is False
    assert client.get(board).json() == []


def test_public_sample_is_readable_but_not_editable_and_cross_site_auth_is_blocked(client,monkeypatch):
    from app.models import Job
    monkeypatch.setattr(settings,'auth_required',True)
    with workers.SessionLocal() as db:
        job=Job(title='Fictional Sample Role',raw_text='Build Python systems with relevant experience.',is_demo=True)
        db.add(job); db.commit(); jid=str(job.id)
    endpoint='/api/v1/jobs/'+jid
    assert client.get('/api/v1/jobs').json()['items'][0]['is_demo'] is True
    assert client.get(endpoint).status_code==200
    assert client.get(endpoint+'/rankings').status_code==200
    signup_account(client)
    assert client.patch(endpoint,json={'required_skills':['SQL']}).status_code==403
    assert client.post(endpoint+'/match').status_code==403
    assert client.post('/api/v1/auth/logout',headers={'Origin':'https://unrelated.example'}).status_code==403
    assert client.get('/api/v1/auth/me').json()['user'] is not None
    assert client.post('/api/v1/auth/signup',json={'name':'Test User','email':'invalid','password':'short'}).status_code==422


def test_demo_seed_is_idempotent_and_produces_scored_records(client,monkeypatch):
    from app.services import demo
    from sqlalchemy import select, func
    from app.models import Job, Candidate, MatchResult
    class Evaluation:
        model_id='test-only-model'
        metadata={'embedding_dimensions':768}
        def __init__(self,job):pass
        def prepare_many(self,candidates):return [None]*len(candidates)
        def compare_prepared(self,item):return 80,[{'requirement':'Build systems','evidence':'Built systems','similarity':80}]
    monkeypatch.setattr(workers,'SemanticEvaluation',Evaluation)
    monkeypatch.setattr(demo,'SessionLocal',workers.SessionLocal)
    demo.seed_demo(); demo.seed_demo()
    with workers.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Job))==3
        assert db.scalar(select(func.count()).select_from(Candidate))==36
        assert db.scalar(select(func.count()).select_from(MatchResult))==36
    stats=client.get('/api/v1/dashboard').json()
    assert stats['total_jobs']==3 and stats['total_evaluated']==36
    assert stats['average_score']>0 and sum(b['count'] for b in stats['distribution'])==36


def test_sample_copy_is_private_empty_and_accepts_the_recruiters_resume(client,monkeypatch):
    from app.models import Job
    monkeypatch.setattr(settings,'auth_required',True)
    with workers.SessionLocal() as db:
        sample=Job(title='Sample Python Role',raw_text='Build reliable Python and FastAPI services.',
                   required_skills=['Python','FastAPI'],preferred_skills=['Docker'],
                   min_experience=3,qualifications=['Bachelor degree'],
                   responsibilities=['Build backend APIs'],is_demo=True)
        db.add(sample); db.commit(); source_id=str(sample.id)
    source='/api/v1/jobs/'+source_id
    assert client.post(source+'/copy').status_code==401
    signup_account(client,'copy-owner')
    response=client.post(source+'/copy')
    assert response.status_code==201,response.text
    copy=response.json(); target='/api/v1/jobs/'+copy['id']
    assert copy['id']!=source_id and copy['is_demo'] is False
    assert copy['required_skills']==['Python','FastAPI']
    assert copy['min_experience']==3 and copy['match_status']=='idle'
    assert client.get(target+'/candidates').json()['total']==0
    assert client.get(target+'/rankings').json()['total']==0
    path=next((Path(__file__).resolve().parents[2]/'sample_data/synthetic_resumes').glob('*.pdf'))
    assert client.post(target+'/resumes',files=[('files',(path.name,path.read_bytes()))]).status_code==202
    assert client.get(target+'/candidates').json()['total']==1
    assert client.get(source+'/candidates').json()['total']==0
    assert client.get(source).json()['is_demo'] is True
    client.patch(target,json={'required_skills':['SQL']})
    assert client.get(source).json()['required_skills']==['Python','FastAPI']
    client.post('/api/v1/auth/logout')
    assert client.get(target).status_code==404
    signup_account(client,'different-owner')
    assert client.post(target+'/copy').status_code==404
