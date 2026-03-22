import asyncio
import json
import re
import time
from pathlib import Path

import requests
from playwright.async_api import async_playwright

from play_counter.config import PASSWORD, USERNAME
from play_counter.utils.constants import DISCORD_WEBHOOK_URL, HOME_URLS, LOGIN_URLS

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Cookie storage path (local only - users manage their own)
COOKIES_DIR = Path("cookies")
COOKIES_DIR.mkdir(exist_ok=True)


def get_cookies_path(game: str) -> Path:
    """Get path to cookies file for a game."""
    return COOKIES_DIR / f"{game}_state.json"


def send_discord_notification(game: str, error_message: str):
    """Send notification to Discord when scraping fails."""
    if not DISCORD_WEBHOOK_URL:
        print(f"⏭️ Skipping failure notification for {game} — DISCORD_WEBHOOK_URL not configured")
        return

    payload = {
        "content": f"🚨 **Scraping Failed** 🚨\n\n**Game:** {game}\n**Error:** {error_message}\n**All {MAX_RETRIES} retries exhausted.**"
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code == 204:
            print("✅ Discord notification sent successfully")
        else:
            print(f"⚠️ Failed to send Discord notification: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Error sending Discord notification: {e}")


async def login_with_sega(page, game: str) -> bool:
    """Perform SEGA ID login. Returns True on success."""
    await page.goto(LOGIN_URLS[game], wait_until="domcontentloaded")
    await page.locator("span.c-button--openid--segaId").click()
    await page.locator("#sid").fill(USERNAME)
    await page.locator("#password").fill(PASSWORD)

    if game == "maimai":
        await page.locator("label.c-form__label--bg.agree input#agree").click()
        await page.wait_for_timeout(1000)

        for i in range(3):
            is_checked = await page.locator(
                "label.c-form__label--bg.agree input#agree"
            ).is_checked()
            if is_checked:
                break
            print(f"🔄 Checkbox unchecked, clicking again... (attempt {i + 1})")
            await page.locator("label.c-form__label--bg.agree input#agree").click()
            await page.wait_for_timeout(500)

    elif game == "chunithm":
        await page.get_by_text("Agree to the terms of use for Aime service").click()
        await page.wait_for_timeout(1000)

        for i in range(3):
            is_checked = await page.locator(
                "label.c-form__label--bg:not(.agree) input#agree"
            ).is_checked()
            if is_checked:
                break
            print(f"🔄 Checkbox unchecked, clicking again... (attempt {i + 1})")
            await page.get_by_text(
                "Agree to the terms of use for Aime service"
            ).click()
            await page.wait_for_timeout(500)

    await page.wait_for_selector("button#btnSubmit:not([disabled])", timeout=10000)
    await page.locator("button#btnSubmit").click()
    print("✅ Login button clicked successfully")


async def is_logged_in(page, game: str) -> bool:
    """Check if page is already logged in (cookies are valid)."""
    try:
        await page.goto(LOGIN_URLS[game], wait_until="domcontentloaded")
        # If we're on the home page, we're logged in
        if page.url.startswith(HOME_URLS[game]):
            print("🔄 Using cached session (already logged in)")
            return True
        return False
    except Exception:
        return False


async def save_cookies(context, game: str) -> None:
    """Save cookies to file for future use."""
    cookies = await context.cookies()
    cookies_path = get_cookies_path(game)
    with open(cookies_path, "w") as f:
        json.dump(cookies, f)
    print(f"💾 Saved cookies to {cookies_path}")


async def load_cookies(context, game: str) -> bool:
    """Load cookies from file. Returns True if cookies were loaded."""
    cookies_path = get_cookies_path(game)
    if not cookies_path.exists():
        return False
    try:
        with open(cookies_path) as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        print(f"📂 Loaded cookies from {cookies_path}")
        return True
    except Exception as e:
        print(f"⚠️ Failed to load cookies: {e}")
        return False


async def fetch_player_data(game: str) -> dict:
    """
    Logs into the game website and retrieves player data (rating + cumulative play count).
    Uses cookie caching for faster subsequent runs.

    Returns:
        dict: {"rating": float/int, "cumulative": int}

    For chunithm:
        - Rating from home page: extracts from .player_rating_num_block images
        - Play count from playerData page: extracts from .user_data_play_count

    For maimai:
        - Rating from home page: extracts from .rating_block
        - Play count from playerData page: extracts via regex "maimaiDX total play count：XXX"
    """
    start_time = time.perf_counter()
    using_cached_session = False

    if not USERNAME or not PASSWORD:
        default_rating = 0 if game == "maimai" else 0.0
        print("⚠️ SEGA credentials are not configured. Returning default values.")
        return {"rating": default_rating, "cumulative": 0}

    cookies_loaded = False
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with async_playwright() as p:
                browser = await p.firefox.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                login_start = time.perf_counter()
                cookies_path = get_cookies_path(game)
                if cookies_path.exists():
                    cookies_loaded = await load_cookies(context, game)
                    if cookies_loaded:
                        if await is_logged_in(page, game):
                            using_cached_session = True
                            print(f"✅ Using cached session for {game}")
                        else:
                            print(f"⚠️ Cookies expired, performing fresh login...")
                            using_cached_session = False
                            cookies_path.unlink(missing_ok=True)
                            await login_with_sega(page, game)
                            await save_cookies(context, game)
                else:
                    using_cached_session = False
                    print(f"🔄 No cached cookies found, logging in...")
                    await login_with_sega(page, game)
                    await save_cookies(context, game)

                login_time = time.perf_counter() - login_start

                print(f"🔄 Waiting for {game} home page...")
                try:
                    await page.wait_for_url(HOME_URLS[game], timeout=10000)
                except Exception as e:
                    print(page.url)
                    print(f"❌ Failed to load {game} home page: {e}")
                    if cookies_loaded:
                        print("🔄 Cached session failed, retrying with fresh login...")
                        cookies_path = get_cookies_path(game)
                        cookies_path.unlink(missing_ok=True)
                        using_cached_session = False
                        await login_with_sega(page, game)
                        await save_cookies(context, game)
                        await page.wait_for_url(HOME_URLS[game], timeout=10000)
                    else:
                        await browser.close()
                        raise

                # === Get rating ===
                print(f"🔄 Extracting {game} rating from home page...")

                if game == "chunithm":
                    rating_block = page.locator(".player_rating_num_block")
                    images = await rating_block.locator("img").all()

                    rating_str = ""
                    for img in images:
                        src = await img.get_attribute("src")
                        if not src:
                            continue

                        filename = src.split("/")[-1]

                        if "comma" in filename:
                            rating_str += "."
                        elif "rating_" in filename:
                            digit = filename.split("_")[-1].replace(".png", "")
                            rating_str += str(int(digit))

                    rating = float(rating_str) if rating_str else 0.0

                elif game == "maimai":
                    rating_text = await page.locator(".rating_block").inner_text()
                    rating = int(rating_text) if rating_text.isdigit() else 0

                print(f"✅ {game} rating: {rating}")

                # === Get play count ===
                print(f"🔄 Navigating to {game} play data page...")

                if game == "chunithm":
                    await page.goto(
                        f"{HOME_URLS[game]}playerData", wait_until="domcontentloaded"
                    )
                    play_count_text = await page.locator(
                        "div.user_data_play_count div.user_data_text"
                    ).inner_text()
                    cumulative = (
                        int(play_count_text) if play_count_text.isdigit() else 0
                    )

                elif game == "maimai":
                    await page.goto(
                        "https://maimaidx-eng.com/maimai-mobile/playerData/",
                        wait_until="domcontentloaded",
                    )
                    play_count_text = await page.locator(
                        "div.m_5.m_b_5.t_r.f_12"
                    ).inner_text()
                    match = re.search(
                        r"maimaiDX total play count：(\d+)", play_count_text
                    )
                    cumulative = int(match.group(1)) if match else 0

                await save_cookies(context, game)
                await browser.close()

                total_time = time.perf_counter() - start_time
                session_type = "cached" if using_cached_session else "fresh login"
                print(
                    f"✅ [{session_type}] {game} done in {total_time:.2f}s "
                    f"(login: {login_time:.2f}s) - Rating: {rating}, Cumulative: {cumulative}"
                )
                return {"rating": rating, "cumulative": cumulative}

        except Exception as e:
            last_error = str(e)
            print(f"⚠️ Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                print(f"⏳ Retrying in {RETRY_DELAY} seconds...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                total_time = time.perf_counter() - start_time
                print(f"❌ {game} failed after {total_time:.2f}s")
                send_discord_notification(game, last_error)
                return {"rating": 0 if game == "maimai" else 0.0, "cumulative": 0}


# Backward compatibility wrapper (if needed elsewhere)
async def fetch_cumulative(game: str) -> int:
    """Legacy function - returns only cumulative count"""
    data = await fetch_player_data(game)
    return data["cumulative"]
