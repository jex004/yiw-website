import unittest
from events import normalize_events


class EventsTests(unittest.TestCase):
    def test_sort_and_optional_fields(self):
        result = normalize_events(
            [
                {"id": "a", "date": "2020-01-01", "title": "First"},
                {
                    "id": "b",
                    "date": "2024-01-01",
                    "title": "Second",
                    "images": [
                        {"url": "/events/one.jpg", "alt": "First photo"},
                        {"url": "https://example.com/two.jpg"},
                    ],
                },
            ]
        )
        self.assertEqual([event["id"] for event in result], ["b", "a"])
        self.assertEqual(result[0]["images"][1]["alt"], "Second")
        self.assertEqual(result[1]["images"], [])
        self.assertEqual(result[1]["description"], "")

    def test_rejects_bad_dates_duplicate_ids_and_images(self):
        valid = {"id": "a", "date": "2024-01-01", "title": "Event"}
        for rows in (
            [dict(valid, date="2024-02-30")],
            [valid, valid],
            [dict(valid, images=[{"url": "javascript:alert(1)"}])],
            [dict(valid, images={"url": "/events/photo.jpg"})],
            [dict(valid, summary=123)],
            [dict(valid, title="")],
        ):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                normalize_events(rows)

    def test_more_than_two_images_are_preserved(self):
        images = [{"url": f"/events/photo-{index}.jpg"} for index in range(5)]
        result = normalize_events(
            [
                {
                    "id": "photos",
                    "date": "2024-01-01",
                    "title": "Photos",
                    "images": images,
                }
            ]
        )
        self.assertEqual(
            [image["url"] for image in result[0]["images"]],
            [image["url"] for image in images],
        )

    def test_empty(self):
        self.assertEqual(normalize_events([]), [])


if __name__ == "__main__":
    unittest.main()
