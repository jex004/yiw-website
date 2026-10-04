import importlib
import base64
import json
import tempfile
from pathlib import Path
from itsdangerous import TimestampSigner
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace
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

    def test_directory_preserves_profiles_defaults_and_bot_filter(self):
        members = [
            {
                "user": {"id": "1", "username": "One", "avatar": "abc"},
                "joined_at": "2024-01-01T00:00:00Z",
            },
            {"user": {"id": "2", "username": "Two"}, "joined_at": None},
            {"user": {"id": "3", "username": "Three"}, "joined_at": "invalid"},
            {"user": {"id": "4", "username": "Bot", "bot": True}},
        ]
        profiles = [
            SimpleNamespace(
                discord_id="1",
                minecraft_username="player",
                preferred_name="First",
                bio="intro",
                detailed_bio="details",
            ),
            SimpleNamespace(
                discord_id="3",
                minecraft_username=None,
                preferred_name=None,
                bio=None,
                detailed_bio=None,
            ),
        ]
        self.db.query.return_value.all.return_value = profiles
        with patch.object(
            self.app_module, "fetch_members", AsyncMock(return_value=members)
        ):
            result = self.client.get("/api/members").json()["members"]
        self.assertEqual(
            result,
            [
                {
                    "id": "1",
                    "username": "One",
                    "avatar_url": "https://cdn.discordapp.com/avatars/1/abc.png",
                    "minecraft_username": "player",
                    "preferred_name": "First",
                    "date_joined": "Jan 2024",
                    "bio": "intro",
                    "detailed_bio": "details",
                    "has_claimed_profile": True,
                },
                {
                    "id": "2",
                    "username": "Two",
                    "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png",
                    "minecraft_username": "Not set",
                    "preferred_name": "",
                    "date_joined": "Unknown",
                    "bio": "",
                    "detailed_bio": "",
                    "has_claimed_profile": False,
                },
                {
                    "id": "3",
                    "username": "Three",
                    "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png",
                    "minecraft_username": "Not set",
                    "preferred_name": "",
                    "date_joined": "Unknown",
                    "bio": "",
                    "detailed_bio": "",
                    "has_claimed_profile": True,
                },
            ],
        )

    def test_server_creation_is_separate_from_archive(self):
        self.db.query.return_value.all.return_value = []
        with patch.object(self.app_module, "YIW_SERVER_ID", "0"), patch.object(
            self.app_module, "read_content", return_value=[]
        ):
            result = self.client.get("/api/events").json()
        self.assertEqual(result["server_created_at"], "2015-01-01")
        self.assertEqual(result["events"], [])

    def test_content_errors_keep_existing_responses(self):
        for path, message in (
            ("/api/events", "Event details need to be checked by the server owner."),
            (
                "/api/locations",
                "Country counts need to be checked by the server owner.",
            ),
        ):
            with self.subTest(path=path), patch.object(
                self.app_module, "read_content", side_effect=ValueError
            ):
                result = self.client.get(path)
                self.assertEqual(result.status_code, 503)
                self.assertEqual(result.json(), {"detail": message})

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
            json={"bio": "new bio", "mc_name": "name", "preferred_name": "  First  "},
        )
        self.assertEqual(result.json(), {"status": "success"})
        self.assertEqual(profile.bio, "new bio")
        self.assertEqual(profile.preferred_name, "First")
        for value in (None, "", "x" * 17):
            data = {"bio": "new bio", "mc_name": "name"}
            if value is not None:
                data["preferred_name"] = value
            result = self.client.post(
                "/api/profile/update",
                headers={"Origin": "https://example.test"},
                json=data,
            )
            self.assertEqual(
                result.status_code, 422 if value and len(value) > 16 else 200
            )
            self.assertEqual(profile.preferred_name, "First" if value is None else "")

        for field, limit in (
            ("preferred_name", 16),
            ("mc_name", 16),
            ("bio", 64),
            ("detailed_bio", 500),
        ):
            for length in (limit, limit + 1):
                with self.subTest(field=field, length=length):
                    data = {"bio": "new bio", "mc_name": "name", field: "x" * length}
                    result = self.client.post(
                        "/api/profile/update",
                        headers={"Origin": "https://example.test"},
                        json=data,
                    )
                    self.assertEqual(result.status_code, 200 if length == limit else 422)

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
