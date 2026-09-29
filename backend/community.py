"""Discord member loading and timeline calculations (no environment or database access)."""

from collections import Counter
from datetime import datetime, timezone


def build_server_info(guild, members):
    created_ms = (int(guild["id"]) >> 22) + 1420070400000
    owner = next(
        (member for member in members if member["user"]["id"] == guild["owner_id"]),
        None,
    )
    owner_name = None
    if owner:
        owner_name = (
            owner.get("nick")
            or owner["user"].get("global_name")
            or owner["user"]["username"]
        )
    icon = guild.get("icon")
    emojis = [
        {
            "id": emoji["id"],
            "name": emoji.get("name") or "Unnamed emoji",
            "animated": bool(emoji.get("animated")),
            "image_url": f"https://cdn.discordapp.com/emojis/{emoji['id']}.webp?size=96"
            + ("&animated=true" if emoji.get("animated") else ""),
            "still_url": f"https://cdn.discordapp.com/emojis/{emoji['id']}.webp?size=96&animated=false",
        }
        for emoji in guild.get("emojis", [])
        if emoji.get("id")
    ]
    stickers = []
    for sticker in guild.get("stickers", []):
        format_type = sticker.get("format_type")
        sticker_id = sticker["id"]
        image_url = None
        if format_type in (1, 2):
            image_url = f"https://cdn.discordapp.com/stickers/{sticker_id}.png"
        elif format_type == 4:
            image_url = f"https://media.discordapp.net/stickers/{sticker_id}.gif"
        stickers.append(
            {
                "id": sticker_id,
                "name": sticker["name"],
                "description": sticker.get("description") or "",
                "animated": format_type in (2, 3, 4),
                "image_url": image_url,
                "discord_url": f"https://discord.com/channels/{guild['id']}",
            }
        )
    return {
        "name": guild["name"],
        "description": guild.get("description"),
        "founded_at": datetime.fromtimestamp(created_ms / 1000, timezone.utc)
        .date()
        .isoformat(),
        "owner_name": owner_name,
        "member_count": sum(not member["user"].get("bot", False) for member in members),
        "icon_url": (
            f"https://cdn.discordapp.com/icons/{guild['id']}/{icon}.png?size=256"
            if icon
            else None
        ),
        "emojis": sorted(emojis, key=lambda item: item["name"].casefold()),
        "stickers": sorted(stickers, key=lambda item: item["name"].casefold()),
    }


async def fetch_server_info(token, guild_id):
    import asyncio
    import httpx
    from fastapi import HTTPException

    if not token or not guild_id:
        raise HTTPException(503, "Discord server access has not been configured.")
    async with httpx.AsyncClient(timeout=20) as client:

        async def fetch_guild():
            try:
                response = await client.get(
                    f"https://discord.com/api/v10/guilds/{guild_id}",
                    headers={"Authorization": f"Bot {token}"},
                )
                response.raise_for_status()
                guild = response.json()
                if not isinstance(guild, dict) or not all(
                    guild.get(key) for key in ("id", "name", "owner_id")
                ):
                    raise ValueError("Missing server information")
                return guild
            except (httpx.HTTPError, ValueError):
                raise HTTPException(
                    502, "Could not load server information. Please try again later."
                ) from None

        guild, members = await asyncio.gather(
            fetch_guild(), fetch_members(token, guild_id)
        )
    return build_server_info(guild, members)


def aggregate_locations(counts, countries):
    if not isinstance(counts, dict):
        raise ValueError("Expected country counts")
    for code, count in counts.items():
        if code not in countries or type(count) is not int or count < 0:
            raise ValueError("Use known country codes and nonnegative integer counts")
    return [
        dict(countries[code], count=count)
        for code, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if count > 0
    ]


async def fetch_members(token, guild_id):
    import httpx
    from fastapi import HTTPException

    if not token or not guild_id:
        raise HTTPException(503, "Discord member access has not been configured.")
    members = {}
    after = "0"
    async with httpx.AsyncClient(timeout=20) as client:
        while True:
            try:
                response = await client.get(
                    f"https://discord.com/api/v10/guilds/{guild_id}/members",
                    headers={"Authorization": f"Bot {token}"},
                    params={"limit": 1000, "after": after},
                )
                response.raise_for_status()
                page = response.json()
            except (httpx.HTTPError, ValueError):
                raise HTTPException(
                    502, "Could not load Discord members. Please try again later."
                ) from None
            if not isinstance(page, list):
                raise HTTPException(
                    502, "Discord returned an unexpected member response."
                )
            for member in page:
                members[member["user"]["id"]] = member
            if len(page) < 1000:
                return list(members.values())
            next_after = max((member["user"]["id"] for member in page), key=int)
            if int(next_after) <= int(after):
                raise HTTPException(
                    502, "Could not load the complete Discord member list."
                )
            after = next_after


def build_timeline(members, custom_events, today=None):
    today = today or datetime.now(timezone.utc).date().isoformat()
    joins = []
    human_count = 0
    for member in members:
        user = member["user"]
        if user.get("bot"):
            continue
        human_count += 1
        try:
            joined = datetime.fromisoformat(member["joined_at"].replace("Z", "+00:00"))
            if joined.tzinfo is None:
                joined = joined.replace(tzinfo=timezone.utc)
            day = joined.astimezone(timezone.utc).date().isoformat()
            if day > today:
                continue
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        avatar = user.get("avatar")
        joins.append(
            {
                "type": "join",
                "id": user["id"],
                "date": day,
                "username": user["username"],
                "avatar_url": (
                    f"https://cdn.discordapp.com/avatars/{user['id']}/{avatar}.png"
                    if avatar
                    else "https://cdn.discordapp.com/embed/avatars/0.png"
                ),
            }
        )
    daily = Counter(event["date"] for event in joins)
    chart = []
    total = 0
    for day, count in sorted(daily.items()):
        total += count
        chart.append({"date": day, "joins": count, "total_members": total})
    if chart and chart[-1]["date"] < today:
        chart.append({"date": today, "joins": 0, "total_members": total})
    return {
        "timeline": sorted(
            joins + custom_events, key=lambda event: event["date"], reverse=True
        ),
        "chart_data": chart,
        "current_members": human_count,
        "missing_join_dates": human_count - len(joins),
    }
