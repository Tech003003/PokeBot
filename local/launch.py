"""Local launcher for NexusBot. Starts FastAPI, serves the built React frontend,
and auto-opens your default browser to the dashboard."""
import os
import sys
import time
import threading
import webbrowser
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND_BUILD = ROOT / "frontend" / "build"

# Make backend importable regardless of cwd
sys.path.insert(0, str(BACKEND))

# Tell backend to use a local SQLite db next to this launcher
os.environ.setdefault("NEXUSBOT_DB", str(ROOT / "nexusbot.db"))
os.environ.setdefault("CORS_ORIGINS", "*")

from server import app  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from starlette.responses import FileResponse  # noqa: E402


def _attach_frontend():
    if not FRONTEND_BUILD.exists():
        print(f"[warn] frontend build not found at {FRONTEND_BUILD}. "
              "Run `cd frontend && yarn build` first.")
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
    print(f"\n  NexusBot Command Center → {url}\n")
    _open_browser(url)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
