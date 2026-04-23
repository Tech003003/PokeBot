"""SQLite-backed storage for TechBot. Portable for local desktop deployment."""
import aiosqlite
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DB_PATH = os.environ.get("TECHBOT_DB", str(Path(__file__).parent / "techbot.db"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id() -> str:
    return str(uuid.uuid4())


SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    site TEXT NOT NULL,
    url TEXT NOT NULL,
    purchase_mode TEXT NOT NULL DEFAULT 'monitor',
    priority INTEGER NOT NULL DEFAULT 5,
    active INTEGER NOT NULL DEFAULT 1,
    max_price REAL,
    quantity INTEGER NOT NULL DEFAULT 1,
    profile_id TEXT,
    status TEXT NOT NULL DEFAULT 'IDLE',
    last_checked TEXT,
    last_message TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    first_name TEXT, last_name TEXT, email TEXT, phone TEXT,
    address1 TEXT, address2 TEXT, city TEXT, state TEXT, zip TEXT, country TEXT,
    card_name TEXT, card_number TEXT, card_exp_month TEXT, card_exp_year TEXT, card_cvv TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drops (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    run_at TEXT NOT NULL,
    urls TEXT NOT NULL,
    site TEXT NOT NULL,
    queue_handling INTEGER NOT NULL DEFAULT 1,
    blast_mode INTEGER NOT NULL DEFAULT 1,
    purchase_mode TEXT NOT NULL DEFAULT 'cart',
    profile_id TEXT,
    status TEXT NOT NULL DEFAULT 'SCHEDULED',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS history (
    id TEXT PRIMARY KEY,
    watch_id TEXT,
    name TEXT,
    site TEXT,
    url TEXT,
    outcome TEXT NOT NULL,
    price REAL,
    message TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    k TEXT PRIMARY KEY,
    v TEXT NOT NULL
);
"""

DEFAULT_SETTINGS = {
    "poll_interval_ms": 700,
    "concurrent_workers": 5,
    "jitter_ms": 200,
    "cdp_url": "http://127.0.0.1:9222",
    "discord_webhook": "",
    "sound_alerts": True,
    "desktop_toasts": True,
    "headless_fallback": False,
    "auto_refresh_on_error": True,
    "stop_before_place_order": True,  # safety default for full-auto mode
    "enforce_max_price": True,         # price guard: skip purchase if live price > max_price
    "strict_price_guard": False,       # if true, skip purchase when price can't be read
    "price_guard_cooldown_s": 300,     # seconds to wait after a price-guard skip
    "discord_enabled": False,
    "discord_bot_token": "",
    "discord_channel_rules": {},       # { channel_id: {action, priority, max_price, profile_id, auto_start} }
}


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()
        for k, v in DEFAULT_SETTINGS.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (k, v) VALUES (?, ?)",
                (k, json.dumps(v)),
            )
        await db.commit()


async def get_setting(key: str) -> Any:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT v FROM settings WHERE k=?", (key,)) as cur:
            row = await cur.fetchone()
            if row:
                return json.loads(row[0])
            return DEFAULT_SETTINGS.get(key)


async def get_all_settings() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT k, v FROM settings") as cur:
            rows = await cur.fetchall()
    out = dict(DEFAULT_SETTINGS)
    for k, v in rows:
        try:
            out[k] = json.loads(v)
        except Exception:
            out[k] = v
    return out


async def set_setting(key: str, value: Any):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings (k, v) VALUES (?, ?) "
            "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            (key, json.dumps(value)),
        )
        await db.commit()


async def update_settings(patch: dict):
    for k, v in patch.items():
        await set_setting(k, v)


# -- Generic CRUD helpers ------------------------------------------------

async def _fetchall(table: str, where: str = "", params: tuple = ()) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        q = f"SELECT * FROM {table}"
        if where:
            q += f" WHERE {where}"
        q += " ORDER BY created_at DESC"
        async with db.execute(q, params) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def _fetchone(table: str, id_: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(f"SELECT * FROM {table} WHERE id=?", (id_,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def _insert(table: str, data: dict) -> dict:
    data = dict(data)
    data["id"] = data.get("id") or _gen_id()
    data["created_at"] = data.get("created_at") or _now()
    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    vals = tuple(data.values())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", vals)
        await db.commit()
    return data


async def _update(table: str, id_: str, patch: dict) -> Optional[dict]:
    if not patch:
        return await _fetchone(table, id_)
    cols = ", ".join(f"{k}=?" for k in patch)
    vals = tuple(patch.values()) + (id_,)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE {table} SET {cols} WHERE id=?", vals)
        await db.commit()
    return await _fetchone(table, id_)


async def _delete(table: str, id_: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(f"DELETE FROM {table} WHERE id=?", (id_,))
        await db.commit()
        return cur.rowcount > 0


# -- Watchlist -----------------------------------------------------------
async def list_watch() -> list[dict]:
    return await _fetchall("watchlist")


async def get_watch(id_: str) -> Optional[dict]:
    return await _fetchone("watchlist", id_)


async def create_watch(data: dict) -> dict:
    data.setdefault("status", "IDLE")
    return await _insert("watchlist", data)


async def update_watch(id_: str, patch: dict) -> Optional[dict]:
    return await _update("watchlist", id_, patch)


async def delete_watch(id_: str) -> bool:
    return await _delete("watchlist", id_)


async def set_watch_status(id_: str, status: str, message: str = ""):
    await _update(
        "watchlist",
        id_,
        {"status": status, "last_message": message, "last_checked": _now()},
    )


# -- Profiles ------------------------------------------------------------
async def list_profiles(): return await _fetchall("profiles")
async def get_profile(id_): return await _fetchone("profiles", id_)
async def create_profile(data): return await _insert("profiles", data)
async def update_profile(id_, patch): return await _update("profiles", id_, patch)
async def delete_profile(id_): return await _delete("profiles", id_)


# -- Drops ---------------------------------------------------------------
async def list_drops(): return await _fetchall("drops")
async def get_drop(id_): return await _fetchone("drops", id_)
async def create_drop(data):
    if isinstance(data.get("urls"), list):
        data["urls"] = json.dumps(data["urls"])
    return await _insert("drops", data)
async def update_drop(id_, patch):
    if "urls" in patch and isinstance(patch["urls"], list):
        patch["urls"] = json.dumps(patch["urls"])
    return await _update("drops", id_, patch)
async def delete_drop(id_): return await _delete("drops", id_)


# -- History -------------------------------------------------------------
async def list_history(limit: int = 200):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM history ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def log_history(entry: dict):
    return await _insert("history", entry)
