"""Align ML drain-cycle schema defaults.

Revision ID: 20261013_ml_drain_defaults
Revises: 2b3d279896e3
"""

from alembic import op


revision = "20261013_ml_drain_defaults"
down_revision = "2b3d279896e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE drain_logs ALTER COLUMN cycle_estimate_hours SET DEFAULT 2400.0"
    )
    op.execute(
        "ALTER TABLE prediction_results ADD COLUMN IF NOT EXISTS rul_hours DOUBLE PRECISION"
    )
    op.execute(
        "ALTER TABLE drain_logs ADD COLUMN IF NOT EXISTS threshold_crossed_at TIMESTAMP"
    )
    op.execute(
        "ALTER TABLE drain_logs ADD COLUMN IF NOT EXISTS event_observed BOOLEAN NOT NULL DEFAULT FALSE"
    )
    op.execute(
        "ALTER TABLE drain_logs ADD COLUMN IF NOT EXISTS event_reason VARCHAR(100)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE drain_logs ALTER COLUMN cycle_estimate_hours SET DEFAULT 2000.0"
    )
    op.execute(
        "ALTER TABLE prediction_results DROP COLUMN IF EXISTS rul_hours"
    )
    op.execute("ALTER TABLE drain_logs DROP COLUMN IF EXISTS threshold_crossed_at")
    op.execute("ALTER TABLE drain_logs DROP COLUMN IF EXISTS event_observed")
    op.execute("ALTER TABLE drain_logs DROP COLUMN IF EXISTS event_reason")
