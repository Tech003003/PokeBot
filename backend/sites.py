"""Per-site selector + flow logic for TechBot. 9 retailers supported.

Each site module exposes:
    SELECTORS: list of CSS/Playwright selectors to detect "add to cart" state
    CART_URL: the retailer's cart page URL
    QUEUE_SIGNATURES: body-text signatures that indicate the user is in a waiting-room queue
    detect_in_stock(page) -> bool
    add_to_cart(page) -> bool
    goto_cart(page)
    CHECKOUT_URL (optional)
    is_queue(page) -> bool
"""
from __future__ import annotations
import asyncio
import random
from typing import Optional

SITES = [
    "walmart", "pokemoncenter", "amazon", "target", "bestbuy",
    "gamestop", "costco", "samsclub", "tcgplayer",
]

SITE_LABELS = {
    "walmart": "WMRT", "pokemoncenter": "PKMN", "amazon": "AMZN",
    "target": "TGT", "bestbuy": "BBY", "gamestop": "GME",
    "costco": "COST", "samsclub": "SAMS", "tcgplayer": "TCG",
}

BUTTON_TYPES = ["cart", "preorder", "waitlist"]
BUTTON_LABELS = {
    "cart": "Add to Cart",
    "preorder": "Pre-Order",
    "waitlist": "Waitlist / Notify Me",
}

_CART_URLS = {
    "walmart": "https://www.walmart.com/cart",
    "pokemoncenter": "https://www.pokemoncenter.com/cart",
    "amazon": "https://www.amazon.com/gp/cart/view.html",
    "target": "https://www.target.com/co-cart",
    "bestbuy": "https://www.bestbuy.com/cart",
    "gamestop": "https://www.gamestop.com/cart/",
    "costco": "https://www.costco.com/CheckoutCartView",
    "samsclub": "https://www.samsclub.com/cart",
    "tcgplayer": "https://shop.tcgplayer.com/cart",
}

