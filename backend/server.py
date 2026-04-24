"""TechBot Command Center — FastAPI backend."""
from __future__ import annotations
import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

import db
import sites as sitelib
from engine import engine

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("techbot")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.init_db()
    logger.info("TechBot backend started")
    try:
        s = await db.get_all_settings()
        if s.get("discord_enabled") and s.get("discord_bot_token"):
            await engine.discord.start(s["discord_bot_token"])
    except Exception as e:
        logger.warning(f"Discord auto-start failed: {e}")
    yield
    try:
        await engine.discord.stop()
        await engine.stop_all()
        await engine.disconnect_brave()
    except Exception:
        pass


app = FastAPI(title="TechBot Command Center", lifespan=lifespan)
api = APIRouter(prefix="/api")


# ------ Pydantic schemas ------
class WatchIn(BaseModel):
    name: str
    site: str
    url: str
    purchase_mode: str = "monitor"
    priority: int = 5
    active: bool = True
    max_price: Optional[float] = None
    quantity: int = 1
    profile_id: Optional[str] = None
    button_types: list[str] = ["cart"]


class WatchPatch(BaseModel):
    name: Optional[str] = None
    site: Optional[str] = None
    url: Optional[str] = None
    purchase_mode: Optional[str] = None
    priority: Optional[int] = None
    active: Optional[bool] = None
    max_price: Optional[float] = None
    quantity: Optional[int] = None
    profile_id: Optional[str] = None
    button_types: Optional[list[str]] = None


class ProfileIn(BaseModel):
    label: str
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    address1: str = ""
    address2: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    country: str = "US"
    card_name: str = ""
    card_number: str = ""
    card_exp_month: str = ""
    card_exp_year: str = ""
    card_cvv: str = ""


class DropIn(BaseModel):
    name: str
    site: str
    run_at: str
    urls: list[str]
    queue_handling: bool = True
    blast_mode: bool = True
    purchase_mode: str = "cart"
    profile_id: Optional[str] = None


class SettingsPatch(BaseModel):
    poll_interval_ms: Optional[int] = None
    concurrent_workers: Optional[int] = None
    jitter_ms: Optional[int] = None
    cdp_url: Optional[str] = None
    discord_webhook: Optional[str] = None
    sound_alerts: Optional[bool] = None
    desktop_toasts: Optional[bool] = None
    headless_fallback: Optional[bool] = None
    auto_refresh_on_error: Optional[bool] = None
    stop_before_place_order: Optional[bool] = None
    enforce_max_price: Optional[bool] = None
    strict_price_guard: Optional[bool] = None
    price_guard_cooldown_s: Optional[int] = None
    discord_enabled: Optional[bool] = None
    discord_bot_token: Optional[str] = None
    discord_channel_rules: Optional[dict] = None


class ConnectIn(BaseModel):
    cdp_url: Optional[str] = None


# ------ Helpers ------
def _bool_fix(d: dict) -> dict:
    for k, v in list(d.items()):
        if isinstance(v, bool):
            d[k] = 1 if v else 0
    return d


def _mask_profile(p: dict) -> dict:
    p = dict(p)
    if p.get("card_number"):
        n = p["card_number"]
        p["card_number"] = ("•" * max(0, len(n) - 4)) + n[-4:] if len(n) > 4 else ""
    if p.get("card_cvv"):
        p["card_cvv"] = "•••"
    return p


# ------ Meta / health ------
@api.get("/")
async def root():
    return {"app": "TechBot Command Center", "ok": True}


@api.get("/meta/sites")
async def meta_sites():
    return {"sites": sitelib.SITES, "labels": sitelib.SITE_LABELS}


@api.get("/meta/modes")
async def meta_modes():
    return {
        "modes": ["monitor", "cart", "checkout", "auto"],
        "button_types": sitelib.BUTTON_TYPES,
        "button_labels": sitelib.BUTTON_LABELS,
    }


# ------ Status ------
@api.get("/status")
async def get_status():
    s = await engine.status()
    s["settings"] = await db.get_all_settings()
    return s


# ------ Brave ------
@api.post("/brave/connect")
async def brave_connect(body: ConnectIn):
    if body.cdp_url:
        await db.set_setting("cdp_url", body.cdp_url)
    return await engine.connect_brave(body.cdp_url)


@api.post("/brave/disconnect")
async def brave_disconnect():
    return await engine.disconnect_brave()


# ------ Watchlist ------
@api.post("/watch")
async def watch_create(body: WatchIn):
    if body.site not in sitelib.SITES:
        raise HTTPException(400, f"Unknown site '{body.site}'")
    data = _bool_fix(body.model_dump())
    if isinstance(data.get("button_types"), list):
        data["button_types"] = json.dumps(data["button_types"])
    created = await db.create_watch(data)
    if isinstance(created.get("button_types"), str):
        try:
            created["button_types"] = json.loads(created["button_types"])
        except Exception:
            pass
    return created


@api.patch("/watch/{wid}")
async def watch_update(wid: str, body: WatchPatch):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    patch = _bool_fix(patch)
    if isinstance(patch.get("button_types"), list):
        patch["button_types"] = json.dumps(patch["button_types"])
    item = await db.update_watch(wid, patch)
    if not item:
        raise HTTPException(404, "watch not found")
    if isinstance(item.get("button_types"), str):
        try:
            item["button_types"] = json.loads(item["button_types"])
        except Exception:
            pass
    return item


