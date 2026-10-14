from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd
import pytest

from app.ml.features import FEATURE_COLUMNS, MIN_HOURLY_ROWS, build_feature_matrix
from app.services.drain_log_service import (
    DEFAULT_CYCLE_ESTIMATE_HOURS,
    end_drain_cycle,
    get_elapsed_fraction,
)


def _hourly_frame(rows: int = MIN_HOURLY_ROWS) -> pd.DataFrame:
    timestamps = [datetime(2026, 1, 1) + timedelta(hours=i) for i in range(rows)]
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "ph": np.linspace(7.2, 6.8, rows),
            "tds": np.linspace(180.0, 220.0, rows),
            "turbidity": np.linspace(0.5, 2.0, rows),
            "temperature": np.full(rows, 26.0),
        }
    )


def test_feature_matrix_matches_model_contract():
    result = build_feature_matrix(
        _hourly_frame(),
        elapsed_fraction=0.5,
        overall_scores=[90.0 - i * 0.1 for i in range(MIN_HOURLY_ROWS)],
    )

    assert result is not None
    assert list(result.columns) == FEATURE_COLUMNS
    assert len(result) == MIN_HOURLY_ROWS
    assert result["elapsed_hours"].iloc[-1] == pytest.approx(0.5)
    assert result["score_drop_168"].iloc[-1] == pytest.approx(-16.8)


def test_feature_matrix_rejects_short_history():
    assert build_feature_matrix(_hourly_frame(MIN_HOURLY_ROWS - 1)) is None


def test_drain_cycle_default_matches_training_cycle_estimate():
    assert DEFAULT_CYCLE_ESTIMATE_HOURS == 2400.0


@pytest.mark.asyncio
async def test_elapsed_fraction_is_bounded_and_uses_active_cycle():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = SimpleNamespace(
        started_at=datetime.utcnow() - timedelta(hours=1200),
        cycle_estimate_hours=2400.0,
    )
    db.execute.return_value = result

    fraction = await get_elapsed_fraction(db)

    assert fraction == pytest.approx(0.5, abs=0.01)


@pytest.mark.asyncio
async def test_elapsed_fraction_is_capped_at_one():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = SimpleNamespace(
        started_at=datetime.utcnow() - timedelta(hours=3000),
        cycle_estimate_hours=2400.0,
    )
    db.execute.return_value = result

    assert await get_elapsed_fraction(db) == 1.0


@pytest.mark.asyncio
async def test_end_cycle_marks_unobserved_quality_event():
    db = AsyncMock()
    result = MagicMock()
    cycle = SimpleNamespace(
        threshold_crossed_at=None,
        event_observed=True,
        event_reason=None,
        notes=None,
    )
    result.scalars.return_value.first.return_value = cycle
    db.execute.return_value = result

    ended = await end_drain_cycle(db, drain_log_id=1, ended_by="operator")

    assert ended is cycle
    assert cycle.event_observed is False
    assert cycle.event_reason == "cycle_ended_before_quality_threshold"
