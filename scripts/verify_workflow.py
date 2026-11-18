"""Real embeddings + HTTP upload + durable database integration, no mocked scores.
Run after migrations with backend running. Uses synthetic documents only.
"""
import json
import time
import sys
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
API='http://127.0.0.1:8000/api/v1'


def wait(client,path,field,active,timeout=600):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        response=client.get(path);response.raise_for_status();data=response.json()
        if data[field] not in active:return data
        time.sleep(1)
    raise TimeoutError('Background operation did not complete within 10 minutes.')


def main():
    report=[]
    with httpx.Client(base_url=API,timeout=90) as client:
        health=client.get('/health');health.raise_for_status()
        for slug in ['python_backend','react_fullstack','ai_ml']:
            raw=(ROOT/'sample_data/job_descriptions'/f'{slug}.txt').read_text()
            response=client.post('/jobs',json={'title':raw.splitlines()[0].split(' with ')[0][:150],'raw_text':raw})
            response.raise_for_status();job=response.json();jid=job['id']
            files=[('files',(p.name,p.read_bytes())) for p in sorted((ROOT/'sample_data/synthetic_resumes').glob('*')) if p.suffix in ['.pdf','.docx']]
            response=client.post(f'/jobs/{jid}/resumes',files=files);response.raise_for_status()
            batch=wait(client,'/batches/'+response.json()['id'],'status',['pending','processing'])
            assert batch['processed_files']==12 and batch['failed_files']==0,batch
            response=client.post(f'/jobs/{jid}/match');response.raise_for_status()
            final=wait(client,f'/jobs/{jid}','match_status',['processing'])
            assert final['match_status']=='completed',final['match_error']
            ranking=client.get(f'/jobs/{jid}/rankings').json()
            assert ranking['total']==12
            scores=[r['overall_score'] for r in ranking['items']]
            assert scores==sorted(scores,reverse=True) and all(0<=s<=100 for s in scores)
            for result in ranking['items']:
                e=result['explanation']
                assert abs(sum(e['contributions'].values())-result['overall_score'])<=.011
                assert abs(sum(e['weights'].values())-1)<1e-9
                assert e['semantic_evidence'],'No real semantic evidence generated'
                detail=client.get(f"/jobs/{jid}/matches/{result['candidate_id']}");detail.raise_for_status()
                candidate=client.get('/candidates/'+result['candidate_id']);candidate.raise_for_status()
            top=ranking['items'][0]
            print(slug,'top:',top['candidate']['name'],'score:',top['overall_score'])
            report.append(dict(job=slug,job_id=jid,processed=12,top_candidate=top['candidate']['name'],top_score=top['overall_score'],
                               bottom_candidate=ranking['items'][-1]['candidate']['name'],bottom_score=scores[-1]))
        assert len({r['top_candidate'] for r in report})==3,'Different JDs must select different strong profiles.'
        # New HTTP client verifies state survives a client/browser refresh.
    with httpx.Client(base_url=API) as client:
        for item in report: assert client.get('/jobs/'+item['job_id']+'/rankings').json()['total']==12
    output=ROOT/'test-artifacts';output.mkdir(exist_ok=True)
    (output/'workflow-report.json').write_text(json.dumps(report,indent=2))
    print('PASS: three JDs × 12 resumes; persisted results, genuine embeddings, bounded sorted scores, reconciling contributions.')


if __name__=='__main__':main()