# CRITICAL: Every selector below MUST be scoped to the primary product buy-box
# container. Generic selectors (like a bare `button[data-test='addToCartButton']`
# or `button:has-text('Add to cart')`) will match buttons inside "related items"
# / "you might also like" carousels on out-of-stock pages and cause the bot to
# purchase the wrong product (see Issue #1 / plushie bug on Target).
# If a retailer ships a redesign, prefer adding a NEW scoped selector over
# widening an existing one.
_SELECTORS = {
    "walmart": [
        # Walmart primary buy-box container is `div[data-testid='add-to-cart-section']`
        # or the atf-content container. The `atc` automation-id on the primary CTA
        # is unique to the main product on the PDP; carousel cards use a different id.
        "div[data-testid='add-to-cart-section'] button[data-automation-id='atc']:not([disabled])",
        "div[data-testid='atf-content'] button[data-automation-id='atc']:not([disabled])",
        "[data-tl-id='ProductPrimaryCTA-cta_add_to_cart_button']:not([disabled])",
    ],
    "pokemoncenter": [
        # Main PDP buy-box only. Recommendation tiles use their own `product-card-*`
        # testids and will NOT match this scope.
        "[data-testid='pdp-buy-box'] button[data-testid='add-to-cart-button']:not([disabled])",
        "[data-testid='product-form'] button[data-testid='add-to-cart-button']:not([disabled])",
        "form[data-testid='product-form'] button[type='submit']:has-text('Add to Cart'):not([disabled])",
    ],
    "amazon": [
        # Amazon uses strict unique IDs for the main buy-box ATC button.
        "#add-to-cart-button:not([disabled])",
        "#add-to-cart-button-ubb:not([disabled])",
        "input#add-to-cart-button:not([disabled])",
        "input[name='submit.add-to-cart']:not([disabled])",
    ],
    "target": [
        # Target's PDP primary CTA uses unique data-test identifiers that are
        # NEVER used in "related items" or "also bought" carousels. We strictly
        # whitelist those. Do NOT add `button[data-test='addToCartButton']` — that
        # id ALSO appears on carousel product cards and will buy a plushie.
        "button[data-test='shipItButton']:not([disabled])",
        "button[data-test='orderPickupButton']:not([disabled])",
        "button[data-test='@web/site-top-of-funnel/ProductDetailAddToCartButton']:not([disabled])",
        "[data-test='buy-box-actions'] button[data-test='shipItButton']:not([disabled])",
        "[data-test='buy-box-actions'] button[data-test='orderPickupButton']:not([disabled])",
        "[data-test='buy-box-actions'] button[data-test='addToCartButton']:not([disabled])",
    ],
    "bestbuy": [
        # Scope to the main SKU/fulfillment area. `.add-to-cart-button` and the
        # data-button-state are also used inside recommendation strips, so we
        # require an ancestor .sku-page / .fulfillment-add-to-cart-button container.
        ".sku-page .fulfillment-add-to-cart-button button:not([disabled])",
        ".sku-page button.add-to-cart-button:not([disabled])",
        ".sku-page button[data-button-state='ADD_TO_CART']:not([disabled])",
        ".fulfillment-add-to-cart-button button[data-button-state='ADD_TO_CART']:not([disabled])",
    ],
    "gamestop": [
        # GameStop's PDP wraps the primary CTA in `.product-detail` or the
        # `.cart-and-ipay` block. Bare `button.add-to-cart` would also match the
        # buttons inside the "People also bought" strip.
        ".product-detail .cart-and-ipay button.add-to-cart:not([disabled])",
        ".product-detail .add-to-cart-global:not([disabled])",
        ".product-detail button.add-to-cart-global:not([disabled])",
        ".pdp-main button.add-to-cart:not([disabled])",
    ],
    "costco": [
        # Costco's PDP uses `#add-to-cart-btn` (unique ID) or a button inside
        # `.product-info-wrapper`. Generic `input[value='Add to Cart']` fallback
        # was removed — too prone to matching recommendation widgets.
        "#add-to-cart-btn:not([disabled])",
        ".product-info-wrapper #add-to-cart-btn:not([disabled])",
        ".product-info-wrapper button[automation-id='addToCartButton']:not([disabled])",
        ".product-info-wrapper input[value='Add to Cart']:not([disabled])",
    ],
    "samsclub": [
        # Sam's Club PDP is wrapped in `[data-testid='pdp-buy-box']` /
        # `.sc-add-to-cart`. The same testid appears on carousel cards; scoping
        # to the buy-box container avoids that collision.
        "[data-testid='pdp-buy-box'] button[data-testid='add-to-cart-button']:not([disabled])",
        ".pdp-main [data-testid='add-to-cart-button']:not([disabled])",
        ".sc-add-to-cart button:not([disabled])",
    ],
    "tcgplayer": [
        # TCGPlayer's PDP is `.product-details`; the shop listing pages have
        # many per-row add-to-cart buttons, so we scope strictly.
        ".product-details .add-to-cart button:not([disabled])",
        ".product-details button.btn-add-to-cart:not([disabled])",
        ".product-details__price-and-actions button:has-text('Add to Cart'):not([disabled])",
    ],
}

# Pre-order buttons. Retailers often use a distinct CTA for upcoming releases.
_PREORDER_SELECTORS = {
    "walmart": [
        "button[data-automation-id='preorder-button']",
        "button:has-text('Pre-order'):not([disabled])",
        "button:has-text('Preorder'):not([disabled])",
    ],
    "pokemoncenter": [
        "button:has-text('Pre-order'):not([disabled])",
        "button:has-text('Preorder'):not([disabled])",
    ],
    "amazon": [
        "#one-click-button:has-text('Pre-order')",
        "input[name='submit.preorder']:not([disabled])",
        "button:has-text('Pre-order'):not([disabled])",
    ],
    "target": [
        "button[data-test='preorderButton']:not([disabled])",
        "button:has-text('Preorder'):not([disabled])",
    ],
    "bestbuy": [
        "button[data-button-state='PRE_ORDER']:not([disabled])",
        "button:has-text('Pre-Order'):not([disabled])",
    ],
    "gamestop": [
        "button.pre-order:not([disabled])",
        "button:has-text('Pre-Order'):not([disabled])",
    ],
    "costco": [
        "button:has-text('Pre-Order'):not([disabled])",
    ],
    "samsclub": [
        "button:has-text('Pre-Order'):not([disabled])",
    ],
    "tcgplayer": [
        "button:has-text('Pre-Order'):not([disabled])",
    ],
}

