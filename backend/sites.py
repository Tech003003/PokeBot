"""Per-site selector + flow logic for NexusBot. 9 retailers supported.

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

_SELECTORS = {
    "walmart": [
        "button[data-automation-id='atc']",
        "button[data-automation-id='add-to-cart-button']",
        "[data-tl-id='ProductPrimaryCTA-cta_add_to_cart_button']",
        "button:has-text('Add to cart'):not([disabled])",
    ],
    "pokemoncenter": [
        "button[data-testid='add-to-cart-button']:not([disabled])",
        "button:has-text('Add to Cart'):not([disabled])",
        ".add-to-cart:not([disabled])",
    ],
    "amazon": [
        "#add-to-cart-button:not([disabled])",
        "#add-to-cart-button-ubb:not([disabled])",
        "input[name='submit.add-to-cart']:not([disabled])",
    ],
    "target": [
        "button[data-test='shipItButton']:not([disabled])",
        "button[data-test='orderPickupButton']:not([disabled])",
        "button:has-text('Add to cart'):not([disabled])",
    ],
    "bestbuy": [
        "button.add-to-cart-button:not([disabled])",
        "button[data-button-state='ADD_TO_CART']:not([disabled])",
        "button:has-text('Add to Cart'):not([disabled])",
    ],
    "gamestop": [
        "button.add-to-cart:not([disabled])",
        "button:has-text('Add to Cart'):not([disabled])",
    ],
    "costco": [
        "input[value='Add to Cart']:not([disabled])",
        "button:has-text('Add to Cart'):not([disabled])",
        "#add-to-cart-btn:not([disabled])",
    ],
    "samsclub": [
        "button[data-testid='add-to-cart-button']:not([disabled])",
        "button:has-text('Add to cart'):not([disabled])",
    ],
    "tcgplayer": [
        "button:has-text('Add to Cart'):not([disabled])",
        "button.btn-add-to-cart:not([disabled])",
    ],
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


async def detect_in_stock(page, site: str) -> Optional[object]:
    """Return a Locator handle if an in-stock add-to-cart button is visible, else None."""
    selectors = _SELECTORS.get(site, [])
    for s in selectors:
        try:
            btn = page.locator(s).first
            if await btn.is_visible(timeout=800):
                return btn
        except Exception:
            continue
    return None


async def add_to_cart(page, site: str, logger) -> bool:
    btn = await detect_in_stock(page, site)
    if not btn:
        return False
    try:
        await btn.scroll_into_view_if_needed(timeout=1500)
    except Exception:
        pass
    try:
        await btn.click(timeout=3000)
        logger("SUCCESS", f"[{SITE_LABELS.get(site, site.upper())}] Add-to-cart clicked")
        await asyncio.sleep(random.uniform(0.6, 1.2))
        return True
    except Exception as e:
        logger("WARN", f"[{SITE_LABELS.get(site, site.upper())}] ATC click failed: {str(e)[:80]}")
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
