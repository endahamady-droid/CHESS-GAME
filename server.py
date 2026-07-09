from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import secrets
import sqlite3
import subprocess
import time
from http import cookies
from urllib.parse import quote

try:
    import bcrypt
except ImportError:
    bcrypt = None

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None


ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(ROOT, "chess_online.db"))
DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_POSTGRES = bool(DATABASE_URL)
ENGINE_PATH = os.path.join(ROOT, "engine.exe" if os.name == "nt" else "engine")
PUBLIC_PATH = os.path.join(ROOT, "public")
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8080"))
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "babba")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "130577")
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", str(60 * 60 * 12)))
RATE_LIMIT_WINDOW = 60
RATE_LIMITS = {
    "global": (240, RATE_LIMIT_WINDOW),
    "login": (5, 15 * 60),
    "register": (10, RATE_LIMIT_WINDOW),
    "rooms": (20, RATE_LIMIT_WINDOW),
    "chat": (30, RATE_LIMIT_WINDOW),
    "moves": (60, RATE_LIMIT_WINDOW),
}
RATE_BUCKETS = {}
TWOFA_CHALLENGES = {}


class Database:
    def __init__(self, connection, is_postgres=False):
        self.connection = connection
        self.is_postgres = is_postgres

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()
        self.connection.close()

    def _sql(self, sql):
        return sql.replace("?", "%s") if self.is_postgres else sql

    def execute(self, sql, params=()):
        return self.connection.execute(self._sql(sql), params)

    def executescript(self, script):
        if not self.is_postgres:
            return self.connection.executescript(script)
        for statement in [part.strip() for part in script.split(";") if part.strip()]:
            self.execute(statement)


