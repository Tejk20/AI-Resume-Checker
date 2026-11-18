"""Check the compiled SPA and real API are served together on the hosted port."""
import json
import os
from urllib.request import urlopen
from urllib.error import HTTPError

base='http://127.0.0.1:'+os.environ.get('PORT','8000')
with urlopen(base+'/api/v1/health',timeout=10) as response:
    health=json.load(response)
    assert health['status']=='ok' and health['database']=='connected'
for path in ['/', '/rankings', '/upload', '/jobs/new']:
    with urlopen(base+path,timeout=10) as response:
        assert '<div id="root"></div>' in response.read().decode()
try:
    urlopen(base+'/api/v1/nonexistent',timeout=10)
    raise AssertionError('Unknown API endpoint returned the frontend')
except HTTPError as error:
    assert error.code==404
print('PASS: real API/database health, compiled React routes and API 404 boundaries.')
