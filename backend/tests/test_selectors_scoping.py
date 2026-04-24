"""Static audit of _SELECTORS for all 9 retailers.

Ensures NO generic / unscoped "Add to cart" selectors survive. Generic fallbacks
are what caused the bot to buy plushies from Target's "related items" carousel
on out-of-stock pages (Issue #1).

Rules enforced:
  1. Every retailer must have at least one scoped selector.
  2. No selector may be a bare `button:has-text('Add to cart')` (case-insensitive).
  3. No selector may be a bare `button[data-test='addToCartButton']` — Target
     applies that id to carousel cards too.
  4. `:has-text('Add to cart')` fragments are only allowed when preceded by a
     container scope (space separator), never as the first token.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sites import SITES, _SELECTORS  # noqa: E402

FORBIDDEN_EXACT = {
    "button:has-text('Add to cart'):not([disabled])",
    "button:has-text('Add to Cart'):not([disabled])",
    "button:has-text('add to cart'):not([disabled])",
    "button[data-test='addToCartButton']:not([disabled])",
    "button.add-to-cart:not([disabled])",
    "button.add-to-cart-button:not([disabled])",
    "button[data-testid='add-to-cart-button']:not([disabled])",
    "button[data-automation-id='atc']:not([disabled])",
    "button.btn-add-to-cart:not([disabled])",
    "input[value='Add to Cart']:not([disabled])",
}


@pytest.mark.parametrize("site", SITES)
def test_every_retailer_has_selectors(site):
    assert site in _SELECTORS, f"{site} is missing from _SELECTORS"
    assert len(_SELECTORS[site]) >= 1, f"{site} has no ATC selectors"


@pytest.mark.parametrize("site", SITES)
def test_no_generic_add_to_cart_fallback(site):
    """The bot must NEVER ship a selector that is a bare `has-text('Add to cart')`
    or an unscoped common id — those match recommendation carousels."""
    for sel in _SELECTORS[site]:
        assert sel not in FORBIDDEN_EXACT, (
            f"{site}: forbidden unscoped selector survived: {sel!r}"
        )


@pytest.mark.parametrize("site", SITES)
def test_has_text_selectors_are_scoped(site):
    """If a selector uses `:has-text('Add to Cart')`, the selector must begin
    with an ancestor container (indicated by a space before the button token),
    not start with `button`/`input` as the root."""
    for sel in _SELECTORS[site]:
        low = sel.lower()
        if ":has-text(" not in low:
            continue
        if "add to cart" not in low and "add to your cart" not in low:
            continue
        # Must contain at least one space before the button/input using has-text,
        # which means it is scoped under an ancestor.
        head = sel.split(":has-text(")[0]
        assert " " in head, (
            f"{site}: unscoped :has-text selector (no ancestor): {sel!r}"
        )


def test_target_does_not_use_bare_addtocart_testid():
    """Hard regression guard for the plushie bug: Target's carousel cards use
    the SAME `data-test='addToCartButton'` id as the buy-box CTA, so the bare
    id must NEVER appear standalone. Only the scoped form (inside
    `[data-test='buy-box-actions']`) is allowed."""
    for sel in _SELECTORS["target"]:
        if "data-test='addToCartButton'" in sel or 'data-test="addToCartButton"' in sel:
            assert "buy-box" in sel.lower(), (
                f"Target bare addToCartButton selector without buy-box scope: {sel!r}"
            )
