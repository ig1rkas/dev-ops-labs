#!/usr/bin/env python3
"""Check the real API and PostgreSQL, without third-party test libraries."""
import json
import os
import urllib.request
import uuid
from datetime import datetime, timezone

BASE = os.getenv("BASE_URL", "http://127.0.0.1:8080").rstrip("/")

def request(path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=None if data is None else json.dumps(data).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)

print("Started:", datetime.now(timezone.utc).isoformat())
assert request("/api/readiness")["status"] == "ready"
email = "lab-" + uuid.uuid4().hex + "@example.org"
account = request("/api/auth/register", {"email": email, "full_name": "Лабораторный студент", "password": "Lab-password-2026"})
assert account["user"]["email"] == email
print("PASS registration writes a user to PostgreSQL:", email)
me = request("/api/auth/me", token=account["token"])
assert me["email"] == email
print("PASS a fresh HTTP request reads the saved user:", me["id"])
login = request("/api/auth/login", {"email": email, "password": "Lab-password-2026"})
assert login["user"]["id"] == me["id"]
print("PASS login reads the same account from PostgreSQL")
subjects = request("/api/subjects")
assert len(subjects) > 0
print("PASS frontend catalog API returns subjects:", len(subjects))
with urllib.request.urlopen(BASE + "/", timeout=15) as response:
    assert b'root' in response.read()
print("PASS React frontend is served")
print("All checks passed")
