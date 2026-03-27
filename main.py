import asyncio
import sys
from datetime import datetime

from play_counter.config import CONFIG
from play_counter.daily_play_notifier import send_notification
from play_counter.db import get_previous_cumulative, get_previous_rating, test_db_connection, upsert_play_data
from play_counter.reports.monthly import generate_monthly_report
from play_counter.reports.weekly import generate_weekly_report
from play_counter.scraper import fetch_player_data


async def main():
    # Backfill mode: fix a past failed day
    if "--backfill" in sys.argv:
        idx = sys.argv.index("--backfill")
        target_date = sys.argv[idx + 1]

        maimai_cumulative = await get_previous_cumulative("maimai", target_date)
        chunithm_cumulative = await get_previous_cumulative("chunithm", target_date)
        maimai_rating = await get_previous_rating("maimai", target_date)
        chunithm_rating = await get_previous_rating("chunithm", target_date)

        await upsert_play_data(
            target_date,
            0,                   # maimai_play_count
            0,                   # chunithm_play_count
            maimai_cumulative,
            chunithm_cumulative,
            maimai_rating,
            chunithm_rating,
            scrape_failed=True,
            failure_reason="manual backfill — carried forward from previous day",
        )
        print(f"Backfilled {target_date} with carried-forward values.")
        return

    # Quick Docker health check: python main.py --test
    if "--test" in sys.argv:
        print("[TEST] Docker health check...")
        print(f"   Timezone:  {datetime.now().astimezone().tzinfo}")
        print(f"   Python:    {sys.version.split()[0]}")
        print(f"   Timestamp: {datetime.now():%Y-%m-%d %H:%M:%S}")

        # Test Playwright browser
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.firefox.launch(headless=True)
                await browser.close()
            print("   Playwright: [OK] Firefox OK")
        except Exception as e:
            print(f"   Playwright: [ERROR] {e}")
            sys.exit(1)

        # Test DB connections
        db_ok = await test_db_connection()
        if db_ok:
            print("\n[OK] All systems go! Docker setup is working.")
        else:
            print("\n[ERROR] Database connection failed.")
            sys.exit(1)
        return

    # Test DB connection first
    if not await test_db_connection():
        print("Exiting: Database is unreachable.")
        sys.exit(1)

    today = datetime.today()
    today_str = today.strftime("%Y-%m-%d")

    if today.day == 1:
        await generate_monthly_report()
    if today.weekday() == 0:
        await generate_weekly_report()

    # Fetch all player data (rating + cumulative) in one pass
    tasks = {game: fetch_player_data(game) for game, enable in CONFIG.items() if enable}
    player_data_results = await asyncio.gather(*tasks.values())
    player_data = dict(zip(tasks.keys(), player_data_results))

    # Extract cumulative, ratings, and failure info
    cumulative = {game: data["cumulative"] for game, data in player_data.items()}
    ratings = {game: data["rating"] for game, data in player_data.items()}
    scrape_failed = any(data.get("failed", False) for data in player_data.values())
    failure_reason = " | ".join(
        f"{game}: {data.get('failure_reason', 'unknown')}"
        for game, data in player_data.items()
        if data.get("failed", False)
    )

    # Initialize new_plays dict before failure handling
    new_plays = {game: 0 for game in cumulative}

    # Carry forward previous values on failure
    if scrape_failed:
        for game in cumulative:
            last_known_cumulative = await get_previous_cumulative(game, today_str)
            cumulative[game] = last_known_cumulative
            new_plays[game] = 0
        for game in ratings:
            if ratings[game] is None or ratings[game] == 0:
                ratings[game] = await get_previous_rating(game, today_str)

    # Calculate new plays (delta)
    # prev_cumulative = the *_cumulative value from the most recent DB record (yesterday's baseline)
    # On first run: prev_cumulative is 0, so new_plays=0 (don't record prior plays)
    # On subsequent runs: new_plays = today's cumulative - prev_cumulative (actual delta)
    prev_cumulative = {game: await get_previous_cumulative(game, today_str) for game in cumulative}
    new_plays = {}
    for game in cumulative:
        if prev_cumulative[game] == 0:
            new_plays[game] = 0
        else:
            new_plays[game] = max(0, cumulative[game] - prev_cumulative[game])

    # Insert with ratings and failure info
    await upsert_play_data(
        today_str,
        new_plays.get("maimai", 0),
        new_plays.get("chunithm", 0),
        cumulative.get("maimai", 0),
        cumulative.get("chunithm", 0),
        ratings.get("maimai"),
        ratings.get("chunithm"),
        scrape_failed=scrape_failed,
        failure_reason=failure_reason if scrape_failed else None,
    )

    send_notification("chunithm", new_plays.get("chunithm", 0))
    send_notification("maimai", new_plays.get("maimai", 0))


if __name__ == "__main__":
    asyncio.run(main())