# Waitlist / "Notify me when available" buttons. Clicking these doesn't purchase —
# it signs you up for a notification. The engine treats these separately.
_WAITLIST_SELECTORS = {
    "walmart": [
        "button:has-text('Notify me'):not([disabled])",
        "button:has-text('Notify when available'):not([disabled])",
    ],
    "pokemoncenter": [
        "button:has-text('Notify me'):not([disabled])",
        "button:has-text('Email when available'):not([disabled])",
    ],
    "amazon": [
        "button:has-text('Sign up to be notified'):not([disabled])",
        "#notify-me-button:not([disabled])",
    ],
    "target": [
        "button[data-test='notifyMeButton']:not([disabled])",
        "button:has-text('Notify me'):not([disabled])",
    ],
    "bestbuy": [
        "button:has-text('Notify Me'):not([disabled])",
        "button[data-button-state='COMING_SOON']:not([disabled])",
    ],
    "gamestop": [
        "button:has-text('Notify Me'):not([disabled])",
    ],
    "costco": [
        "button:has-text('Notify Me'):not([disabled])",
    ],
    "samsclub": [
        "button:has-text('Notify Me'):not([disabled])",
    ],
    "tcgplayer": [
        "button:has-text('Notify Me'):not([disabled])",
    ],
}

_SELECTOR_GROUPS = {
    "cart": _SELECTORS,
    "preorder": _PREORDER_SELECTORS,
    "waitlist": _WAITLIST_SELECTORS,
}

_OOS_SIGNATURES = {
    "walmart": ["Out of stock", "currently unavailable"],
    "pokemoncenter": ["Sold Out", "Out of Stock"],
    "amazon": ["Currently unavailable", "Out of Stock"],
    "target": ["Out of stock", "Sold out"],
    "bestbuy": ["Sold Out", "Coming Soon"],
    "gamestop": ["Not Available", "Out of Stock"],
    "costco": ["Out of Stock"],
    "samsclub": ["Out of stock"],
    "tcgplayer": ["Out of Stock"],
}

_QUEUE_SIGNATURES = {
    "walmart": [
        "You are in line", "You're in line", "Waiting Room",
        "Your turn will be here soon", "Please wait", "high traffic",
    ],
    "pokemoncenter": ["You are in line", "virtual queue", "queue-it"],
    "target": ["You are now in line", "virtual waiting room"],
    "bestbuy": ["You are in line", "Please wait", "virtual queue"],
    "default": ["queue-it", "You are in line", "Waiting Room", "Please wait"],
}

_CAPTCHA_SIGNATURES = [
    "Press & Hold", "Verify you are human", "Are you a robot",
    "unusual traffic", "Please verify you are", "Robot or human",
    "Additional Verification Required",
]

# Error modals / banners that appear AFTER a click when the retailer
# silently rejects the add-to-cart (bot detection, rate limit, stock race, etc.)
_ATC_ERROR_SIGNATURES = {
    "walmart": ["could not be added", "not added to your cart", "try again later"],
    "target": ["Item not added to cart", "Something went wrong and the item"],
    "pokemoncenter": ["There was a problem", "Unable to add", "could not be added"],
    "amazon": ["wasn't added to your cart", "could not add", "unavailable at this time"],
    "bestbuy": ["couldn't be added", "unable to add", "try again"],
    "gamestop": ["could not be added", "Error adding"],
    "costco": ["could not be added", "Unable to add"],
    "samsclub": ["not added", "try again"],
    "tcgplayer": ["unable to add", "error adding"],
}

