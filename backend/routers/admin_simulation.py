"""G3 仿真底表的只读统计接口。

只读 simulation_* 表，不参与真实推荐/统计；数据由
`python -m backend.scripts.import_simulation` 导入。
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, distinct, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import (
    SimulationGroupResult,
    SimulationMealLog,
    SimulationRoom,
    SimulationRoomVote,
    SimulationRun,
)

router = APIRouter(
    prefix="/admin/stats/simulation",
    tags=["仿真实验"],
    dependencies=[Depends(require_admin)],
)


def _dt(value) -> Optional[str]:
    return value.isoformat() if value is not None else None


def _run_brief(run: SimulationRun) -> dict:
    return {
        "id": run.id,
        "name": run.name,
        "seed": run.seed,
        "personas": run.personas,
        "days": run.days,
        "meals_per_day": run.meals_per_day,
        "rooms": run.rooms_count,
        "members_per_room": run.members_per_room,
        "lambda_decay": run.lambda_decay,
        "omega_group": run.omega_group,
        "generated_at": _dt(run.generated_at),
        "imported_at": _dt(run.imported_at),
        "meal_rows": run.meal_rows,
        "room_rows": run.room_rows,
        "vote_rows": run.vote_rows,
    }


@router.get("/runs")
def list_runs(db: Session = Depends(get_db)) -> dict:
    rows = (
        db.query(SimulationRun)
        .order_by(SimulationRun.imported_at.desc(), SimulationRun.id.desc())
        .all()
    )
    return {"total": len(rows), "items": [_run_brief(row) for row in rows]}


@router.get("/runs/{run_id}")
def run_detail(run_id: int, db: Session = Depends(get_db)) -> dict:
    run = db.get(SimulationRun, run_id)
    if run is None:
        raise HTTPException(404, "仿真运行不存在")

    meal_rows = (
        db.query(
            SimulationMealLog.arm,
            func.count(SimulationMealLog.id).label("rows"),
            func.count(distinct(SimulationMealLog.persona_id)).label("personas"),
            func.sum(
                case((SimulationMealLog.duplicated.is_(True), 1), else_=0)
            ).label("duplicates"),
            func.avg(SimulationMealLog.total_score).label("avg_score"),
            func.avg(SimulationMealLog.decay_weight).label("avg_decay"),
        )
        .filter(SimulationMealLog.run_id == run_id)
        .group_by(SimulationMealLog.arm)
        .order_by(SimulationMealLog.arm)
        .all()
    )
    by_arm = [
        {
            "arm": arm,
            "rows": int(rows),
            "personas": int(personas or 0),
            "duplicate_rate": round(float(duplicates or 0) / rows, 6) if rows else 0.0,
            "avg_score": round(float(avg_score or 0), 3),
            "avg_decay_weight": round(float(avg_decay or 0), 4),
        }
        for arm, rows, personas, duplicates, avg_score, avg_decay in meal_rows
    ]

    room_modes = dict(
        db.query(SimulationRoom.mode_type, func.count(SimulationRoom.id))
        .filter(SimulationRoom.run_id == run_id)
        .group_by(SimulationRoom.mode_type)
        .all()
    )
    vote_types = dict(
        db.query(SimulationRoomVote.vote_type, func.count(SimulationRoomVote.id))
        .filter(SimulationRoomVote.run_id == run_id)
        .group_by(SimulationRoomVote.vote_type)
        .order_by(SimulationRoomVote.vote_type)
        .all()
    )

    group_results = [
        {
            "strategy": row.strategy,
            "avg_score": round(float(row.avg_score), 3),
            "least_misery_score": round(float(row.least_misery_score), 3),
        }
        for row in db.query(SimulationGroupResult)
        .filter(SimulationGroupResult.run_id == run_id)
        .order_by(SimulationGroupResult.strategy)
        .all()
    ]

    metrics = run.metrics or {}
    return {
        "run": _run_brief(run),
        "meals": {
            "total": int(sum(item["rows"] for item in by_arm)),
            "by_arm": by_arm,
        },
        "rooms": {
            "total": int(run.room_rows),
            "votes": int(run.vote_rows),
            "by_mode": {str(k): int(v) for k, v in room_modes.items()},
            "vote_types": {str(k): int(v) for k, v in vote_types.items()},
        },
        "group_results": group_results,
        "duplication_rate_curve": metrics.get("duplication_rate_curve") or {},
        "repeat_metrics": metrics.get("repeat_metrics") or {},
        "params": metrics.get("params") or {},
    }
