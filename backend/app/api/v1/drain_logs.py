from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.drain_log import DrainLog
from app.services.drain_log_service import (
    end_drain_cycle,
    get_active_drain_log,
    get_drain_history,
    start_drain_cycle,
)
from app.services.ml_config import invalidate_ml_config_cache

router = APIRouter(prefix="/drain-logs", tags=["Drain Logs"])


class DrainCycleStartRequest(BaseModel):
    cycle_estimate_hours: float = Field(default=2400.0, gt=0)
    created_by: str = Field(default="operator", max_length=50)
    notes: str | None = None


@router.get("/active", response_model=dict | None)
async def active_drain_cycle(db: AsyncSession = Depends(get_db)):
    active = await get_active_drain_log(db)
    return active.to_dict() if active else None


@router.get("/", response_model=list[dict])
async def drain_history(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return [log.to_dict() for log in await get_drain_history(db, limit)]


@router.post("/start", response_model=dict)
async def start_drain(
    body: DrainCycleStartRequest,
    db: AsyncSession = Depends(get_db),
):
    log = await start_drain_cycle(
        db,
        cycle_estimate_hours=body.cycle_estimate_hours,
        created_by=body.created_by,
        notes=body.notes,
    )
    invalidate_ml_config_cache()
    return log.to_dict()


@router.post("/{drain_log_id}/end", response_model=dict)
async def end_drain(
    drain_log_id: int,
    db: AsyncSession = Depends(get_db),
):
    log = await end_drain_cycle(db, drain_log_id, ended_by="operator")
    if log is None:
        raise HTTPException(status_code=404, detail="Drain cycle not found")
    invalidate_ml_config_cache()
    return log.to_dict()
