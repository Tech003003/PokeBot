"""Behavioural tests for the positive-confirmation ATC verifier.

Spins up a deliberately tiny fake of the Playwright Page/Locator APIs used by
`sites.verify_atc_success` and `sites.get_cart_count`. We don't boot Chromium;
we only exercise the control-flow the engine actually relies on.

Covered cases:
  1. Success modal appears → verify returns True.
  2. Cart count increments from N → N+1 → verify returns True.
  3. Cart count stays flat and no modal → verify returns False (no false positive).
  4. Retailer error banner appears (`Item not added to cart`) → verify returns
     False quickly (short-circuits before timeout).
  5. Badge was None pre-click and becomes >=1 post-click → verify returns True.
"""
import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sites  # noqa: E402


# ---------- Minimal fake Locator / Page ------------------------------------

class FakeLocator:
    def __init__(self, page, selector, is_text=False, text_pattern=None):
        self.page = page
        self.selector = selector
        self.is_text = is_text
        self.text_pattern = text_pattern

    @property
    def first(self):
        return self

    async def count(self):
        return 1 if self._resolve() is not None else 0

    async def is_visible(self, timeout=None):
        node = self._resolve()
        return bool(node and node.get("visible", True))

    async def text_content(self, timeout=None):
        node = self._resolve()
        return (node or {}).get("text", "")

    async def click(self, timeout=None):
        return None

    def _resolve(self):
        if self.is_text:
            # text match: iterate page.text_nodes
            for n in self.page.text_nodes:
                if self.text_pattern.search(n.get("text", "")):
                    return n
            return None
        return self.page.elements.get(self.selector)


class FakePage:
    """Matches the subset of Playwright API used by sites.verify_atc_success
    and sites.get_cart_count:
        - page.locator(sel).first → FakeLocator
        - page.get_by_text(pattern).first → FakeLocator
    """
    def __init__(self, elements=None, text_nodes=None):
        # selector -> {'text': str, 'visible': bool}
        self.elements = dict(elements or {})
        self.text_nodes = list(text_nodes or [])

    def locator(self, selector):
        return FakeLocator(self, selector)

    def get_by_text(self, pattern):
        return FakeLocator(self, None, is_text=True, text_pattern=pattern)


def _logger():
    logs = []
    def _l(level, msg):
        logs.append((level, msg))
    _l.logs = logs
    return _l


# ---------- Tests -----------------------------------------------------------

def test_success_modal_confirms():
    """Target's 'Added to cart' dialog appearing = success, no cart count needed."""
    page = FakePage(elements={
        "div[aria-label='Added to cart']": {"text": "Added to cart", "visible": True},
    })
    lg = _logger()
    ok = asyncio.run(sites.verify_atc_success(page, "target", lg, pre_cart_count=0, wait_s=1.0))
    assert ok is True
    assert any("confirmed" in m.lower() for _, m in lg.logs)


def test_cart_count_increment_confirms():
    """Walmart: no modal, but the cart badge went 0 → 1 → that IS success."""
    page = FakePage(elements={
        "a[link-identifier='cartNavIcon'] [data-automation-id='cart-item-count']":
            {"text": "1", "visible": True},
    })
    lg = _logger()
    ok = asyncio.run(sites.verify_atc_success(page, "walmart", lg, pre_cart_count=0, wait_s=1.0))
    assert ok is True


def test_unchanged_cart_and_no_modal_is_failure():
    """The exact false-positive bug we're fixing: no modal, badge didn't move.
    Must return False so the engine retries instead of reporting 'Purchased'."""
    page = FakePage(elements={
        "a[link-identifier='cartNavIcon'] [data-automation-id='cart-item-count']":
            {"text": "0", "visible": True},
    })
    lg = _logger()
    ok = asyncio.run(sites.verify_atc_success(page, "walmart", lg, pre_cart_count=0, wait_s=0.8))
    assert ok is False


def test_error_banner_short_circuits_to_failure():
    """Target's 'Item not added to cart' banner must fail immediately, not time out."""
    page = FakePage(text_nodes=[
        {"text": "Item not added to cart", "visible": True},
    ])
    lg = _logger()
    ok = asyncio.run(sites.verify_atc_success(page, "target", lg, pre_cart_count=1, wait_s=2.0))
    assert ok is False
    assert any("rejected" in m.lower() for _, m in lg.logs)


def test_badge_appears_from_hidden_to_one():
    """Empty-cart case: badge wasn't rendered pre-click (pre_count=None), now shows '1'."""
    page = FakePage(elements={
        "#nav-cart-count": {"text": "1", "visible": True},
    })
    lg = _logger()
    ok = asyncio.run(sites.verify_atc_success(page, "amazon", lg, pre_cart_count=None, wait_s=1.0))
    assert ok is True


def test_get_cart_count_returns_none_when_badge_hidden():
    """Empty cart on most retailers hides the badge entirely."""
    page = FakePage()
    count = asyncio.run(sites.get_cart_count(page, "walmart"))
    assert count is None


def test_get_cart_count_parses_numeric_badge():
    page = FakePage(elements={
        "#nav-cart-count": {"text": "3", "visible": True},
    })
    count = asyncio.run(sites.get_cart_count(page, "amazon"))
    assert count == 3
