import asyncpg
from datetime import datetime

from play_counter.config import DATABASE_URL, LOCAL_DATABASE_URL

MISSING_DATABASE_URL_MESSAGE = (
    "DATABASE_URL is not configured. Set it in environment variables or .env."
)


async def connect_db():
    if not DATABASE_URL:
        raise RuntimeError(MISSING_DATABASE_URL_MESSAGE)
    return await asyncpg.connect(DATABASE_URL)


async def connect_local_db():
    """Connect to the local Postgres. Returns None if LOCAL_DATABASE_URL is not set."""
    if not LOCAL_DATABASE_URL:
        return None
    try:
        return await asyncpg.connect(LOCAL_DATABASE_URL)
    except Exception as e:
        print(f"[WARN] Local DB connection failed (non-fatal): {e}")
        return None


async def get_cumulative(game: str, date_str: str) -> int:
    conn = await connect_db()
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        col = f"{game}_cumulative"
        row = await conn.fetchrow(
            f"SELECT {col} FROM public.play_data WHERE play_date = $1", date_obj
        )
        return row[col] if row and row[col] is not None else 0
    finally:
        await conn.close()


async def get_previous_cumulative(game: str, today_str: str) -> int:
    """Get the most recent cumulative before today. Used to correctly calculate new plays across runs."""
    conn = await connect_db()
    try:
        date_obj = datetime.strptime(today_str, "%Y-%m-%d")
        col = f"{game}_cumulative"
        row = await conn.fetchrow(
            f"SELECT {col} FROM public.play_data WHERE play_date < $1 ORDER BY play_date DESC LIMIT 1",
            date_obj,
        )
        return row[col] if row and row[col] is not None else 0
    finally:
        await conn.close()


async def get_previous_rating(game: str, exclude_date: str) -> float | None:
    """Get the most recent rating before a given date, excluding failed scrapes."""
    conn = await connect_db()
    try:
        date_obj = datetime.strptime(exclude_date, "%Y-%m-%d")
        col = f"{game}_rating"
        row = await conn.fetchrow(
            f"""
                SELECT {col} FROM public.play_data
                WHERE play_date < $1
                  AND {col} IS NOT NULL
                  AND scrape_failed = FALSE
                ORDER BY play_date DESC
                LIMIT 1
            """,
            date_obj,
        )
        return row[col] if row else None
    finally:
        await conn.close()


async def upsert_play_data(
    date_str: str,
    maimai_new: int,
    chunithm_new: int,
    maimai_cumulative: int,
    chunithm_cumulative: int,
    maimai_rating: int,
    chunithm_rating: float,
    scrape_failed: bool = False,
    failure_reason: str = None,
):
    upsert_query = """
        INSERT INTO public.play_data
            (play_date, maimai_play_count, chunithm_play_count,
             maimai_cumulative, chunithm_cumulative,
             maimai_rating, chunithm_rating, scrape_failed, failure_reason)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        ON CONFLICT (play_date) DO UPDATE
          SET maimai_play_count=EXCLUDED.maimai_play_count,
              chunithm_play_count=EXCLUDED.chunithm_play_count,
              maimai_cumulative=EXCLUDED.maimai_cumulative,
              chunithm_cumulative=EXCLUDED.chunithm_cumulative,
              maimai_rating=EXCLUDED.maimai_rating,
              chunithm_rating=EXCLUDED.chunithm_rating,
              scrape_failed=EXCLUDED.scrape_failed,
              failure_reason=EXCLUDED.failure_reason
    """
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    params = (
        date_obj,
        maimai_new,
        chunithm_new,
        maimai_cumulative,
        chunithm_cumulative,
        maimai_rating,
        chunithm_rating,
        scrape_failed,
        failure_reason,
    )

    # Write to cloud DB (primary)
    conn = await connect_db()
    try:
        await conn.execute(upsert_query, *params)
        print(
            f"[OK] Cloud DB saved: {date_str} | Maimai new: {maimai_new}, Chunithm new: {chunithm_new} | "
            f"Maimai cumulative: {maimai_cumulative}, Chunithm cumulative: {chunithm_cumulative}"
        )
    finally:
        await conn.close()

    # Write to local DB (secondary, non-fatal if it fails)
    local_conn = await connect_local_db()
    if local_conn:
        try:
            await local_conn.execute(upsert_query, *params)
            print(f"[OK] Local DB saved: {date_str}")
        except Exception as e:
            print(f"[WARN] Local DB write failed (non-fatal): {e}")
        finally:
            await local_conn.close()


async def test_db_connection():
    if not DATABASE_URL:
        print(f"Database connection failed: {MISSING_DATABASE_URL_MESSAGE}")
        return False

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.close()
        print("[OK] Cloud DB connection OK")
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

    # Also test local DB if configured
    if LOCAL_DATABASE_URL:
        local_conn = await connect_local_db()
        if local_conn:
            await local_conn.close()
            print("[OK] Local DB connection OK")
        else:
            print("[WARN] Local DB not reachable (continuing with cloud only)")

    return True
