"""Verify saved rankings and retained baselines across algorithm/model upgrades."""
import argparse
import json
import time
from pathlib import Path
import httpx
import psycopg

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--rematch', action='store_true')
args = parser.parse_args()
report = json.loads((ROOT/'test-artifacts/workflow-report.json').read_text())


def rankings(client, endpoint):
    items = []
    while True:
        response = client.get(endpoint+'/rankings', params={'offset':len(items), 'limit':100})
        response.raise_for_status()
        page = response.json()
        items.extend(page['items'])
        if len(items) >= page['total']:
            return items


with httpx.Client(base_url='http://127.0.0.1:8000/api/v1', timeout=30) as client:
    assert client.get('/health').json()['database'] == 'connected'
    for item in report:
        endpoint = '/jobs/'+item['job_id']
        if args.rematch:
            response = client.post(endpoint+'/match')
            response.raise_for_status()
            deadline = time.monotonic()+600
            while time.monotonic() < deadline:
                state = client.get(endpoint).json()
                if state['match_status'] != 'processing':
                    break
                time.sleep(1)
            assert state['match_status'] == 'completed', state.get('match_error')
        rows = rankings(client, endpoint)
        assert len(rows) >= item['processed'], 'Saved sample candidates disappeared'
        scores = [row['overall_score'] for row in rows]
        assert scores == sorted(scores, reverse=True)
        assert all(0 <= score <= 100 for score in scores)
        for row in rows:
            explanation = row['explanation']
            assert abs(sum(explanation['contributions'].values())-row['overall_score']) <= .011
            assert abs(sum(explanation['weights'].values())-1) < 1e-9
        # A deliberate model/policy change may change scores and leaders. Verify
        # the old reference result is either current or physically preserved.
        previous = next(row for row in rows if row['candidate']['name'] == item['top_candidate'])
        if previous['overall_score'] != item['top_score']:
            response = client.get(endpoint+'/matches/'+previous['candidate_id']+'/history', params={'limit':100})
            response.raise_for_status()
            assert any(h['payload']['overall_score'] == item['top_score'] for h in response.json()), 'Original reference score not preserved in history'
        page = client.get(endpoint+'/rankings', params={'offset':1,'limit':2}).json()
        assert len(page['items']) == 2 and page['total'] == len(rows)
        filtered = client.get(endpoint+'/rankings', params={'search':item['top_candidate']}).json()
        assert filtered['total'] >= 1
        ordered = client.get(endpoint+'/rankings', params={'sort':'experience','limit':100}).json()['items']
        years = [row['explanation']['relevant_years'] for row in ordered if row['explanation']['relevant_years'] is not None]
        assert years == sorted(years, reverse=True)
with psycopg.connect(host='127.0.0.1',port=5433,user='resume',dbname='resume_matcher',connect_timeout=5) as db:
    counts = db.execute('SELECT (SELECT count(*) FROM jobs), (SELECT count(*) FROM candidates), (SELECT count(*) FROM match_results)').fetchone()
    assert counts[0] >= len(report) and counts[1] >= sum(item['processed'] for item in report)
    assert counts[1] >= counts[2]
    assert db.execute("SELECT data_type FROM information_schema.columns WHERE table_name='match_results' AND column_name='explanation'").fetchone() == ('jsonb',)
    print('PostgreSQL persisted counts (jobs, candidates, matches):', counts)
    print('Migration:', db.execute('SELECT version_num FROM alembic_version').fetchone()[0])
print('PASS: current rankings, archived reference scores, filters, pagination, relevant experience sorting and JSONB persistence.')
