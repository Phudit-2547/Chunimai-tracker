# 🎮 Chunimai Tracker

A Python-based automated tracker for your **CHUNITHM** and **maimai DX** arcade game play counts and ratings. It scrapes your player data daily from the official SEGA game portals, stores it in PostgreSQL, and sends daily/weekly/monthly summary notifications to Discord.

## ✨ Features

- 🕹️ **Daily Play Tracking** — Automatically scrapes cumulative play counts and ratings for both CHUNITHM and maimai DX
- 📊 **Rating Tracking** — Records your in-game rating over time
- 📈 **Weekly & Monthly Reports** — Auto-generates summary reports every Monday and 1st of the month
- 🔔 **Discord Notifications** — Sends daily play count updates via Discord webhooks
- 🐳 **Docker Support** — Fully containerized with Docker Compose (Postgres + app)
- ☁️ **Dual Database** — Writes to both a cloud database (primary) and a local Postgres (secondary/backup)
- 🔄 **CI/CD** — GitHub Actions for scheduled scraping and multi-arch Docker image publishing
- 🔁 **Retry Logic** — Built-in retry mechanism for scraping and notifications with Discord error alerts

## 📁 Project Structure

```
Chunimai-tracker/
├── main.py                          # Entry point — orchestrates scraping, DB writes, and notifications
├── play_counter/
│   ├── config.py                    # Environment variable loading & notification config
│   ├── scraper.py                   # Playwright-based web scraper for SEGA game portals
│   ├── db.py                        # Async PostgreSQL operations (cloud + local)
│   ├── daily_play_notifier.py       # Discord webhook notification sender
│   ├── reports/
│   │   ├── weekly.py                # Weekly summary report generator
│   │   └── monthly.py               # Monthly summary report generator
│   └── utils/
│       ├── constants.py             # URLs, webhook references, cost per play
│       └── date_helpers.py          # Date range utilities for reports
├── init.sql                         # Database schema initialization (legacy, local Docker only)
├── Dockerfile                       # Multi-stage Docker build (Python 3.12 + Playwright Firefox)
├── docker-compose.yml               # App + Postgres 17 service definitions
├── alembic/
│   ├── env.py                       # Alembic environment configuration
│   ├── script.py.mako                # Migration script template
│   └── versions/                    # Database migration scripts
│       ├── 001_init.py              # Initial schema migration
│       └── 002_add_scrape_failure.py # Add scrape_failed and failure_reason columns
├── alembic.ini                      # Alembic configuration
├── run.sh                           # Convenience script to run via Docker
├── .github/workflows/
│   ├── schedule.yml                 # Cron job — runs scraper daily at 22:00 (Asia/Bangkok)
│   └── docker-publish.yml           # Builds & pushes multi-arch Docker image to GHCR
├── pyproject.toml                   # Project metadata & dependencies (managed with uv)
├── requirements.txt                 # Pip-compatible dependency list
└── .env.example                     # Example environment variables
```

## 🚀 Run Your Own Instance (GitHub Actions)

You can run the tracker on your own GitHub account without needing to set up Docker or local Python. Just fork the repository and configure your secrets.

