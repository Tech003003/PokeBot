"""Local launcher for NexusBot.

Works in two modes:
  • Dev mode: run directly with `python local/launch.py`. Reads code from /app.
  • Frozen mode: run as a PyInstaller-built NexusBot.exe. Reads bundled resources
    from sys._MEIPASS and stores the SQLite DB next to the .exe.

Starts FastAPI + serves the pre-built React frontend + auto-opens your browser.
"""
import os
import sys
import time
import threading
import webbrowser
from pathlib import Path

# --- Path resolution (must happen BEFORE any Playwright / backend import) ----
FROZEN = getattr(sys, "frozen", False)
if FROZEN:
    BUNDLE = Path(sys._MEIPASS)                 # temp dir with bundled resources
    EXE_DIR = Path(sys.executable).resolve().parent
    BACKEND_DIR = BUNDLE / "backend"
    FRONTEND_BUILD = BUNDLE / "frontend" / "build"
    # Playwright needs to find its bundled chromium
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(BUNDLE / "ms-playwright"))
    # Persistent DB lives beside the .exe so it survives app updates
    os.environ.setdefault("NEXUSBOT_DB", str(EXE_DIR / "nexusbot.db"))
else:
    ROOT = Path(__file__).resolve().parent.parent
    BACKEND_DIR = ROOT / "backend"
    FRONTEND_BUILD = ROOT / "frontend" / "build"
    os.environ.setdefault("NEXUSBOT_DB", str(ROOT / "nexusbot.db"))

os.environ.setdefault("CORS_ORIGINS", "*")
sys.path.insert(0, str(BACKEND_DIR))

# --- Safe to import backend now ---------------------------------------------
import uvicorn  # noqa: E402
from server import app  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from starlette.responses import FileResponse  # noqa: E402


def _attach_frontend():
    if not FRONTEND_BUILD.exists():
        print(f"[warn] frontend build not found at {FRONTEND_BUILD}. "
              "Dev mode needs `cd frontend && yarn build` first.")
        return
    app.mount("/static", StaticFiles(directory=str(FRONTEND_BUILD / "static")), name="static")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        f = FRONTEND_BUILD / full_path
        if f.is_file():
            return FileResponse(str(f))
        return FileResponse(str(FRONTEND_BUILD / "index.html"))


_attach_frontend()


def _open_browser(url: str, delay: float = 1.2):
    def _go():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Thread(target=_go, daemon=True).start()


if __name__ == "__main__":
    port = int(os.environ.get("NEXUSBOT_PORT", 8787))
    url = f"http://127.0.0.1:{port}"
    print(f"\n  NexusBot Command Center → {url}\n  (This window must stay open while the app runs)\n")
    _open_browser(url)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
