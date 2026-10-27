#!/usr/bin/env python3
"""Three bounded configuration probes against our own localhost only."""
from check import get

checks = [
    ('Path traversal through alias', '/docs/../.env', (400, 403, 404)),
    ('Hidden configuration disclosure', '/.env', (403, 404)),
    ('Unauthenticated administrator access', '/admin/', (401,)),
]
for label, path, expected in checks:
    code, _, body = get(path)
    assert code in expected, (label, code)
    assert 'DATABASE_URL=' not in body and 'POSTGRES_PASSWORD=' not in body
    print(f'PASS {label}: GET {path} -> {code}; no protected data disclosed')
assert get('/', host='foreign.invalid')[0] == 404
print('PASS Host confusion: unknown host cannot reach the application')
print('Only the owned localhost lab was tested; no external websites were scanned.')
