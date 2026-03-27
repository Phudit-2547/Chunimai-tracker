import asyncio
import sys
from datetime import datetime

from play_counter.config import CONFIG
from play_counter.daily_play_notifier import send_notification
from play_counter.db import get_previous_cumulative, test_db_connection, upsert_play_data
from play_counter.reports.monthly import generate_monthly_report
from play_counter.reports.weekly import generate_weekly_report
from play_counter.scraper import fetch_player_data


async def main():
    # Quick Docker health check: python main.py --test
    if "--test" in sys.argv:
        print("🧪 Docker health check...")
        print(f"   Timezone:  {datetime.now().astimezone().tzinfo}")
        print(f"   Python:    {sys.version.split()[0]}")
        print(f"   Timestamp: {datetime.now():%Y-%m-%d %H:%M:%S}")

        # Test Playwright browser
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.firefox.launch(headless=True)
                await browser.close()
            print("   Playwright: ✅ Firefox OK")
        except Exception as e:
            print(f"   Playwright: ❌ {e}")
            sys.exit(1)

        # Test DB connections
        db_ok = await test_db_connection()
        if db_ok:
            print("\n✅ All systems go! Docker setup is working.")
        else:
            print("\n❌ Database connection failed.")
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