def connect_db():
    if USE_POSTGRES:
        if psycopg is None:
            raise RuntimeError("psycopg_missing_install_requirements")
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        return Database(conn, True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return Database(conn, False)


def init_db():
    with connect_db() as db:
        id_type = "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
        db.executescript(
            f"""
            CREATE TABLE IF NOT EXISTS players (
                id {id_type},
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                is_disabled INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                draws INTEGER NOT NULL DEFAULT 0,
                elo INTEGER NOT NULL DEFAULT 1200,
                provider TEXT NOT NULL DEFAULT 'local',
                provider_id TEXT,
                quiz_level_reached INTEGER NOT NULL DEFAULT 1,
                quiz_score INTEGER NOT NULL DEFAULT 0,
                games_played INTEGER NOT NULL DEFAULT 0,
                twofa_secret TEXT,
                twofa_enabled INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rooms (
                id {id_type},
                code TEXT UNIQUE NOT NULL,
                white_player_id INTEGER NOT NULL REFERENCES players(id),
                black_player_id INTEGER REFERENCES players(id),
                fen TEXT NOT NULL,
                turn TEXT NOT NULL DEFAULT 'white',
                status TEXT NOT NULL DEFAULT 'waiting',
                winner_player_id INTEGER REFERENCES players(id),
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS moves (
                id {id_type},
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                player_id INTEGER NOT NULL REFERENCES players(id),
                move_text TEXT NOT NULL,
                fen_after TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id {id_type},
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                player_id INTEGER NOT NULL REFERENCES players(id),
                message TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS game_history (
                id {id_type},
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                opponent_id INTEGER REFERENCES players(id) ON DELETE SET NULL,
                result TEXT NOT NULL,
                elo_before INTEGER NOT NULL,
                elo_after INTEGER NOT NULL,
                elo_delta INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS login_attempts (
                id {id_type},
                ip TEXT NOT NULL,
                username TEXT,
                success INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );
            """
        )
        ensure_column(db, "players", "is_admin", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(db, "players", "is_disabled", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(db, "players", "email", "TEXT")
        ensure_column(db, "players", "elo", "INTEGER NOT NULL DEFAULT 1200")
        ensure_column(db, "players", "provider", "TEXT NOT NULL DEFAULT 'local'")
        ensure_column(db, "players", "provider_id", "TEXT")
        ensure_column(db, "players", "quiz_level_reached", "INTEGER NOT NULL DEFAULT 1")
        ensure_column(db, "players", "quiz_score", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(db, "players", "games_played", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(db, "players", "twofa_secret", "TEXT")
        ensure_column(db, "players", "twofa_enabled", "INTEGER NOT NULL DEFAULT 0")
        ensure_admin(db)


def ensure_column(db, table, column, definition):
    if db.is_postgres:
        rows = db.execute(
            """
            SELECT column_name AS name
            FROM information_schema.columns
            WHERE table_name = ?
            """,
            (table,),
        ).fetchall()
    else:
        rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    columns = [row["name"] for row in rows]
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def ensure_admin(db):
    admin = db.execute("SELECT * FROM players WHERE username = ?", (ADMIN_USERNAME,)).fetchone()
    salt, password_hash = hash_password(ADMIN_PASSWORD)
    if admin is None:
        db.execute(
            """
            INSERT INTO players (username, password_salt, password_hash, is_admin, created_at)
            VALUES (?, ?, ?, 1, ?)
            """,
            (ADMIN_USERNAME, salt, password_hash, int(time.time())),
        )
    else:
        db.execute(
            """
            UPDATE players
            SET password_salt = ?, password_hash = ?, is_admin = 1, is_disabled = 0
            WHERE id = ?
            """,
            (salt, password_hash, admin["id"]),
        )


def hash_password(password, salt=None):
    if bcrypt is not None:
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        return ("bcrypt", hashed.decode("utf-8"))
    if salt is None:
        salt = secrets.token_bytes(16)
    elif isinstance(salt, str):
        salt = base64.b64decode(salt.encode("ascii"))
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return (
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password, salt, expected_hash):
    if salt == "bcrypt" and bcrypt is not None:
        return bcrypt.checkpw(password.encode("utf-8"), expected_hash.encode("utf-8"))
    _, actual_hash = hash_password(password, salt)
    return hmac.compare_digest(actual_hash, expected_hash)


def client_ip(handler):
    forwarded = handler.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return handler.client_address[0]


def clean_rate_buckets(now):
    for key in list(RATE_BUCKETS.keys()):
        RATE_BUCKETS[key] = [stamp for stamp in RATE_BUCKETS[key] if now - stamp < 15 * 60]
        if not RATE_BUCKETS[key]:
            del RATE_BUCKETS[key]


def rate_limited(handler, bucket_name, identifier=None):
    now = int(time.time())
    clean_rate_buckets(now)
    limit, window = RATE_LIMITS[bucket_name]
    key = f"{bucket_name}:{identifier or client_ip(handler)}"
    attempts = [stamp for stamp in RATE_BUCKETS.get(key, []) if now - stamp < window]
    if len(attempts) >= limit:
        json_response(handler, 429, {"error": "rate_limited"})
        return True
    attempts.append(now)
    RATE_BUCKETS[key] = attempts
    return False


def record_login_attempt(ip, username, success):
    with connect_db() as db:
        db.execute(
            "INSERT INTO login_attempts (ip, username, success, created_at) VALUES (?, ?, ?, ?)",
            (ip, username[:80] if username else None, 1 if success else 0, int(time.time())),
        )


def sanitize_text(value, max_length):
    text = str(value or "").strip()
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    return text[:max_length]


def sanitize_username(value):
    username = str(value or "").strip()
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    return "".join(ch for ch in username if ch in allowed)[:24]


def create_session(db, player_id):
    token = secrets.token_urlsafe(32)
    db.execute(
        "INSERT INTO sessions (token, player_id, created_at) VALUES (?, ?, ?)",
        (token, player_id, int(time.time())),
    )
    return token


def make_2fa_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def hotp(secret, counter):
    padded = secret + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(padded.encode("ascii"), casefold=True)
    msg = counter.to_bytes(8, "big")
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = int.from_bytes(digest[offset : offset + 4], "big") & 0x7FFFFFFF
    return f"{code % 1_000_000:06d}"


def verify_totp(secret, code, window=1):
    code = str(code or "").strip().replace(" ", "")
    if not code.isdigit() or len(code) != 6 or not secret:
        return False
    counter = int(time.time() // 30)
    for step in range(-window, window + 1):
        if hmac.compare_digest(hotp(secret, counter + step), code):
            return True
    return False


def new_2fa_challenge(player_id):
    token = secrets.token_urlsafe(24)
    TWOFA_CHALLENGES[token] = {"player_id": player_id, "created_at": int(time.time())}
    return token


def consume_2fa_challenge(token):
    challenge = TWOFA_CHALLENGES.pop(str(token or ""), None)
    if not challenge:
        return None
    if int(time.time()) - challenge["created_at"] > 5 * 60:
        return None
    return challenge["player_id"]


def otpauth_uri(username, secret):
    label = quote(f"INFO7 Chess:{username}")
    issuer = quote("INFO7 Chess")
    return f"otpauth://totp/{label}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"


def get_cookie_token(handler):
    raw_cookie = handler.headers.get("Cookie", "")
    if not raw_cookie:
        return ""
    parsed = cookies.SimpleCookie(raw_cookie)
    morsel = parsed.get("info7_session")
    return morsel.value if morsel else ""


def set_session_cookie(handler, token):
    handler.send_header(
        "Set-Cookie",
        f"info7_session={token}; Max-Age={SESSION_TTL_SECONDS}; Path=/; HttpOnly; SameSite=Lax; Secure",
    )


def clear_session_cookie(handler):
    handler.send_header("Set-Cookie", "info7_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax; Secure")


def elo_k_factor(elo, games_played):
    if games_played < 30 or elo < 1200:
        return 40
    if elo > 2400:
        return 10
    return 20


def expected_score(player_elo, opponent_elo):
    return 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))


def calculate_elo(player, opponent, score):
    before = int(player["elo"])
    opponent_elo = int(opponent["elo"])
    k = elo_k_factor(before, int(player["games_played"]))
    after = round(before + k * (score - expected_score(before, opponent_elo)))
    return max(100, after)


def finish_game(db, room, winner_id=None, is_draw=False):
    white = db.execute("SELECT * FROM players WHERE id = ?", (room["white_player_id"],)).fetchone()
    black = db.execute("SELECT * FROM players WHERE id = ?", (room["black_player_id"],)).fetchone()
    if not white or not black:
        return []

    if is_draw:
        white_score, black_score = 0.5, 0.5
        white_result, black_result = "draw", "draw"
    elif winner_id == white["id"]:
        white_score, black_score = 1, 0
        white_result, black_result = "win", "loss"
    else:
        white_score, black_score = 0, 1
        white_result, black_result = "loss", "win"

    white_after = calculate_elo(white, black, white_score)
    black_after = calculate_elo(black, white, black_score)
    now = int(time.time())
    rows = [
        (white, black, white_result, white_after),
        (black, white, black_result, black_after),
    ]

    for player, opponent, result, after in rows:
        before = int(player["elo"])
        delta = after - before
        db.execute(
            """
            INSERT INTO game_history (room_id, player_id, opponent_id, result, elo_before, elo_after, elo_delta, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (room["id"], player["id"], opponent["id"], result, before, after, delta, now),
        )
        db.execute(
            "UPDATE players SET elo = ?, games_played = games_played + 1 WHERE id = ?",
            (after, player["id"]),
        )

    if is_draw:
        db.execute("UPDATE players SET draws = draws + 1 WHERE id IN (?, ?)", (white["id"], black["id"]))
    elif winner_id == white["id"]:
        db.execute("UPDATE players SET wins = wins + 1 WHERE id = ?", (white["id"],))
        db.execute("UPDATE players SET losses = losses + 1 WHERE id = ?", (black["id"],))
    else:
        db.execute("UPDATE players SET wins = wins + 1 WHERE id = ?", (black["id"],))
        db.execute("UPDATE players SET losses = losses + 1 WHERE id = ?", (white["id"],))

    return [
        {"player_id": white["id"], "elo_before": white["elo"], "elo_after": white_after, "elo_delta": white_after - white["elo"]},
        {"player_id": black["id"], "elo_before": black["elo"], "elo_after": black_after, "elo_delta": black_after - black["elo"]},
    ]


def new_room_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


def run_engine(*args):
    if not os.path.exists(ENGINE_PATH):
        raise RuntimeError("engine_not_built")
    result = subprocess.run(
        [ENGINE_PATH, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=5,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "engine_error")
    return result.stdout.strip()


def starting_fen():
    return run_engine("start")


def send_security_headers(handler):
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "DENY")
    handler.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
    handler.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    handler.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    handler.send_header(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'",
    )


def json_response(handler, status, data, cookie_token=None, clear_cookie=False):
    body = json.dumps(data).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    send_security_headers(handler)
    handler.send_header("Access-Control-Allow-Origin", handler.headers.get("Origin", "*"))
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Credentials", "true")
    if cookie_token:
        set_session_cookie(handler, cookie_token)
    if clear_cookie:
        clear_session_cookie(handler)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def file_response(handler, path):
    if not os.path.exists(path) or not os.path.isfile(path):
        json_response(handler, 404, {"error": "not_found"})
        return

    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as file:
        body = file.read()

    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    send_security_headers(handler)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    if length == 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def auth_player(handler):
    header = handler.headers.get("Authorization", "")
    token = ""
    if header.startswith("Bearer "):
        token = header.removeprefix("Bearer ").strip()
    if not token:
        token = get_cookie_token(handler)
    if not token:
        return None
    with connect_db() as db:
        return db.execute(
            """
            SELECT players.*
            FROM sessions
            JOIN players ON players.id = sessions.player_id
            WHERE sessions.token = ? AND sessions.created_at >= ? AND players.is_disabled = 0
            """,
            (token, int(time.time()) - SESSION_TTL_SECONDS),
        ).fetchone()


def public_player(row):
    return {
        "id": row["id"],
        "username": row["username"],
        "is_admin": bool(row["is_admin"]),
        "is_disabled": bool(row["is_disabled"]),
        "wins": row["wins"],
        "losses": row["losses"],
        "draws": row["draws"],
        "email": row["email"] if "email" in row.keys() else None,
        "elo": row["elo"],
        "provider": row["provider"],
        "quiz_level_reached": row["quiz_level_reached"],
        "quiz_score": row["quiz_score"],
        "games_played": row["games_played"],
        "twofa_enabled": bool(row["twofa_enabled"]),
    }


def require_admin(handler):
    player = auth_player(handler)
    if player is None:
        json_response(handler, 401, {"error": "login_required"})
        return None
    if player["is_admin"] != 1:
        json_response(handler, 403, {"error": "admin_required"})
        return None
    return player


def room_for_player(db, code, player):
    room = db.execute("SELECT * FROM rooms WHERE code = ?", (code,)).fetchone()
    if room is None:
        return None, "room_not_found"
    if player["id"] not in (room["white_player_id"], room["black_player_id"]):
        return None, "not_in_room"
    return room, None


class ChessHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        json_response(self, 200, {"ok": True})

    def do_GET(self):
        try:
            self.route_get()
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})

    def do_POST(self):
        try:
            self.route_post()
        except json.JSONDecodeError:
            json_response(self, 400, {"error": "invalid_json"})
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})

    def route_get(self):
        parsed_path = urlparse(self.path).path
        path = parsed_path.strip("/").split("/")
        if path == [""]:
            path = []

        if not path or path[0] != "api" and path[0] != "health":
            requested = "index.html" if not path else os.path.normpath(parsed_path.lstrip("/"))
            public_root = os.path.abspath(PUBLIC_PATH)
            file_path = os.path.abspath(os.path.join(PUBLIC_PATH, requested))
            if not file_path.startswith(public_root):
                json_response(self, 403, {"error": "forbidden"})
                return
            file_response(self, file_path)
            return

        if path == ["health"]:
            json_response(self, 200, {"ok": True})
            return

        if path == ["api", "profile"]:
            player = auth_player(self)
            if player is None:
                json_response(self, 401, {"error": "login_required"})
                return
            json_response(self, 200, {"player": public_player(player)})
            return

        if path == ["api", "me", "history"]:
            player = auth_player(self)
            if player is None:
                json_response(self, 401, {"error": "login_required"})
                return
            with connect_db() as db:
                history = db.execute(
                    """
                    SELECT game_history.*, opponents.username AS opponent_username
                    FROM game_history
                    LEFT JOIN players opponents ON opponents.id = game_history.opponent_id
                    WHERE game_history.player_id = ?
                    ORDER BY game_history.created_at DESC
                    LIMIT 50
                    """,
                    (player["id"],),
                ).fetchall()
            json_response(self, 200, {"history": [dict(item) for item in history]})
            return

        if path == ["api", "2fa", "setup"]:
            player = auth_player(self)
            if player is None:
                json_response(self, 401, {"error": "login_required"})
                return
            secret = player["twofa_secret"] or make_2fa_secret()
            with connect_db() as db:
                db.execute("UPDATE players SET twofa_secret = ? WHERE id = ?", (secret, player["id"]))
            json_response(
                self,
                200,
                {
                    "secret": secret,
                    "otpauth_url": otpauth_uri(player["username"], secret),
                    "manual_code": secret,
                },
            )
            return

        if len(path) == 3 and path[:2] == ["api", "rooms"]:
            code = path[2].upper()
            with connect_db() as db:
                room = db.execute("SELECT * FROM rooms WHERE code = ?", (code,)).fetchone()
                if room is None:
                    json_response(self, 404, {"error": "room_not_found"})
                    return
                moves = db.execute(
                    "SELECT id, player_id, move_text, fen_after, created_at FROM moves WHERE room_id = ? ORDER BY id",
                    (room["id"],),
                ).fetchall()
            json_response(
                self,
                200,
                {
                    "code": room["code"],
                    "fen": room["fen"],
                    "turn": room["turn"],
                    "status": room["status"],
                    "white_player_id": room["white_player_id"],
                    "black_player_id": room["black_player_id"],
                    "moves": [dict(move) for move in moves],
                },
            )
            return

        if len(path) == 4 and path[:2] == ["api", "rooms"] and path[3] == "chat":
            player = auth_player(self)
            if player is None:
                json_response(self, 401, {"error": "login_required"})
                return
            code = path[2].upper()
            with connect_db() as db:
                room, error = room_for_player(db, code, player)
                if error:
                    json_response(self, 404 if error == "room_not_found" else 403, {"error": error})
                    return
                messages = db.execute(
                    """
                    SELECT chat_messages.id, chat_messages.message, chat_messages.created_at,
                           players.id AS player_id, players.username
                    FROM chat_messages
                    JOIN players ON players.id = chat_messages.player_id
                    WHERE chat_messages.room_id = ?
                    ORDER BY chat_messages.id ASC
                    LIMIT 200
                    """,
                    (room["id"],),
                ).fetchall()
            json_response(self, 200, {"messages": [dict(message) for message in messages]})
            return

        if path == ["api", "admin", "players"]:
            admin = require_admin(self)
            if admin is None:
                return
            with connect_db() as db:
                players = db.execute(
                    """
                    SELECT id, username, email, is_admin, is_disabled, wins, losses, draws,
                           elo, provider, quiz_level_reached, quiz_score, games_played, created_at
                    FROM players
                    ORDER BY created_at DESC
                    """
                ).fetchall()
            json_response(self, 200, {"players": [dict(player) for player in players]})
            return

        if path == ["api", "admin", "rooms"]:
            admin = require_admin(self)
            if admin is None:
                return
            with connect_db() as db:
                rooms = db.execute(
                    """
                    SELECT rooms.*, white.username AS white_username, black.username AS black_username
                    FROM rooms
                    LEFT JOIN players white ON white.id = rooms.white_player_id
                    LEFT JOIN players black ON black.id = rooms.black_player_id
                    ORDER BY rooms.updated_at DESC
                    LIMIT 100
                    """
                ).fetchall()
            json_response(self, 200, {"rooms": [dict(room) for room in rooms]})
            return

        if path == ["api", "admin", "database"]:
            admin = require_admin(self)
            if admin is None:
                return
            with connect_db() as db:
                players_count = db.execute("SELECT COUNT(*) AS count FROM players").fetchone()["count"]
                rooms_count = db.execute("SELECT COUNT(*) AS count FROM rooms").fetchone()["count"]
                moves_count = db.execute("SELECT COUNT(*) AS count FROM moves").fetchone()["count"]
            json_response(
                self,
                200,
                {
                    "path": DB_PATH,
                    "exists": os.path.exists(DB_PATH),
                    "size_bytes": os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0,
                    "players": players_count,
                    "rooms": rooms_count,
                    "moves": moves_count,
                },
            )
            return

        json_response(self, 404, {"error": "not_found"})

    def route_post(self):
        path = urlparse(self.path).path.strip("/").split("/")
        data = read_json(self)

        if path == ["api", "register"]:
            if rate_limited(self, "register"):
                return
            username = sanitize_username(data.get("username", ""))
            email = sanitize_text(data.get("email", ""), 160).lower() or None
            password = str(data.get("password", ""))
            try:
                elo = max(400, min(2800, int(data.get("elo", 1200))))
            except (TypeError, ValueError):
                elo = 1200
            if len(username) < 3 or len(password) < 4:
                json_response(self, 400, {"error": "username_or_password_too_short"})
                return
            salt, password_hash = hash_password(password)
            try:
                with connect_db() as db:
                    db.execute(
                        """
                        INSERT INTO players (username, email, password_salt, password_hash, elo, provider, created_at)
                        VALUES (?, ?, ?, ?, ?, 'local', ?)
                        """,
                        (username, email, salt, password_hash, elo, int(time.time())),
                    )
            except Exception:
                json_response(self, 409, {"error": "username_or_email_already_exists"})
                return
            json_response(self, 201, {"ok": True})
            return

        if path == ["api", "login"]:
            ip = client_ip(self)
            username = sanitize_text(data.get("username", ""), 160)
            if rate_limited(self, "login", f"{ip}:{username.lower()}"):
                return
            password = str(data.get("password", ""))
            with connect_db() as db:
                player = db.execute(
                    "SELECT * FROM players WHERE username = ? OR email = ?",
                    (username, username.lower()),
                ).fetchone()
                if player is None or not verify_password(password, player["password_salt"], player["password_hash"]):
                    record_login_attempt(ip, username, False)
                    json_response(self, 401, {"error": "bad_login"})
                    return
                if player["is_disabled"] == 1:
                    record_login_attempt(ip, username, False)
                    json_response(self, 403, {"error": "account_disabled"})
                    return
                if player["twofa_enabled"] == 1:
                    challenge = new_2fa_challenge(player["id"])
                    record_login_attempt(ip, username, True)
                    json_response(
                        self,
                        200,
                        {
                            "requires_2fa": True,
                            "challenge": challenge,
                            "player_hint": {"username": player["username"]},
                        },
                    )
                    return
                token = create_session(db, player["id"])
            record_login_attempt(ip, username, True)
            json_response(self, 200, {"token": token, "player": public_player(player)}, cookie_token=token)
            return

        if path == ["api", "login", "2fa"]:
            if rate_limited(self, "login", f"2fa:{client_ip(self)}"):
                return
            challenge = str(data.get("challenge", ""))
            code = str(data.get("code", ""))
            player_id = consume_2fa_challenge(challenge)
            if player_id is None:
                json_response(self, 401, {"error": "bad_or_expired_2fa_challenge"})
                return
            with connect_db() as db:
                player = db.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
                if player is None or player["twofa_enabled"] != 1 or not verify_totp(player["twofa_secret"], code):
                    json_response(self, 401, {"error": "bad_2fa_code"})
                    return
                token = create_session(db, player["id"])
            json_response(self, 200, {"token": token, "player": public_player(player)}, cookie_token=token)
            return

        if path == ["api", "logout"]:
            header = self.headers.get("Authorization", "")
            token = header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else get_cookie_token(self)
            if token:
                with connect_db() as db:
                    db.execute("DELETE FROM sessions WHERE token = ?", (token,))
            json_response(self, 200, {"ok": True}, clear_cookie=True)
            return

        player = auth_player(self)
        if player is None:
            json_response(self, 401, {"error": "login_required"})
            return

        if path == ["api", "quiz", "progress"]:
            try:
                level = max(1, min(8, int(data.get("level", player["quiz_level_reached"]))))
                score = max(0, int(data.get("score", player["quiz_score"])))
                passed = bool(data.get("passed", False))
            except (TypeError, ValueError):
                json_response(self, 400, {"error": "bad_quiz_payload"})
                return
            next_level = max(player["quiz_level_reached"], level + 1 if passed else level)
            with connect_db() as db:
                db.execute(
                    """
                    UPDATE players
                    SET quiz_level_reached = ?, quiz_score = CASE WHEN quiz_score > ? THEN quiz_score ELSE ? END
                    WHERE id = ?
                    """,
                    (next_level, score, score, player["id"]),
                )
                updated = db.execute("SELECT * FROM players WHERE id = ?", (player["id"],)).fetchone()
            json_response(self, 200, {"player": public_player(updated)})
            return

        if path == ["api", "2fa", "enable"]:
            code = str(data.get("code", ""))
            with connect_db() as db:
                fresh = db.execute("SELECT * FROM players WHERE id = ?", (player["id"],)).fetchone()
                if not fresh["twofa_secret"] or not verify_totp(fresh["twofa_secret"], code):
                    json_response(self, 400, {"error": "bad_2fa_code"})
                    return
                db.execute("UPDATE players SET twofa_enabled = 1 WHERE id = ?", (player["id"],))
                updated = db.execute("SELECT * FROM players WHERE id = ?", (player["id"],)).fetchone()
            json_response(self, 200, {"player": public_player(updated)})
            return

        if path == ["api", "2fa", "disable"]:
            code = str(data.get("code", ""))
            with connect_db() as db:
                fresh = db.execute("SELECT * FROM players WHERE id = ?", (player["id"],)).fetchone()
                if fresh["twofa_enabled"] == 1 and not verify_totp(fresh["twofa_secret"], code):
                    json_response(self, 400, {"error": "bad_2fa_code"})
                    return
                db.execute("UPDATE players SET twofa_enabled = 0, twofa_secret = NULL WHERE id = ?", (player["id"],))
                updated = db.execute("SELECT * FROM players WHERE id = ?", (player["id"],)).fetchone()
            json_response(self, 200, {"player": public_player(updated)})
            return

        if path == ["api", "rooms"]:
            if rate_limited(self, "rooms"):
                return
            code = new_room_code()
            with connect_db() as db:
                while db.execute("SELECT 1 FROM rooms WHERE code = ?", (code,)).fetchone():
                    code = new_room_code()
                now = int(time.time())
                db.execute(
                    """
                    INSERT INTO rooms (code, white_player_id, fen, turn, created_at, updated_at)
                    VALUES (?, ?, ?, 'white', ?, ?)
                    """,
                    (code, player["id"], starting_fen(), now, now),
                )
            json_response(self, 201, {"code": code, "color": "white"})
            return

        if len(path) == 5 and path[:3] == ["api", "admin", "players"]:
            admin = require_admin(self)
            if admin is None:
                return
            try:
                player_id = int(path[3])
            except ValueError:
                json_response(self, 400, {"error": "bad_player_id"})
                return

            action = path[4]
            with connect_db() as db:
                target = db.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
                if target is None:
                    json_response(self, 404, {"error": "player_not_found"})
                    return
                if action == "disable":
                    if target["id"] == admin["id"]:
                        json_response(self, 400, {"error": "cannot_disable_yourself"})
                        return
                    db.execute("UPDATE players SET is_disabled = 1 WHERE id = ?", (player_id,))
                    db.execute("DELETE FROM sessions WHERE player_id = ?", (player_id,))
                    json_response(self, 200, {"ok": True})
                    return
                if action == "enable":
                    db.execute("UPDATE players SET is_disabled = 0 WHERE id = ?", (player_id,))
                    json_response(self, 200, {"ok": True})
                    return
                if action == "make-admin":
                    db.execute("UPDATE players SET is_admin = 1 WHERE id = ?", (player_id,))
                    json_response(self, 200, {"ok": True})
                    return
                if action == "remove-admin":
                    if target["id"] == admin["id"]:
                        json_response(self, 400, {"error": "cannot_remove_your_own_admin"})
                        return
                    db.execute("UPDATE players SET is_admin = 0 WHERE id = ?", (player_id,))
                    json_response(self, 200, {"ok": True})
                    return

            json_response(self, 404, {"error": "unknown_admin_action"})
            return

        if len(path) == 4 and path[:2] == ["api", "rooms"] and path[3] == "join":
            code = path[2].upper()
            with connect_db() as db:
                room = db.execute("SELECT * FROM rooms WHERE code = ?", (code,)).fetchone()
                if room is None:
                    json_response(self, 404, {"error": "room_not_found"})
                    return
                if room["white_player_id"] == player["id"]:
                    json_response(self, 200, {"code": code, "color": "white"})
                    return
                if room["black_player_id"] not in (None, player["id"]):
                    json_response(self, 409, {"error": "room_full"})
                    return
                db.execute(
                    "UPDATE rooms SET black_player_id = ?, status = 'playing', updated_at = ? WHERE id = ?",
                    (player["id"], int(time.time()), room["id"]),
                )
            json_response(self, 200, {"code": code, "color": "black"})
            return

        if len(path) == 4 and path[:2] == ["api", "rooms"] and path[3] == "chat":
            if rate_limited(self, "chat"):
                return
            code = path[2].upper()
            message = sanitize_text(data.get("message", ""), 400)
            if not message:
                json_response(self, 400, {"error": "empty_message"})
                return
            if len(message) > 400:
                json_response(self, 400, {"error": "message_too_long"})
                return

            with connect_db() as db:
                room, error = room_for_player(db, code, player)
                if error:
                    json_response(self, 404 if error == "room_not_found" else 403, {"error": error})
                    return
                db.execute(
                    """
                    INSERT INTO chat_messages (room_id, player_id, message, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (room["id"], player["id"], message, int(time.time())),
                )
            json_response(self, 201, {"ok": True})
            return

        if len(path) == 4 and path[:2] == ["api", "rooms"] and path[3] == "moves":
            if rate_limited(self, "moves"):
                return
            code = path[2].upper()
            move_text = str(data.get("move", "")).strip().lower()
            with connect_db() as db:
                room = db.execute("SELECT * FROM rooms WHERE code = ?", (code,)).fetchone()
                if room is None:
                    json_response(self, 404, {"error": "room_not_found"})
                    return
                if room["status"] != "playing":
                    json_response(self, 409, {"error": "room_not_playing"})
                    return
                expected_player = room["white_player_id"] if room["turn"] == "white" else room["black_player_id"]
                if expected_player != player["id"]:
                    json_response(self, 403, {"error": "not_your_turn"})
                    return

                engine_output = run_engine(room["fen"], room["turn"], move_text)
                parts = engine_output.split()
                if not parts or parts[0] != "ok":
                    json_response(self, 400, {"error": parts[1] if len(parts) > 1 else "illegal_move"})
                    return

                new_fen, new_turn = parts[1], parts[2]
                check_state = parts[3] if len(parts) > 3 else "safe"
                game_state = parts[4] if len(parts) > 4 else "playing"
                is_draw = game_state in ("draw", "stalemate")
                status = "finished" if game_state in ("checkmate", "draw", "stalemate") else "playing"
                winner_id = player["id"] if game_state == "checkmate" else None
                elo_changes = []

                db.execute(
                    """
                    UPDATE rooms
                    SET fen = ?, turn = ?, status = ?, winner_player_id = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (new_fen, new_turn, status, winner_id, int(time.time()), room["id"]),
                )
                db.execute(
                    """
                    INSERT INTO moves (room_id, player_id, move_text, fen_after, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (room["id"], player["id"], move_text, new_fen, int(time.time())),
                )
                if status == "finished":
                    elo_changes = finish_game(db, room, winner_id, is_draw)

            json_response(
                self,
                200,
                {
                    "ok": True,
                    "fen": new_fen,
                    "turn": new_turn,
                    "check": check_state == "check",
                    "status": status,
                    "elo_changes": elo_changes,
                },
            )
            return

        json_response(self, 404, {"error": "not_found"})


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), ChessHandler)
    print(f"INFO7 chess server listening on http://localhost:{PORT}")
    server.serve_forever()