# Buttons to close an error modal so we can retry cleanly
_ATC_ERROR_CLOSE = [
    "button[aria-label='Close']",
    "button[aria-label='close']",
    "button:has-text('Continue shopping')",
    "button:has-text('Try again')",
    "button:has-text('OK')",
    "button:has-text('Close')",
    "[data-test='modalCloseButton']",
]

# Header cart-count badge per retailer. If the count is visible pre-click and
# increments post-click, that's the strongest positive confirmation we have.
_CART_COUNT_SELECTORS = {
    "walmart": [
        "a[link-identifier='cartNavIcon'] [data-automation-id='cart-item-count']",
        "a[link-identifier='cartNavIcon'] span[aria-hidden='true']",
        "[data-testid='cart-icon'] [data-automation-id='cart-item-count']",
    ],
    "pokemoncenter": [
        "[data-testid='minicart-count']",
        "[data-testid='cart-count']",
        "a[href*='/cart'] [class*='count']",
    ],
    "amazon": [
        "#nav-cart-count",
        "span#nav-cart-count",
    ],
    "target": [
        "a[data-test='@web/CartLink'] [data-test='@web/CartIcon/countBubble']",
        "a[data-test='@web/CartLink'] span[aria-hidden='true']",
        "[data-test='@web/CartIcon/countBubble']",
    ],
    "bestbuy": [
        ".shop-cart-icon .cart-count",
        "a[data-track='Cart'] .cart-count",
        "#cart-count",
    ],
    "gamestop": [
        ".minicart-quantity",
        ".minicart .minicart-quantity",
        "a.minicart-link .minicart-quantity",
    ],
    "costco": [
        "#cart-d span.cart-count",
        "#cart-d .count",
        ".cart-count",
    ],
    "samsclub": [
        "[data-testid='cart-count']",
        "a[href*='/cart'] [data-testid*='count']",
    ],
    "tcgplayer": [
        ".header-cart__count",
        "a[href*='/cart'] .count",
    ],
}

# Positive success indicators per retailer (sidecart, flyout, success toast).
# Presence of ANY of these after a click is treated as confirmed ATC success,
# independent of the cart-count check.
_ATC_SUCCESS_SELECTORS = {
    "walmart": [
        "div[data-testid='atc-sidebar']",
        "div[aria-label='Added to cart']",
        "[data-automation-id='atc-confirmation']",
    ],
    "pokemoncenter": [
        "[data-testid='added-to-cart-modal']",
        "[data-testid='cart-notification']",
        "div[role='status']:has-text('added to your cart')",
    ],
    "amazon": [
        "#huc-v2-order-row-confirm-text",
        "#attachSiNoCoverage",
        "#NATC_SMART_WAGON_CONF_MSG_SUCCESS",
        "div:has-text('Added to Cart')",
    ],
    "target": [
        "div[aria-label='Added to cart']",
        "[data-test='addedToCartModal']",
        "div[role='dialog']:has-text('Added to cart')",
    ],
    "bestbuy": [
        ".added-to-cart-notification",
        "div[role='status']:has-text('Added to cart')",
        ".cart-flyout",
    ],
    "gamestop": [
        ".add-to-cart-messages:has-text('added to your cart')",
        ".minicart-flyout:visible",
    ],
    "costco": [
        "#added-to-cart-modal",
        "div.modal-content:has-text('Added to Your Cart')",
    ],
    "samsclub": [
        "[data-testid='added-to-cart-modal']",
        "div[role='dialog']:has-text('Added to cart')",
    ],
    "tcgplayer": [
        ".cart-flyout:visible",
        "div:has-text('Added to Cart')",
    ],
}


async def get_cart_count(page, site: str) -> Optional[int]:
    """Best-effort: read the header mini-cart badge count. Returns None when the
    badge isn't rendered (e.g. empty cart often hides the badge on Walmart/Target)
    or the page hasn't loaded it yet. Callers must treat None as 'unknown', not 0."""
    import re
    for sel in _CART_COUNT_SELECTORS.get(site, []):
        try:
            el = page.locator(sel).first
            if not await el.count():
                continue
            txt = (await el.text_content(timeout=500)) or ""
            txt = txt.strip()
            if not txt:
                continue
            m = re.search(r"\d+", txt)
            if m:
                return int(m.group(0))
        except Exception:
            continue
    return None


