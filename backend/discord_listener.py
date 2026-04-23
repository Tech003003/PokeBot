"""Discord message listener for NexusBot.

Listens to messages in user-configured channels (in the USER'S OWN Discord server,
typically populated via Discord's 'Follow' feature from public drop-alert channels),
parses retailer URLs from message text + embeds, and auto-adds them to the
watchlist. Optionally auto-starts a watcher in the configured mode.

NOTE: You cannot add this bot to servers you don't own. The intended workflow is:
  1. User creates their own Discord server.
  2. User invites this bot to their own server.
  3. User follows the source (public drop-alert) announcement channels into their
     own channels. Discord mirrors the messages — this bot listens to the mirrored
     copies in the user's server.
"""
from __future__ import annotations
import asyncio
import re
from typing import Optional

import discord

import db
import sites as sitelib

URL_RE = re.compile(r"https?://[^\s\)\]\"'>]+")
PRICE_RE = re.compile(r"\$\s?(\d+(?:,\d{3})*(?:\.\d{1,2})?)")

SITE_DOMAINS = {
    "walmart": ["walmart.com"],
    "pokemoncenter": ["pokemoncenter.com"],
    "amazon": ["amazon.com", "amzn.to", "amzn.com", "a.co"],
    "target": ["target.com"],
    "bestbuy": ["bestbuy.com"],
    "gamestop": ["gamestop.com"],
    "costco": ["costco.com"],
    "samsclub": ["samsclub.com"],
    "tcgplayer": ["tcgplayer.com"],
}


def _detect_site(url: str) -> Optional[str]:
    u = url.lower()
    for site, domains in SITE_DOMAINS.items():
        if any(d in u for d in domains):
            return site
    return None


