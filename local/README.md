# NexusBot Command Center

Local, self-hosted Pokémon TCG / hot-drop scalper dashboard with optional auto-purchase.
Rebuild of the original Pokémon Scalper V5 (`bot.py` / `Main.py` / NiceGUI) with:

- Dense "command center" React dashboard (replaces the NiceGUI single panel)
- Sub-second polling (configurable, default 700 ms) with jitter
- Four purchase modes per item: **Monitor**, **Add to cart**, **Checkout (stop before Place Order)**, **Full Auto**
- Global safety switch that blocks the final "Place Order" click even in Full Auto
- Walmart-style **Drop Scheduler** — schedule a date/time, arm a URL (or many) for blast, auto-advance waiting-room queues
- CAPTCHA pause-and-wait (solve in Brave, bot resumes)
- 9 retailers: Walmart, Pokémon Center, Amazon, Target, Best Buy, GameStop, Costco, Sam's Club, TCGPlayer
- Reusable shipping/payment Profiles for autofill during checkout
- Live WebSocket terminal stream + purchase history
- Discord webhook notifications, desktop toasts, sound alerts
- All data in local SQLite file (`nexusbot.db`). Nothing leaves your PC.

---

## 1. First-time setup (Windows)

1. Install Python 3.10+ (check "Add to PATH") and Node.js 18+ (Yarn comes with Corepack).
2. Double-click **`local/Start.bat`**. It will:
   - create a venv,
   - install backend deps (`pip install -r backend/requirements.txt`),
   - install the Playwright Chromium driver,
   - build the React frontend (first run only),
   - launch the dashboard at **http://127.0.0.1:8787** and open your browser.

## 2. Connecting to Brave (required for monitoring / auto-purchase)

The bot attaches to your **own Brave browser** over the Chrome DevTools Protocol, so your
logins, saved addresses and payment methods stay inside Brave.

1. Close all Brave windows.
2. Double-click **`local/Start-Brave.bat`** (or run manually:
   `"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\Desktop\NexusBotBraveSession"`).
3. In the Brave window that opens, log into Walmart / Target / Pokémon Center / etc.
4. Back on the dashboard, click **Connect Brave** (top-right). When it turns orange/solid, you're wired in.

## 3. Using it

- **Watchlist** → add products (URL + retailer + mode). Start/stop each with ▶/■. Start All in header.
- **Drops** → schedule a date/time for a Walmart 9 PM drop, paste one or more URLs, enable blast + queue handling. Click **Arm**. The bot will wake up ~30 s before the drop, handle the waiting room, and execute your chosen mode as soon as stock is live.
- **Profiles** → shipping/payment info used by Checkout / Full Auto modes for autofill. Stored in the local SQLite file.
- **Settings** → poll interval, jitter, Discord webhook, sounds, global "stop before Place Order" safety.

## 4. Purchase modes

| Mode | What the bot does when stock is detected |
|---|---|
| `monitor`  | Notifies only (Discord + terminal). No clicks. |
| `cart`     | Clicks Add to Cart, navigates to cart, stops. |
| `checkout` | Cart → Checkout → autofills shipping/payment from profile, stops before Place Order. |
| `auto`     | Same as `checkout`, plus clicks **Place Order** if the global safety toggle is OFF. |

Global safety (on by default): even in `auto`, the final Place-Order click is blocked. Turn it off in **Settings → Safety** once you're confident.

## 5. Architecture

- `backend/server.py` — FastAPI + WebSocket + REST (`/api/*`)
- `backend/engine.py` — Async Playwright CDP engine, per-item workers, drop scheduler
- `backend/sites.py`  — Selectors + flows for 9 retailers
- `backend/db.py`     — SQLite (aiosqlite) persistence
- `frontend/`         — React dashboard (Chivo / Inter / JetBrains Mono, "Performance Pro" dark theme)
- `local/launch.py`   — Single-process launcher that mounts the built frontend + starts uvicorn on 127.0.0.1:8787

## 6. Notes / disclaimers

- Site selectors drift. If a retailer's Add-to-Cart button stops firing, open `backend/sites.py` and add the new selector to the `_SELECTORS` list for that site.
- Auto-purchase is at your own risk. Start with `cart` or `checkout` mode before enabling `auto`.
- Respect each retailer's terms of service and local laws.
