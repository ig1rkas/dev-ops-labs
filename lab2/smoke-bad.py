#!/usr/bin/env python3
"""Verify that the deliberately bad image still runs the same application."""
import json
import subprocess
import time
import urllib.request

name = 'idioma-lab2-bad-proof'
command = [
    'docker', 'run', '-d', '--name', name,
    '--network', 'idioma-lab2_edge', '--network', 'idioma-lab2_data',
    '-p', '127.0.0.1:18003:8000',
    '-e', 'DATABASE_URL=postgresql+psycopg://idioma:local-lab-password@db:5432/idioma',
    '-e', 'AUTO_CREATE_TABLES=false',
    '-e', 'TELEGRAM_POLLING_ENABLED=false',
    '-e', 'TELEGRAM_MTPROTO_ENABLED=false',
    'idioma-labs/backend:bad-benchmark',
]
subprocess.run(command, check=True, capture_output=True)
try:
    for attempt in range(45):
        try:
            with urllib.request.urlopen('http://127.0.0.1:18003/api/readiness', timeout=2) as response:
                ready = json.load(response)
            break
        except Exception:
            if attempt == 44:
                raise
            time.sleep(1)
    user = subprocess.check_output(['docker', 'exec', name, 'whoami'], text=True).strip()
    assert user == 'root'
    assert ready['status'] == 'ready'
    with urllib.request.urlopen('http://127.0.0.1:18003/api/subjects', timeout=5) as response:
        subjects = json.load(response)
    assert len(subjects) > 0
    print('PASS bad image runs the same FastAPI service')
    print('PASS readiness checks real PostgreSQL:', ready)
    print('PASS catalog reads PostgreSQL, subjects:', len(subjects))
    print('whoami:', user)
finally:
    subprocess.run(['docker', 'rm', '-f', name], check=True, capture_output=True)
