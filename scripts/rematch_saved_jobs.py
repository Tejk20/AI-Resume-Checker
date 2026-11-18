"""Rematch saved jobs without uploading copies; verify every old result is archived."""
import time
import httpx


def all_pages(client,path):
    items=[]
    while True:
        response=client.get(path,params={'offset':len(items),'limit':100});response.raise_for_status()
        data=response.json();items.extend(data['items'])
        if len(items)>=data['total']:return items


def main():
    total=0
    with httpx.Client(base_url='http://127.0.0.1:8000/api/v1',timeout=30) as client:
        health=client.get('/health');health.raise_for_status()
        model=health.json()['semantic_model']
        for job in all_pages(client,'/jobs'):
            endpoint='/jobs/'+job['id']
            candidates=client.get(endpoint+'/candidates').json()['total']
            if not candidates:continue
            before={r['candidate_id']:r for r in all_pages(client,endpoint+'/rankings')}
            response=client.post(endpoint+'/match');response.raise_for_status()
            deadline=time.monotonic()+600
            while time.monotonic()<deadline:
                state=client.get(endpoint).json()
                if state['match_status']!='processing':break
                time.sleep(1)
            assert state['match_status']=='completed',state.get('match_error')
            results=all_pages(client,endpoint+'/rankings')
            assert len(results)==candidates
            assert len({r['candidate_id'] for r in results})==len(results)
            for result in results:
                assert result['embedding_model']==model
                assert result['algorithm_version']=='2.0.0-section-aware'
                assert result['scoring_config']['semantic']['embedding_dimensions']==768 if model.endswith('all-mpnet-base-v2') else True
                old=before.get(result['candidate_id'])
                if old:
                    history=client.get(endpoint+'/matches/'+result['candidate_id']+'/history',params={'limit':100}).json()
                    assert any(h['embedding_model']==old['embedding_model'] and h['payload']['overall_score']==old['overall_score'] for h in history)
            total+=len(results)
            print('Refreshed job',job['id'],':',len(results),'results; previous scores archived.',flush=True)
    print('PASS:',total,'current results use',model,'with historical scores retained.')


if __name__=='__main__':main()
