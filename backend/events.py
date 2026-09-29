"""Validate owner-authored event content without loading app configuration."""

from datetime import date
from urllib.parse import urlsplit


def normalize_events(rows):
    if not isinstance(rows, list):
        raise ValueError("Events must be a list")
    events = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each event must be an object")
        for field in ("id", "date", "title"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"Event requires {field}")
        if row["id"] in seen:
            raise ValueError("Event IDs must be unique")
        seen.add(row["id"])
        date.fromisoformat(row["date"])
        if len(row["date"]) != 10:
            raise ValueError("Use YYYY-MM-DD dates")
        for field in ("summary", "description"):
            if not isinstance(row.get(field, ""), str):
                raise ValueError(f"{field} must be text")
        images = row.get("images", [])
        if not isinstance(images, list) or len(images) > 2:
            raise ValueError("Use up to two images per event")
        for image in images:
            if not isinstance(image, dict) or not isinstance(image.get("url"), str):
                raise ValueError("Images need a URL")
            url = image["url"]
            parsed = urlsplit(url)
            if not (
                url.startswith("/events/")
                or (parsed.scheme == "https" and parsed.netloc)
            ):
                raise ValueError("Use /events/ paths or HTTPS image URLs")
            if "\\" in url or any(ord(char) < 32 for char in url):
                raise ValueError("Invalid image URL")
            if not isinstance(image.get("alt", ""), str):
                raise ValueError("Image alt text must be a string")
        events.append(
            {
                "id": row["id"],
                "date": row["date"],
                "title": row["title"],
                "summary": row.get("summary", ""),
                "description": row.get("description", ""),
                "images": [
                    {"url": img["url"], "alt": img.get("alt", row["title"])}
                    for img in images
                ],
            }
        )
    return sorted(events, key=lambda event: (event["date"], event["id"]), reverse=True)
