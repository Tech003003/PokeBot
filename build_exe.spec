# PyInstaller spec for NexusBot Windows .exe build.
# Used by .github/workflows/build.yml on windows-latest runners.
# Produces dist/NexusBot/NexusBot.exe + supporting files.

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [
    ("frontend/build", "frontend/build"),
    # The CI step installs Playwright browsers to ./ms-playwright before this runs.
    ("ms-playwright", "ms-playwright"),
]
binaries = []
hiddenimports = [
    # uvicorn dynamic loaders
    "uvicorn.logging",
    "uvicorn.loops", "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan", "uvicorn.lifespan.on",
    # local backend modules
    "server", "engine", "sites", "db",
    # deps that PyInstaller sometimes misses
    "aiosqlite", "httpx", "websockets", "playwright_stealth",
]

# Pull in all of playwright's data files + submodules
for pkg in ("playwright", "playwright_stealth"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

hiddenimports += collect_submodules("fastapi")
hiddenimports += collect_submodules("starlette")

block_cipher = None

a = Analysis(
    ["local/launch.py"],
    pathex=["backend"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "pandas", "numpy"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NexusBot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # keep a console window so users see status + can close to stop
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="NexusBot",
)
