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
├── init.sql                         # Database schema initialization
├── Dockerfile                       # Multi-stage Docker build (Python 3.12 + Playwright Firefox)
├── docker-compose.yml               # App + Postgres 17 service definitions
├── run.sh                           # Convenience script to run via Docker
├── .github/workflows/
│   ├── schedule.yml                 # Cron job — runs scraper daily at 22:00 (Asia/Bangkok)
│   └── docker-publish.yml           # Builds & pushes multi-arch Docker image to GHCR
├── pyproject.toml                   # Project metadata & dependencies (managed with uv)
├── requirements.txt                 # Pip-compatible dependency list
└── .env.example                     # Example environment variables
```

## 🚀 Getting Started

### Prerequisites

- **Python** 3.10+
- **[uv](https://github.com/astral-sh/uv)** (recommended package manager)
- **PostgreSQL** 17+ (or use Docker)
- **SEGA ID** account linked to CHUNITHM / maimai DX
- **Discord Webhook URL**

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
| `DISCORD_WEBHOOK_URL`| Discord webhook URL for daily notifications      | ✅       |
| `DATABASE_URL`       | Cloud PostgreSQL connection string (primary DB)   | ✅       |
| `USERNAME`           | SEGA ID username                                 | ✅       |
| `PASSWORD`           | SEGA ID password                                 | ✅       |
| `POSTGRES_PASSWORD`  | Local Postgres password (used by Docker Compose) | 🐳       |
| `LOCAL_DATABASE_URL` | Local Postgres connection string (auto-set by Docker) | ❌   |

### 3a. Run with Docker (Recommended)

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
```

## 🗄️ Database Schema

The tracker stores data in a single `play_data` table:

```sql
CREATE TABLE IF NOT EXISTS public.play_data (
    play_date            DATE PRIMARY KEY,
    maimai_play_count    INTEGER DEFAULT 0,
    chunithm_play_count  INTEGER DEFAULT 0,
    maimai_cumulative    INTEGER DEFAULT 0,
    chunithm_cumulative  INTEGER DEFAULT 0,
    maimai_rating        NUMERIC,
    chunithm_rating      NUMERIC
);
```

## ⚙️ GitHub Actions Workflows

### Scheduled Scraper (`schedule.yml`)
- Runs daily at **22:00 Asia/Bangkok** (15:00 UTC)
- Can also be triggered manually via `workflow_dispatch`
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

