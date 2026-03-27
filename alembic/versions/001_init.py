"""Initial schema - create play_data table

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.play_data (
            play_date               DATE PRIMARY KEY,
            maimai_play_count       INTEGER DEFAULT 0,
            chunithm_play_count     INTEGER DEFAULT 0,
            maimai_cumulative       INTEGER DEFAULT 0,
            chunithm_cumulative     INTEGER DEFAULT 0,
            maimai_rating           NUMERIC,
            chunithm_rating         NUMERIC
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.play_data")
