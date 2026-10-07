import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from uuid import UUID, uuid4

import httpx
from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from starlette.middleware.sessions import SessionMiddleware

from community import (
    aggregate_locations,
    avatar_url,
    build_timeline,
    fetch_members,
    fetch_server_info,
    server_created_date,
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


class ProfileComment(Base):
    __tablename__ = "profile_comments"
    __table_args__ = (
        UniqueConstraint("profile_id", "author_id", "slot"),
        CheckConstraint("slot IN (1, 2)"),
    )
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    profile_id = Column(String, nullable=False, index=True)
    author_id = Column(String, ForeignKey("users.discord_id"), nullable=False)
    slot = Column(Integer, nullable=False)
    body = Column(String(200), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(DateTime(timezone=True), nullable=True)


class AnalyticsCount(Base):
    __tablename__ = "analytics_counts"
    day = Column(Date, primary_key=True)
    kind = Column(String, primary_key=True)
    visitor = Column(String(64), primary_key=True)
    count = Column(Integer, nullable=False)


class SignInCount(Base):
    __tablename__ = "signin_counts"
    day = Column(Date, primary_key=True)
    user_id = Column(String, ForeignKey("users.discord_id"), primary_key=True)
    count = Column(Integer, nullable=False)
    last_signin = Column(DateTime(timezone=True), nullable=False)


def record_metric(db, kind, identifier):
    today = datetime.now(timezone.utc).date()
    digest = hmac.new(
        SESSION_SECRET.encode(), f"{today}:{kind}:{identifier}".encode(), hashlib.sha256
    ).hexdigest()
    insert = (
        sqlite_insert if db.get_bind().dialect.name == "sqlite" else postgres_insert
    )
    statement = insert(AnalyticsCount).values(
        day=today, kind=kind, visitor=digest, count=1
    )
    db.execute(
        statement.on_conflict_do_update(
            index_elements=["day", "kind", "visitor"],
            set_={"count": AnalyticsCount.count + 1},
        )
    )
    if kind == "signin":
        statement = insert(SignInCount).values(
            day=today,
            user_id=identifier,
            count=1,
            last_signin=datetime.now(timezone.utc),
        )
        db.execute(
            statement.on_conflict_do_update(
                index_elements=["day", "user_id"],
                set_={
                    "count": SignInCount.count + 1,
                    "last_signin": statement.excluded.last_signin,
                },
            )
        )
    cutoff = today - timedelta(days=89)
    for model in (AnalyticsCount, SignInCount):
        db.query(model).filter(model.day < cutoff).delete(synchronize_session=False)


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


def require_same_origin(request: Request):
    if request.headers.get("origin") != PUBLIC_URL:
        raise HTTPException(403, "Invalid request origin.")


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
            "scope": "identify",
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
        db.flush()
        record_metric(db, "signin", discord_id)
        db.commit()
        db.refresh(existing_user if existing_user else new_user)

        request.session.clear()
        request.session["discord_id"] = discord_id
        response = RedirectResponse(url=PUBLIC_URL + "/members")
        response.delete_cookie("discord_id")
        return response


@app.post("/api/visits", status_code=204)
def count_visit(
    request: Request,
    visitor: UUID = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    require_same_origin(request)
    record_metric(db, "view", str(visitor))
    db.commit()


@app.get("/api/stats")
async def site_stats(
    request: Request, days: int = Query(30, ge=1, le=90), db: Session = Depends(get_db)
):
    discord_id = request.session.get("discord_id")
    if not discord_id:
        raise HTTPException(
            401, "Sign in with the server owner's Discord account to view statistics."
        )
    if not DISCORD_BOT_TOKEN or not YIW_SERVER_ID:
        raise HTTPException(503, "Discord server access has not been configured.")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"https://discord.com/api/v10/guilds/{YIW_SERVER_ID}",
                headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"},
            )
            response.raise_for_status()
            owner_id = response.json()["owner_id"]
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(
            503, "Could not verify the server owner. Please try again."
        ) from None
    if discord_id != owner_id:
        raise HTTPException(403, "Only the Discord server owner can view statistics.")
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)
    rows = (
        db.query(
            AnalyticsCount.day,
            AnalyticsCount.kind,
            func.sum(AnalyticsCount.count),
            func.count(),
        )
        .filter(AnalyticsCount.day >= start, AnalyticsCount.day <= today)
        .group_by(AnalyticsCount.day, AnalyticsCount.kind)
        .all()
    )
    daily = {}
    for offset in range(days):
        day = start + timedelta(days=offset)
        daily[day] = {
            "date": day.isoformat(),
            "views": 0,
            "visitors": 0,
            "signins": 0,
            "accounts": 0,
        }
    for day, kind, total, unique in rows:
        total_key, unique_key = (
            ("views", "visitors") if kind == "view" else ("signins", "accounts")
        )
        daily[day][total_key] = total
        daily[day][unique_key] = unique
    accounts = (
        db.query(
            User.discord_id,
            User.username,
            func.sum(SignInCount.count),
            func.max(SignInCount.last_signin),
        )
        .join(SignInCount, SignInCount.user_id == User.discord_id)
        .filter(SignInCount.day >= start, SignInCount.day <= today)
        .group_by(User.discord_id, User.username)
        .order_by(func.max(SignInCount.last_signin).desc(), User.discord_id)
        .all()
    )
    return JSONResponse(
        {
            "daily": list(reversed(daily.values())),
            "signed_in_users": [
                {
                    "id": user_id,
                    "username": username,
                    "count": count,
                    "last_signin": (
                        last_signin.replace(tzinfo=timezone.utc)
                        if last_signin.tzinfo is None
                        else last_signin.astimezone(timezone.utc)
                    ).isoformat(),
                }
                for user_id, username, count, last_signin in accounts
            ],
        },
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/logout", status_code=204)
def logout(request: Request):
    require_same_origin(request)
    request.session.clear()


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
    bio: str = Body(..., max_length=64),
    mc_name: str = Body(..., max_length=16),
    detailed_bio: str | None = Body(None, max_length=500),
    preferred_name: str | None = Body(None, max_length=16),
):
    require_same_origin(request)
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


def comment_author(request: Request, db: Session = Depends(get_db)):
    require_same_origin(request)
    discord_id = request.session.get("discord_id")
    user = db.get(User, discord_id) if discord_id else None
    if user is None:
        raise HTTPException(401, "Sign in with Discord to comment.")
    return user


def comment_text(body):
    body = body.strip()
    if not body:
        raise HTTPException(422, "Comments cannot be blank.")
    return body


def serialize_comment(comment, author):
    return {
        "id": comment.id,
        "author_id": comment.author_id,
        "username": author.username,
        "body": comment.body,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
    }


@app.get("/api/members/{profile_id}/comments")
def get_comments(profile_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(ProfileComment, User)
        .join(User, ProfileComment.author_id == User.discord_id)
        .filter(ProfileComment.profile_id == profile_id)
        .order_by(ProfileComment.created_at, ProfileComment.id)
        .all()
    )
    return {
        "comments": [serialize_comment(comment, author) for comment, author in rows]
    }


@app.post("/api/members/{profile_id}/comments", status_code=201)
async def create_comment(
    profile_id: str,
    body: str = Body(..., embed=True, min_length=1, max_length=200),
    author: User = Depends(comment_author),
    db: Session = Depends(get_db),
):
    body = comment_text(body)
    members = await fetch_members(DISCORD_BOT_TOKEN, YIW_SERVER_ID)
    if not any(
        m["user"]["id"] == profile_id and not m["user"].get("bot") for m in members
    ):
        raise HTTPException(404, "Member profile not found.")
    # Serialize this author's inserts; the slot constraint also enforces the limit.
    db.query(User).filter(User.discord_id == author.discord_id).with_for_update().one()
    used = {
        row.slot
        for row in db.query(ProfileComment)
        .filter_by(profile_id=profile_id, author_id=author.discord_id)
        .all()
    }
    slot = next((slot for slot in (1, 2) if slot not in used), None)
    if slot is None:
        raise HTTPException(409, "You can leave up to two comments on each profile.")
    comment = ProfileComment(
        profile_id=profile_id, author_id=author.discord_id, slot=slot, body=body
    )
    db.add(comment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Your comments changed. Refresh and try again."
        ) from None
    db.refresh(comment)
    return serialize_comment(comment, author)


def owned_comment(comment_id, author, db):
    comment = db.get(ProfileComment, comment_id)
    if comment is None:
        raise HTTPException(404, "Comment not found.")
    if comment.author_id != author.discord_id:
        raise HTTPException(403, "You can only change your own comments.")
    return comment


@app.patch("/api/comments/{comment_id}")
def edit_comment(
    comment_id: str,
    body: str = Body(..., embed=True, min_length=1, max_length=200),
    author: User = Depends(comment_author),
    db: Session = Depends(get_db),
):
    comment = owned_comment(comment_id, author, db)
    comment.body = comment_text(body)
    comment.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(comment)
    return serialize_comment(comment, author)


@app.delete("/api/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: str,
    author: User = Depends(comment_author),
    db: Session = Depends(get_db),
):
    db.delete(owned_comment(comment_id, author, db))
    db.commit()


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
    return {
        **build_timeline(members, events),
        "server_created_at": (
            server_created_date(YIW_SERVER_ID)
            if YIW_SERVER_ID and YIW_SERVER_ID.isdecimal()
            else None
        ),
    }


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
        created_at = server_created_date(YIW_SERVER_ID)
    return {
        "server_created_at": created_at,
        "events": sorted(
            merged.values(),
            key=lambda event: (event["date"], event["id"]),
            reverse=True,
        ),
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
    @app.get("/stats")
    def website():
        return FileResponse(
            STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"}
        )

    app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
