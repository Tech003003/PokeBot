"""Regression: the monitor worker must NOT close the user's Brave tab after a
successful purchase / cart-add / pre-order. The user relies on that tab to
finish checkout manually or verify the result.

Previously `_monitor_item`'s `finally` block called `page.close()` unconditionally
on worker exit, which yanked the tab away after reporting success.
"""
import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class FakePage:
    def __init__(self):
        self.closed = False

    async def goto(self, *a, **kw):
        pass

    async def reload(self, *a, **kw):
        pass

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_page_stays_open_on_successful_cart_add(monkeypatch):
    """Simulate the cart-mode success path and assert page.close() was NEVER called."""
    import engine as engine_mod
    import db
    import sites as sites_mod

    fake_page = FakePage()

    async def _noop(*_a, **_kw):
        return None

    async def _empty_settings():
        return {
            "poll_interval_ms": 50, "jitter_ms": 0, "reload_every_n_polls": 20,
            "atc_max_retries": 1, "stop_before_place_order": True,
            "enforce_max_price": False, "strict_price_guard": False,
            "price_guard_cooldown_s": 1,
        }

    async def _get_watch(_wid):
        return {
            "id": "w1", "name": "Test Item", "site": "target",
            "url": "https://example.com/x", "purchase_mode": "cart",
            "button_types": ["cart"], "profile_id": None, "max_price": None,
        }

    async def _get_profile(_):
        return None

    # A locator-like object that "detects stock" once then never again.
    class FakeBtn:
        async def is_visible(self, timeout=None): return True
        async def scroll_into_view_if_needed(self, timeout=None): pass
        async def click(self, timeout=None): pass

    calls = {"detect": 0, "verify": 0}
    async def _detect_in_stock(_page, _site, _allowed):
        calls["detect"] += 1
        if calls["detect"] == 1:
            return FakeBtn(), "cart"
        return None, None

    async def _add_to_cart(*_a, **_kw): return True
    async def _verify_ok(*_a, **_kw): return True
    async def _get_cart_count(*_a, **_kw): return 0
    async def _goto_cart(*_a, **_kw): pass
    async def _get_price(*_a, **_kw): return None
    async def _is_captcha(*_a, **_kw): return False
    async def _is_queue(*_a, **_kw): return False

    monkeypatch.setattr(db, "get_watch", _get_watch)
    monkeypatch.setattr(db, "get_profile", _get_profile)
    monkeypatch.setattr(db, "get_all_settings", _empty_settings)
    monkeypatch.setattr(db, "set_watch_status", _noop)
    monkeypatch.setattr(db, "log_history", _noop)

    monkeypatch.setattr(sites_mod, "is_captcha", _is_captcha)
    monkeypatch.setattr(sites_mod, "is_queue", _is_queue)
    monkeypatch.setattr(sites_mod, "detect_in_stock", _detect_in_stock)
    monkeypatch.setattr(sites_mod, "get_price", _get_price)
    monkeypatch.setattr(sites_mod, "add_to_cart", _add_to_cart)
    monkeypatch.setattr(sites_mod, "verify_atc_success", _verify_ok)
    monkeypatch.setattr(sites_mod, "get_cart_count", _get_cart_count)
    monkeypatch.setattr(sites_mod, "goto_cart", _goto_cart)

    eng = engine_mod.MonitorEngine()
    # Inject the fake page so _monitor_item doesn't need a real browser.
    async def _new_page():
        return fake_page
    eng._new_page = _new_page  # type: ignore[method-assign]

    await eng._monitor_item("w1")

    assert fake_page.closed is False, (
        "page.close() was called after a successful cart-add — the user's tab "
        "would vanish right when they need it."
    )
