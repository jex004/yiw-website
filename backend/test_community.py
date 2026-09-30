import unittest

from community import aggregate_locations, build_timeline, build_server_info, avatar_url


def member(id, joined_at, bot=False, avatar=None):
    return {
        "user": {"id": id, "username": f"member-{id}", "bot": bot, "avatar": avatar},
        "joined_at": joined_at,
    }


class AvatarTests(unittest.TestCase):
    def test_custom_and_context_specific_fallbacks(self):
        self.assertEqual(
            avatar_url({"id": "123", "avatar": "abc"}),
            "https://cdn.discordapp.com/avatars/123/abc.png",
        )
        self.assertEqual(
            avatar_url({"id": "123"}), "https://cdn.discordapp.com/embed/avatars/0.png"
        )
        self.assertIsNone(avatar_url({"id": "123"}, fallback=None))


class ServerInfoTests(unittest.TestCase):
    def test_server_expressions_formats_and_empty_defaults(self):
        guild = dict(
            self.guild,
            emojis=[
                {"id": "1", "name": "wave", "animated": True},
                {"id": "2", "name": "apple", "animated": False},
            ],
            stickers=[
                {"id": str(i), "name": f"Sticker {i}", "format_type": i}
                for i in range(1, 5)
            ],
        )
        result = build_server_info(guild, [])
        self.assertEqual(result["emojis"][0]["name"], "apple")
        self.assertIn("animated=true", result["emojis"][1]["image_url"])
        self.assertIn("animated=false", result["emojis"][1]["still_url"])
        self.assertTrue(result["stickers"][0]["image_url"].endswith(".png"))
        self.assertTrue(result["stickers"][1]["animated"])
        self.assertIsNone(result["stickers"][2]["image_url"])
        self.assertEqual(
            result["stickers"][3]["image_url"],
            "https://media.discordapp.net/stickers/4.gif",
        )
        self.assertEqual(build_server_info(self.guild, [])["emojis"], [])
        self.assertEqual(build_server_info(self.guild, [])["stickers"], [])

    guild = {
        "id": str((1704067200000 - 1420070400000) << 22),
        "name": "Test server",
        "owner_id": "1",
        "description": "About the server",
        "icon": "hash",
    }

    def test_server_creation_date_owner_and_human_count(self):
        owner = member("1", None)
        owner["nick"] = "Owner nickname"
        result = build_server_info(
            self.guild, [owner, member("2", None), member("3", None, bot=True)]
        )
        self.assertEqual(result["founded_at"], "2024-01-01")
        self.assertEqual(result["owner_name"], "Owner nickname")
        self.assertEqual(result["member_count"], 2)
        self.assertEqual(result["name"], "Test server")
        self.assertIn("/hash.png", result["icon_url"])

    def test_missing_owner_and_optional_details(self):
        result = build_server_info(dict(self.guild, icon=None, description=None), [])
        self.assertIsNone(result["owner_name"])
        self.assertIsNone(result["icon_url"])
        self.assertIsNone(result["description"])
        self.assertEqual(result["member_count"], 0)

    def test_owner_display_name_falls_back_to_username(self):
        owner = member("1", None)
        self.assertEqual(
            build_server_info(self.guild, [owner])["owner_name"], "member-1"
        )
        owner["user"]["global_name"] = "Display name"
        self.assertEqual(
            build_server_info(self.guild, [owner])["owner_name"], "Display name"
        )


class LocationTests(unittest.TestCase):
    countries = {
        "USA": {"code": "USA", "name": "United States", "coords": [-97, 38]},
        "JPN": {"code": "JPN", "name": "Japan", "coords": [138, 36]},
    }

    def test_totals_sorted_and_zero_omitted(self):
        self.assertEqual(
            aggregate_locations({"USA": 3, "JPN": 1}, self.countries),
            [
                dict(self.countries["USA"], count=3),
                dict(self.countries["JPN"], count=1),
            ],
        )
        self.assertEqual(aggregate_locations({"USA": 0}, self.countries), [])
        self.assertEqual(aggregate_locations({}, self.countries), [])

    def test_invalid_counts_and_individual_assignments_rejected(self):
        for counts in (
            [],
            {"USA": -1},
            {"USA": True},
            {"USA": 1.5},
            {"USA": "2"},
            {"US": 2},
            {"123": {"name": "Example", "country": "USA"}},
        ):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                aggregate_locations(counts, self.countries)


class TimelineTests(unittest.TestCase):
    def test_same_day_joins_are_grouped_and_bots_excluded(self):
        result = build_timeline(
            [
                member("1", "2024-02-01T12:00:00Z"),
                member("2", "2024-01-01T12:00:00Z"),
                member("3", "2024-01-01T14:00:00Z"),
                member("4", "2024-01-01T14:00:00Z", bot=True),
            ],
            [],
            today="2024-03-01",
        )
        self.assertEqual(
            result["chart_data"],
            [
                {"date": "2024-01-01", "joins": 2, "total_members": 2},
                {"date": "2024-02-01", "joins": 1, "total_members": 3},
                {"date": "2024-03-01", "joins": 0, "total_members": 3},
            ],
        )
        self.assertEqual(result["current_members"], 3)
        self.assertEqual(result["timeline"][0]["id"], "1")

    def test_missing_invalid_future_dates_and_utc_conversion(self):
        result = build_timeline(
            [
                member("1", None),
                member("2", "invalid"),
                member("3", "2025-01-01T00:00:00Z"),
                member("4", "2024-01-02T01:00:00+02:00"),
            ],
            [],
            today="2024-01-02",
        )
        self.assertEqual(result["missing_join_dates"], 3)
        self.assertEqual(result["chart_data"][0]["date"], "2024-01-01")

    def test_empty_and_milestones_only(self):
        event = {
            "type": "custom",
            "id": "launch",
            "date": "2020-01-01",
            "title": "Launch",
        }
        result = build_timeline([], [event], today="2024-01-01")
        self.assertEqual(result["chart_data"], [])
        self.assertEqual(result["timeline"], [event])

    def test_avatar_urls_and_no_duplicate_today(self):
        result = build_timeline(
            [
                member("1", "2024-01-01T00:00:00Z"),
                member("2", "2024-01-01T01:00:00Z", avatar="hash"),
            ],
            [],
            today="2024-01-01",
        )
        self.assertEqual(len(result["chart_data"]), 1)
        self.assertEqual(
            result["timeline"][0]["avatar_url"],
            "https://cdn.discordapp.com/embed/avatars/0.png",
        )
        self.assertEqual(
            result["timeline"][1]["avatar_url"],
            "https://cdn.discordapp.com/avatars/2/hash.png",
        )


if __name__ == "__main__":
    unittest.main()
