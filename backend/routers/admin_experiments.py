"""G3 正式实验输出适配器。

默认只读 consolidated/G3/data/parallel_benchmark_full.json；文件未生成、半截写入或
结构不合法时返回明确空态。绝不回退到种子快照或合成曲线。
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..deps import require_admin

router = APIRouter(
    prefix="/admin",
    tags=["管理后台"],
    # 实验台会跑仿真、写文件、改算法参数，同样只对管理员开放
    dependencies=[Depends(require_admin)],
)
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BENCHMARK_PATH = ROOT / "docs/review/consolidated/G3/data/parallel_benchmark_full.json"


def _empty_curve() -> dict:
    return {"days": [], "ours_lambda_0.5": [], "baseline_no_decay": []}


def _empty_bars() -> dict:
    return {"strategies": [], "avg_scores": [], "least_misery_scores": []}


def _unavailable(reason: str, *, scope: str = "GLOBAL") -> dict:
    return {
        "available": False,
        "applicable": False,
        "reason": reason,
        "items": [],
        "duplication_rate_curve": _empty_curve(),
        "group_satisfaction_bars": _empty_bars(),
        "meta": {"scope": scope},
    }


def _numbers(value, *, low: float, high: float) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and math.isfinite(float(item))
            and low <= float(item) <= high
            for item in value
        )
    )


def _validate_payload(payload: dict) -> Optional[str]:
    if not isinstance(payload, dict):
        return "实验输出不是 JSON 对象"
    curve = payload.get("duplication_rate_curve")
    bars = payload.get("group_satisfaction_bars")
    if not isinstance(curve, dict) or not isinstance(bars, dict):
        return "实验输出缺少曲线或柱状结构"
    days = curve.get("days")
    ours = curve.get("ours_lambda_0.5")
    baseline = curve.get("baseline_no_decay")
    if days != list(range(1, 15)):
        return "实验曲线 days 必须为 1..14"
    if not _numbers(ours, low=0, high=1) or not _numbers(baseline, low=0, high=1):
        return "实验曲线必须为 0~1 的有限数值"
    if len(ours) != 14 or len(baseline) != 14:
        return "实验曲线必须各有 14 个真实数据点"
    strategies = bars.get("strategies")
    averages = bars.get("avg_scores")
    least = bars.get("least_misery_scores")
    if not isinstance(strategies, list) or len(strategies) != 3:
        return "实验策略必须为三项"
    if not _numbers(averages, low=0, high=100) or not _numbers(least, low=0, high=100):
        return "实验柱状值必须为 0~100 的有限数值"
    if len(averages) != 3 or len(least) != 3:
        return "实验柱状数组必须与三项策略等长"
    if not isinstance(payload.get("generated_at"), str) or not payload["generated_at"]:
        return "实验输出缺少 generated_at"
    if not isinstance(payload.get("sample"), dict):
        return "实验输出缺少 sample"
    return None


def load_benchmark(path: Path) -> tuple[Optional[dict], Optional[str]]:
    if not path.is_file():
        return None, f"G3 正式实验输出尚未生成：{path.name}"
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"G3 实验输出不可读取：{type(exc).__name__}"
    error = _validate_payload(payload)
    if error:
        return None, error
    return payload, None


@router.get("/experiments")
def get_experiments(
    lambda_val: Optional[float] = Query(None, ge=0.1, le=2.0),
    omega_val: Optional[float] = Query(None, ge=0, le=1),
    campus: Optional[str] = Query(None),
    mode_type: Optional[str] = Query(None),
    cuisine_type: Optional[str] = Query(None),
):
    if (campus and campus != "ALL") or mode_type or cuisine_type:
        return _unavailable("C05/C06 为 GLOBAL 固定实验，不支持校区、模式或菜系筛选")
    configured = os.getenv("ADMIN_BENCHMARK_PATH") or os.getenv("G3_BENCHMARK_PATH")
    path = Path(configured).expanduser().resolve() if configured else DEFAULT_BENCHMARK_PATH
    payload, error = load_benchmark(path)
    if error:
        return _unavailable(error)
    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    actual_lambda = float(params.get("lambda_val", 0.5))
    actual_omega = float(params.get("omega_val", 0.5))
    if lambda_val is not None and not math.isclose(lambda_val, actual_lambda, abs_tol=1e-9):
        return _unavailable(f"正式输出仅有 λ={actual_lambda}，请求 λ={lambda_val} 没有对应运行结果")
    if omega_val is not None and not math.isclose(omega_val, actual_omega, abs_tol=1e-9):
        return _unavailable(f"正式输出仅有 ω={actual_omega}，请求 ω={omega_val} 没有对应运行结果")
    return {
        "available": True,
        "applicable": True,
        "generated_at": payload["generated_at"],
        "sample": payload["sample"],
        "duplication_rate_curve": payload["duplication_rate_curve"],
        "group_satisfaction_bars": payload["group_satisfaction_bars"],
        "meta": {
            "scope": "GLOBAL",
            "source": "G3_PARALLEL_BENCHMARK",
            "file": path.name,
            "lambda_val": actual_lambda,
            "omega_val": actual_omega,
            "seed": params.get("seed"),
            "errors": params.get("errors", []),
        },
    }
