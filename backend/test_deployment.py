import base64
import importlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


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
        for path in ("/", "/members", "/map", "/timeline", "/gallery", "/stats"):
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
                    self.assertEqual(
                        result.status_code, 200 if length == limit else 422
                    )

    def test_public_health_and_anonymous_session(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/api/me").json(), {"authenticated": False})

    def test_logout_clears_session_and_rejects_cross_origin_requests(self):
        payload = base64.b64encode(
            json.dumps({"discord_id": "123", "oauth_state": "pending"}).encode()
        )
        cookie = TimestampSigner("test-secret-only").sign(payload).decode()
        self.client.cookies.set("yiw_session", cookie, domain="example.test", path="/")
        result = self.client.post(
            "/api/logout", headers={"Origin": "https://evil.test"}
        )
        self.assertEqual(result.status_code, 403)
        self.assertEqual(self.client.cookies.get("yiw_session"), cookie)
        result = self.client.post(
            "/api/logout", headers={"Origin": "https://example.test"}
        )
        self.assertEqual(result.status_code, 204)
        self.assertIn("expires=Thu, 01 Jan 1970", result.headers["set-cookie"])
        self.assertEqual(self.client.get("/api/me").json(), {"authenticated": False})
        self.assertEqual(self.client.get("/api/stats").status_code, 401)
        self.assertEqual(
            self.client.post(
                "/api/logout", headers={"Origin": "https://example.test"}
            ).status_code,
            204,
        )

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

    def test_comments_permissions_limits_and_persistence(self):
        app = self.app_module
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        app.Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine)
        with factory() as db:
            db.add_all(
                [
                    app.User(discord_id="visitor", username="OutsideUser"),
                    app.User(discord_id="other", username="Other"),
                ]
            )
            db.commit()

        def database():
            with factory() as db:
                yield db

        app.app.dependency_overrides[app.get_db] = database
        url = "/api/members/member/comments"
        headers = {"Origin": "https://example.test"}

        def sign_in(user):
            self.client.cookies.clear()
            payload = base64.b64encode(json.dumps({"discord_id": user}).encode())
            self.client.cookies.set(
                "yiw_session",
                TimestampSigner("test-secret-only").sign(payload).decode(),
            )

        try:
            self.assertEqual(self.client.get(url).json(), {"comments": []})
            self.assertEqual(
                self.client.post(
                    url, headers=headers, json={"body": "hello"}
                ).status_code,
                401,
            )
            sign_in("visitor")
            self.assertEqual(
                self.client.post(
                    url, headers={"Origin": "https://evil.test"}, json={"body": "hello"}
                ).status_code,
                403,
            )
            with patch.object(
                app,
                "fetch_members",
                AsyncMock(
                    return_value=[
                        {"user": {"id": "member"}},
                        {"user": {"id": "second"}},
                    ]
                ),
            ):
                for body in ("", "   ", "x" * 201):
                    self.assertEqual(
                        self.client.post(
                            url, headers=headers, json={"body": body}
                        ).status_code,
                        422,
                    )
                first = self.client.post(url, headers=headers, json={"body": "x" * 200})
                self.assertEqual(first.status_code, 201)
                first = first.json()
                self.assertEqual(first["username"], "OutsideUser")
                self.assertEqual(
                    self.client.post(
                        url, headers=headers, json={"body": "second"}
                    ).status_code,
                    201,
                )
                self.assertEqual(
                    self.client.post(
                        url, headers=headers, json={"body": "third"}
                    ).status_code,
                    409,
                )
                self.assertEqual(
                    self.client.post(
                        "/api/members/second/comments",
                        headers=headers,
                        json={"body": "different profile"},
                    ).status_code,
                    201,
                )
                self.assertEqual(
                    self.client.post(
                        "/api/members/missing/comments",
                        headers=headers,
                        json={"body": "hello"},
                    ).status_code,
                    404,
                )
                item = f"/api/comments/{first['id']}"
                sign_in("other")
                self.assertEqual(
                    self.client.patch(
                        item, headers=headers, json={"body": "changed"}
                    ).status_code,
                    403,
                )
                self.assertEqual(
                    self.client.delete(item, headers=headers).status_code, 403
                )
                self.assertEqual(
                    self.client.post(
                        url, headers=headers, json={"body": "from other"}
                    ).status_code,
                    201,
                )
                sign_in("visitor")
                for body in ("  ", "x" * 201):
                    self.assertEqual(
                        self.client.patch(
                            item, headers=headers, json={"body": body}
                        ).status_code,
                        422,
                    )
                edited = self.client.patch(
                    item, headers=headers, json={"body": " edited "}
                )
                self.assertEqual(edited.json()["body"], "edited")
                self.assertIsNotNone(edited.json()["updated_at"])
                self.assertEqual(
                    self.client.delete(item, headers=headers).status_code, 204
                )
                self.assertEqual(
                    self.client.post(
                        url, headers=headers, json={"body": "replacement"}
                    ).status_code,
                    201,
                )
                self.assertEqual(
                    self.client.post(
                        url, headers=headers, json={"body": "third again"}
                    ).status_code,
                    409,
                )
                self.client.cookies.clear()
                self.assertEqual(len(self.client.get(url).json()["comments"]), 3)
                self.assertEqual(
                    self.client.delete(item, headers=headers).status_code, 401
                )
        finally:
            app.app.dependency_overrides[app.get_db] = lambda: self.db
            engine.dispose()

    def test_discord_login_accepts_non_members(self):
        result = self.client.get("/login", follow_redirects=False)
        query = parse_qs(urlsplit(result.headers["location"]).query)
        self.assertEqual(query["scope"], ["identify"])
        discord = AsyncMock()
        discord.post.return_value = MagicMock(
            json=lambda: {"access_token": "test-token"}
        )
        discord.get.return_value = MagicMock(
            json=lambda: {"id": "visitor", "username": "Visitor"}
        )
        with patch.object(self.app_module.httpx, "AsyncClient") as client:
            client.return_value.__aenter__.return_value = discord
            response = self.client.get(
                f"/auth/callback?code=test&state={query['state'][0]}",
                follow_redirects=False,
            )
        self.assertEqual(response.status_code, 307)
        self.assertEqual(discord.get.await_count, 1)
        self.assertEqual(response.headers["location"], "https://example.test/members")

    def test_analytics_counts_and_owner_access(self):
        app = self.app_module
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        app.Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine)
        with factory() as db:
            db.add_all(
                [
                    app.User(discord_id="owner", username="ServerOwner"),
                    app.User(discord_id="someone-else", username="Visitor"),
                ]
            )
            db.commit()

        def database():
            with factory() as db:
                yield db

        app.app.dependency_overrides[app.get_db] = database
        headers = {"Origin": "https://example.test"}
        visitor = str(uuid4())
        try:
            self.assertEqual(
                self.client.post(
                    "/api/visits",
                    headers={"Origin": "https://evil.test"},
                    json={"visitor": visitor},
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.post(
                    "/api/visits", headers=headers, json={"visitor": "not-a-uuid"}
                ).status_code,
                422,
            )
            for identifier in (visitor, visitor, str(uuid4())):
                self.assertEqual(
                    self.client.post(
                        "/api/visits", headers=headers, json={"visitor": identifier}
                    ).status_code,
                    204,
                )
            self.assertEqual(self.client.get("/api/stats").status_code, 401)
            with factory() as db:
                app.record_metric(db, "signin", "owner")
                app.record_metric(db, "signin", "owner")
                app.record_metric(db, "signin", "someone-else")
                db.add(
                    app.AnalyticsCount(
                        day=datetime.now(timezone.utc).date() - timedelta(days=91),
                        kind="view",
                        visitor="old",
                        count=1,
                    )
                )
                db.commit()
                app.record_metric(db, "view", visitor)
                db.commit()
                rows = db.query(app.AnalyticsCount).all()
                self.assertEqual(len(rows), 4)
                self.assertTrue(all(len(row.visitor) == 64 for row in rows))
                self.assertTrue(
                    all(
                        row.visitor not in (visitor, "owner", "someone-else")
                        for row in rows
                    )
                )
                self.assertNotEqual(
                    next(row.visitor for row in rows if row.kind == "view"),
                    next(row.visitor for row in rows if row.kind == "signin"),
                )
            discord = AsyncMock()
            discord.get.return_value = MagicMock(json=lambda: {"owner_id": "owner"})
            with patch.object(app, "DISCORD_BOT_TOKEN", "test-bot"), patch.object(
                app, "YIW_SERVER_ID", "test-guild"
            ), patch.object(app.httpx, "AsyncClient") as client:
                client.return_value.__aenter__.return_value = discord
                for account, expected in (("other", 403), ("owner", 200)):
                    self.client.cookies.clear()
                    payload = base64.b64encode(
                        json.dumps({"discord_id": account}).encode()
                    )
                    self.client.cookies.set(
                        "yiw_session",
                        TimestampSigner("test-secret-only").sign(payload).decode(),
                    )
                    response = self.client.get("/api/stats?days=7")
                    self.assertEqual(response.status_code, expected)
                users = {
                    user["username"]: user
                    for user in response.json()["signed_in_users"]
                }
                self.assertEqual(set(users), {"ServerOwner", "Visitor"})
                self.assertEqual(users["ServerOwner"]["count"], 2)
                self.assertEqual(users["Visitor"]["count"], 1)
                self.assertTrue(users["ServerOwner"]["last_signin"].endswith("+00:00"))
                data = response.json()["daily"]
                self.assertEqual(len(data), 7)
                self.assertEqual(
                    data[0],
                    {
                        "date": datetime.now(timezone.utc).date().isoformat(),
                        "views": 4,
                        "visitors": 2,
                        "signins": 3,
                        "accounts": 2,
                    },
                )
                self.assertEqual(data[1]["views"], 0)
                self.assertEqual(
                    self.client.get("/api/stats?days=100").status_code, 422
                )
        finally:
            app.app.dependency_overrides[app.get_db] = lambda: self.db
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