@api.get("/watch")
async def watch_list():
    rows = await db.list_watch()
    for r in rows:
        if isinstance(r.get("button_types"), str):
            try:
                r["button_types"] = json.loads(r["button_types"])
            except Exception:
                r["button_types"] = ["cart"]
    return rows


@api.delete("/watch/{wid}")
async def watch_delete(wid: str):
    await engine.stop_item(wid)
    ok = await db.delete_watch(wid)
    if not ok:
        raise HTTPException(404)
    return {"ok": True}


@api.post("/watch/{wid}/start")
async def watch_start(wid: str):
    return await engine.start_item(wid)


@api.post("/watch/{wid}/stop")
async def watch_stop(wid: str):
    return await engine.stop_item(wid)


@api.post("/watch/start-all")
async def watch_start_all():
    return await engine.start_all()


@api.post("/watch/stop-all")
async def watch_stop_all():
    return await engine.stop_all()


# ------ Profiles ------
@api.get("/profiles")
async def profile_list():
    return [_mask_profile(p) for p in await db.list_profiles()]


@api.get("/profiles/{pid}")
async def profile_get(pid: str):
    p = await db.get_profile(pid)
    if not p:
        raise HTTPException(404)
    return _mask_profile(p)


@api.post("/profiles")
async def profile_create(body: ProfileIn):
    return _mask_profile(await db.create_profile(body.model_dump()))


@api.patch("/profiles/{pid}")
async def profile_update(pid: str, body: ProfileIn):
    patch = {k: v for k, v in body.model_dump().items() if v not in ("", None) and not str(v).startswith("••")}
    p = await db.update_profile(pid, patch)
    if not p:
        raise HTTPException(404)
    return _mask_profile(p)


@api.delete("/profiles/{pid}")
async def profile_delete(pid: str):
    ok = await db.delete_profile(pid)
    if not ok:
        raise HTTPException(404)
    return {"ok": True}


# ------ Drops ------
@api.get("/drops")
async def drops_list():
    rows = await db.list_drops()
    for r in rows:
        if isinstance(r.get("urls"), str):
            try:
                r["urls"] = json.loads(r["urls"])
            except Exception:
                r["urls"] = [r["urls"]]
    return rows


@api.post("/drops")
async def drops_create(body: DropIn):
    if body.site not in sitelib.SITES:
        raise HTTPException(400, f"Unknown site '{body.site}'")
    d = await db.create_drop(_bool_fix(body.model_dump()))
    if isinstance(d.get("urls"), str):
        try:
            d["urls"] = json.loads(d["urls"])
        except Exception:
            pass
    return d


@api.delete("/drops/{did}")
async def drops_delete(did: str):
    await engine.cancel_drop(did)
    ok = await db.delete_drop(did)
    if not ok:
        raise HTTPException(404)
    return {"ok": True}


@api.post("/drops/{did}/arm")
async def drops_arm(did: str):
    return await engine.schedule_drop(did)


@api.post("/drops/{did}/cancel")
async def drops_cancel(did: str):
    return await engine.cancel_drop(did)


# ------ History ------
@api.get("/history")
async def history():
    return await db.list_history()


# ------ Settings ------
@api.get("/settings")
async def settings_get():
    return await db.get_all_settings()


@api.patch("/settings")
async def settings_patch(body: SettingsPatch):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    await db.update_settings(patch)
    new_settings = await db.get_all_settings()
    if "discord_enabled" in patch or "discord_bot_token" in patch:
        want_on = bool(new_settings.get("discord_enabled")) and bool(new_settings.get("discord_bot_token"))
        is_on = engine.discord.task is not None and not engine.discord.task.done()
        try:
            if want_on and not is_on:
                await engine.discord.start(new_settings["discord_bot_token"])
            elif not want_on and is_on:
                await engine.discord.stop()
            elif want_on and is_on and "discord_bot_token" in patch:
                await engine.discord.stop()
                await engine.discord.start(new_settings["discord_bot_token"])
        except Exception as e:
            logger.warning(f"Discord reconfigure failed: {e}")
    return new_settings


# ------ Discord ------
@api.get("/discord/status")
async def discord_status():
    return {
        "connected": engine.discord.connected,
        "running": engine.discord.task is not None and not engine.discord.task.done(),
    }


@api.post("/discord/start")
async def discord_start():
    s = await db.get_all_settings()
    token = s.get("discord_bot_token") or ""
    if not token:
        raise HTTPException(400, "No bot token configured")
    return await engine.discord.start(token)


@api.post("/discord/stop")
async def discord_stop():
    return await engine.discord.stop()


# ------ Websocket logs ------
@app.websocket("/api/ws/logs")
async def ws_logs(ws: WebSocket):
    await ws.accept()
    q = engine.logs.subscribe()
    try:
        while True:
            try:
                entry = await asyncio.wait_for(q.get(), timeout=15)
                await ws.send_json(entry)
            except asyncio.TimeoutError:
                await ws.send_json({"level": "PING", "msg": "pong", "ts": ""})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        engine.logs.unsubscribe(q)


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
