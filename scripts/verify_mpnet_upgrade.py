"""Real HTTP + PostgreSQL + both models + restart/rematch verification.

Creates a separate, uniquely named synthetic verification database. Preserves
the live application's jobs/results. Requires the local PostgreSQL instance.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from uuid import uuid4
import httpx
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
os.chdir(ROOT/'backend')
from app.core.config import settings

MINILM='sentence-transformers/all-MiniLM-L6-v2'
MPNET='sentence-transformers/all-mpnet-base-v2'
ARTIFACTS=ROOT/'test-artifacts'


def poll(client,path,field,active,timeout=600):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        response=client.get(path);response.raise_for_status();data=response.json()
        if data[field] not in active:return data
        time.sleep(.5)
    raise TimeoutError('Background operation timed out.')


def start_server(model,env,port,log):
    environment={**env,'EMBEDDING_MODEL':model,'HF_HUB_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false'}
    process=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],
        cwd=ROOT/'backend',env=environment,stdout=log,stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        if process.poll() is not None:raise RuntimeError('Verification API exited; inspect the private verification log.')
        try:
            data=httpx.get(f'http://127.0.0.1:{port}/api/v1/health',timeout=2)
            if data.status_code==200 and data.json()['semantic_model']==model:return process
        except httpx.HTTPError:pass
        time.sleep(.5)
    stop_server(process)
    raise TimeoutError('Verification API did not become ready.')


def stop_server(process):
    if process and process.poll() is None:
        process.terminate()
        try:process.wait(timeout=15)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)


def main():
    ARTIFACTS.mkdir(exist_ok=True)
    url=make_url(settings.database_url)
    database='resume_mpnet_verify_'+uuid4().hex[:10]
    connection={'host':url.host,'port':url.port or 5432,'user':url.username,'password':url.password,'connect_timeout':5}
    with psycopg.connect(**connection,dbname='postgres',autocommit=True) as db:
        db.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
    environment={**os.environ,'DATABASE_URL':url.set(database=database).render_as_string(hide_password=False),
        'UPLOAD_DIR':str(ARTIFACTS/'mpnet-private-uploads')}
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT/'backend',env=environment,check=True)
    subprocess.run([sys.executable,'-m','alembic','check'],cwd=ROOT/'backend',env=environment,check=True)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    report={'database':database,'jobs':[],'checks':[]}
    process=None
    with (ARTIFACTS/'mpnet-integration-server.log').open('w',encoding='utf-8') as log:
        try:
            process=start_server(MINILM,environment,port,log)
            with httpx.Client(base_url=f'http://127.0.0.1:{port}/api/v1',timeout=90) as client:
                for slug,title in [('python_backend','Python Backend Developer'),('react_fullstack','React Full Stack Developer'),('ai_ml','AI/ML Engineer')]:
                    text=(ROOT/'sample_data/job_descriptions'/f'{slug}.txt').read_text()
                    response=client.post('/jobs',json={'title':title,'raw_text':text});response.raise_for_status()
                    job_id=response.json()['id']
                    files=[('files',(p.name,p.read_bytes())) for p in sorted((ROOT/'sample_data/synthetic_resumes').iterdir()) if p.suffix in {'.pdf','.docx'}]
                    upload=client.post('/jobs/'+job_id+'/resumes',files=files);upload.raise_for_status()
                    batch=poll(client,'/batches/'+upload.json()['id'],'status',{'pending','processing'})
                    assert batch['processed_files']==12 and batch['failed_files']==0,batch
                    client.post('/jobs/'+job_id+'/match').raise_for_status()
                    assert poll(client,'/jobs/'+job_id,'match_status',{'processing'})['match_status']=='completed'
                    baseline=client.get('/jobs/'+job_id+'/rankings').json()
                    assert baseline['total']==12
                    assert all(r['embedding_model']==MINILM for r in baseline['items'])
                    report['jobs'].append({'job':slug,'job_id':job_id,'baseline':{r['candidate_id']:r['overall_score'] for r in baseline['items']}})
            stop_server(process)
            process=start_server(MPNET,environment,port,log)
            with httpx.Client(base_url=f'http://127.0.0.1:{port}/api/v1',timeout=90) as client:
                for item in report['jobs']:
                    endpoint='/jobs/'+item['job_id']
                    # The saved baseline remains intact after selecting a different model.
                    before=client.get(endpoint+'/rankings').json()
                    assert all(r['embedding_model']==MINILM for r in before['items'])
                    for _ in range(2):
                        client.post(endpoint+'/match').raise_for_status()
                        final=poll(client,endpoint,'match_status',{'processing'})
                        assert final['match_status']=='completed',final['match_error']
                    ranking=client.get(endpoint+'/rankings').json()
                    assert ranking['total']==12
                    scores=[r['overall_score'] for r in ranking['items']]
                    assert scores==sorted(scores,reverse=True)
                    for result in ranking['items']:
                        assert result['embedding_model']==MPNET
                        assert result['scoring_config']['semantic']['embedding_dimensions']==768
                        assert result['run_id'] and result['algorithm_version']=='2.0.0-section-aware'
                        explanation=result['explanation']
                        assert 0<=result['overall_score']<=100 and 0<=result['semantic_score']<=100
                        assert abs(sum(explanation['contributions'].values())-result['overall_score'])<=.011
                        history=client.get(endpoint+'/matches/'+result['candidate_id']+'/history').json()
                        assert len(history)==2
                        legacy=next(h for h in history if h['embedding_model']==MINILM)
                        assert legacy['payload']['overall_score']==item['baseline'][result['candidate_id']]
                        assert history[0]['scoring_config']['default_weights']=={'semantic':.25,'skill':.4,'experience':.25,'education':.1}
                    item['saved_mpnet']={r['candidate_id']:r['overall_score'] for r in ranking['items']}
                    item['top_candidate']=ranking['items'][0]['candidate']['name']
                    item['top_score']=ranking['items'][0]['overall_score']
                    print(item['job'],'MPNet leader:',item['top_candidate'],item['top_score'],flush=True)
            stop_server(process)
            # A new OS process verifies persistence, not just a new HTTP client.
            process=start_server(MPNET,environment,port,log)
            with httpx.Client(base_url=f'http://127.0.0.1:{port}/api/v1',timeout=20) as client:
                for item in report['jobs']:
                    ranking=client.get('/jobs/'+item['job_id']+'/rankings').json()
                    assert {r['candidate_id']:r['overall_score'] for r in ranking['items']}==item['saved_mpnet']
            with psycopg.connect(**connection,dbname=database) as db:
                counts=db.execute('SELECT (SELECT count(*) FROM candidates), (SELECT count(*) FROM match_results), (SELECT count(*) FROM match_result_history), (SELECT count(*) FROM matching_runs)').fetchone()
                assert counts==(36,36,72,9),counts
                assert db.execute("SELECT data_type FROM information_schema.columns WHERE table_name='matching_runs' AND column_name='scoring_config'").fetchone()==('jsonb',)
                report['counts']={'candidates':counts[0],'current_results':counts[1],'history_snapshots':counts[2],'runs':counts[3]}
            report['checks']=['Both models generated actual embeddings','36 mixed PDF/DOCX candidates processed','MiniLM results survive model selection change','MiniLM snapshots preserved on MPNet rematch','Second MPNet rematch creates no duplicate pairs','36 scores persist after OS process restart','PostgreSQL JSONB provenance and migration consistency verified']
            (ARTIFACTS/'mpnet-integration-report.json').write_text(json.dumps(report,indent=2))
            print('PASS:',report['counts'], '; actual API restart, provenance, historical scores and duplicate-free rematching verified.')
        finally:stop_server(process)


if __name__=='__main__':main()