async def verify_atc_success(page, site: str, logger, pre_cart_count: Optional[int] = None,
                             wait_s: float = 3.0) -> bool:
    """Positive-confirmation ATC check.

    Returns True only when we see a concrete success signal:
        (a) the retailer's success modal / sidecart / toast appears, OR
        (b) the header cart-count badge increments above `pre_cart_count`.

    Returns False when:
        * a known retailer error signature appears (short-circuit), OR
        * no positive signal is seen within `wait_s` (timeout → retry on next poll).

    Callers pass the cart count they read BEFORE clicking so we can detect the
    badge going from N → N+1 even when the site never shows a modal.
    """
    import re
    label = SITE_LABELS.get(site, site.upper())
    success_selectors = _ATC_SUCCESS_SELECTORS.get(site, [])
    error_sigs = _ATC_ERROR_SIGNATURES.get(site, [])
    error_pattern = None
    if error_sigs:
        error_pattern = re.compile("|".join(re.escape(s) for s in error_sigs), re.IGNORECASE)

    deadline = asyncio.get_event_loop().time() + wait_s
    poll_interval = 0.2

    while asyncio.get_event_loop().time() < deadline:
        # (1) Early-fail on any known error banner.
        if error_pattern is not None:
            try:
                err_el = page.get_by_text(error_pattern).first
                if await err_el.is_visible(timeout=150):
                    matched = ""
                    try:
                        matched = (await err_el.text_content(timeout=300)) or ""
                    except Exception:
                        pass
                    logger("WARN", f"[{label}] cart rejected: '{matched.strip()[:60]}'")
                    for sel in _ATC_ERROR_CLOSE:
                        try:
                            el = page.locator(sel).first
                            if await el.is_visible(timeout=300):
                                await el.click(timeout=1200)
                                await asyncio.sleep(0.2)
                                break
                        except Exception:
                            continue
                    return False
            except Exception:
                pass

        # (2) Positive: retailer-specific success modal/toast/sidecart.
        for sel in success_selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=150):
                    logger("SUCCESS", f"[{label}] ATC confirmed via success modal")
                    return True
            except Exception:
                continue

        # (3) Positive: header cart-count badge incremented.
        try:
            cur = await get_cart_count(page, site)
            if cur is not None:
                if pre_cart_count is None:
                    # Badge wasn't visible pre-click (likely empty cart) but now
                    # shows a count >= 1 — treat as success.
                    if cur >= 1:
                        logger("SUCCESS", f"[{label}] ATC confirmed: cart badge now {cur}")
                        return True
                elif cur > pre_cart_count:
                    logger("SUCCESS", f"[{label}] ATC confirmed: cart {pre_cart_count} → {cur}")
                    return True
        except Exception:
            pass

        await asyncio.sleep(poll_interval)

    logger("WARN", f"[{label}] ATC unconfirmed after {wait_s:.1f}s (no success modal, no cart increment) — treating as failure")
    return False

# Checkout / place-order selectors per site (best-effort; retailers change these frequently)
_CHECKOUT_BTN = {
    "walmart": ["button:has-text('Checkout')", "button[link-identifier='checkoutBtn']"],
    "pokemoncenter": ["button:has-text('Checkout')", "[data-testid='checkout-button']"],
    "amazon": ["input[name='proceedToRetailCheckout']", "#sc-buy-box-ptc-button input"],
    "target": ["button[data-test='checkout-button']", "button:has-text('Check out')"],
    "bestbuy": ["button:has-text('Checkout')", ".checkout-buttons__checkout button"],
    "gamestop": ["button:has-text('Checkout')"],
    "costco": ["button:has-text('Checkout')"],
    "samsclub": ["button:has-text('Checkout')"],
    "tcgplayer": ["button:has-text('Go to Cart')", "button:has-text('Checkout')"],
}

