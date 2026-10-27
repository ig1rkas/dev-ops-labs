#!/usr/bin/env python3
import concurrent.futures
import json
import subprocess
import time
from datetime import datetime, timezone
from check import BASE, api, compose, wait_ready

print('Started:', datetime.now(timezone.utc).isoformat(), flush=True)
db_id = compose('ps', '-q', 'db', capture=True).stdout.strip()
def inspect(cid):
    return json.loads(subprocess.check_output(['docker', 'inspect', cid], text=True))[0]
before = inspect(db_id)['RestartCount']
print('Requesting immediate PostgreSQL process shutdown inside its container...', flush=True)
# Do not use docker stop: it intentionally suppresses the restart policy.
compose('exec', '-T', '-u', 'postgres', 'db', 'pg_ctl', '-D', '/var/lib/postgresql/data', 'stop', '-m', 'immediate', '-t', '5', check=False)
time.sleep(2)
wait_ready()
after = inspect(db_id)['RestartCount']
assert after > before, (before, after)
print('PASS same DB container restarted automatically:', before, '->', after, flush=True)
print('PASS backend reconnected:', api('/api/readiness'), flush=True)

name = 'idioma-lab2-too-small'
command = ['docker', 'create', '--name', name, '--memory=40m', '--memory-swap=40m', '--cpus=0.1', '--network=none', '-e', 'AUTO_CREATE_TABLES=false', '-e', 'TELEGRAM_POLLING_ENABLED=false', '-e', 'TELEGRAM_MTPROTO_ENABLED=false', 'idioma-labs/backend:lab2-good']
subprocess.run(command, check=True, capture_output=True)
try:
    subprocess.run(['docker', 'start', name], check=True, capture_output=True)
    for _ in range(60):
        state = inspect(name)['State']
        if not state['Running']:
            break
        time.sleep(1)
    state = inspect(name)['State']
    (BASE / 'evidence/oom.json').write_text(json.dumps(state, indent=2) + '\n')
    assert state['OOMKilled'] and state['ExitCode'] == 137, state
    print('PASS overly tight limit: actual backend OOMKilled=true, exit=137, memory=40MiB, cpu=0.1', flush=True)
finally:
    subprocess.run(['docker', 'rm', '-f', name], check=True, capture_output=True)

backend_id = compose('ps', '-q', 'backend', capture=True).stdout.strip()
def cpu_stat():
    raw = compose('exec', '-T', 'backend', 'cat', '/sys/fs/cgroup/cpu.stat', capture=True).stdout
    return dict((key, int(value)) for key, value in (line.split() for line in raw.splitlines()))
start = cpu_stat()
stats = []
def load(_):
    try:
        assert len(api('/api/subjects')) > 0
        return 200
    except Exception as exc:
        return type(exc).__name__

started = time.perf_counter()
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    futures = [pool.submit(load, i) for i in range(240)]
    while not all(f.done() for f in futures):
        stats.append(subprocess.check_output(['docker', 'stats', '--no-stream', '--format', '{{.Name}} CPU={{.CPUPerc}} MEM={{.MemUsage}}', backend_id], text=True).strip())
    results = [f.result() for f in futures]
elapsed = time.perf_counter() - started
end = cpu_stat()
assert results.count(200) == len(results), results
throttled = end['nr_throttled'] - start['nr_throttled']
assert throttled > 0, (start, end)
(BASE / 'evidence/stats.txt').write_text('\n'.join(stats) + '\n')
summary = {'requests': len(results), 'successful': results.count(200), 'seconds': round(elapsed, 3), 'backend_memory_limit': '512MiB', 'backend_cpus': 0.5, 'cpu_before': start, 'cpu_after': end, 'throttled_periods_delta': throttled}
(BASE / 'evidence/load.json').write_text(json.dumps(summary, indent=2) + '\n')
print('PASS tuned limits hold real API load:', json.dumps(summary), flush=True)
print('All resilience checks passed', flush=True)
