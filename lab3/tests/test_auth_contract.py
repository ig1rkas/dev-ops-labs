import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes import get_db
from app.db.base import Base
from app.main import app
from app.models.user import User


class AuthContractTests(unittest.TestCase):
    def setUp(self):
        # SQLite is used ONLY for isolated unit tests. The deployed app uses
        # PostgreSQL, which is checked again by the smoke test after deployment.
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)

        def database():
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_db] = database
        self.client = TestClient(app)
        self.payload = {
            "email": "contract-student@example.org",
            "full_name": "Contract Student",
            "password": "Test-password-2026",
        }

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def register(self):
        response = self.client.post("/api/auth/register", json=self.payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_password_is_not_stored_or_returned_in_plaintext(self):
        account = self.register()
        self.assertNotIn("password", account["user"])
        self.assertNotIn("password_hash", account["user"])
        with Session(self.engine) as session:
            stored = session.scalar(select(User).where(User.email == self.payload["email"]))
            self.assertNotEqual(stored.password_hash, self.payload["password"])
            self.assertTrue(stored.password_hash.startswith("pbkdf2_sha256$"))

    def test_registered_account_can_be_read_and_logged_in_again(self):
        account = self.register()
        fresh = self.client.get("/api/auth/me", headers={"Authorization": "Bearer " + account["token"]})
        self.assertEqual(fresh.status_code, 200)
        self.assertEqual(fresh.json()["id"], account["user"]["id"])
        login = self.client.post("/api/auth/login", json={"email": self.payload["email"], "password": self.payload["password"]})
        self.assertEqual(login.status_code, 200, login.text)
        self.assertEqual(login.json()["user"]["id"], account["user"]["id"])

    def test_wrong_password_and_missing_token_are_rejected(self):
        self.register()
        login = self.client.post("/api/auth/login", json={"email": self.payload["email"], "password": "wrong-password"})
        self.assertEqual(login.status_code, 401)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_duplicate_registration_is_rejected(self):
        self.register()
        self.assertEqual(self.client.post("/api/auth/register", json=self.payload).status_code, 409)

    def test_public_registration_cannot_create_admin(self):
        response = self.client.post("/api/auth/register", json={**self.payload, "role": "admin"})
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
