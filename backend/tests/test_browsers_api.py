"""Integration tests for the multi-browser / proxy-browser feature.

Covers:
  - /api/browsers CRUD (list, create, patch, delete)
  - is_default flag flip (only one default at a time)
  - /api/browsers/{id}/connect|disconnect|launch behaviour in cloud
    (must NOT 500, must return structured JSON)
  - /api/watch and /api/drops accept + persist browser_id
  - /api/status has `browsers` key
  - /api/brave/connect (legacy) syncs cdp_url to the default row
  - A quick sanity ping of existing CRUD (watch/drops/profiles/settings)

Uses the public REACT_APP_BACKEND_URL so we exercise the real ingress path.
Creates and cleans up its own rows; does NOT touch the seeded Default browser.
"""

from __future__ import annotations

import os
import uuid

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
API = f"{BASE_URL}/api"

TIMEOUT = 30


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ------------------------- /api/browsers ------------------------- #

class TestBrowsersCRUD:
    """Browser row CRUD + default-flag semantics."""

    def test_list_has_default_seed(self, client):
        r = client.get(f"{API}/browsers", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        rows = r.json()
        assert isinstance(rows, list)
        assert len(rows) >= 1, "expected auto-seeded Default browser row"
        defaults = [x for x in rows if x.get("is_default")]
        assert len(defaults) >= 1, f"no default row found: {rows}"
        # every row should have an id
        for x in rows:
            assert "id" in x and isinstance(x["id"], str)

    def test_create_update_flip_default_delete(self, client):
        unique = f"TEST_Browser_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": unique,
            "cdp_url": "http://127.0.0.1:9333",
            "user_data_dir": "C:/tmp/TEST_profile",
            "proxy": "",
            "max_workers": 2,
            "is_default": False,
        }
        r = client.post(f"{API}/browsers", json=payload, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        created = r.json()
        assert created["name"] == unique
        assert created["cdp_url"] == "http://127.0.0.1:9333"
        assert created["max_workers"] == 2
        bid = created["id"]
        assert isinstance(bid, str) and bid

        # PATCH name + cdp_url
        new_name = unique + "_upd"
        r = client.patch(f"{API}/browsers/{bid}",
                         json={"name": new_name,
                               "cdp_url": "http://127.0.0.1:9444"},
                         timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        upd = r.json()
        assert upd["name"] == new_name
        assert upd["cdp_url"] == "http://127.0.0.1:9444"

        # GET list and verify persistence
        rows = client.get(f"{API}/browsers", timeout=TIMEOUT).json()
        match = [x for x in rows if x["id"] == bid]
        assert match and match[0]["name"] == new_name

        # Flip default flag to this row
        r = client.patch(f"{API}/browsers/{bid}",
                         json={"is_default": True}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert bool(r.json()["is_default"]) is True

        rows = client.get(f"{API}/browsers", timeout=TIMEOUT).json()
        defaults = [x for x in rows if x.get("is_default")]
        assert len(defaults) == 1, f"multiple defaults found: {defaults}"
        assert defaults[0]["id"] == bid

        # Flip back to the originally-seeded default so we don't leave a
        # test row as the global default.
        other = [x for x in rows if x["id"] != bid][0]
        r = client.patch(f"{API}/browsers/{other['id']}",
                         json={"is_default": True}, timeout=TIMEOUT)
        assert r.status_code == 200
        rows = client.get(f"{API}/browsers", timeout=TIMEOUT).json()
        defaults = [x for x in rows if x.get("is_default")]
        assert len(defaults) == 1 and defaults[0]["id"] == other["id"]

        # DELETE the TEST row
        r = client.delete(f"{API}/browsers/{bid}", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        # Confirm gone
        rows = client.get(f"{API}/browsers", timeout=TIMEOUT).json()
        assert all(x["id"] != bid for x in rows)

    def test_patch_missing_returns_404(self, client):
        r = client.patch(f"{API}/browsers/does-not-exist",
                         json={"name": "x"}, timeout=TIMEOUT)
        assert r.status_code == 404

    def test_delete_missing_returns_404(self, client):
        r = client.delete(f"{API}/browsers/does-not-exist", timeout=TIMEOUT)
        assert r.status_code == 404


# -------------- connect / disconnect / launch in cloud -------------- #

class TestBrowserConnectLifecycle:
    """These endpoints must NOT 500 in cloud (no Brave available)."""

    def _make_row(self, client) -> str:
        r = client.post(f"{API}/browsers", json={
            "name": f"TEST_conn_{uuid.uuid4().hex[:6]}",
            "cdp_url": "http://127.0.0.1:9555",
            "user_data_dir": "",
            "proxy": "",
            "max_workers": 0,
            "is_default": False,
        }, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        return r.json()["id"]

    def _cleanup(self, client, bid):
        try:
            client.delete(f"{API}/browsers/{bid}", timeout=TIMEOUT)
        except Exception:
            pass

    def test_connect_returns_200_with_connected_false(self, client):
        bid = self._make_row(client)
        try:
            r = client.post(f"{API}/browsers/{bid}/connect", timeout=TIMEOUT)
            assert r.status_code == 200, r.text
            data = r.json()
            # No Brave → must report connected: false
            assert data.get("connected") is False, data
            # And must carry a human message (error/message/detail)
            assert any(k in data for k in ("error", "message", "detail", "reason")), data
        finally:
            self._cleanup(client, bid)

    def test_disconnect_returns_200_when_nothing_connected(self, client):
        bid = self._make_row(client)
        try:
            r = client.post(f"{API}/browsers/{bid}/disconnect", timeout=TIMEOUT)
            assert r.status_code == 200, r.text
        finally:
            self._cleanup(client, bid)

    def test_launch_returns_404_not_500(self, client):
        bid = self._make_row(client)
        try:
            r = client.post(f"{API}/browsers/{bid}/launch", timeout=TIMEOUT)
            # Expected: 404 "brave.exe not found" — must NOT 500
            assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text}"
            body = r.json()
            assert "detail" in body
            assert "brave" in str(body["detail"]).lower()
        finally:
            self._cleanup(client, bid)

    def test_launch_unknown_id_returns_404(self, client):
        r = client.post(f"{API}/browsers/nope/launch", timeout=TIMEOUT)
        assert r.status_code == 404


# -------------- browser_id on watch and drops -------------- #

class TestBrowserIdPropagation:

    def test_watch_persists_browser_id(self, client):
        # Use the default browser id
        rows = client.get(f"{API}/browsers", timeout=TIMEOUT).json()
        default = [x for x in rows if x.get("is_default")][0]
        bid = default["id"]

        payload = {
            "name": f"TEST_watch_{uuid.uuid4().hex[:6]}",
            "site": "bestbuy",
            "url": "https://www.bestbuy.com/site/abc/1234.p",
            "browser_id": bid,
        }
        r = client.post(f"{API}/watch", json=payload, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        w = r.json()
        wid = w["id"]
        try:
            assert w.get("browser_id") == bid

            all_watch = client.get(f"{API}/watch", timeout=TIMEOUT).json()
            found = [x for x in all_watch if x["id"] == wid]
            assert found and found[0].get("browser_id") == bid
        finally:
            client.delete(f"{API}/watch/{wid}", timeout=TIMEOUT)

    def test_drops_persists_browser_id(self, client):
        rows = client.get(f"{API}/browsers", timeout=TIMEOUT).json()
        default = [x for x in rows if x.get("is_default")][0]
        bid = default["id"]

        payload = {
            "name": f"TEST_drop_{uuid.uuid4().hex[:6]}",
            "site": "bestbuy",
            "run_at": "2099-01-01T00:00:00Z",
            "urls": ["https://www.bestbuy.com/site/x/1.p"],
            "browser_id": bid,
        }
        r = client.post(f"{API}/drops", json=payload, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        did = d["id"]
        try:
            assert d.get("browser_id") == bid
            all_drops = client.get(f"{API}/drops", timeout=TIMEOUT).json()
            found = [x for x in all_drops if x["id"] == did]
            assert found and found[0].get("browser_id") == bid
        finally:
            client.delete(f"{API}/drops/{did}", timeout=TIMEOUT)


# ------------------ /api/status exposes browsers ------------------ #

class TestStatusBrowsers:

    def test_status_has_browsers_key(self, client):
        r = client.get(f"{API}/status", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        s = r.json()
        assert "browsers" in s, f"no browsers key in status: {list(s)}"
        assert isinstance(s["browsers"], list)


# ------------- legacy /api/brave/connect syncs default ------------- #

class TestLegacyBraveConnectSync:

    def test_legacy_connect_writes_cdp_to_default_row(self, client):
        sentinel = f"http://127.0.0.1:{9000 + (uuid.uuid4().int % 1000)}"
        r = client.post(f"{API}/brave/connect", json={"cdp_url": sentinel},
                        timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("connected") is False  # no Brave in cloud

        # Default browser row should now carry this cdp_url
        rows = client.get(f"{API}/browsers", timeout=TIMEOUT).json()
        default = [x for x in rows if x.get("is_default")][0]
        assert default["cdp_url"] == sentinel, default

        # Settings should also carry it
        settings = client.get(f"{API}/settings", timeout=TIMEOUT).json()
        assert settings.get("cdp_url") == sentinel


# ---------------- existing CRUD regression sanity ---------------- #

class TestLegacyRegression:

    def test_meta_sites(self, client):
        r = client.get(f"{API}/meta/sites", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "sites" in data and "labels" in data

    def test_profiles_crud(self, client):
        r = client.post(f"{API}/profiles", json={
            "label": f"TEST_profile_{uuid.uuid4().hex[:6]}",
            "first_name": "Te", "last_name": "St",
            "email": "t@t.com",
        }, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        try:
            rows = client.get(f"{API}/profiles", timeout=TIMEOUT).json()
            assert any(x["id"] == pid for x in rows)
        finally:
            r = client.delete(f"{API}/profiles/{pid}", timeout=TIMEOUT)
            assert r.status_code == 200

    def test_settings_patch_roundtrip(self, client):
        orig = client.get(f"{API}/settings", timeout=TIMEOUT).json()
        orig_val = orig.get("poll_interval_ms", 1500)
        new_val = int(orig_val) + 1
        r = client.patch(f"{API}/settings",
                         json={"poll_interval_ms": new_val}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert r.json().get("poll_interval_ms") == new_val
        # restore
        client.patch(f"{API}/settings",
                     json={"poll_interval_ms": int(orig_val)}, timeout=TIMEOUT)

    def test_watch_start_stop_no_crash(self, client):
        # Create a watch row and hit start/stop; it should not 500 even if
        # Brave is unavailable — engine should fail soft.
        payload = {
            "name": f"TEST_ws_{uuid.uuid4().hex[:6]}",
            "site": "bestbuy",
            "url": "https://www.bestbuy.com/site/x/9.p",
        }
        r = client.post(f"{API}/watch", json=payload, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        wid = r.json()["id"]
        try:
            r = client.post(f"{API}/watch/{wid}/start", timeout=TIMEOUT)
            assert r.status_code == 200, r.text
            r = client.post(f"{API}/watch/{wid}/stop", timeout=TIMEOUT)
            assert r.status_code == 200, r.text
        finally:
            client.delete(f"{API}/watch/{wid}", timeout=TIMEOUT)
