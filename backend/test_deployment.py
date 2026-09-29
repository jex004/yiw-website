import importlib
import base64
import json
import tempfile
from pathlib import Path
from itsdangerous import TimestampSigner
import os
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient


class DeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.static = tempfile.TemporaryDirectory()
        Path(cls.static.name, "index.html").write_text("<html>YIW</html>")
        with patch("dotenv.load_dotenv"), patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://test:test@localhost/test",
                "STATIC_DIR": cls.static.name,
                "PUBLIC_URL": "https://example.test",
                "SESSION_SECRET": "test-secret-only",
                "DISCORD_CLIENT_ID": "test-client",
                "DISCORD_CLIENT_SECRET": "test-client-secret",
            },
        ), patch("sqlalchemy.create_engine"), patch(
            "sqlalchemy.sql.schema.MetaData.create_all"
        ):
            cls.app_module = importlib.import_module("main")
        cls.db = MagicMock()
        cls.app_module.app.dependency_overrides[cls.app_module.get_db] = lambda: cls.db

    def setUp(self):
        self.client = TestClient(self.app_module.app, base_url="https://example.test")

    @classmethod
    def tearDownClass(cls):
        cls.static.cleanup()

    def test_website_routes_and_missing_api(self):
        for path in ("/", "/members", "/map", "/timeline", "/gallery"):
            self.assertEqual(self.client.get(path).text, "<html>YIW</html>")
        self.assertEqual(self.client.get("/api/missing").status_code, 404)

    def test_signed_session_can_update_own_profile(self):
        payload = base64.b64encode(json.dumps({"discord_id": "123"}).encode())
        cookie = TimestampSigner("test-secret-only").sign(payload).decode()
        self.client.cookies.set("yiw_session", cookie)
        profile = MagicMock()
        self.db.query.return_value.filter.return_value.first.return_value = profile
        result = self.client.post(
            "/api/profile/update",
            headers={"Origin": "https://example.test"},
            json={"bio": "new bio", "mc_name": "name"},
        )
        self.assertEqual(result.json(), {"status": "success"})
        self.assertEqual(profile.bio, "new bio")

    def test_public_health_and_anonymous_session(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/api/me").json(), {"authenticated": False})

    def test_old_or_forged_cookie_cannot_authenticate(self):
        self.client.cookies.set("discord_id", "123")
        self.client.cookies.set("yiw_session", "forged")
        self.assertFalse(self.client.get("/api/me").json()["authenticated"])
        result = self.client.post(
            "/api/profile/update",
            headers={"Origin": "https://example.test"},
            json={"bio": "test", "mc_name": "test"},
        )
        self.assertEqual(result.json(), {"error": "Not logged in"})

    def test_cross_origin_update_rejected(self):
        result = self.client.post(
            "/api/profile/update",
            headers={"Origin": "https://evil.test"},
            json={"bio": "test", "mc_name": "test"},
        )
        self.assertEqual(result.status_code, 403)

    def test_login_cookie_and_state_validation(self):
        result = self.client.get("/login", follow_redirects=False)
        query = parse_qs(urlsplit(result.headers["location"]).query)
        self.assertEqual(query["redirect_uri"], ["https://example.test/auth/callback"])
        self.assertTrue(query["state"][0])
        cookie = result.headers["set-cookie"].lower()
        for flag in ("httponly", "secure", "samesite=lax"):
            self.assertIn(flag, cookie)
        result = self.client.get("/auth/callback?code=test&state=wrong")
        self.assertEqual(result.status_code, 400)


if __name__ == "__main__":
    unittest.main()
