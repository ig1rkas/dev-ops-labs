#!/usr/bin/env python3
"""A WORKING, intentionally bad pipeline, restricted to a separate local stack."""
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import uuid

from ci import LAB, ROOT, STATE, command, dump, now, pipeline_lock


def main():
    folder = LAB / 'evidence/bad-pipeline'
    folder.mkdir(parents=True, exist_ok=True)
    context = STATE / ('bad-context-' + uuid.uuid4().hex)
    result = {'started_at': now(), 'execution': 'local', 'intentional_bad_practices': True}
    with pipeline_lock(), (folder / 'pipeline.log').open('w') as log:
        try:
            shutil.copytree(ROOT, context, ignore=shutil.ignore_patterns('.git', '.state', '.cache', 'evidence', 'node_modules', '__pycache__'))
            auth = context / 'lab0/app/src/backend/app/services/auth.py'
            source = auth.read_text()
            auth.write_text(source.replace('def hash_password(password: str) -> str:\n', 'def hash_password(password: str) -> str:\n    return password  # Deliberate regression for this bad pipeline.\n', 1))
            command(['docker', 'build', '-f', 'lab3/Dockerfile.quality', '-t', 'idioma-lab3/quality:locked', '.'], log)
            tests = ['docker', 'run', '--rm', '--network=none', '-e', 'PYTHONPATH=/src', '-e', 'AUTO_CREATE_TABLES=false', '-e', 'TELEGRAM_POLLING_ENABLED=false', '-e', 'TELEGRAM_MTPROTO_ENABLED=false',
                     '--mount', f'type=bind,source={context / "lab0/app/src/backend"},target=/src,readonly',
                     '--mount', f'type=bind,source={LAB / "tests"},target=/tests,readonly',
                     'idioma-lab3/quality:locked', 'python', '-m', 'unittest', 'discover', '-s', '/tests', '-v']
            # BAD 1: a genuine failed test does NOT block the rest of the pipeline.
            result['ignored_test_exit_code'] = command(tests, log, check=False)
            if result['ignored_test_exit_code'] == 0:
                raise RuntimeError('The demonstration expected a real failed test')
            # BAD 2: disable caching; BAD 3: overwrite latest, with no version history.
            command(['docker', 'build', '--no-cache', '--progress=plain', '-f', context / 'lab2/Dockerfile.bad', '-t', 'localhost:5003/idioma/bad-backend:latest', context], log)
            command(['docker', 'build', '--no-cache', '--progress=plain', '-f', context / 'lab2/Dockerfile.good', '--target', 'frontend', '-t', 'localhost:5003/idioma/bad-frontend:latest', context], log)
            # BAD 4: no Trivy/security gate before push or deployment.
            command(['docker', 'compose', '-f', LAB / 'registry.compose.yaml', 'up', '-d'], log)
            command(['docker', 'push', 'localhost:5003/idioma/bad-backend:latest'], log)
            command(['docker', 'push', 'localhost:5003/idioma/bad-frontend:latest'], log)
            # BAD 5: public hardcoded dummy passwords; BAD 6: no deploy health gate.
            command(['docker', 'compose', '-f', LAB / 'bad.compose.yaml', 'up', '-d'], log)
            result.update(deployed_despite_failed_tests=True, security_scan='absent', versioning='latest only')

            # This is an external observation AFTER the bad pipeline deployed.
            # It is evidence, not a blocking verification stage of that pipeline.
            for attempt in range(90):
                try:
                    with urllib.request.urlopen('http://127.0.0.1:8084/api/health', timeout=2) as response:
                        result['observed_health'] = json.load(response)
                    break
                except Exception:
                    if attempt == 89:
                        raise
                    time.sleep(1)
            email = 'bad-observer-' + uuid.uuid4().hex + '@example.org'
            payload = {'email': email, 'full_name': 'Bad pipeline observer', 'password': 'Test-password-2026'}
            request = urllib.request.Request('http://127.0.0.1:8084/api/auth/register', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=10) as response:
                result['observed_registration_status'] = response.status
            request = urllib.request.Request('http://127.0.0.1:8084/api/auth/login', data=json.dumps({'email': email, 'password': payload['password']}).encode(), headers={'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    login_status = response.status
            except urllib.error.HTTPError as error:
                login_status = error.code
            result['observed_login_status'] = login_status
            assert login_status == 401, 'The injected application regression did not reproduce'
            result.update(status='completed with ignored failed tests', finished_at=now())
            log.write('\nOBSERVATION: site answers, but login is broken; failed tests were ignored.\n')
            command(['docker', 'compose', '-f', LAB / 'bad.compose.yaml', 'ps'], log)
            dump(folder / 'result.json', result)
        finally:
            shutil.rmtree(context, ignore_errors=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