def _first_price(text: str) -> Optional[float]:
    if not text:
        return None
    m = PRICE_RE.search(text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_message(msg: "discord.Message") -> Optional[dict]:
    """Return a dict with {name, url, site, price} or None if nothing parseable."""
    text_blobs: list[str] = []
    name = None
    url = None
    site = None
    price = None

    if msg.content:
        text_blobs.append(msg.content)

    for embed in msg.embeds or []:
        if embed.title and not name:
            name = embed.title
        for t in (embed.title, embed.description, embed.footer.text if embed.footer else None):
            if t:
                text_blobs.append(t)
        if embed.url:
            s = _detect_site(embed.url)
            if s and not url:
                url, site = embed.url, s
                if not name:
                    name = embed.title or url
        for field in embed.fields or []:
            if field.value:
                text_blobs.append(f"{field.name}: {field.value}")
            if field.name and "price" in field.name.lower() and price is None:
                price = _first_price(field.value or "")

    # URL: prefer retailer URLs found in any text blob if embed.url wasn't a retailer
    if not url:
        for blob in text_blobs:
            for m in URL_RE.finditer(blob):
                u = m.group(0).rstrip(".,;)>]}\"'")
                s = _detect_site(u)
                if s:
                    url, site = u, s
                    break
            if url:
                break

    if not url or not site:
        return None

    if price is None:
        for blob in text_blobs:
            price = _first_price(blob)
            if price is not None:
                break

    # Clean up name: strip retailer prefixes like "Target - ..."
    if not name:
        name = f"Discord · {sitelib.SITE_LABELS.get(site, site)}"
    name = re.sub(r"^\s*(Target|Walmart|Amazon|Best\s?Buy|Pok[eé]mon\s?Center|GameStop|Costco|Sam'?s\s?Club|TCG\s?Player)\s*[-–—:]\s*",
                  "", name, flags=re.I).strip()

    # If the remaining title is a generic status string, prefer the first line of description
    GENERIC = re.compile(r"^\s*(item\s+)?(in\s*stock|restocked?|drop|alert|live|new\s+drop)\s*!?\s*$", re.I)
    if GENERIC.match(name):
        for embed in msg.embeds or []:
            if embed.description:
                first_line = embed.description.strip().splitlines()[0].strip()
                if first_line and len(first_line) > 5:
                    name = first_line
                    break

    name = name[:180] or f"Discord · {site}"

    return {"name": name, "url": url, "site": site, "price": price}


class DiscordListener:
    """Owns the discord.py client and its asyncio task lifecycle."""

    def __init__(self, engine):
        self.engine = engine
        self.client: Optional[discord.Client] = None
        self.task: Optional[asyncio.Task] = None
        self.connected: bool = False
        self._dedupe: set[str] = set()   # URLs seen this session to avoid dup-adds
        self._dedupe_cap: int = 500

    def _log(self, level: str, msg: str):
        self.engine.log(level, f"[discord] {msg}")

    async def start(self, token: str) -> dict:
        if self.task and not self.task.done():
            return {"ok": True, "running": True, "message": "already running"}
        if not token:
            return {"ok": False, "error": "no token"}

        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)

        @self.client.event
        async def on_ready():
            self.connected = True
            self._log("SUCCESS", f"logged in as {self.client.user} "
                                 f"(watching {len(self.client.guilds)} guild(s))")

        @self.client.event
        async def on_disconnect():
            self.connected = False
            self._log("WARN", "disconnected")

        @self.client.event
        async def on_message(msg: discord.Message):
            try:
                if self.client.user and msg.author.id == self.client.user.id:
                    return
                await self._handle(msg)
            except Exception as e:
                self._log("ERROR", f"on_message: {str(e)[:140]}")

        async def _runner():
            try:
                await self.client.start(token)
            except discord.LoginFailure:
                self._log("ERROR", "login failed — bad token")
            except Exception as e:
                self._log("ERROR", f"client crashed: {str(e)[:140]}")
            finally:
                self.connected = False

        self.task = asyncio.create_task(_runner())
        self._log("INFO", "starting…")
        return {"ok": True, "running": True}

    async def stop(self) -> dict:
        try:
            if self.client:
                await self.client.close()
        except Exception:
            pass
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except Exception:
                pass
        self.client = None
        self.task = None
        self.connected = False
        self._log("INFO", "stopped")
        return {"ok": True}

    async def _handle(self, msg: discord.Message):
        settings = await db.get_all_settings()
        rules = settings.get("discord_channel_rules") or {}
        cid = str(msg.channel.id)
        rule = rules.get(cid)
        if not rule:
            return  # channel not configured → ignore

        parsed = parse_message(msg)
        if not parsed:
            return

        # Dedupe on URL within this session
        if parsed["url"] in self._dedupe:
            self._log("INFO", f"dup skip: {parsed['name']}")
            return
        self._dedupe.add(parsed["url"])
        if len(self._dedupe) > self._dedupe_cap:
            self._dedupe = set(list(self._dedupe)[-self._dedupe_cap // 2:])

        action = (rule.get("action") or "monitor").lower()
        priority = int(rule.get("priority") or 5)
        max_price = rule.get("max_price")
        profile_id = rule.get("profile_id") or None
        auto_start = bool(rule.get("auto_start", True))

        # Don't duplicate a watch that already exists for this exact URL
        existing = [w for w in await db.list_watch() if w["url"] == parsed["url"]]
        if existing:
            self._log("INFO", f"already in watchlist: {parsed['name']}")
            watch_id = existing[0]["id"]
        else:
            data = {
                "name": parsed["name"],
                "site": parsed["site"],
                "url": parsed["url"],
                "purchase_mode": action,
                "priority": priority,
                "active": 1,
                "max_price": float(max_price) if max_price not in (None, "") else None,
                "quantity": 1,
                "profile_id": profile_id,
                "status": "IDLE",
            }
            created = await db.create_watch(data)
            watch_id = created["id"]
            price_note = f" @ ${parsed['price']:.2f}" if parsed.get("price") else ""
            self._log("SUCCESS", f"added '{parsed['name']}' [{parsed['site']}] mode={action}{price_note}")

        # Auto-start the watcher unless the rule says monitor-only or auto_start is off
        if auto_start and action != "monitor":
            try:
                await self.engine.start_item(watch_id)
            except Exception as e:
                self._log("WARN", f"auto-start failed: {str(e)[:120]}")

        # Try to acknowledge in-channel (best-effort — ignore if we lack perms)
        try:
            await msg.add_reaction("🎯")
        except Exception:
            pass