_PRICE_SELECTORS = {
    "walmart": [
        "span[itemprop='price']",
        "span[data-automation-id='product-price']",
        "div[data-testid='price-wrap'] span",
        "[data-seo-id='hero-price']",
    ],
    "pokemoncenter": [
        "[data-testid='product-price']",
        ".product-price",
        "span[class*='price']",
    ],
    "amazon": [
        "#corePrice_feature_div .a-offscreen",
        "#apex_desktop .a-offscreen",
        ".a-price .a-offscreen",
        "#priceblock_ourprice",
    ],
    "target": [
        "[data-test='product-price']",
        "span[data-test='product-price']",
    ],
    "bestbuy": [
        ".priceView-customer-price span",
        ".priceView-hero-price span",
        "div[data-testid='customer-price'] span",
    ],
    "gamestop": [
        ".product-price .sales .value",
        ".price .sales .value",
        "span[itemprop='price']",
    ],
    "costco": [
        ".price .your-price .value",
        ".op-price .currency + span",
        "span[automation-id='productPriceOutput']",
    ],
    "samsclub": [
        "[data-testid='price-value']",
        ".Price-group .Price-characteristic",
    ],
    "tcgplayer": [
        ".price-guide__points__price",
        ".product-listing__price",
        "span.spotlight__price",
    ],
}


async def get_price(page, site: str) -> Optional[float]:
    """Best-effort: extract the current listed price in dollars, or None if it
    can't be read. Handles prices like '$12.99', '1,299.00', '$1,299'."""
    import re
    selectors = _PRICE_SELECTORS.get(site, [])
    for s in selectors:
        try:
            el = page.locator(s).first
            if not await el.count():
                continue
            txt = (await el.text_content(timeout=800)) or ""
            txt = txt.strip().replace(",", "")
            m = re.search(r"(\d+(?:\.\d{1,2})?)", txt)
            if m:
                return float(m.group(1))
        except Exception:
            continue
    return None


_PLACE_ORDER_BTN = {
    "walmart": ["button:has-text('Place order')", "button[data-automation-id='placeOrder']"],
    "pokemoncenter": ["button:has-text('Place Order')"],
    "amazon": ["input[name='placeYourOrder1']", "#placeYourOrder"],
    "target": ["button[data-test='placeOrderButton']"],
    "bestbuy": ["button:has-text('Place Your Order')"],
    "gamestop": ["button:has-text('Place Order')"],
    "costco": ["button:has-text('Place Your Order')"],
    "samsclub": ["button:has-text('Place order')"],
    "tcgplayer": ["button:has-text('Submit Order')", "button:has-text('Place Order')"],
}


def cart_url(site: str) -> str:
    return _CART_URLS.get(site, "")


async def is_captcha(page) -> bool:
    try:
        body = await page.inner_text("body", timeout=2000)
        return any(sig.lower() in body.lower() for sig in _CAPTCHA_SIGNATURES)
    except Exception:
        return False


async def is_queue(page, site: str) -> bool:
    sigs = _QUEUE_SIGNATURES.get(site, _QUEUE_SIGNATURES["default"])
    try:
        url = page.url or ""
        if "queue-it" in url or "waitingroom" in url.lower():
            return True
        body = await page.inner_text("body", timeout=2000)
        return any(sig.lower() in body.lower() for sig in sigs)
    except Exception:
        return False


async def detect_in_stock(page, site: str, allowed_types: Optional[list] = None):
    """Return (Locator, button_type) if a buy-type button is visible for the allowed
    types, else (None, None). Order of priority: cart → preorder → waitlist."""
    if not allowed_types:
        allowed_types = ["cart"]
    for btype in ("cart", "preorder", "waitlist"):
        if btype not in allowed_types:
            continue
        selectors = _SELECTOR_GROUPS.get(btype, {}).get(site, [])
        for s in selectors:
            try:
                btn = page.locator(s).first
                if await btn.is_visible(timeout=600):
                    return btn, btype
            except Exception:
                continue
    return None, None


