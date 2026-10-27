#!/usr/bin/env python3
"""The same real pipeline can run locally and as individual GitHub Actions steps."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import difflib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid

LAB = Path(__file__).resolve().parent
ROOT = LAB.parent
STATE = Path(os.getenv('LAB3_STATE_DIR', str(LAB / '.state'))).resolve()
EVIDENCE = LAB / 'evidence'
STAGES = ['quality', 'build', 'scan', 'publish', 'deploy', 'verify']
TRIVY = 'aquasec/trivy:0.76.1@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c'
URL = 'http://127.0.0.1:8083'


def now():
    return datetime.now(timezone.utc).isoformat()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def load(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def command(args, log, *, env=None, check=True):
    log.write('\n$ ' + shlex.join(str(a) for a in args) + '\n')
    log.flush()
    result = subprocess.run([str(a) for a in args], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=env)
    log.write(f'\nexit_code={result.returncode}\n')
    log.flush()
    if check and result.returncode:
        raise subprocess.CalledProcessError(result.returncode, args)
    return result.returncode


def capture(args):
    return subprocess.check_output([str(a) for a in args], cwd=ROOT, text=True).strip()


def image_info(name):
    return json.loads(capture(['docker', 'image', 'inspect', name]))[0]


def source_fingerprint():
    digest = hashlib.sha256()
    paths = []
    for folder in [ROOT / 'lab0/app/src/backend/app', ROOT / 'lab0/app/src/frontend', LAB / 'tests']:
        paths.extend(p for p in folder.rglob('*') if p.is_file() and not any(part in ['node_modules', '__pycache__', 'dist'] for part in p.parts))
    paths.extend([ROOT / 'lab0/app/src/backend/requirements.lock', ROOT / 'lab2/Dockerfile.good', LAB / 'ci.py', LAB / 'Dockerfile.quality', LAB / 'ruff.toml'])
    for path in sorted(paths):
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def secrets_file():
    STATE.mkdir(parents=True, exist_ok=True)
    STATE.chmod(0o700)
    path = STATE / 'deploy.env'
    saved = {}
    if path.exists():
        saved = dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)
    values = {}
    for name in ['POSTGRES_PASSWORD', 'ADMIN_PASSWORD']:
        supplied = os.getenv('LAB3_' + name)
        if os.getenv('GITHUB_ACTIONS') == 'true' and not supplied:
            raise RuntimeError('Set the GitHub Actions secret LAB3_' + name)
        value = supplied or saved.get(name) or secrets.token_urlsafe(24)
        if not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', value):
            raise RuntimeError(name + ' must be a URL-safe value of 16..128 characters')
        values[name] = value
    path.write_text(''.join(key + '=' + value + '\n' for key, value in values.items()))
    path.chmod(0o600)
    return path


def compose_args(manifest):
    env = os.environ.copy()
    env.update(BACKEND_IMAGE=manifest['backend']['digest_ref'], FRONTEND_IMAGE=manifest['frontend']['digest_ref'], RELEASE_VERSION=manifest['version'])
    return ['docker', 'compose', '--env-file', secrets_file(), '-f', LAB / 'compose.yaml'], env


def active_containers():
    raw = capture(['docker', 'ps', '-a', '--filter', 'label=com.docker.compose.project=idioma-lab3', '--format', '{{.ID}} {{.Image}}'])
    return sorted(raw.splitlines())


@contextmanager
def pipeline_lock():
    STATE.mkdir(parents=True, exist_ok=True)
    STATE.chmod(0o700)
    with (STATE / 'pipeline.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another lab3 pipeline or deployment is running')
        yield


class Pipeline:
    def __init__(self, run_id=None, scenario='good'):
        self.id = run_id or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + scenario + '-' + uuid.uuid4().hex[:6]
        if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', self.id):
            raise ValueError('Invalid run ID')
        self.directory = EVIDENCE / self.id
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'run.json'
        self.data = load(self.path)
        if self.data is None:
            self.data = {
                'id': self.id, 'execution': 'local' if os.getenv('GITHUB_ACTIONS') != 'true' else 'github-actions',
                'scenario': scenario, 'started_at': now(), 'status': 'running',
                'base_git_head': capture(['git', 'rev-parse', 'HEAD']),
                'source_sha256': source_fingerprint(),
                'deployment_before': active_containers(),
                'registry': os.getenv('LAB3_REGISTRY', 'localhost:5003/idioma'),
                'stages': {stage: {'status': 'pending'} for stage in STAGES},
            }
            self.data['version'] = 'src-' + self.data['source_sha256'][:12] + '-' + self.id.lower()
            self.save()
        elif scenario != self.data['scenario']:
            raise ValueError('Run ID already belongs to another scenario')

    def save(self):
        dump(self.path, self.data)

    def stage(self, name):
        index = STAGES.index(name)
        if self.data['stages'][name]['status'] != 'pending':
            raise RuntimeError('This stage was already executed; use a new run ID')
        if any(self.data['stages'][previous]['status'] != 'passed' for previous in STAGES[:index]):
            raise RuntimeError('A preceding stage has not passed')
        record = self.data['stages'][name]
        record.update(status='running', started_at=now())
        self.save()
        print(f'[{self.id}] {name}: running', flush=True)
        started = time.perf_counter()
        with (self.directory / (name + '.log')).open('w') as log:
            try:
                if source_fingerprint() != self.data['source_sha256']:
                    raise RuntimeError('Source changed after the run started; refusing an untested deployment')
                getattr(self, name)(log)
                record['status'] = 'passed'
            except Exception as error:
                record.update(status='failed', error=str(error))
                log.write('\nFAILED: ' + str(error) + '\n')
                self.data['status'] = 'failed'
                for following in STAGES[index + 1:]:
                    self.data['stages'][following] = {'status': 'skipped', 'reason': name + ' failed'}
            finally:
                record.update(finished_at=now(), seconds=round(time.perf_counter() - started, 3))
                self.data['deployment_after'] = active_containers()
                if name == 'verify' and record['status'] == 'passed':
                    self.data['status'] = 'passed'
                self.data['updated_at'] = now()
                self.save()
        print(f'[{self.id}] {name}: {record["status"]} ({record["seconds"]}s)', flush=True)
        return record['status'] == 'passed'

    def quality(self, log):
        command(['docker', 'build', '--progress=plain', '-f', 'lab3/Dockerfile.quality', '-t', 'idioma-lab3/quality:locked', '.'], log)
        source = ROOT / 'lab0/app/src/backend'
        if self.data['scenario'] == 'broken-code':
            destination = STATE / 'regression' / self.id
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            path = destination / 'app/services/auth.py'
            original = path.read_text()
            needle = 'def hash_password(password: str) -> str:\n'
            if needle not in original:
                raise RuntimeError('Regression insertion point changed')
            changed = original.replace(needle, needle + '    return password  # Intentional regression: the real test must reject this.\n', 1)
            path.write_text(changed)
            (self.directory / 'regression.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True), fromfile='original/app/services/auth.py', tofile='regression/app/services/auth.py')))
            source = destination
        args = ['docker', 'run', '--rm', '--network=none', '-e', 'PYTHONPATH=/src', '-e', 'AUTO_CREATE_TABLES=false', '-e', 'TELEGRAM_POLLING_ENABLED=false', '-e', 'TELEGRAM_MTPROTO_ENABLED=false',
                '--mount', f'type=bind,source={source},target=/src,readonly',
                '--mount', f'type=bind,source={LAB / "tests"},target=/tests,readonly',
                '--mount', f'type=bind,source={LAB / "ruff.toml"},target=/quality/ruff.toml,readonly',
                'idioma-lab3/quality:locked']
        command(args + ['ruff', 'check', '--no-cache', '--config', '/quality/ruff.toml', '/src/app', '/tests'], log)
        command(args + ['python', '-m', 'unittest', 'discover', '-s', '/src/tests', '-p', 'test_*.py', '-v'], log)
        command(args + ['python', '-m', 'unittest', 'discover', '-s', '/tests', '-p', 'test_*.py', '-v'], log)

    def build(self, log):
        self.data['images'] = {}
        for kind in ['backend', 'frontend']:
            tag = f'idioma-lab3/{kind}:{self.data["version"]}'
            dockerfile = 'lab3/Dockerfile.vulnerable' if kind == 'backend' and self.data['scenario'] == 'vulnerable' else 'lab2/Dockerfile.good'
            args = ['docker', 'build', '--progress=plain', '-f', dockerfile, '-t', tag, '--label', 'org.opencontainers.image.revision=' + self.data['source_sha256']]
            if dockerfile == 'lab2/Dockerfile.good':
                args += ['--target', kind]
            command(args + ['.'], log)
            info = image_info(tag)
            self.data['images'][kind] = {'local_tag': tag, 'image_id': info['Id'], 'bytes': info['Size']}

    def scan(self, log):
        failed = False
        self.data['security'] = {}
        for kind, image in self.data['images'].items():
            if image_info(image['local_tag'])['Id'] != image['image_id']:
                raise RuntimeError('Image tag changed after build')
            archive = STATE / (self.id + '-' + kind + '.tar')
            try:
                command(['docker', 'image', 'save', image['local_tag'], '-o', archive], log)
                base = ['docker', 'run', '--rm', '--memory=2g', '--cpus=1',
                        '--mount', f'type=bind,source={archive},target=/input/image.tar,readonly',
                        '-v', 'idioma-lab3-trivy-cache:/cache',
                        '--mount', f'type=bind,source={self.directory},target=/reports', TRIVY,
                        '--cache-dir', '/cache', 'image', '--input', '/input/image.tar', '--scanners', 'vuln', '--timeout', '10m']
                report = kind + '-trivy.json'
                command(base + ['--severity', 'HIGH,CRITICAL', '--exit-code', '0', '--format', 'json', '--output', '/reports/' + report], log)
                data = load(self.directory / report)
                vulnerabilities = [v for result in data.get('Results', []) for v in result.get('Vulnerabilities', [])]
                counts = Counter(v['Severity'] for v in vulnerabilities)
                code = command(base + ['--skip-db-update', '--severity', 'CRITICAL', '--exit-code', '1', '--format', 'table'], log, check=False)
                self.data['security'][kind] = {'HIGH': counts['HIGH'], 'CRITICAL': counts['CRITICAL'], 'trivy_exit_code': code, 'report': report, 'trivy_image': TRIVY}
                log.write('\nSeverity counts: ' + json.dumps(self.data['security'][kind]) + '\n')
                failed |= code != 0
            finally:
                archive.unlink(missing_ok=True)
        if failed:
            raise RuntimeError('Trivy CRITICAL gate rejected the image(s); publication and deployment are blocked')

    def publish(self, log):
        registry = self.data['registry']
        if registry.startswith('localhost:5003/'):
            command(['docker', 'compose', '-f', LAB / 'registry.compose.yaml', 'up', '-d'], log)
            for attempt in range(30):
                try:
                    with urllib.request.urlopen('http://127.0.0.1:5003/v2/', timeout=2) as response:
                        if response.status == 200:
                            break
                except Exception:
                    if attempt == 29:
                        raise
                    time.sleep(1)
        manifest = {'version': self.data['version'], 'source_sha256': self.data['source_sha256'], 'published_at': now()}
        for kind, image in self.data['images'].items():
            if image_info(image['local_tag'])['Id'] != image['image_id']:
                raise RuntimeError('Refusing to publish an image that differs from the scanned image')
            tag = registry.rstrip('/') + '/' + kind + ':' + self.data['version']
            command(['docker', 'tag', image['local_tag'], tag], log)
            command(['docker', 'push', tag], log)
            repository = tag.rsplit(':', 1)[0]
            digest = next(d for d in image_info(tag)['RepoDigests'] if d.startswith(repository + '@'))
            manifest[kind] = {**image, 'tag': tag, 'digest_ref': digest}
        self.data['release'] = manifest
        dump(self.directory / 'release.json', manifest)

    def deploy(self, log):
        deploy_release(self.data['release'], log)

    def verify(self, log):
        verify_release(self.data['release'], log)
        dump(STATE / 'current.json', self.data['release'])


def deploy_release(manifest, log, timeout=90):
    current = load(STATE / 'current.json')
    if current:
        dump(STATE / 'previous.json', current)
    dump(STATE / 'attempt.json', manifest)
    args, env = compose_args(manifest)
    command(args + ['pull', 'backend', 'frontend'], log, env=env)
    command(args + ['up', '-d', '--wait', '--wait-timeout', str(timeout)], log, env=env)


def verify_release(manifest, log):
    command(['curl', '-fsS', '--retry', '8', '--retry-delay', '1', '--retry-connrefused', URL + '/api/readiness'], log)
    with urllib.request.urlopen(URL + '/api/readiness', timeout=10) as response:
        ready = json.load(response)
    if ready['instance'] != 'lab3-' + manifest['version']:
        raise RuntimeError('The running service does not match the requested release')
    with urllib.request.urlopen(URL + '/', timeout=10) as response:
        if response.status != 200 or b'id="root"' not in response.read():
            raise RuntimeError('Frontend is not serving the real React application')
    email = 'ci-' + uuid.uuid4().hex + '@example.org'
    payload = {'email': email, 'full_name': 'CI student', 'password': 'Test-password-2026'}
    request = urllib.request.Request(URL + '/api/auth/register', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=10) as response:
        account = json.load(response)
    request = urllib.request.Request(URL + '/api/auth/me', headers={'Authorization': 'Bearer ' + account['token']})
    with urllib.request.urlopen(request, timeout=10) as response:
        me = json.load(response)
    if me['email'] != email:
        raise RuntimeError('Database read/write smoke check failed')
    log.write(f'\nPASS actual deployed release {manifest["version"]}: frontend=200, PostgreSQL registration/readback user_id={me["id"]}\n')
    args, env = compose_args(manifest)
    command(args + ['ps'], log, env=env)


def rollback():
    target = load(STATE / 'previous.json')
    if not target:
        raise RuntimeError('No previous working version has been recorded')
    folder = EVIDENCE / ('rollback-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    folder.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with (folder / 'rollback.log').open('w') as log:
        args, env = compose_args(target)
        command(args + ['pull', 'backend', 'frontend'], log, env=env)
        command(args + ['up', '-d', '--wait', '--wait-timeout', '90'], log, env=env)
        verify_release(target, log)
    dump(STATE / 'current.json', target)
    result = {'status': 'passed', 'finished_at': now(), 'seconds': round(time.perf_counter() - started, 3), 'restored_version': target['version'], 'release': target}
    dump(folder / 'rollback.json', result)
    print('Rollback passed:', target['version'], 'seconds=', result['seconds'], flush=True)
    return folder, result


def demo_rollback():
    stable = load(STATE / 'current.json')
    if not stable:
        raise RuntimeError('Run a successful pipeline before the rollback demonstration')
    folder = EVIDENCE / ('broken-release-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    folder.mkdir(parents=True, exist_ok=True)
    version = 'broken-' + uuid.uuid4().hex[:12]
    tag = 'idioma-lab3/backend:' + version
    manifest = {**stable, 'version': version, 'purpose': 'intentional local rollback exercise'}
    with (folder / 'broken-release.log').open('w') as log:
        command(['docker', 'build', '--progress=plain', '-f', 'lab3/Dockerfile.broken', '--build-arg', 'BASE_IMAGE=' + stable['backend']['local_tag'], '-t', tag, '.'], log)
        published = stable['backend']['tag'].rsplit(':', 1)[0] + ':' + version
        command(['docker', 'tag', tag, published], log)
        command(['docker', 'push', published], log)
        repository = published.rsplit(':', 1)[0]
        digest = next(d for d in image_info(published)['RepoDigests'] if d.startswith(repository + '@'))
        manifest['backend'] = {'tag': published, 'local_tag': tag, 'digest_ref': digest, 'image_id': image_info(tag)['Id']}
        dump(folder / 'broken-release.json', manifest)
        try:
            broken = False
            try:
                deploy_release(manifest, log, timeout=20)
            except subprocess.CalledProcessError:
                broken = True
                log.write('\nEXPECTED: intentionally broken deployment failed its readiness check.\n')
            args, env = compose_args(manifest)
            command(args + ['ps', '-a'], log, env=env)
            command(args + ['logs', '--tail', '25', 'backend'], log, env=env)
            code = command(['curl', '-fsS', '--max-time', '5', URL + '/api/readiness'], log, check=False)
            if not broken or code == 0:
                raise RuntimeError('Broken release did not reproduce the expected outage')
        finally:
            # Restore our own service even if the demonstration fails midway.
            restored_folder, result = rollback()
    dump(folder / 'demonstration.json', {'status': 'passed', 'broken_version': version, 'restored_version': result['restored_version'], 'rollback_seconds': result['seconds'], 'rollback_evidence': str(restored_folder.relative_to(LAB))})
    print('Broken release -> rollback -> live service verified', flush=True)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ['run', 'stage']:
        child = sub.add_parser(action)
        if action == 'stage':
            child.add_argument('name', choices=STAGES)
        child.add_argument('--scenario', choices=['good', 'broken-code', 'vulnerable'], default='good')
        child.add_argument('--run-id')
    sub.add_parser('rollback')
    sub.add_parser('demo-rollback')
    args = parser.parse_args()
    with pipeline_lock():
        if args.action == 'rollback':
            rollback()
        elif args.action == 'demo-rollback':
            demo_rollback()
        else:
            pipeline = Pipeline(args.run_id, args.scenario)
            names = STAGES if args.action == 'run' else [args.name]
            for name in names:
                if not pipeline.stage(name):
                    print('FAILED; evidence:', pipeline.directory, flush=True)
                    return 1
            print('Evidence:', pipeline.directory, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
