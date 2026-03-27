"""Add scrape_failed and failure_reason columns

Revision ID: 002
Revises: 001
Create Date: 2026-03-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE public.play_data
        ADD COLUMN IF NOT EXISTS scrape_failed BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS failure_reason TEXT
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE public.play_data
        DROP COLUMN IF EXISTS scrape_failed,
        DROP COLUMN IF EXISTS failure_reason
    """)
