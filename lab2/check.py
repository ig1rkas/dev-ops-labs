#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)
BASE = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:8082'

def compose(*args, capture=False, check=True):
    return subprocess.run(['docker', 'compose', '-f', str(BASE / 'compose.yaml'), *args], check=check, text=True, capture_output=capture)

def api(path, data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(URL + path, data=None if data is None else json.dumps(data).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)

def wait_ready():
    for _ in range(90):
        try:
            if api('/api/readiness')['status'] == 'ready':
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError('The service did not recover within 90 seconds')

def main():
    print('Started:', datetime.now(timezone.utc).isoformat())
    wait_ready()
    assert compose('exec', '-T', 'backend', 'whoami', capture=True).stdout.strip() == 'app'
    assert compose('exec', '-T', 'frontend', 'whoami', capture=True).stdout.strip() == 'nginx'
    print('PASS backend user=app, frontend user=nginx')
    email = 'persistence-' + uuid.uuid4().hex + '@example.org'
    saved = api('/api/auth/register', {'email': email, 'full_name': 'Проверка тома', 'password': 'Lab-password-2026'})
    print('Saved user:', email, 'id=', saved['user']['id'])
    old_id = compose('ps', '-q', 'db', capture=True).stdout.strip()
    print('Removing/recreating the database container, keeping its named volume...')
    compose('up', '-d', '--force-recreate', '--wait', 'db')
    new_id = compose('ps', '-q', 'db', capture=True).stdout.strip()
    assert old_id != new_id
    wait_ready()
    assert api('/api/auth/me', token=saved['token'])['email'] == email
    print('PASS database container changed:', old_id[:12], '->', new_id[:12])
    print('PASS the user and auth token survived in the named volume')

    # BusyBox nc uses -z as a bounded TCP connection probe; DNS failure also
    # demonstrates absence of the database service from the frontend network.
    probe = compose('exec', '-T', 'frontend', 'sh', '-c', 'nc -z -w 2 db 5432', capture=True, check=False)
    print('frontend -> db:5432 exit=', probe.returncode, (probe.stderr or probe.stdout).strip())
    assert probe.returncode != 0, 'Frontend unexpectedly reached PostgreSQL'
    rows = compose('exec', '-T', 'backend', 'python', '-c', 'from app.db.session import engine; from sqlalchemy import text; c=engine.connect(); print(c.execute(text("SELECT COUNT(*) FROM users")).scalar())', capture=True)
    print('PASS backend -> db, users=', rows.stdout.strip())
    db_info = json.loads(subprocess.check_output(['docker', 'inspect', new_id], text=True))[0]
    db_address = db_info['NetworkSettings']['Networks']['idioma-lab2_data']['IPAddress']
    direct_probe = compose('exec', '-T', 'frontend', 'sh', '-c', 'nc -z -w 2 "$1" 5432', 'sh', db_address, capture=True, check=False)
    assert direct_probe.returncode != 0, 'Frontend reached PostgreSQL by its direct IP address'
    print('PASS direct TCP isolation: frontend ->', db_address + ':5432', 'exit=', direct_probe.returncode)
    frontend_id = compose('ps', '-q', 'frontend', capture=True).stdout.strip()
    backend_id = compose('ps', '-q', 'backend', capture=True).stdout.strip()
    def networks(cid):
        data = json.loads(subprocess.check_output(['docker', 'inspect', cid], text=True))[0]
        return set(data['NetworkSettings']['Networks'])
    assert not (networks(frontend_id) & networks(new_id))
    assert networks(backend_id) & networks(new_id)
    print('PASS network membership proves frontend and database share no network')
    print('All Docker stack checks passed')

if __name__ == '__main__':
    main()
