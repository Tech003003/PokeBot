"""TechBot Command Center — FastAPI backend."""
from __future__ import annotations
import asyncio
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
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
    browser_id: Optional[str] = None


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
    browser_id: Optional[str] = None


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
    duration_min: int = 15
    browser_id: Optional[str] = None


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
    reload_every_n_polls: Optional[int] = None
    atc_max_retries: Optional[int] = None


class ConnectIn(BaseModel):
    cdp_url: Optional[str] = None
    browser_id: Optional[str] = None


class BrowserIn(BaseModel):
    name: str
    cdp_url: str = "http://127.0.0.1:9222"
    user_data_dir: str = ""   # Windows path; used by the launch helper
    proxy: str = ""           # optional --proxy-server=... URL
    max_workers: int = 0      # 0 = share the global concurrent_workers cap
    is_default: bool = False


class BrowserPatch(BaseModel):
    name: Optional[str] = None
    cdp_url: Optional[str] = None
    user_data_dir: Optional[str] = None
    proxy: Optional[str] = None
    max_workers: Optional[int] = None
    is_default: Optional[bool] = None


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
    # Legacy single-browser shim: writing `cdp_url` also updates the default
    # browser row so both "Settings > CDP URL" and the Browsers tab stay in sync.
    if body.cdp_url:
        await db.set_setting("cdp_url", body.cdp_url)
        default_row = await db.get_default_browser()
        if default_row:
            await db.update_browser(default_row["id"], {"cdp_url": body.cdp_url})
    return await engine.connect_brave(cdp_url=body.cdp_url, browser_id=body.browser_id)


@api.post("/brave/disconnect")
async def brave_disconnect(browser_id: Optional[str] = None):
    return await engine.disconnect_brave(browser_id=browser_id)


def _resolve_brave_exe() -> Optional[str]:
    if platform.system() != "Windows":
        exe_candidates = [
            "brave", "brave-browser",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
    else:
        exe_candidates = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
    return next((p for p in exe_candidates if p and (shutil.which(p) or os.path.isfile(p))), None)


def _launch_brave_process(port: int, profile_dir: str, proxy: str = "") -> dict:
    """Spawn a detached Brave process listening on `port` with its own profile.
    Raises HTTPException on failure so callers can surface it to the UI."""
    brave_exe = _resolve_brave_exe()
    if not brave_exe:
        raise HTTPException(404, "brave.exe not found at default install locations")
    os.makedirs(profile_dir, exist_ok=True)
    args = [
        brave_exe,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
    ]
    if proxy:
        args.append(f"--proxy-server={proxy}")
    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
              "stdin": subprocess.DEVNULL, "close_fds": True}
    if platform.system() == "Windows":
        DETACHED = 0x00000008  # DETACHED_PROCESS
        CREATE_NEW_GROUP = 0x00000200
        kwargs["creationflags"] = DETACHED | CREATE_NEW_GROUP
    else:
        kwargs["start_new_session"] = True
    try:
        subprocess.Popen(args, **kwargs)
    except Exception as e:
        raise HTTPException(500, f"Failed to launch Brave: {str(e)[:200]}")
    return {"ok": True, "brave_exe": brave_exe, "port": port, "profile_dir": profile_dir,
            "proxy": proxy,
            "message": f"Brave launched on port {port}. Sign in to retailers inside it, then click Connect."}


@api.post("/brave/launch")
async def brave_launch():
    """Legacy one-click launch of the default Brave on port 9222. Kept so existing
    buttons still work; for per-browser launching use /api/browsers/{id}/launch."""
    profile_dir = os.path.join(os.path.expanduser("~"), "TechBotBraveSession")
    return _launch_brave_process(9222, profile_dir)


# ------ Browsers ------
def _parse_cdp_port(cdp_url: str) -> int:
    # accepts http://host:port or just host:port; defaults to 9222.
    try:
        host_port = cdp_url.split("://", 1)[-1]
        port_part = host_port.split(":")[-1].split("/")[0]
        return int(port_part)
    except Exception:
        return 9222


@api.get("/browsers")
async def browsers_list():
    rows = await db.list_browsers()
    # Annotate each row with its live connection state so the UI can show a
    # green dot next to connected sessions.
    live = {b["browser_id"] for b in (await engine.status())["browsers"] if b.get("connected")}
    for r in rows:
        r["connected"] = r["id"] in live
    return rows


@api.post("/browsers")
async def browsers_create(body: BrowserIn):
    data = _bool_fix(body.model_dump())
    return await db.create_browser(data)


@api.patch("/browsers/{bid}")
async def browsers_update(bid: str, body: BrowserPatch):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    patch = _bool_fix(patch)
    # Guard: refuse to unset the default flag if this is the only default row.
    # Without this, a user could end up with zero defaults and orphan the
    # fallback resolution used by _resolve_browser().
    if patch.get("is_default") == 0:
        current = await db.get_browser(bid)
        if current and current.get("is_default"):
            others = [b for b in await db.list_browsers() if b["id"] != bid and b.get("is_default")]
            if not others:
                raise HTTPException(400, "Cannot unset default on the only default browser. Promote another row first.")
    row = await db.update_browser(bid, patch)
    if not row:
        raise HTTPException(404, "browser not found")
    return row


@api.delete("/browsers/{bid}")
async def browsers_delete(bid: str):
    row = await db.get_browser(bid)
    if not row:
        raise HTTPException(404)
    # Forbid deleting the default browser — watchlist items / drops rely on a
    # default existing as fallback when their own browser_id is null. The UI
    # already disables the delete button but we enforce here too.
    if row.get("is_default"):
        raise HTTPException(400, "Cannot delete the default browser. Promote another row to default first.")
    # Disconnect any live session tied to this row before dropping it.
    await engine.disconnect_brave(browser_id=bid)
    await db.delete_browser(bid)
    return {"ok": True}


@api.post("/browsers/{bid}/connect")
async def browsers_connect(bid: str):
    return await engine.connect_brave(browser_id=bid)


@api.post("/browsers/{bid}/disconnect")
async def browsers_disconnect(bid: str):
    return await engine.disconnect_brave(browser_id=bid)


@api.post("/browsers/{bid}/launch")
async def browsers_launch(bid: str):
    """Spawn a Brave process for this row. Uses the row's `cdp_url` port,
    `user_data_dir`, and optional `proxy`. Windows-only for the spawn itself —
    on other OSes we still try best-effort via the resolved binary."""
    row = await db.get_browser(bid)
    if not row:
        raise HTTPException(404, "browser not found")
    port = _parse_cdp_port(row.get("cdp_url") or "")
    profile_dir = row.get("user_data_dir") or os.path.join(
        os.path.expanduser("~"), f"TechBotBrave_{row['name'].replace(' ', '_')}"
    )
    return _launch_brave_process(port, profile_dir, row.get("proxy") or "")


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
