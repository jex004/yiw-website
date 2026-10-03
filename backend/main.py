import os
import json
import secrets
import time
from urllib.parse import urlencode
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi import FastAPI, Depends, Request, Body, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, Column, String, Date
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime, timezone
from community import (
    aggregate_locations,
    avatar_url,
    build_timeline,
    fetch_members,
    fetch_server_info,
)
from events import normalize_events

load_dotenv()
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:5173").rstrip("/")
REDIRECT_URI = PUBLIC_URL + "/auth/callback"
SESSION_SECRET = os.getenv("SESSION_SECRET")
if not SESSION_SECRET:
    if os.getenv("RAILWAY_ENVIRONMENT_ID") or PUBLIC_URL.startswith("https://"):
        raise RuntimeError("SESSION_SECRET must be configured for deployment")
    SESSION_SECRET = secrets.token_urlsafe(48)
YIW_SERVER_ID = os.getenv("YIW_SERVER_ID")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


DATABASE_URL = os.environ["DATABASE_URL"]
if DATABASE_URL.startswith(("postgres://", "postgresql://")):
    DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL.split("://", 1)[1]
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def read_content(filename):
    return json.loads(Path(__file__).with_name(filename).read_text(encoding="utf-8"))


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    discord_id = Column(String, primary_key=True, index=True)
    username = Column(String)
    avatar_url = Column(String)
    minecraft_username = Column(String)
    preferred_name = Column(String)
    bio = Column(String)
    detailed_bio = Column(String)


class TimelineEvent(Base):
    __tablename__ = "events"
    id = Column(String, primary_key=True, index=True)
    event_date = Column(Date)
    title = Column(String)
    description = Column(String)
    icon = Column(String)


Base.metadata.create_all(bind=engine)

# Keep existing profile tables compatible.
with engine.connect() as conn:
    for column in ("preferred_name", "minecraft_username", "bio", "detailed_bio"):
        conn.execute(
            text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column} VARCHAR;")
        )
    conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[PUBLIC_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="yiw_session",
    max_age=60 * 60 * 24 * 7,
    same_site="lax",
    https_only=PUBLIC_URL.startswith("https://"),
)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/login")
def login(request: Request):
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(503, "Discord login is not configured.")
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    request.session["oauth_started"] = time.time()
    query = urlencode(
        {
            "client_id": CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": "identify guilds",
            "state": state,
        }
    )
    return RedirectResponse("https://discord.com/oauth2/authorize?" + query)


