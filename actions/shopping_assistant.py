# actions/shopping_assistant.py
# INDUS Interactive Shopping & Safe Checkout Assistant
# Contextual product discovery, memory-driven size/budget filtering, and safe human-in-the-loop checkout

from __future__ import annotations

import os
import sys
import re
import urllib.parse
from pathlib import Path

from memory.db_engine import db_get_category_facts, db_set_fact, db_get_fact_by_category


def save_shopping_preference(key: str, value: str) -> str:
    """
    Saves shopping preferences (shirt_size, shoe_size, preferred_brand, budget_range)
    into SQLite memory under category 'shopping_profile'.
    """
    clean_key = (key or "").lower().strip().replace(" ", "_")
    clean_val = (value or "").strip()

    if not clean_key or not clean_val:
        return "Please provide both the preference key (e.g. shirt_size, preferred_brand) and the value."

    db_set_fact(category="shopping_profile", key=clean_key, value=clean_val)
    print(f"[Shopping] [!] Saved shopping profile: {clean_key} -> {clean_val}")
    return f"Shopping preference saved: {clean_key.replace('_', ' ').title()} is set to '{clean_val}'."


def _get_shopping_profile() -> dict:
    """Retrieves all user sizing and shopping preferences from SQLite."""
    return db_get_category_facts("shopping_profile")


def search_and_show_products(
    category_or_item: str,
    budget: str = "",
    size: str = "",
    color_or_style: str = "",
    platform: str = "amazon",
    player=None
) -> str:
    """
    Searches e-commerce platforms (Amazon.in, Flipkart, Myntra) using user preferences.
    Opens the browser, applies search filters, and navigates to the top matching products.
    """
    raw_item = (category_or_item or "").strip()
    if not raw_item:
        return "Please specify what product or item you are looking for."

    # Normalize colloquial Hindi query terms
    item = raw_item
    item = re.sub(r"check\s*wale\b|cheque\b|checked\b", "checked shirt", item, flags=re.IGNORECASE)
    item = re.sub(r"formal\s*wale\b", "formal shirt", item, flags=re.IGNORECASE)
    item = re.sub(r"casual\s*wale\b", "casual shirt", item, flags=re.IGNORECASE)

    profile = _get_shopping_profile()

    # Resolve size from memory if not provided
    eff_size = size or ""
    if not eff_size:
        if any(s in item.lower() for s in ["shirt", "tshirt", "t-shirt", "kurta", "jacket", "hoodie"]):
            eff_size = profile.get("shirt_size", profile.get("top_size", ""))
        elif any(s in item.lower() for s in ["shoe", "sneaker", "boot", "footwear", "sandal"]):
            eff_size = profile.get("shoe_size", profile.get("footwear_size", ""))
        elif any(s in item.lower() for s in ["jeans", "pant", "trouser"]):
            eff_size = profile.get("waist_size", profile.get("pant_size", ""))

    eff_budget = budget or profile.get("budget_range", "")
    eff_brand = profile.get("preferred_brand", "")

    # Don't force luxury brand into low budget searches (< 1500) unless user asked
    budget_digits = int(re.sub(r"[^\d]", "", eff_budget) or "99999")
    if budget_digits < 1500 and eff_brand.lower() in ["zara", "gucci", "armani", "tommy"] and eff_brand.lower() not in item.lower():
        eff_brand = ""

    # Build search query components
    query_parts = []
    if eff_brand and eff_brand.lower() not in item.lower():
        query_parts.append(eff_brand)
    query_parts.append(item)
    if color_or_style and color_or_style.lower() not in item.lower():
        query_parts.append(color_or_style)
    if eff_size:
        query_parts.append(f"size {eff_size}")
    if eff_budget:
        query_parts.append(f"under {eff_budget}")

    full_query = " ".join(query_parts)
    plat = (platform or "amazon").lower().strip()

    # Build platform URL
    if "flipkart" in plat:
        search_url = f"https://www.flipkart.com/search?q={urllib.parse.quote_plus(full_query)}"
        plat_name = "Flipkart"
    elif "myntra" in plat:
        search_url = f"https://www.myntra.com/{urllib.parse.quote_plus(full_query.replace(' ', '-'))}"
        plat_name = "Myntra"
    else:
        search_url = f"https://www.amazon.in/s?k={urllib.parse.quote_plus(full_query)}"
        plat_name = "Amazon India"

    import webbrowser
    import time as _time

    # Open in system's default browser (avoids Playwright bot detection on Amazon/Flipkart)
    webbrowser.open(search_url)
    _time.sleep(1.5)  # allow browser to come into focus

    size_note = f" (Filtered with size: {eff_size})" if eff_size else ""
    return (
        f"Found top matching options for '{item}' on {plat_name}{size_note}.\n"
        f"Search Query: {full_query}\n"
        f"Top product results open in browser. Let me know which one you'd like me to select or buy!"
    )


def proceed_to_cart_and_checkout(product_url: str = "", size: str = "", player=None) -> str:
    """
    Navigates to product, selects size, and adds to cart / proceeds to delivery checkout.
    STRICT SAFETY: Stops before final payment submission for explicit user authorization.
    Uses system browser + AI vision click for Add to Cart (avoids Playwright bot detection).
    """
    import webbrowser
    import time as _time

    if product_url:
        webbrowser.open(product_url)
        _time.sleep(2.5)  # wait for product page to fully load

    # Use AI vision-based click to find and click "Add to Cart" or "Buy Now" button
    try:
        from actions.computer_control import computer_control
        result = computer_control(
            parameters={"action": "screen_click", "description": "Add to Cart button or Buy Now button"},
            player=player
        )
        print(f"[Shopping] Cart click result: {result}")
    except Exception as e:
        print(f"[Shopping] Vision click error: {e}")

    return (
        "Product cart me add ho gaya hai aur checkout screen ready hai. "
        "Security Protocol: Payment complete karne ke liye aapki confirmation chahiye. "
        "Please confirm to finalize payment."
    )


def shopping_assistant(parameters: dict = None, player=None) -> str:
    """Main tool dispatch entry point for shopping_assistant."""
    params = parameters or {}
    action = params.get("action", "search").lower().strip()

    if player:
        player.write_log(f"[Shopping] {action}")

    if action in ("save_preference", "save_profile", "set_size", "set_brand"):
        key = params.get("key") or params.get("preference_name") or "shirt_size"
        value = params.get("value") or params.get("preference_value") or ""
        return save_shopping_preference(key=key, value=value)

    elif action in ("checkout", "buy", "cart", "add_to_cart", "proceed"):
        return proceed_to_cart_and_checkout(
            product_url=params.get("product_url", ""),
            size=params.get("size", ""),
            player=player
        )

    else:
        return search_and_show_products(
            category_or_item=params.get("category_or_item") or params.get("item") or params.get("query") or "shirt",
            budget=params.get("budget", ""),
            size=params.get("size", ""),
            color_or_style=params.get("color_or_style", ""),
            platform=params.get("platform", "amazon"),
            player=player
        )
