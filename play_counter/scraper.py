import asyncio
import re

import requests
from playwright.async_api import async_playwright

from play_counter.config import PASSWORD, USERNAME
from play_counter.utils.constants import DISCORD_WEBHOOK_URL, HOME_URLS, LOGIN_URLS

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def send_discord_notification(game: str, error_message: str):
    """Send notification to Discord when scraping fails."""
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


async def fetch_player_data(game: str) -> dict:
    """
    Logs into the game website and retrieves player data (rating + cumulative play count).

    Returns:
        dict: {"rating": float/int, "cumulative": int}

    For chunithm:
        - Rating from home page: extracts from .player_rating_num_block images
        - Play count from playerData page: extracts from .user_data_play_count

    For maimai:
        - Rating from home page: extracts from .rating_block
        - Play count from playerData page: extracts via regex "maimaiDX total play count：XXX"
    """
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with async_playwright() as p:
                browser = await p.firefox.launch(headless=True)
                context = await browser.new_context()

                # Start tracing
                await context.tracing.start(
                    screenshots=True, snapshots=True, sources=True
                )
                page = await context.new_page()

                print(f"🔄 Logging into {game}... (Attempt {attempt})")
                await page.goto(LOGIN_URLS[game], wait_until="domcontentloaded")
                await page.locator("span.c-button--openid--segaId").click()
                await page.locator("#sid").fill(USERNAME)
                await page.locator("#password").fill(PASSWORD)

                # Check the agreement checkbox right before login
                if game == "maimai":
                    await page.locator(
                        "label.c-form__label--bg.agree input#agree"
                    ).click()
                    await page.wait_for_timeout(1000)

                    # Ensure checkbox is checked (retry if needed)
                    for i in range(3):
                        is_checked = await page.locator(
                            "label.c-form__label--bg.agree input#agree"
                        ).is_checked()
                        if is_checked:
                            break
                        print(
                            f"🔄 Checkbox unchecked, clicking again... (attempt {i + 1})"
                        )
                        await page.locator(
                            "label.c-form__label--bg.agree input#agree"
                        ).click()
                        await page.wait_for_timeout(500)

                elif game == "chunithm":
                    await page.get_by_text(
                        "Agree to the terms of use for Aime service"
                    ).click()
                    await page.wait_for_timeout(1000)

                    # Ensure checkbox is checked (retry if needed)
                    for i in range(3):
                        is_checked = await page.locator(
                            "label.c-form__label--bg:not(.agree) input#agree"
                        ).is_checked()
                        if is_checked:
                            break
                        print(
                            f"🔄 Checkbox unchecked, clicking again... (attempt {i + 1})"
                        )
                        await page.get_by_text(
                            "Agree to the terms of use for Aime service"
                        ).click()
                        await page.wait_for_timeout(500)

                # Wait for login button to be enabled and click
                print("🔄 Waiting for login button to be enabled...")
                await page.wait_for_selector(
                    "button#btnSubmit:not([disabled])", timeout=10000
                )
                await page.locator("button#btnSubmit").click()
                print("✅ Login button clicked successfully")

                print(f"🔄 Waiting for {game} home page...")
                try:
                    await page.wait_for_url(HOME_URLS[game])
                except Exception as e:
                    print(page.url)
                    print(f"❌ Failed to load {game} home page: {e}")
                    await context.tracing.stop(path="trace.zip")
                    await browser.close()
                    raise

                # === STEP 1: Get rating from home page ===
                print(f"🔄 Extracting {game} rating from home page...")

                if game == "chunithm":
                    # Parse rating from images
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
                    # Simple text extraction
                    rating_text = await page.locator(".rating_block").inner_text()
                    rating = int(rating_text) if rating_text.isdigit() else 0

                print(f"✅ {game} rating: {rating}")

                # === STEP 2: Navigate to play data page ===
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

                await context.tracing.stop(path="trace.zip")
                await browser.close()

                print(
                    f"✅ Fetched {game} data - Rating: {rating}, Cumulative: {cumulative}"
                )
                return {"rating": rating, "cumulative": cumulative}

        except Exception as e:
            last_error = str(e)
            print(f"⚠️ Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                print(f"⏳ Retrying in {RETRY_DELAY} seconds...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                print("❌ All retries failed.")
                send_discord_notification(game, last_error)
                return {"rating": 0 if game == "maimai" else 0.0, "cumulative": 0}


# Backward compatibility wrapper (if needed elsewhere)
async def fetch_cumulative(game: str) -> int:
    """Legacy function - returns only cumulative count"""
    data = await fetch_player_data(game)
    return data["cumulative"]
