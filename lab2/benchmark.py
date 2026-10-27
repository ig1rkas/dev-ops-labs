#!/usr/bin/env python3
"""Measure real rebuilds after a one-line code edit in a temporary copy."""
import json
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
OUT = BASE / 'evidence'
OUT.mkdir(exist_ok=True)
result = {'started_at': datetime.now(timezone.utc).isoformat(), 'architecture': subprocess.check_output(['docker', 'info', '--format', '{{.Architecture}}'], text=True).strip()}

def build(context, kind, phase):
    tag = 'idioma-labs/backend:' + kind + '-benchmark'
    command = ['docker', 'build', '--progress=plain', '-f', str(context / 'lab2' / ('Dockerfile.' + kind)), '-t', tag]
    if kind == 'good':
        command += ['--target', 'backend']
    command.append(str(context))
    print('Building', phase, kind, flush=True)
    with (OUT / (phase + '-' + kind + '.log')).open('w') as log:
        start = time.perf_counter()
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        elapsed = time.perf_counter() - start
    info = json.loads(subprocess.check_output(['docker', 'image', 'inspect', tag], text=True))[0]
    return {'seconds': round(elapsed, 3), 'bytes': info['Size'], 'image': tag, 'image_id': info['Id'], 'user': info['Config'].get('User') or 'root (default)'}

with tempfile.TemporaryDirectory(prefix='idioma-lab2-benchmark-') as temporary:
    context = Path(temporary) / 'context'
    shutil.copytree(ROOT, context, ignore=shutil.ignore_patterns('.git', 'evidence', 'certs', 'auth', 'node_modules', '__pycache__', '.DS_Store'))
    result['initial_bad'] = build(context, 'bad', 'initial')
    result['initial_good'] = build(context, 'good', 'initial')
    source = context / 'lab0/app/src/backend/app/main.py'
    source.write_text(source.read_text() + '\n# One-line source change for the rebuild measurement.\n')
    result['rebuild_bad'] = build(context, 'bad', 'rebuild')
    result['rebuild_good'] = build(context, 'good', 'rebuild')
assert result['rebuild_good']['bytes'] < result['rebuild_bad']['bytes'], result
(OUT / 'benchmark.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