async def add_to_cart(page, site: str, logger, btn=None, btn_type: str = "cart") -> bool:
    if btn is None:
        btn, btn_type = await detect_in_stock(page, site, ["cart", "preorder", "waitlist"])
    if not btn:
        return False
    try:
        await btn.scroll_into_view_if_needed(timeout=1500)
    except Exception:
        pass
    try:
        await btn.click(timeout=3000)
        label = BUTTON_LABELS.get(btn_type, btn_type)
        logger("SUCCESS", f"[{SITE_LABELS.get(site, site.upper())}] {label} clicked")
        await asyncio.sleep(random.uniform(0.6, 1.2))
        return True
    except Exception as e:
        logger("WARN", f"[{SITE_LABELS.get(site, site.upper())}] button click failed: {str(e)[:80]}")
        return False


async def goto_cart(page, site: str):
    url = _CART_URLS.get(site)
    if url:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        except Exception:
            pass


async def click_checkout(page, site: str, logger) -> bool:
    for s in _CHECKOUT_BTN.get(site, []):
        try:
            btn = page.locator(s).first
            if await btn.is_visible(timeout=2000):
                await btn.click(timeout=3000)
                logger("INFO", f"[{SITE_LABELS.get(site, site.upper())}] Checkout clicked")
                await asyncio.sleep(random.uniform(1.5, 2.5))
                return True
        except Exception:
            continue
    return False


async def click_place_order(page, site: str, logger) -> bool:
    for s in _PLACE_ORDER_BTN.get(site, []):
        try:
            btn = page.locator(s).first
            if await btn.is_visible(timeout=2000):
                await btn.click(timeout=3000)
                logger("SUCCESS", f"[{SITE_LABELS.get(site, site.upper())}] PLACE ORDER clicked")
                await asyncio.sleep(2)
                return True
        except Exception:
            continue
    return False


# Generic best-effort autofill (selectors shared across many retailers)
_FILL_MAP = {
    "first_name": ["input[name='firstName']", "input#firstName", "input[autocomplete='given-name']"],
    "last_name":  ["input[name='lastName']", "input#lastName", "input[autocomplete='family-name']"],
    "email":      ["input[type='email']", "input[name='email']", "input[autocomplete='email']"],
    "phone":      ["input[type='tel']", "input[name='phone']", "input[autocomplete='tel']"],
    "address1":   ["input[name='addressLineOne']", "input[name='address1']", "input[autocomplete='address-line1']"],
    "address2":   ["input[name='addressLineTwo']", "input[name='address2']", "input[autocomplete='address-line2']"],
    "city":       ["input[name='city']", "input[autocomplete='address-level2']"],
    "state":      ["select[name='state']", "input[name='state']", "select[autocomplete='address-level1']"],
    "zip":        ["input[name='postalCode']", "input[name='zipCode']", "input[autocomplete='postal-code']"],
    "card_number":["input[name='cardNumber']", "input[autocomplete='cc-number']", "input#cardNumber"],
    "card_exp_month": ["input[name='expirationMonth']", "select[autocomplete='cc-exp-month']"],
    "card_exp_year":  ["input[name='expirationYear']", "select[autocomplete='cc-exp-year']"],
    "card_cvv":   ["input[name='cvv']", "input[autocomplete='cc-csc']", "input#cvv"],
    "card_name":  ["input[name='nameOnCard']", "input[autocomplete='cc-name']"],
}


async def autofill(page, profile: dict, logger):
    if not profile:
        return
    filled = 0
    for key, selectors in _FILL_MAP.items():
        val = profile.get(key)
        if not val:
            continue
        for s in selectors:
            try:
                el = page.locator(s).first
                if await el.is_visible(timeout=500):
                    await el.fill(str(val), timeout=1500)
                    filled += 1
                    break
            except Exception:
                continue
    logger("INFO", f"Autofill attempted: {filled} fields matched")
