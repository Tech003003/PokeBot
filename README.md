# TechBot Command Center — Complete User Guide (No Coding Required)

A local Pokémon / hot-item scalper dashboard with optional auto-purchase. Everything
runs on **your own PC** — your logins, shipping address, and payment info never leave
your computer.

---

## 🚀 EASIEST INSTALL — download the ready-to-run .exe

If you just want to run the app without installing Python, Node.js, or anything else:

1. Install **[Brave browser](https://brave.com/download)** (the bot drives your Brave window).
2. Go to the "Actions" tab on the repo.
3. Download **`TechBot-windows.zip`** under **Assets**.
4. Right-click the ZIP → **Extract All…** → pick anywhere (Desktop is fine).
5. Open the extracted folder, double-click **`TechBot.exe`**.
6. The dashboard opens automatically at **http://127.0.0.1:8787**.
7. Double-click **`Start-Brave.bat`** (also in the folder) to open Brave with the debug port,
   log into your retailer accounts once, then click **CONNECT BRAVE** on the dashboard.

That's it. No coding, no Python, no installs beyond Brave.

> **First launch notes:** Windows Defender may flag the .exe once as "Windows protected your
> PC" — click **More info** → **Run anyway**. This is a normal false-positive for
> PyInstaller-bundled Python apps. The ZIP is ~250 MB (it includes the Chromium browser
> driver and the entire Python runtime — you never need to install those yourself).

### Don't see a Release yet?

Someone needs to **tag a version** on the repo to trigger a build. From the repo page on
GitHub → Releases → **Draft a new release** → create a new tag like `v1.0.0` → publish.
GitHub's build pipeline automatically produces the .exe ZIP and attaches it to that
release (takes ~8 minutes). You can also go to the **Actions** tab → **Build Windows EXE**
→ **Run workflow** to build on-demand without tagging.

---

---

## 🤖 Bonus — Auto-import drops from a public drop-alert Discord (PokePings, etc.)

TechBot can listen to a Discord channel and **auto-add any retailer URL it sees to your
Watchlist** — optionally auto-starting the watcher in cart/checkout/auto mode. This lets
you piggyback on public drop-alert services like PokePings.

### ⚠ Important: you cannot add bots to servers you don't own

PokePings (and most public drop-alert services) won't let you add your own bot to their
server. The legit workaround, built into Discord itself:

1. **Create your own Discord server** (free, takes 10 seconds — click the `+` in your
   server list → Create My Own → For me and my friends).
2. **Create a bot** at [discord.com/developers/applications](https://discord.com/developers/applications):
   - Click **New Application** → name it "TechBot" → **Bot** tab → **Reset Token** → Copy.
   - Under **Privileged Gateway Intents**, enable **MESSAGE CONTENT INTENT**.
   - **OAuth2 → URL Generator** → scopes: `bot`. Permissions: `View Channels`,
     `Read Message History`, `Add Reactions`. Copy the URL, open it, invite the bot to
     **your** server.
3. **"Follow" PokePings' channels into yours:**
   - In your own server, create a channel called `#drops` (or one per retailer).
   - Go to PokePings' server and open one of the alert channels (like the Target one).
     **If it has the megaphone/Announcement icon next to the channel name**, click the
     **"Follow"** button at the top and pick the channel in your server to mirror into.
   - Discord will now automatically repost every PokePings alert into your own channel,
     where your bot can read it. This is 100% Discord ToS compliant.
   - If PokePings' channels are NOT Announcement channels (no Follow button), the only
     other legit options are: (a) use their official webhook/API if offered, or (b) ask
     their admins to convert the channels. Self-botting with your user token is
     ToS-violating and will get your account banned — TechBot refuses to do that.
4. **Configure the listener in TechBot:**
   - Dashboard → **Settings** tab → **Discord Auto-Import** section.
   - Paste your bot's token.
   - Check **Enable Discord listener**.
   - Click **+ Add channel** and paste the ID of your mirror channel (right-click the
     channel in Discord → Copy Channel ID; enable Developer Mode in Settings → Advanced
     if you don't see that).
   - For each channel, pick:
     - **Action** — what to do when an alert arrives (`monitor` = just add; `cart` = add
       & auto-start in cart mode; etc.).
     - **Priority** (1–10).
     - **Max $** — optional ceiling; combined with the Price Guard, skips purchases on
       overpriced drops.
     - **auto-start** — whether to start the watcher immediately after adding.
   - Click **Save Settings**. The bot connects and the status dot turns green.

### What gets parsed

For each new message in a configured channel, the bot extracts:
- The **retailer URL** (matched against Walmart / Pokémon Center / Amazon / Target /
  Best Buy / GameStop / Costco / Sam's Club / TCGPlayer domains)
- The **product name** (from embed title, or first line of embed description if the
  title is just "Restocked" / "In Stock")
- The **price** (from a field labeled "Price", or the first `$XX.XX` found anywhere)

Duplicate URLs are de-duplicated within a session, and any URL already in your Watchlist
is reused instead of re-added. The bot reacts with 🎯 in the source channel so you can
tell at a glance which alerts it picked up.

---

## Table of contents

0. [🚀 Easy install — download the .exe](#-easiest-install--download-the-ready-to-run-exe) (start here if you don't code)
1. [What you're installing](#1-what-youre-installing) *(build-from-source path)*
2. [Download the project to your PC](#2-download-the-project-to-your-pc)
3. [Install Python](#3-install-python)
4. [Install Node.js](#4-install-nodejs)
5. [Install Brave browser](#5-install-brave-browser)
6. [First-time setup (one click)](#6-first-time-setup-one-click)
7. [Every-day use — how to launch the app](#7-every-day-use--how-to-launch-the-app)
8. [Dashboard tour](#8-dashboard-tour)
9. [Configuring a Watch](#9-configuring-a-watch-full-reference)
10. [Configuring a Drop (scheduled drops)](#10-configuring-a-drop-full-reference)
11. [Configuring a Profile (autofill)](#11-configuring-a-profile-full-reference)
12. [Global Settings reference](#12-global-settings-full-reference)
13. [Troubleshooting](#13-troubleshooting)
14. [Legal / disclaimer](#14-legal--disclaimer)

---

## 1. What you're installing

Three free programs:

1. **Python** — the language the bot is written in. [python.org](https://www.python.org/downloads/)
2. **Node.js** — builds the dashboard's web page. [nodejs.org](https://nodejs.org/)
3. **Brave browser** — the browser the bot controls. [brave.com/download](https://brave.com/download)

After the one-time setup, you'll never type a command again — just double-click `Start.bat`.

---

## 2. Download the project to your PC

### Option A — ZIP download (easiest)

1. In Emergent, click **"Save to GitHub"** in the chat input (connect your GitHub
   account if prompted — make one free at [github.com/signup](https://github.com/signup)).
2. Open the GitHub repo Emergent created.
3. Click the green **"Code"** button → **"Download ZIP"**.
4. Find the ZIP in your Downloads, right-click → **"Extract All…"** → pick Desktop.
5. Rename the extracted folder to **`TechBot`**.

### Option B — `git clone`

```
git clone https://github.com/<you>/<repo>.git TechBot
```

---

## 3. Install Python

1. Go to [python.org/downloads](https://www.python.org/downloads/).
2. Click the big yellow **Download Python 3.X.X** button.
3. Open the installer. **⚠ Tick the "Add python.exe to PATH" box at the bottom of the first screen** — this is the single most important step.
4. Click **Install Now** → **Close**.

**Verify:** press **Win key** → type `cmd` → Enter → type `python --version` → Enter.
You should see `Python 3.12.x` (or similar). If you see `'python' is not recognized`,
uninstall Python from Add/Remove Programs and reinstall with the PATH box ticked.

---

## 4. Install Node.js

1. Go to [nodejs.org](https://nodejs.org/).
2. Download the **LTS** version (big green button). Run the `.msi` file.
3. Click Next → I accept → Next → Next → Install → Finish.
4. Open a fresh `cmd` window and type `corepack enable` → Enter. (Enables Yarn.)

---

## 5. Install Brave browser

1. [brave.com/download](https://brave.com/download) → install.
2. Open Brave once.
3. **Log into each retailer you want to buy from** (Walmart, Target, Pokémon Center,
   Best Buy, etc.) and **save your shipping address + payment method inside each
   account**. This is the secret sauce: when the bot adds to cart and hits checkout,
   your retailer account already knows who you are — no autofill required.

---

## 6. First-time setup (one click)

1. Open the **`TechBot`** folder → open the **`local`** folder.
2. Double-click **`Start.bat`**.
3. A black window opens and shows:
   ```
   [1/4] Checking Python...
   [2/4] Installing Python deps...
   [3/4] Building frontend...
   [4/4] Starting dashboard at http://127.0.0.1:8787 ...
   ```
4. **The first run takes 3–8 minutes** (downloads Playwright's browser driver and
   builds the dashboard). Leave the black window open — closing it stops the bot.
5. Your browser auto-opens **http://127.0.0.1:8787**. If it doesn't, open any
   browser and paste that URL.

---

## 7. Every-day use — how to launch the app

After setup, daily launch takes ~5 seconds.

1. Double-click **`local/Start.bat`** — dashboard opens.
2. Double-click **`local/Start-Brave.bat`** — opens a special Brave window the bot
   can control. The first time, log into your retailer accounts in this window.
   Brave will remember them next time.
3. On the dashboard, click **CONNECT BRAVE** (top-right). It turns orange/solid
   when wired in.
4. Click **START ALL**, or start individual watches with the ▶ button.

**Stopping:** click **STOP ALL**, close the black `Start.bat` window, close the
Brave window.

---

## 8. Dashboard tour

Six tabs along the top, under the header.

**Header** (always visible):
- TechBot logo (left)
- Brave CDP URL field + **CONNECT BRAVE** button (orange = ready to connect, solid = live)
- **START ALL** (green) — runs every active watcher
- **STOP ALL** (red) — kill switch; stops every watcher and every drop
- `ENGINE · LIVE` indicator appears when something is running

**Tabs:**

| Tab       | Purpose                                                        |
|-----------|----------------------------------------------------------------|
| Monitor   | Live stats + status cards + streaming log terminal             |
| Watchlist | Add/edit/start/stop individual product watchers                |
| Drops     | Schedule timed drops (Walmart 9 PM style)                      |
| Profiles  | Shipping/payment presets for autofill                          |
| History   | Every cart/checkout/purchase/price-skip event the bot logged   |
| Settings  | Engine speed, notifications, price guard, safety toggles       |

---

## 9. Configuring a Watch (full reference)

In **Watchlist → + Add** (or click the pencil on an existing row).

| Field          | What it does                                                             | Tips                                                                 |
|----------------|---------------------------------------------------------------------------|----------------------------------------------------------------------|
| **Name**       | Label shown in the dashboard and notifications.                           | Use something short and unique, e.g. "151 ETB - PKMN".               |
| **URL**        | The product page URL copied straight from your browser.                   | Must be the product page, not a search page.                         |
| **Site**       | Which retailer the URL belongs to. Changes which selectors the bot uses.  | Must match the URL's domain, or the bot won't detect stock.          |
| **Mode**       | What the bot does when it finds stock. See [Purchase modes](#purchase-modes) below. | Start with `Add to cart` until you trust it.                    |
| **Priority**   | 1–10. Higher = runs first when the worker slots are full.                 | Keep reserved for rare drops. Default 5 is fine.                     |
| **Quantity**   | How many units to add to cart (for retailers that support qty select).    | Most retailers cap at 1 per account for hot items.                   |
| **Max Price**  | ✨ Price guard ceiling. If the live page price is higher, the bot refuses to purchase and logs a `PRICE_SKIP` event. Blank = no guard. | Stops bait-and-switch pricing during chaotic drops. |
| **Profile**    | Which Profile to use for autofill (only matters in `Checkout` / `Full Auto` modes). | Leave blank for `Monitor` or `Cart` modes.                 |
| **Active**     | If checked, included in **START ALL**. Uncheck to pause without deleting.  |                                                                      |

### Purchase modes

| Mode                       | What happens when stock is detected                                                                  |
|----------------------------|-------------------------------------------------------------------------------------------------------|
| **Monitor only**           | Logs it, Discord/sound/toast notifications fire, no clicks. Safest.                                  |
| **Add to cart**            | Clicks Add to Cart, navigates to the cart page, stops. You finish checkout manually.                 |
| **Checkout (stop before place)** | Adds to cart → clicks Checkout → autofills your Profile → **stops before** Place Order. You click the final button. |
| **Full auto**              | Same as Checkout, then clicks **Place Order** — but **only** if the global safety toggle in Settings is OFF. Default OFF for safety. |

### Row actions (right side of each Watchlist row)

- **▶ Play** (green) — start just this watcher
- **■ Stop** (yellow) — stop just this watcher
- **✏ Pencil** — edit
- **🗑 Trash** — delete (auto-stops it first)

---

## 10. Configuring a Drop (full reference)

The Drop Scheduler is for **timed drops** like Walmart's 9 PM Eastern releases,
where you need to be on the page the instant it goes live.

In **Drops → + Schedule**:

| Field                          | What it does                                                                 | Recommended                                                                 |
|--------------------------------|-------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| **Name**                       | Label for the drop.                                                           | "Walmart Sep ETB Drop"                                                      |
| **Site**                       | Which retailer all URLs belong to.                                            | Must match every URL's domain.                                              |
| **Run At (local)**             | Exact date + time when the bot should start hammering.                        | Use **your** local time — dashboard converts to UTC internally.             |
| **URLs (one per line)**        | Paste every product URL you want the bot to race for.                         | For Walmart drops, paste all candidate SKUs — bot races them simultaneously.|
| **Mode**                       | Same four modes as a Watch.                                                   | `Add to cart` for first try, upgrade to `Checkout` once you trust it.        |
| **Profile**                    | Autofill profile for Checkout/Full Auto modes.                                |                                                                             |
| **Auto-advance queue**         | ON = bot automatically clicks through Walmart's "You are in line" / waiting-room pages. | **Always ON** for Walmart/Target/Best Buy drops.                  |
| **Blast all URLs in parallel** | ON = every URL gets its own tab, all run at once. OFF = bot tries them one at a time. | **ON** for high-stakes drops. OFF if you want a polite single lane. |

### How a drop runs

1. You schedule it with Run At = `9:00 PM tonight`.
2. At **8:59:30 PM** the bot wakes up, ARMs itself, and logs `[DROP:name] ARMED`.
3. At Run At, one browser tab opens per URL (if Blast is ON). Each tab reloads every
   ~0.4 s, handles queue pages, and clicks Add to Cart the instant it's available.
4. When a tab hits stock, the bot runs your chosen mode (cart / checkout / auto)
   and logs the result to History.
5. The drop runs for up to **15 minutes** then stops automatically.

### Drop row actions

- **⚡ Arm** — start this drop immediately, ignoring the schedule.
- **Cancel** — stop an in-progress or scheduled drop.
- **🗑 Trash** — delete the drop entry.

---

## 11. Configuring a Profile (full reference)

Only needed for `Checkout` or `Full Auto` modes **when the retailer doesn't already
have your info saved**. Most people can skip profiles entirely if they've saved their
shipping + payment inside each retailer account.

In **Profiles → + Add**:

| Field                 | Notes                                                              |
|-----------------------|---------------------------------------------------------------------|
| Label                 | How this profile appears in the dropdown (e.g. "Home", "Work").     |
| First Name / Last Name| As they appear on your ID/card.                                     |
| Email / Phone         | Some retailers ask for these on guest checkout.                     |
| Address 1 / 2 / City / State / ZIP | Standard US shipping address.                            |
| Name on Card          | Cardholder name as printed on the card.                             |
| Card #                | Your credit/debit card number. Stored **unencrypted in a local file** on your PC (`techbot.db`). |
| MM / YY               | Expiration month (1–12) / year (2-digit).                           |
| CVV                   | 3–4 digit security code. Stored locally.                            |

**Security notes:**
- Card data stays in the SQLite file next to the app. Nothing is uploaded.
- When listed in the dashboard, card numbers show only the last 4 digits and CVV is masked.
- If you uninstall or lose the app, back up `techbot.db` first or you'll lose stored cards.
- Setting up saved payment methods **inside each retailer's account** is safer — the bot
  doesn't need your card that way.

---

## 12. Global Settings (full reference)

Everything in the **Settings** tab.

### Engine section

| Setting               | Range / default            | Effect                                                                                              |
|-----------------------|----------------------------|-----------------------------------------------------------------------------------------------------|
| Poll Interval (ms)    | 100–5000, default 700      | How often each watcher re-checks its page. Lower = faster but more server load. Below 300 risks rate-limiting. |
| Jitter (ms)           | 0–2000, default 200        | Random extra delay added to every poll so you don't look robotic.                                  |
| Concurrent Workers    | 1–20, default 5            | Max watchers that can run at the same time. Extra ones queue up.                                   |
| Brave CDP URL         | default `http://127.0.0.1:9222` | Where the bot connects to your Brave. Only change if you changed the port in `Start-Brave.bat`. |

### Notifications section

| Setting         | Effect                                                                                    |
|-----------------|--------------------------------------------------------------------------------------------|
| Discord Webhook | Paste a webhook URL from a Discord channel. Bot will send embed notifications on IN_STOCK, IN_CART, CHECKOUT_READY, ORDER PLACED, and PRICE GUARD SKIP. [How to create a webhook](https://support.discord.com/hc/en-us/articles/228383668). |
| Sound alerts    | Plays a ding when something important happens (in-app).                                    |
| Desktop toasts  | Uses your OS notification system for alerts.                                               |

### ✨ Price Guard section

This is the **smart price-drop guard**. When the bot sees stock, it scrapes the
current listed price **before any click**, compares it to your `Max Price`, and
refuses to buy if the live price is higher.

| Setting                         | Default | Effect                                                                                  |
|---------------------------------|---------|------------------------------------------------------------------------------------------|
| **Enforce per-item Max Price**  | ON      | Master toggle. OFF disables the price guard entirely.                                    |
| **Strict: skip if price can't be read** | OFF     | ON = if the bot can't find the price on the page, skip the purchase anyway. OFF = if price is unreadable, proceed as usual. Turn ON for maximum safety on sites where selectors change often. |
| **Skip Cooldown (sec)**         | 300     | After a price-guard skip, wait this many seconds before re-polling that item. Prevents notification spam. |

**Example:** You set Max Price = `$50` on a watch. The item drops at $79.99.
The bot detects stock, reads `$79.99 > $50`, logs a `PRICE_SKIP` event in History,
sends a yellow Discord alert, and waits 300 seconds before trying again.

### Safety section

| Setting                                    | Default | Effect                                                                                                  |
|--------------------------------------------|---------|----------------------------------------------------------------------------------------------------------|
| **Stop before Place Order (global kill)**  | ON      | Even in Full Auto mode, the bot stops **before** clicking the final Place Order button. Flip OFF only when you're certain you want real orders placed automatically. |

---

## 13. Troubleshooting

**"Python is not recognized as an internal or external command"**
→ You skipped "Add python.exe to PATH" during install. Uninstall, reinstall, tick the box.

**`yarn: command not found` or the Start.bat hangs on `yarn install`**
→ The Start.bat will now auto-enable Yarn via `corepack enable`, and fall back to `npm`
if that fails. If it still errors, open a fresh Command Prompt and run `corepack enable`
manually, or `npm install -g yarn`, then re-run `Start.bat`.

**`ERROR: Could not find a version that satisfies the requirement emergentintegrations`**
→ You grabbed an older version of `requirements.txt`. The fixed file only lists the
actual dependencies the app uses (fastapi, uvicorn, playwright, discord.py, etc.). If
you're still seeing this, re-download the project and make sure `backend/requirements.txt`
has ~11 lines, not 133.

**Dashboard shows `CDP connect failed: ECONNREFUSED`**
→ You didn't run `Start-Brave.bat`, or you closed the special Brave window. Run it again.

**Bot says `CAPTCHA DETECTED`**
→ Switch to the Brave window, solve the puzzle yourself. Bot resumes automatically.

**Nothing happens when I click START ALL**
→ Check: (1) at least one Watch has **Active** ticked, (2) Brave shows **Brave · Live**,
(3) the URL is a valid product page (not a category/search page).

**"Add to cart clicked" but nothing got added**
→ The retailer changed their page. Open `backend/sites.py`, find that site under
`_SELECTORS`, add the new button's CSS selector, save, restart `Start.bat`.

**Price guard skipping every time with "price unreadable"**
→ The retailer changed their price element. Open `backend/sites.py`, add a selector
to `_PRICE_SELECTORS` for that site. Or turn off **Strict** mode to proceed anyway.

**Dashboard won't open / port already in use**
→ Close the other program using port 8787, or edit `local/launch.py` and change
`TECHBOT_PORT` to something else like `8888`.

**I want to reset everything**
→ Close the app, delete `techbot.db`, relaunch. Fresh start.

**I want to back up my watches / profiles**
→ Copy the `techbot.db` file somewhere safe. Restore by dropping it back in.

---

## 14. Legal / disclaimer

- Use this only for products you're legally allowed to buy.
- Respect each retailer's Terms of Service. Running bots may violate them and could
  get your account banned.
- Auto-purchase places **real orders with real money**. Start with Cart or Checkout
  mode. Flip off the global safety toggle **only** once you fully trust the setup.
- The author is not liable for mis-purchases, account bans, payment errors, or any
  other consequences.

Happy hunting. 🎴