> **Visual Guide**: Follow the step-by-step screenshots here: [Fork Chunimai Tracker Repository and Set Up Actions Secrets](https://scribehow.com/viewer/Fork_Chunimai_Tracker_Repository_and_Set_Up_Actions_Secrets__pLeL8YA5S4Kg-7uqWRPD7Q)

### 1. Fork the Repository

Navigate to [https://github.com/Phudit-2547/Chunimai-tracker](https://github.com/Phudit-2547/Chunimai-tracker) and click the **Fork** button. Choose your account as the owner.

### 2. Configure Actions Secrets

Go to your forked repository's **Settings** → **Secrets and variables** → **Actions** and click **New repository secret** for each of the following:

| Secret Name | Description | Required |
|-------------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string (e.g., `postgresql://user:pass@host:5432/db`) | ✅ |
| `DISCORD_WEBHOOK_URL` | Discord webhook URL for notifications | ❌ |
| `USERNAME` | Your SEGA ID username | ✅ |
| `PASSWORD` | Your SEGA ID password | ✅ |

### 3. Run the Scraper

1. Go to the **Actions** tab in your forked repository.
2. Click **Run Scraper** workflow.
3. Click **Enable workflow** if prompted, then **Run workflow**.

The scraper will execute and send a Discord notification with your play data.

### 4. Automatic Scheduling

Once enabled, the scraper runs automatically every day at 22:00 (Asia/Bangkok / UTC+7). You don't need to manually trigger it after the first run.

### 5. Supported Login Methods

| Login Method | GitHub Actions | Local/Docker | Cookie Caching |
|-------------|----------------|--------------|----------------|
| **SEGA ID** (username/password) | ✅ Full support | ✅ Full support | ✅ Works |
| **Facebook** | ❌ No browser UI | ✅ Full support | ✅ Works |
| **X (Twitter)** | ❌ No browser UI | ✅ Full support | ✅ Works |
| **LINE** | ❌ No browser UI | ✅ Full support | ✅ Works |

> **Note:** GitHub Actions runs headless without a browser display, so OAuth-based logins (Facebook, X, LINE) cannot be automated. If you use these methods, run the tracker locally or switch to SEGA ID for full automation support.

---

## 🚀 Getting Started

### Prerequisites

- **Python** 3.10+
- **[uv](https://github.com/astral-sh/uv)** (recommended package manager)
- **PostgreSQL** 17+ (or use Docker)
- **SEGA ID** account linked to CHUNITHM / maimai DX
- **Discord Webhook URL** (optional — app works without it, just no notifications)

### 1. Clone the Repository

```bash
git clone https://github.com/Phudit-2547/Chunimai-tracker.git
cd Chunimai-tracker
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

| Variable             | Description                                      | Required |
|----------------------|--------------------------------------------------|----------|
| `DISCORD_WEBHOOK_URL`| Discord webhook URL for notifications             | ❌       |
| `DATABASE_URL`       | Cloud PostgreSQL connection string (primary DB)   | ✅       |
| `USERNAME`           | SEGA ID username                                 | ✅       |
| `PASSWORD`           | SEGA ID password                                 | ✅       |
| `POSTGRES_PASSWORD`  | Local Postgres password (used by Docker Compose) | 🐳       |
| `LOCAL_DATABASE_URL` | Local Postgres connection string (auto-set by Docker) | ❌   |

### 3a. Run with Docker (Recommended)

> **Note:** Docker uses the legacy `init.sql` for local schema initialization. For cloud deployments (GitHub Actions), Alembic migrations are used instead.

```bash
# Start Postgres and run the scraper
./run.sh

# Or manually:
docker compose up -d db
docker compose run --rm app
```

#### Health Check

```bash
docker compose run --rm app uv run python main.py --test
```

This verifies timezone settings, Python version, Playwright Firefox, and database connectivity.

### 3b. Run Locally

```bash
# Install dependencies
uv sync

# Install Playwright browsers
uv run playwright install firefox

# Run the scraper
uv run python main.py

# Backfill a past failed day (YYYY-MM-DD)
uv run python main.py --backfill 2026-03-26
```

> **Note:** When scraping fails, the tracker carries forward the last known cumulative and rating values from the previous successful run. Use `--backfill` to manually fix any past failed days via GitHub Actions.

## 🗄️ Database Schema

The tracker uses **Alembic** for database migrations, ensuring the schema is automatically created and updated.

### Current Schema

The tracker stores data in a single `play_data` table:

```sql
CREATE TABLE IF NOT EXISTS public.play_data (
    play_date            DATE PRIMARY KEY,
    maimai_play_count    INTEGER DEFAULT 0,
    chunithm_play_count  INTEGER DEFAULT 0,
    maimai_cumulative    INTEGER DEFAULT 0,
    chunithm_cumulative  INTEGER DEFAULT 0,
    maimai_rating        NUMERIC,
    chunithm_rating      NUMERIC,
    scrape_failed        BOOLEAN DEFAULT FALSE,
    failure_reason       TEXT
);
```

### How Migrations Work

- Migrations are stored in `alembic/versions/` and named sequentially (e.g., `001_init.py`, `002_xxx.py`)
- The GitHub Actions workflow automatically runs `alembic upgrade head` before each scraper execution
- This means **forks will automatically have their database schema created** on first run

### Adding New Migrations

To add a new migration (e.g., for future `play_history` table):

```bash
# Generate a new migration
uv run alembic revision --autogenerate -m "Add play history table"

# Apply migrations
uv run alembic upgrade head
```

> **Note:** The legacy `init.sql` is only used for local Docker development. Cloud deployments (GitHub Actions) use Alembic migrations exclusively.

## ⚙️ GitHub Actions Workflows

### Scheduled Scraper (`schedule.yml`)
- Runs daily at **22:00 Asia/Bangkok** (15:00 UTC)
- Can also be triggered manually via `workflow_dispatch`
- Supports backfilling past failed days via `backfill_date` input
- Uploads Playwright trace files as artifacts for debugging

### Docker Image Publish (`docker-publish.yml`)
- Triggers on push to `main` branch
- Builds multi-arch images (`linux/amd64`, `linux/arm64`)
- Pushes to GitHub Container Registry (`ghcr.io/phudit-2547/chunimai-tracker`)

## 🛠️ Tech Stack

| Component       | Technology                          |
|-----------------|-------------------------------------|
| Language        | Python 3.12                         |
| Web Scraping    | Playwright (Firefox, headless)      |
| Database        | PostgreSQL 17 + asyncpg             |
| Migrations      | Alembic                             |
| Notifications   | Discord Webhooks                    |
| Package Manager | uv                                  |
| Containerization| Docker + Docker Compose             |
| CI/CD           | GitHub Actions                      |
| Timezone        | Asia/Bangkok (UTC+7)                |

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

Made with ❤️ by [Phudit Pumcharern](https://github.com/Phudit-2547)

<a href="https://deepwiki.com/Phudit-2547/Chunimai_tracker"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"></a>

