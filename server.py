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


ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(ROOT, "chess_online.db"))
ENGINE_PATH = os.path.join(ROOT, "engine.exe" if os.name == "nt" else "engine")
PUBLIC_PATH = os.path.join(ROOT, "public")
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8080"))
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "babba")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "130577")


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with connect_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                is_disabled INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                draws INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                player_id INTEGER NOT NULL REFERENCES players(id),
                move_text TEXT NOT NULL,
                fen_after TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                player_id INTEGER NOT NULL REFERENCES players(id),
                message TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """
        )
        ensure_column(db, "players", "is_admin", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(db, "players", "is_disabled", "INTEGER NOT NULL DEFAULT 0")
        ensure_admin(db)


def ensure_column(db, table, column, definition):
    columns = [row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()]
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
    _, actual_hash = hash_password(password, salt)
    return hmac.compare_digest(actual_hash, expected_hash)


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


def json_response(handler, status, data):
    body = json.dumps(data).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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
    if not header.startswith("Bearer "):
        return None
    token = header.removeprefix("Bearer ").strip()
    with connect_db() as db:
        return db.execute(
            """
            SELECT players.*
            FROM sessions
            JOIN players ON players.id = sessions.player_id
            WHERE sessions.token = ?
            """,
            (token,),
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
                    SELECT id, username, is_admin, is_disabled, wins, losses, draws, created_at
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
            username = str(data.get("username", "")).strip()
            password = str(data.get("password", ""))
            if len(username) < 3 or len(password) < 4:
                json_response(self, 400, {"error": "username_or_password_too_short"})
                return
            salt, password_hash = hash_password(password)
            try:
                with connect_db() as db:
                    db.execute(
                        """
                        INSERT INTO players (username, password_salt, password_hash, created_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (username, salt, password_hash, int(time.time())),
                    )
            except sqlite3.IntegrityError:
                json_response(self, 409, {"error": "username_already_exists"})
                return
            json_response(self, 201, {"ok": True})
            return

        if path == ["api", "login"]:
            username = str(data.get("username", "")).strip()
            password = str(data.get("password", ""))
            with connect_db() as db:
                player = db.execute("SELECT * FROM players WHERE username = ?", (username,)).fetchone()
                if player is None or not verify_password(password, player["password_salt"], player["password_hash"]):
                    json_response(self, 401, {"error": "bad_login"})
                    return
                if player["is_disabled"] == 1:
                    json_response(self, 403, {"error": "account_disabled"})
                    return
                token = secrets.token_urlsafe(32)
                db.execute(
                    "INSERT INTO sessions (token, player_id, created_at) VALUES (?, ?, ?)",
                    (token, player["id"], int(time.time())),
                )
            json_response(self, 200, {"token": token, "player": public_player(player)})
            return

        player = auth_player(self)
        if player is None:
            json_response(self, 401, {"error": "login_required"})
            return

        if path == ["api", "rooms"]:
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
            code = path[2].upper()
            message = str(data.get("message", "")).strip()
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
                status = "finished" if game_state == "checkmate" else "playing"
                winner_id = player["id"] if game_state == "checkmate" else None

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
                if game_state == "checkmate":
                    loser_id = room["black_player_id"] if player["id"] == room["white_player_id"] else room["white_player_id"]
                    db.execute("UPDATE players SET wins = wins + 1 WHERE id = ?", (player["id"],))
                    db.execute("UPDATE players SET losses = losses + 1 WHERE id = ?", (loser_id,))

            json_response(
                self,
                200,
                {
                    "ok": True,
                    "fen": new_fen,
                    "turn": new_turn,
                    "check": check_state == "check",
                    "status": status,
                },
            )
            return

        json_response(self, 404, {"error": "not_found"})


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), ChessHandler)
    print(f"INFO7 chess server listening on http://localhost:{PORT}")
    server.serve_forever()
