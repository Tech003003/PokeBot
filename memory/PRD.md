# TechBot Command Center — PRD

## Original problem statement
Rebuild an existing Python/NiceGUI Pokémon scalper (bot.py + Main.py) into an
inclusive local desktop app with:
- Optional auto-purchase
- Full dashboard for settings + management
- Proper Walmart 9 PM drop handling (auto-refresh + auto-queue advance + multi-URL blast)
- Reliable out-of-stock detection across more retailers

## User choices captured (2026-04-23)
- **Shape**: local desktop app (FastAPI + React served on 127.0.0.1:8787, connects to user's Brave via CDP)
- **Polling**: multiple times per second (default 700 ms, configurable down to 100 ms, with jitter)
- **Purchase modes per item**: Monitor / Cart / Checkout (stop before Place Order) / Full Auto
- **Walmart drops**: scheduled drops, blast multiple URLs in parallel, auto-advance waiting-room queues
- **Sites**: Walmart, Pokémon Center, Amazon, Target, Best Buy, GameStop, Costco, Sam's Club, TCGPlayer
- **Notifications**: Discord webhook + desktop toasts + sound alerts (all configurable)

## Architecture
- `backend/server.py` — FastAPI, /api REST + /api/ws/logs WebSocket
- `backend/engine.py` — MonitorEngine: Playwright CDP, per-item async workers, drop scheduler, LogBus fan-out, Discord notify
- `backend/sites.py`  — Per-retailer SELECTORS / queue sigs / captcha sigs / autofill map, helpers: `detect_in_stock`, `add_to_cart`, `click_checkout`, `click_place_order`, `is_queue`, `is_captcha`, `autofill`
- `backend/db.py`     — SQLite (aiosqlite). Tables: watchlist, profiles, drops, history, settings (JSON values)
- `frontend/src/`     — React dashboard (Chivo / Inter / JetBrains Mono, dark "Performance Pro" theme). Tabs: Monitor / Watchlist / Drops / Profiles / History / Settings
- `local/launch.py`   — Single-process launcher that serves `frontend/build` + starts uvicorn + opens browser
- `local/Start.bat`, `local/Start-Brave.bat`, `local/README.md` — Windows bootstrapping

## What's been implemented (2026-04-23)
- Full CRUD for Watchlist, Profiles (with card masking), Drops, Settings
- Brave CDP connect/disconnect controls in header
- Per-item start/stop + global Start All / Stop All kill switches
- Sub-second polling loop with captcha pause, queue auto-advance, ATC + checkout + autofill + optional place-order
- Drop scheduler that wakes ~30 s early, blasts URLs in parallel, 15-min hammer window
- Global safety toggle that blocks Place-Order even in Full Auto
- Live WebSocket terminal (400-line ring buffer, color-coded by level)
- Purchase history table with outcome badges
- Discord webhook + masked card storage
- Local `.bat`-driven launch path, SQLite portable, no external services required
- Backend smoke-tested via curl (all endpoints respond correctly; CDP errors gracefully surfaced)
- Frontend verified via screenshot (all tabs render, terminal streaming works)

## Prioritized backlog (future / P1-P2)
- **P1** Wire sound alerts (`<audio>` on IN_STOCK) and browser-native desktop toasts in frontend
- **P1** Per-site CAPTCHA solver integration hook (2Captcha / CapMonster) toggle in Settings
- **P1** Proxy list support per site (stealth delays + user-agent rotation already scaffolded, needs UI)
- **P2** Screenshot snapshot on IN_STOCK / PURCHASED events, displayed in History
- **P2** Per-item cooldown after purchase to prevent duplicate orders
- **P2** Field-level encryption for card data using a user-set master password (Fernet)
- **P2** PyInstaller one-file build pipeline (`pyinstaller.spec`) for single `.exe` distribution
- **P2** GameStop/TCGPlayer/Costco selector coverage refresh as sites change
- **P3** Telegram + Email notification options (framework is generic; add channels)
- **P3** Analytics: success rate per site / mode, price alerts below `max_price`

## Known limitations
- Works only when the dashboard and Brave run on the same machine (localhost CDP).
- Retailer selectors drift; expect to add new ones to `backend/sites.py` periodically.
- Full-auto Place-Order is disabled by a global safety toggle by default.
