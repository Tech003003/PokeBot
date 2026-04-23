# Logo slot

Drop a file named **`logo.png`** in this folder (`frontend/public/`).

Recommended specs:
- Square, 256×256 px or larger (it renders at 32×32 but larger = crisper on hi-DPI displays)
- PNG with a transparent background
- Keep the art bright — the header has a near-black background

The header will pick it up automatically on the next `yarn build` (or immediately in dev).

If no `logo.png` is present, the UI falls back to a green rocket icon so the app still looks fine.