@app.get("/auth/callback")
async def auth_callback(
    request: Request, code: str, state: str = "", db: Session = Depends(get_db)
):
    expected = request.session.pop("oauth_state", "")
    started = request.session.pop("oauth_started", 0)
    if (
        not expected
        or not secrets.compare_digest(state, expected)
        or time.time() - started > 600
    ):
        raise HTTPException(400, "Login expired or invalid. Please sign in again.")

    token_url = "https://discord.com/api/oauth2/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=data, headers=headers)
        token_json = token_response.json()
        access_token = token_json.get("access_token")

        if not access_token:
            return {"error": "Failed to get access token from Discord"}

        user_response = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_data = user_response.json()

        guilds_response = await client.get(
            "https://discord.com/api/users/@me/guilds",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        guilds_data = guilds_response.json()

        is_in_server = any(guild["id"] == YIW_SERVER_ID for guild in guilds_data)

        if not is_in_server:
            return {
                "error": "Access Denied. You are not a member of the required Discord server."
            }

        discord_id = user_data["id"]
        username = user_data["username"]
        user_avatar = avatar_url(user_data, fallback=None)

        existing_user = db.query(User).filter(User.discord_id == discord_id).first()

        if existing_user:
            existing_user.username = username
            existing_user.avatar_url = user_avatar
        else:
            new_user = User(
                discord_id=discord_id, username=username, avatar_url=user_avatar
            )
            db.add(new_user)
        db.commit()
        db.refresh(existing_user if existing_user else new_user)

        request.session.clear()
        request.session["discord_id"] = discord_id
        response = RedirectResponse(url=PUBLIC_URL + "/members")
        response.delete_cookie("discord_id")
        return response


@app.get("/api/me")
def get_current_user(request: Request, db: Session = Depends(get_db)):
    discord_id = request.session.get("discord_id")

    if not discord_id:
        return {"authenticated": False}

    user = db.query(User).filter(User.discord_id == discord_id).first()

    if not user:
        return {"authenticated": False}

    return {
        "authenticated": True,
        "user": {
            "discord_id": user.discord_id,
            "username": user.username,
            "avatar_url": user.avatar_url,
        },
    }


@app.get("/api/members")
async def get_member_directory(db: Session = Depends(get_db)):
    discord_members = await fetch_members(DISCORD_BOT_TOKEN, YIW_SERVER_ID)

    all_db_users = db.query(User).all()
    db_user_map = {user.discord_id: user for user in all_db_users}

    directory = []

    for member in discord_members:
        user_data = member["user"]

        if user_data.get("bot"):
            continue

        discord_id = user_data["id"]
        username = user_data["username"]

        raw_date = member.get("joined_at", "")
        try:
            join_date_obj = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            date_joined = join_date_obj.strftime("%b %Y")
        except Exception:
            date_joined = "Unknown"

        db_profile = db_user_map.get(discord_id)
        directory.append(
            {
                "id": discord_id,
                "username": username,
                "avatar_url": avatar_url(user_data),
                "minecraft_username": (
                    (db_profile.minecraft_username or "Not set")
                    if db_profile
                    else "Not set"
                ),
                "date_joined": date_joined,
                "bio": (db_profile.bio or "") if db_profile else "",
                "detailed_bio": (db_profile.detailed_bio or "") if db_profile else "",
                "preferred_name": (
                    (db_profile.preferred_name or "") if db_profile else ""
                ),
                "has_claimed_profile": bool(db_profile),
            }
        )

    return {"members": directory}


@app.post("/api/profile/update")
def update_profile(
    request: Request,
    db: Session = Depends(get_db),
    bio: str = Body(...),
    mc_name: str = Body(...),
    detailed_bio: str | None = Body(None, max_length=10000),
    preferred_name: str | None = Body(None, max_length=80),
):
    if request.headers.get("origin") != PUBLIC_URL:
        raise HTTPException(403, "Invalid request origin.")
    discord_id = request.session.get("discord_id")
    if not discord_id:
        return {"error": "Not logged in"}

    user = db.query(User).filter(User.discord_id == discord_id).first()
    if not user:
        return {"error": "User not found"}

    if detailed_bio is not None:
        user.detailed_bio = detailed_bio
    if preferred_name is not None:
        user.preferred_name = preferred_name.strip()
    user.bio = bio
    user.minecraft_username = mc_name
    db.commit()
    return {"status": "success"}


@app.get("/api/timeline")
async def get_timeline(db: Session = Depends(get_db)):
    members = await fetch_members(DISCORD_BOT_TOKEN, YIW_SERVER_ID)
    events = [
        {
            "type": "custom",
            "id": event.id,
            "date": event.event_date.isoformat(),
            "title": event.title,
            "description": event.description,
            "icon": event.icon,
        }
        for event in db.query(TimelineEvent).all()
        if event.event_date
    ]
    return build_timeline(members, events)


@app.get("/api/server")
async def get_server_info():
    return await fetch_server_info(DISCORD_BOT_TOKEN, YIW_SERVER_ID)


@app.get("/api/events")
def get_events(db: Session = Depends(get_db)):
    try:
        authored = normalize_events(read_content("timeline_events.json"))
    except (OSError, ValueError):
        raise HTTPException(
            503, "Event details need to be checked by the server owner."
        ) from None
    # File entries can add photos/details to an existing database event by matching its ID.
    merged = {
        event.id: {
            "id": event.id,
            "date": event.event_date.isoformat(),
            "title": event.title or "Untitled event",
            "summary": "",
            "description": event.description or "",
            "images": [],
        }
        for event in db.query(TimelineEvent).all()
        if event.event_date
    }
    merged.update({event["id"]: event for event in authored})
    created_at = None
    if YIW_SERVER_ID and YIW_SERVER_ID.isdecimal():
        created_at = datetime.fromtimestamp(
            ((int(YIW_SERVER_ID) >> 22) + 1420070400000) / 1000, timezone.utc
        ).date().isoformat()
    return {
        "server_created_at": created_at,
        "events": sorted(
            merged.values(),
            key=lambda event: (event["date"], event["id"]),
            reverse=True,
        )
    }


@app.get("/api/countries")
def get_countries():
    return read_content("countries.json")


@app.get("/api/locations")
async def get_member_locations():
    try:
        counts = read_content("member_countries.json")
        countries = {
            country["code"]: country for country in read_content("countries.json")
        }
        return aggregate_locations(counts, countries)
    except (OSError, ValueError):
        raise HTTPException(
            503, "Country counts need to be checked by the server owner."
        ) from None


STATIC_DIR = Path(os.getenv("STATIC_DIR", "/app/static"))
if STATIC_DIR.is_dir():

    @app.get("/")
    @app.get("/members")
    @app.get("/map")
    @app.get("/timeline")
    @app.get("/gallery")
    def website():
        return FileResponse(
            STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"}
        )

    app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
