"""Monitor engine: multi-worker Playwright CDP driver with sub-second polling,
Walmart queue handling, drop scheduler, and per-item purchase modes."""
from __future__ import annotations
import asyncio
import json
import random
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from playwright.async_api import async_playwright

import db
import sites
from discord_listener import DiscordListener

# --- Purchase modes ---------------------------------------------------------
PURCHASE_MODES = ("monitor", "cart", "checkout", "auto")


class LogBus:
    """Fan-out in-memory bus for WebSocket log subscribers + ring buffer."""
    def __init__(self, maxlen: int = 500):
        self.buf: list[dict] = []
        self.maxlen = maxlen
        self.subs: set[asyncio.Queue] = set()

    def push(self, level: str, msg: str, meta: Optional[dict] = None):
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "msg": msg,
            "meta": meta or {},
        }
        self.buf.append(entry)
        if len(self.buf) > self.maxlen:
            self.buf = self.buf[-self.maxlen:]
        for q in list(self.subs):
            try:
                q.put_nowait(entry)
            except asyncio.QueueFull:
                pass

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.subs.add(q)
        # prime with recent history
        for e in self.buf[-50:]:
            try:
                q.put_nowait(e)
            except asyncio.QueueFull:
                break
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self.subs.discard(q)


class MonitorEngine:
    def __init__(self):
        self.pw = None
        # Multi-browser sessions keyed by browsers.id. Each entry:
        #   {"browser": BrowserConnection, "context": Context, "cdp_url": str}
        self.sessions: dict[str, dict] = {}
        self.running: bool = False
        self.workers: dict[str, asyncio.Task] = {}  # watch_id -> task
        self.drop_tasks: dict[str, asyncio.Task] = {}
        self.logs = LogBus()
        self._connect_lock = asyncio.Lock()
        self.discord = DiscordListener(self)

    # ------- Back-compat properties for legacy single-browser callers.
    @property
    def browser(self):
        """Legacy: return the default session's Browser, or None."""
        sess = self.sessions.get(self._default_session_id())
        return sess["browser"] if sess else None

    @property
    def context(self):
        sess = self.sessions.get(self._default_session_id())
        return sess["context"] if sess else None

    @property
    def connected(self) -> bool:
        # "Connected" means at least ONE browser session is live.
        return any(
            s["browser"] and s["browser"].is_connected() for s in self.sessions.values()
        )

    def _default_session_id(self) -> Optional[str]:
        # Returns the id of whichever session was registered as default, or any
        # session if there's no explicit default yet (best-effort).
        for bid, sess in self.sessions.items():
            if sess.get("is_default"):
                return bid
        return next(iter(self.sessions.keys()), None)

    # ------- logging helpers -------
    def log(self, level: str, msg: str, meta: Optional[dict] = None):
        self.logs.push(level, msg, meta)

    def logger_for(self, name: str):
        def _inner(level: str, msg: str):
            self.log(level, f"{name}: {msg}")
        return _inner

    async def _resolve_browser(self, browser_id: Optional[str]) -> dict:
        """Load a browsers row by id, or the default row if browser_id is None/unknown."""
        row = None
        if browser_id:
            row = await db.get_browser(browser_id)
        if not row:
            row = await db.get_default_browser()
        if not row:
            # No rows at all — fabricate one from the legacy setting so old
            # installs still work. init_db() usually seeds this first boot.
            cdp = await db.get_setting("cdp_url") or "http://127.0.0.1:9222"
            row = {"id": "legacy", "name": "Default", "cdp_url": cdp, "is_default": 1,
                   "max_workers": 0, "user_data_dir": "", "proxy": ""}
        return row

    async def connect_brave(self, cdp_url: Optional[str] = None,
                            browser_id: Optional[str] = None) -> dict:
        """Attach Playwright over CDP for a single browser row. Back-compat:
        if called with just `cdp_url`, we attach to the default browser row and
        override its URL with the supplied one (mirrors the old single-browser
        behaviour the header Connect button uses)."""
        async with self._connect_lock:
            row = await self._resolve_browser(browser_id)
            bid = row["id"]
            url = cdp_url or row.get("cdp_url")
            try:
                if self.pw is None:
                    self.pw = await async_playwright().start()
                existing = self.sessions.get(bid)
                if existing and existing["browser"] and existing["browser"].is_connected():
                    return {"connected": True, "browser_id": bid, "name": row["name"],
                            "cdp_url": url, "message": "Already connected"}
                browser = await self.pw.chromium.connect_over_cdp(url)
                ctxs = browser.contexts
                context = ctxs[0] if ctxs else await browser.new_context()
                self.sessions[bid] = {
                    "browser": browser, "context": context, "cdp_url": url,
                    "is_default": bool(row.get("is_default")),
                    "name": row.get("name", "Browser"),
                    "max_workers": int(row.get("max_workers") or 0),
                }
                self.log("SUCCESS", f"Connected to {row.get('name','Brave')} @ {url}")
                return {"connected": True, "browser_id": bid, "name": row["name"],
                        "cdp_url": url, "message": "Connected"}
            except Exception as e:
                self.log("ERROR", f"CDP connect failed ({row.get('name','?')}): {str(e)[:160]}")
                return {"connected": False, "browser_id": bid, "cdp_url": url,
                        "message": str(e)[:200]}

    async def disconnect_brave(self, browser_id: Optional[str] = None) -> dict:
        """Disconnect one session. No arg → disconnect ALL sessions (legacy behaviour
        for the global header disconnect button)."""
        targets = [browser_id] if browser_id else list(self.sessions.keys())
        for bid in targets:
            sess = self.sessions.pop(bid, None)
            if sess:
                try:
                    await sess["browser"].close()
                except Exception:
                    pass
                self.log("INFO", f"Disconnected {sess.get('name','Brave')}")
        return {"connected": self.connected, "active": list(self.sessions.keys())}

    async def status(self) -> dict:
        browsers_status = []
        for bid, sess in self.sessions.items():
            browsers_status.append({
                "browser_id": bid,
                "name": sess.get("name"),
                "cdp_url": sess.get("cdp_url"),
                "connected": bool(sess["browser"] and sess["browser"].is_connected()),
                "workers": sum(1 for w in self._workers_by_browser().get(bid, [])),
                "max_workers": sess.get("max_workers", 0),
            })
        return {
            "connected": self.connected,
            "running": self.running,
            "active_workers": list(self.workers.keys()),
            "active_drops": list(self.drop_tasks.keys()),
            "discord_connected": self.discord.connected,
            "browsers": browsers_status,
        }

    def _workers_by_browser(self) -> dict[str, list[str]]:
        """Map each browser_id -> list of watch_ids currently running there."""
        out: dict[str, list[str]] = {}
        for wid, meta in getattr(self, "_worker_meta", {}).items():
            bid = meta.get("browser_id") or "_default"
            out.setdefault(bid, []).append(wid)
        return out

    async def _ensure_context(self, browser_id: Optional[str] = None):
        row = await self._resolve_browser(browser_id)
        bid = row["id"]
        sess = self.sessions.get(bid)
        if not sess or not sess["browser"] or not sess["browser"].is_connected():
            res = await self.connect_brave(browser_id=bid)
            if not res.get("connected"):
                raise RuntimeError(
                    f"{row.get('name','Brave')} not connected: {res.get('message','')}"
                )
            sess = self.sessions.get(bid)
        return sess["context"]

    async def _new_page(self, browser_id: Optional[str] = None):
        ctx = await self._ensure_context(browser_id)
        return await ctx.new_page()

    # ------- Discord / history notify -------
    async def _notify(self, title: str, desc: str, color: int = 0x00FF66):
        hook = await db.get_setting("discord_webhook")
        if not hook:
            return
        payload = {
            "embeds": [{
                "title": title, "description": desc, "color": color,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }]
        }
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                await c.post(hook, json=payload)
        except Exception as e:
            self.log("WARN", f"Discord webhook failed: {str(e)[:80]}")

    # ------- Core monitor loop per watch item -------
    async def _monitor_item(self, watch_id: str):
        item = await db.get_watch(watch_id)
        if not item:
            return
        name = item["name"]
        site = item["site"]
        url = item["url"]
        mode = item["purchase_mode"] or "monitor"
        # Per-item allowed button types (defaults to cart only)
        allowed_types = item.get("button_types")
        if isinstance(allowed_types, str):
            try:
                allowed_types = json.loads(allowed_types)
            except Exception:
                allowed_types = ["cart"]
        if not allowed_types:
            allowed_types = ["cart"]
        profile = await db.get_profile(item["profile_id"]) if item.get("profile_id") else None
        settings = await db.get_all_settings()
        poll_ms = int(settings.get("poll_interval_ms", 50))
        jitter = int(settings.get("jitter_ms", 200))
        reload_every = int(settings.get("reload_every_n_polls", 20))
        atc_max_retries = int(settings.get("atc_max_retries", 0))  # 0 = unlimited

        page = None
        keep_page_open = False  # set True on successful purchase so the user sees the result
        browser_id = item.get("browser_id")
        try:
            page = await self._new_page(browser_id=browser_id)
            self.log("INFO", f"[{sites.SITE_LABELS.get(site, site)}] Monitoring: {name}")
            await db.set_watch_status(watch_id, "WATCHING", "Started")

            # Initial hard navigation (only place we do page.goto by default)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            except Exception as e:
                self.log("WARN", f"[{name}] initial nav: {str(e)[:80]}")

            polls_since_reload = 0
            atc_retries = 0

            while True:
                t0 = time.monotonic()
                try:
                    # Periodic soft reload to refresh client-side state; no full re-navigation
                    if polls_since_reload >= reload_every:
                        try:
                            await page.reload(wait_until="domcontentloaded", timeout=15000)
                        except Exception as e:
                            # Hard fallback: full goto
                            try:
                                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                            except Exception:
                                self.log("WARN", f"[{name}] reload recovered: {str(e)[:60]}")
                        polls_since_reload = 0
                    polls_since_reload += 1
                except Exception as e:
                    self.log("WARN", f"[{name}] poll recover: {str(e)[:80]}")
                    await asyncio.sleep(1)
                    polls_since_reload = 0
                    continue

                # Captcha pause
                if await sites.is_captcha(page):
                    await db.set_watch_status(watch_id, "QUEUED", "Captcha — solve in Brave")
                    self.log("WARN", f"[{name}] CAPTCHA — solve it in Brave, bot is waiting…")
                    while await sites.is_captcha(page):
                        await asyncio.sleep(3)
                    self.log("SUCCESS", f"[{name}] Captcha cleared")
                    polls_since_reload = 0
                    continue

                # Queue / waiting-room handling (Walmart 9PM drop scenario)
                if await sites.is_queue(page, site):
                    await db.set_watch_status(watch_id, "QUEUED", "Waiting room — auto-advancing")
                    self.log("WARN", f"[{name}] In queue — auto-advancing every 3s…")
                    queue_start = time.monotonic()
                    while await sites.is_queue(page, site):
                        for btn_sel in [
                            "button:has-text('Continue')",
                            "button:has-text('Retry')",
                            "a:has-text('Continue')",
                        ]:
                            try:
                                b = page.locator(btn_sel).first
                                if await b.is_visible(timeout=500):
                                    await b.click(timeout=2000)
                            except Exception:
                                pass
                        await asyncio.sleep(3 + random.random())
                        if time.monotonic() - queue_start > 600:
                            try:
                                await page.reload(wait_until="domcontentloaded", timeout=20000)
                            except Exception:
                                pass
                            queue_start = time.monotonic()
                    self.log("SUCCESS", f"[{name}] Queue cleared")
                    polls_since_reload = 0
                    continue

                # Stock detection (per allowed button types)
                btn, btn_type = await sites.detect_in_stock(page, site, allowed_types)
                if btn:
                    # Price-drop guard (before any click)
                    live_price = await sites.get_price(page, site)
                    max_p = item.get("max_price")
                    enforce = bool(settings.get("enforce_max_price", True))
                    strict = bool(settings.get("strict_price_guard", False))
                    cooldown = int(settings.get("price_guard_cooldown_s", 300))
                    if enforce and max_p is not None:
                        if live_price is None and strict:
                            self.log("WARN", f"[{name}] price unreadable + strict guard → skipping ({cooldown}s cooldown)")
                            await db.set_watch_status(watch_id, "WATCHING", "Skipped: price unreadable")
                            await asyncio.sleep(cooldown)
                            continue
                        if live_price is not None and live_price > float(max_p):
                            msg = f"Live ${live_price:.2f} > max ${float(max_p):.2f} — skipping"
                            self.log("WARN", f"[{name}] {msg}")
                            await db.set_watch_status(watch_id, "WATCHING", msg)
                            await db.log_history({
                                "watch_id": watch_id, "name": name, "site": site, "url": url,
                                "outcome": "PRICE_SKIP", "price": live_price, "message": msg,
                            })
                            await self._notify("PRICE GUARD SKIP",
                                               f"**{name}** ${live_price:.2f} > cap ${float(max_p):.2f}",
                                               color=0xFFCC00)
                            await asyncio.sleep(cooldown)
                            continue

                    self.log("SUCCESS", f"[{name}] IN STOCK{f' @ ${live_price:.2f}' if live_price else ''} ({btn_type}) — executing mode={mode}")
                    await db.set_watch_status(watch_id, "IN_STOCK", f"{sites.BUTTON_LABELS.get(btn_type, btn_type)}{f' @ ${live_price:.2f}' if live_price else ''}")
                    await self._notify(
                        f"{sites.BUTTON_LABELS.get(btn_type, btn_type).upper()} AVAILABLE",
                        f"**{name}** on {sites.SITE_LABELS.get(site, site)}\n{url}",
                        color=0x00FF66 if btn_type == "cart" else (0x007AFF if btn_type == "preorder" else 0xFFCC00),
                    )
                    if mode == "monitor":
                        await db.log_history({
                            "watch_id": watch_id, "name": name, "site": site, "url": url,
                            "outcome": "NOTIFIED", "message": f"Monitor-only ({btn_type})",
                        })
                        await asyncio.sleep(60)
                        polls_since_reload = 0
                        continue

                    # Resilient purchase flow — any error here returns to the monitor loop
                    # instead of killing the worker.
                    try:
                        # Capture cart count BEFORE clicking. This lets
                        # verify_atc_success detect a positive N → N+1 increment
                        # even when the retailer hides its success modal.
                        pre_cart_count = None
                        if btn_type != "waitlist":
                            try:
                                pre_cart_count = await sites.get_cart_count(page, site)
                            except Exception:
                                pre_cart_count = None

                        ok = await sites.add_to_cart(page, site, self.logger_for(name), btn=btn, btn_type=btn_type)
                        if not ok:
                            atc_retries += 1
                            if atc_max_retries and atc_retries >= atc_max_retries:
                                await db.set_watch_status(watch_id, "ERROR", f"ATC failed {atc_retries}x — giving up")
                                self.log("ERROR", f"[{name}] ATC failed {atc_retries}x, hit retry cap, stopping")
                                return
                            await db.set_watch_status(watch_id, "WATCHING", f"ATC retry #{atc_retries}")
                            self.log("WARN", f"[{name}] ATC click failed, retry #{atc_retries} (will keep trying)")
                            await asyncio.sleep(0.5)
                            polls_since_reload = reload_every  # force reload next loop
                            continue

                        # Post-click verification: require a POSITIVE success
                        # signal (success modal OR cart-count increment) before
                        # declaring success. Missing modal + unchanged cart = retry.
                        if btn_type != "waitlist":
                            verified = await sites.verify_atc_success(
                                page, site, self.logger_for(name), pre_cart_count=pre_cart_count
                            )
                            if not verified:
                                atc_retries += 1
                                if atc_max_retries and atc_retries >= atc_max_retries:
                                    await db.set_watch_status(watch_id, "ERROR", f"Cart unconfirmed {atc_retries}x — giving up")
                                    return
                                await db.set_watch_status(watch_id, "WATCHING", f"Cart unconfirmed, retry #{atc_retries}")
                                self.log("WARN", f"[{name}] ATC not confirmed (no success signal / cart didn't increment), retry #{atc_retries}")
                                try:
                                    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                                except Exception:
                                    pass
                                polls_since_reload = 0
                                await asyncio.sleep(0.5)
                                continue

                        # Success — reset retry counter
                        atc_retries = 0

                        # Waitlist: terminal, no checkout
                        if btn_type == "waitlist":
                            await db.set_watch_status(watch_id, "PURCHASED", "Joined waitlist / notify-me")
                            await db.log_history({
                                "watch_id": watch_id, "name": name, "site": site, "url": url,
                                "outcome": "WAITLISTED", "price": live_price, "message": "Notify-me signup clicked",
                            })
                            keep_page_open = True
                            return

                        if mode in ("cart", "checkout", "auto"):
                            await sites.goto_cart(page, site)

                        if mode == "cart":
                            await db.set_watch_status(watch_id, "PURCHASED", "Added to cart")
                            await db.log_history({
                                "watch_id": watch_id, "name": name, "site": site, "url": url,
                                "outcome": "IN_CART", "price": live_price, "message": "Item added to cart",
                            })
                            await self._notify("IN CART", f"{name} — complete checkout in Brave", color=0x007AFF)
                            keep_page_open = True
                            return

                        # Proceed to checkout
                        await sites.click_checkout(page, site, self.logger_for(name))
                        if profile:
                            await sites.autofill(page, profile, self.logger_for(name))

                        if mode == "checkout":
                            await db.set_watch_status(watch_id, "PURCHASED", "Checkout filled — stopped before place order")
                            await db.log_history({
                                "watch_id": watch_id, "name": name, "site": site, "url": url,
                                "outcome": "CHECKOUT_READY", "message": "Auto-filled, stopped before Place Order",
                            })
                            await self._notify("READY TO CONFIRM", f"{name} — click Place Order in Brave", color=0xFFCC00)
                            keep_page_open = True
                            return

                        if mode == "auto":
                            if settings.get("stop_before_place_order", True):
                                await db.set_watch_status(watch_id, "PURCHASED", "Stopped before Place Order (global safety)")
                                await db.log_history({
                                    "watch_id": watch_id, "name": name, "site": site, "url": url,
                                    "outcome": "CHECKOUT_READY", "message": "Global safety held final click",
                                })
                                await self._notify("READY TO CONFIRM", f"{name} — place order disabled by safety", color=0xFFCC00)
                                keep_page_open = True
                                return
                            placed = await sites.click_place_order(page, site, self.logger_for(name))
                            outcome = "PURCHASED" if placed else "FAILED"
                            await db.set_watch_status(watch_id, "PURCHASED" if placed else "WATCHING",
                                                      "Order placed" if placed else "Place order failed — will retry")
                            await db.log_history({
                                "watch_id": watch_id, "name": name, "site": site, "url": url,
                                "outcome": outcome, "price": live_price, "message": "Full auto",
                            })
                            await self._notify(
                                "ORDER PLACED" if placed else "PLACE ORDER FAILED",
                                f"{name}", color=0x00FF66 if placed else 0xFF3B30,
                            )
                            if placed:
                                keep_page_open = True
                                return
                            # else fall through to except/continue-style retry
                            atc_retries += 1
                            await asyncio.sleep(0.5)
                            continue
                    except Exception as e:
                        # Any exception during purchase — log & resume monitoring (don't kill worker)
                        atc_retries += 1
                        self.log("WARN", f"[{name}] purchase flow error (retry #{atc_retries}): {str(e)[:120]}")
                        await db.set_watch_status(watch_id, "WATCHING", f"Retrying after error #{atc_retries}")
                        try:
                            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        except Exception:
                            pass
                        polls_since_reload = 0
                        await asyncio.sleep(0.5)
                        continue
                else:
                    await db.set_watch_status(watch_id, "OOS", "Out of stock")

                # Polling cadence
                elapsed = (time.monotonic() - t0) * 1000
                wait_ms = max(50, poll_ms - elapsed) + random.uniform(0, jitter)
                await asyncio.sleep(wait_ms / 1000.0)

        except asyncio.CancelledError:
            await db.set_watch_status(watch_id, "IDLE", "Stopped")
            self.log("INFO", f"[{name}] Stopped")
            raise
        except Exception as e:
            await db.set_watch_status(watch_id, "ERROR", str(e)[:140])
            self.log("ERROR", f"[{name}] fatal: {str(e)[:140]}")
        finally:
            try:
                if page and not keep_page_open:
                    await page.close()
            except Exception:
                pass
            self.workers.pop(watch_id, None)

    # ------- Start/stop controls -------
    async def start_item(self, watch_id: str) -> dict:
        item = await db.get_watch(watch_id)
        if not item:
            return {"ok": False, "error": "not found"}
        if watch_id in self.workers and not self.workers[watch_id].done():
            return {"ok": True, "running": True}
        if not self.connected:
            res = await self.connect_brave()
            if not res["connected"]:
                return {"ok": False, "error": f"Brave not connected: {res['message']}"}
        task = asyncio.create_task(self._monitor_item(watch_id))
        self.workers[watch_id] = task
        self.running = True
        return {"ok": True, "running": True}

    async def stop_item(self, watch_id: str) -> dict:
        task = self.workers.get(watch_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                # CancelledError is a BaseException in 3.8+ and escapes
                # `except Exception`; swallow it so the HTTP handler returns 200.
                pass
        self.workers.pop(watch_id, None)
        await db.set_watch_status(watch_id, "IDLE", "Stopped")
        if not self.workers and not self.drop_tasks:
            self.running = False
        return {"ok": True}

    async def start_all(self) -> dict:
        items = await db.list_watch()
        active = [i for i in items if i.get("active")]
        started = 0
        for it in active:
            r = await self.start_item(it["id"])
            if r.get("ok"):
                started += 1
        return {"ok": True, "started": started}

    async def stop_all(self) -> dict:
        stopped = 0
        for wid in list(self.workers.keys()):
            await self.stop_item(wid)
            stopped += 1
        for did in list(self.drop_tasks.keys()):
            t = self.drop_tasks.pop(did)
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
            stopped += 1
        self.running = False
        return {"ok": True, "stopped": stopped}

    # ------- Drop scheduler -------
    async def _run_drop(self, drop_id: str):
        drop = await db.get_drop(drop_id)
        if not drop:
            return
        name = drop["name"]
        try:
            run_at = datetime.fromisoformat(drop["run_at"])
        except Exception:
            self.log("ERROR", f"[DROP:{name}] bad run_at"); return
        if run_at.tzinfo is None:
            run_at = run_at.replace(tzinfo=timezone.utc)

        urls = drop["urls"]
        if isinstance(urls, str):
            try: urls = json.loads(urls)
            except Exception: urls = [urls]

        now = datetime.now(timezone.utc)
        wait = (run_at - now).total_seconds()
        if wait > 30:
            self.log("INFO", f"[DROP:{name}] Waiting {int(wait)}s until drop time")
            await asyncio.sleep(wait - 30)  # arm 30s early
        await db.update_drop(drop_id, {"status": "ARMING"})
        self.log("WARN", f"[DROP:{name}] ARMED — starting rapid poll window")

        if not self.connected:
            await self.connect_brave(browser_id=drop.get("browser_id"))

        # Spawn one page per URL (blast mode) or one rolling page (sequential)
        blast = bool(drop.get("blast_mode"))
        profile = await db.get_profile(drop["profile_id"]) if drop.get("profile_id") else None
        mode = drop["purchase_mode"] or "cart"
        duration_s = int(drop.get("duration_min") or 15) * 60
        drop_browser_id = drop.get("browser_id")

        async def hammer(u: str):
            try:
                page = await self._new_page(browser_id=drop_browser_id)
            except Exception as e:
                self.log("ERROR", f"[DROP:{name}] page err: {str(e)[:80]}"); return
            end_at = datetime.now(timezone.utc).timestamp() + duration_s
            drop_hit = False
            try:
                while datetime.now(timezone.utc).timestamp() < end_at:
                    try:
                        await page.goto(u, wait_until="domcontentloaded", timeout=15000)
                    except Exception:
                        await asyncio.sleep(0.5); continue
                    if drop.get("queue_handling") and await sites.is_queue(page, drop["site"]):
                        self.log("WARN", f"[DROP:{name}] queued, advancing…")
                        while await sites.is_queue(page, drop["site"]):
                            for b in ["button:has-text('Continue')", "button:has-text('Retry')"]:
                                try:
                                    el = page.locator(b).first
                                    if await el.is_visible(timeout=400):
                                        await el.click(timeout=1500)
                                except Exception:
                                    pass
                            await asyncio.sleep(2)
                        continue
                    btn, btn_type = await sites.detect_in_stock(page, drop["site"], ["cart", "preorder"])
                    if btn:
                        self.log("SUCCESS", f"[DROP:{name}] {sites.BUTTON_LABELS.get(btn_type, btn_type)} ({u})")
                        # Capture cart count pre-click for positive-confirmation.
                        try:
                            pre_cart_count = await sites.get_cart_count(page, drop["site"])
                        except Exception:
                            pre_cart_count = None
                        clicked = await sites.add_to_cart(page, drop["site"], self.logger_for(f"DROP:{name}"), btn=btn, btn_type=btn_type)
                        if not clicked:
                            await asyncio.sleep(0.4); continue
                        verified = await sites.verify_atc_success(
                            page, drop["site"], self.logger_for(f"DROP:{name}"), pre_cart_count=pre_cart_count
                        )
                        if not verified:
                            # False positive — item was OOS or rejected. Keep hammering.
                            await asyncio.sleep(0.4)
                            continue
                        await sites.goto_cart(page, drop["site"])
                        if mode in ("checkout", "auto"):
                            await sites.click_checkout(page, drop["site"], self.logger_for(f"DROP:{name}"))
                            if profile:
                                await sites.autofill(page, profile, self.logger_for(f"DROP:{name}"))
                        if mode == "auto":
                            s = await db.get_all_settings()
                            if not s.get("stop_before_place_order", True):
                                await sites.click_place_order(page, drop["site"], self.logger_for(f"DROP:{name}"))
                        await db.log_history({
                            "name": name, "site": drop["site"], "url": u,
                            "outcome": "DROP_HIT", "message": f"mode={mode}",
                        })
                        await self._notify("DROP HIT", f"{name}\n{u}", color=0x00FF66)
                        drop_hit = True
                        return
                    await asyncio.sleep(0.4 + random.random() * 0.3)
            finally:
                # Leave the page open for the user to verify / finish checkout
                # when a drop was hit. Only auto-close on timeout/failure.
                if not drop_hit:
                    try: await page.close()
                    except Exception: pass

        await db.update_drop(drop_id, {"status": "RUNNING"})
        if blast:
            await asyncio.gather(*[hammer(u) for u in urls], return_exceptions=True)
        else:
            for u in urls:
                await hammer(u)
        await db.update_drop(drop_id, {"status": "COMPLETED"})
        self.drop_tasks.pop(drop_id, None)
        self.log("INFO", f"[DROP:{name}] window complete")

    async def schedule_drop(self, drop_id: str) -> dict:
        if drop_id in self.drop_tasks and not self.drop_tasks[drop_id].done():
            return {"ok": True, "running": True}
        task = asyncio.create_task(self._run_drop(drop_id))
        self.drop_tasks[drop_id] = task
        await db.update_drop(drop_id, {"status": "SCHEDULED"})
        return {"ok": True}

    async def cancel_drop(self, drop_id: str) -> dict:
        t = self.drop_tasks.pop(drop_id, None)
        if t:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        await db.update_drop(drop_id, {"status": "CANCELLED"})
        return {"ok": True}


engine = MonitorEngine()
