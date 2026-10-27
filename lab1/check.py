#!/usr/bin/env python3
import base64
import concurrent.futures
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None
opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))

def get(path='/', host='idioma.local', tls=True, auth=False):
    headers = {'Host': host}
    if auth:
        headers['Authorization'] = 'Basic ' + base64.b64encode(b'admin:local-lab-password').decode()
    url = ('https' if tls else 'http') + '://127.0.0.1' + path
    try:
        response = opener.open(urllib.request.Request(url, headers=headers), timeout=10)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        return response.code, dict(response.headers), response.read().decode(errors='replace')

def compose(*args):
    subprocess.run(['docker', 'compose', '-f', str(BASE / 'compose.yaml'), *args], check=True)

def main():
    import sys
    sys.stdout.reconfigure(line_buffering=True)
    print('Started:', datetime.now(timezone.utc).isoformat(), flush=True)
    code, headers, body = get('/api/health', tls=False)
    assert code == 301 and headers.get('Location') == 'https://idioma.local/api/health', (code, headers)
    print('PASS HTTP 301 ->', headers['Location'])
    assert get('/')[0] == 200
    print('PASS HTTPS serves the React frontend')
    instances = set()
    for _ in range(8):
        code, headers, _ = get('/api/health')
        instance = next((v for k, v in headers.items() if k.lower() == 'x-instance-id'), None)
        assert code == 200, code
        instances.add(instance)
        print('GET /api/health ->', code, instance)
        time.sleep(0.15)
    assert instances == {'backend-1', 'backend-2'}, instances
    print('PASS both upstream instances receive requests')
    assert 'idioma docs alias' in get('/docs/')[2]
    print('PASS /docs/ is served from the alias directory')
    assert get('/admin')[0] == 401
    assert get('/admin', auth=True)[0] == 200
    print('PASS /admin -> 401 without password, 200 with Basic Auth')
    assert 'SECOND PROJECT' in get('/', host='second.local')[2]
    assert get('/api/health', host='second.local')[0] == 404
    assert get('/', host='foreign.invalid')[0] == 404
    assert 'root' not in get('/', host='foreign.invalid')[2]
    print('PASS separate virtual hosts and unknown Host isolation')
    code, _, body = get('/this-page-does-not-exist')
    assert code == 404 and 'idioma custom 404' in body
    print('PASS missing page -> branded 404')
    
    print('Stopping backend1 to check failover...', flush=True)
    compose('stop', 'backend1')
    try:
        for _ in range(6):
            code, headers, _ = get('/api/health')
            assert code == 200, code
            instance = next(v for k, v in headers.items() if k.lower() == 'x-instance-id')
            assert instance == 'backend-2', instance
            print('backend1 stopped: GET /api/health ->', code, instance)
            time.sleep(0.2)
    finally:
        compose('start', 'backend1')
    print('PASS service survives losing half of its backends')
    
    time.sleep(3)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(lambda _: get('/api/health')[0], range(60)))
    counts = {c: codes.count(c) for c in set(codes)}
    assert 429 in counts and set(counts) <= {200, 429}, counts
    print('PASS rate limit, 60 local requests:', counts)
    print('All nginx checks passed', flush=True)

if __name__ == "__main__":
    main()
