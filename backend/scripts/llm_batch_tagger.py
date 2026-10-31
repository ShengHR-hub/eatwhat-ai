"""S11 批量打标（SSOT 附录 C 契约）。

设计边界：
* 每批固定 20 道；只写明确命名的 G2 隔离库，不动演示库/S10 封存库；
* 成功记录永不覆盖；失败进失败清单，禁止默认 0.5 或重复计数；
* JSON/键名/范围/有限值/角色/标签任一非法 → 整批重试，最多 3 次；
* `--dry-run` 不读 Key、不发请求，只产批次计划、提示词指纹与预算估算；
* Key 只从环境变量读取，不打印、不落盘、不进证据。

数据层字段（SSOT v2.3.3）：`feature_vector`、`allergen_tags`、`tagging_status`、
`tagging_error`、`llm_meta`。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.algorithms.vector_spec import FEATURE_KEYS
from backend.models import Dish

BATCH_SIZE = 20
MAX_RETRIES = 3
PROMPT_VERSION = "prompt_v1_appendix_c"
SYSTEM_PROMPT = (
    "你是一个中式餐饮营养学与风味特征工程专家。请根据输入的菜品名称、分类与主辅料，"
    "为每道菜评估 8 个维度的标准化特征分值，并判断其套餐搭配角色。\n"
    "8 个维度键名固定为：spicy_level, oily_level, soup_level, temp_fit, satiety_level, "
    "prep_speed, social_fit, comfort_level，取值范围严格在 0.0 到 1.0 之间的小数。\n"
    "套餐搭配角色 dish_role 只能从 MEAT / VEG / SOUP / ONE_MEAL 中选一。\n"
    "同时识别并输出该菜品命中的常见过敏原/忌口标签数组 allergen_tags"
    "（如：香菜、海鲜、花生、葱姜蒜）。\n"
    "只输出 JSON 数组，不要输出任何解释文字；数组元素字段固定为："
    "dish_name, dish_role, feature_vector{8个键}, allergen_tags[]。"
)
VALID_ROLES = {"MEAT", "VEG", "SOUP", "ONE_MEAL"}
ALLOWED_DB_PREFIX = "eatwhat_g2_s10_"


class BudgetTracker:
    """按服务端返回的真实 usage 累计费用，达到上限后停止后续调用。"""

    def __init__(self, budget_usd: float, input_usd_per_m: float, output_usd_per_m: float):
        if budget_usd <= 0:
            raise ValueError("budget_usd_must_be_positive")
        if input_usd_per_m < 0 or output_usd_per_m < 0:
            raise ValueError("token_rates_must_be_non_negative")
        self.budget_usd = float(budget_usd)
        self.input_usd_per_m = float(input_usd_per_m)
        self.output_usd_per_m = float(output_usd_per_m)
        self.spent_usd = 0.0
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    @property
    def exhausted(self) -> bool:
        return self.spent_usd >= self.budget_usd

    def add_usage(self, meta: dict) -> float:
        usage = meta.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0)
        completion_tokens = int(usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0)
        cost = (
            prompt_tokens * self.input_usd_per_m
            + completion_tokens * self.output_usd_per_m
        ) / 1_000_000
        self.calls += 1
        self.input_tokens += prompt_tokens
        self.output_tokens += completion_tokens
        self.spent_usd += cost
        return cost


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _guard_db(path: Path) -> Path:
    resolved = Path(path).resolve()
    if not resolved.name.startswith(ALLOWED_DB_PREFIX):
        raise SystemExit(
            f"拒绝写 {resolved.name}：S11 只允许写入明确命名的 G2 打标库"
            f"（{ALLOWED_DB_PREFIX}*.db）"
        )
    if not resolved.exists():
        raise SystemExit(f"目标库不存在：{resolved}")
    return resolved


def _as_list(value) -> list:
    if isinstance(value, list):
        return value
    return json.loads(value or "[]")


def _dish_payload(dish: Dish) -> dict:
    return {
        "dish_id": int(dish.id),
        "name": dish.name,
        "cuisine_type": dish.cuisine_type or "",
        "ingredients_main": _as_list(dish.ingredients_main),
        "ingredients_aux": _as_list(dish.ingredients_aux),
    }


def build_user_prompt(items: list[dict]) -> str:
    rows = [
        {
            "name": item["name"],
            "cuisine_type": item["cuisine_type"],
            "ingredients_main": item["ingredients_main"],
            "ingredients_aux": item["ingredients_aux"],
        }
        for item in items
    ]
    return json.dumps(rows, ensure_ascii=False)


def validate_item(item, expected_name: str) -> tuple[bool, str]:
    if not isinstance(item, dict):
        return False, "item_not_object"
    if str(item.get("dish_name", "")).strip() != expected_name:
        return False, "dish_name_mismatch"
    if item.get("dish_role") not in VALID_ROLES:
        return False, "invalid_role"
    vector = item.get("feature_vector")
    if not isinstance(vector, dict):
        return False, "vector_not_object"
    if set(vector.keys()) != set(FEATURE_KEYS):
        return False, "vector_keys_mismatch"
    for key in FEATURE_KEYS:
        value = vector[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False, f"vector_not_number:{key}"
        if not math.isfinite(float(value)):
            return False, f"vector_not_finite:{key}"
        if not 0.0 <= float(value) <= 1.0:
            return False, f"vector_out_of_range:{key}"
    tags = item.get("allergen_tags")
    if not isinstance(tags, list) or not all(isinstance(tag, str) and tag.strip() for tag in tags):
        return False, "allergen_tags_invalid"
    return True, ""


def validate_batch(payload: str, items: list[dict]) -> tuple[list[dict] | None, str]:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None, "json_parse_error"
    if not isinstance(parsed, list):
        return None, "response_not_array"
    if len(parsed) != len(items):
        return None, "response_length_mismatch"
    by_name = {
        row["dish_name"]: row
        for row in parsed
        if isinstance(row, dict) and isinstance(row.get("dish_name"), str)
    }
    validated = []
    for item in items:
        row = by_name.get(item["name"])
        if row is None:
            return None, f"missing_dish:{item['name']}"
        ok, reason = validate_item(row, item["name"])
        if not ok:
            return None, f"{reason}:{item['name']}"
        validated.append(
            {
                "dish_id": item["dish_id"],
                "dish_name": row["dish_name"],
                "dish_role": row["dish_role"],
                "feature_vector": {key: float(row["feature_vector"][key]) for key in FEATURE_KEYS},
                "allergen_tags": [tag.strip() for tag in row["allergen_tags"]],
            }
        )
    return validated, ""


def call_model(base_url: str, api_key: str, model: str, messages: list[dict], timeout: int = 60) -> tuple[str, dict]:
    body = json.dumps(
        {"model": model, "messages": messages, "temperature": 0, "response_format": {"type": "json_object"}},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    meta = {
        "id": payload.get("id"),
        "model": payload.get("model"),
        "usage": payload.get("usage", {}),
    }
    content = payload["choices"][0]["message"]["content"]
    return content, meta


def collect_dishes(db, retry_failed: bool, limit: int, shard_index: int = 0, shard_count: int = 1) -> list[dict]:
    if shard_count < 1 or not 0 <= shard_index < shard_count:
        raise ValueError("invalid_shard")
    query = db.query(Dish).filter(Dish.mode_type == "HOME_COOKING")
    if retry_failed:
        query = query.filter(Dish.tagging_status.in_(("PENDING", "FAILED", None)))
    else:
        query = query.filter((Dish.tagging_status.is_(None)) | (Dish.tagging_status == "PENDING"))
    if shard_count > 1:
        # 按稳定主键取模分片，多个进程的候选集合始终互斥，不依赖动态列表位置。
        query = query.filter(Dish.id % shard_count == shard_index)
    query = query.order_by(Dish.id)
    if limit:
        query = query.limit(limit)
    return [_dish_payload(dish) for dish in query.all()]


def write_failure(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def dry_run(items: list[dict], model: str, budget_usd: float | None) -> dict:
    batches = [items[index : index + BATCH_SIZE] for index in range(0, len(items), BATCH_SIZE)]
    plans = []
    input_chars = 0
    for index, batch in enumerate(batches, start=1):
        prompt = build_user_prompt(batch)
        input_chars += len(prompt)
        plans.append(
            {
                "batch": index,
                "dish_ids": [row["dish_id"] for row in batch],
                "dish_names": [row["name"] for row in batch],
                "prompt_sha256": _sha(prompt),
                "prompt_chars": len(prompt),
            }
        )
    # 中文约 1 token / 1.5 字；输出按每道菜 ~90 token 估
    input_tokens = math.ceil(input_chars / 1.5)
    output_tokens = len(items) * 90
    retry_reserve = 3
    return {
        "mode": "dry_run",
        "model": model or "UNSPECIFIED",
        "prompt_version": PROMPT_VERSION,
        "batch_size": BATCH_SIZE,
        "dish_count": len(items),
        "batch_count": len(batches),
        "max_calls_with_retries": len(batches) * retry_reserve,
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_cost_note": "费用需按所选模型的每百万 token 单价计算；未确认单价时不得发起付费调用",
        "budget_usd": budget_usd,
        "plans": plans,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="S11 LLM 批量打标（默认 dry-run）")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default=os.getenv("LLM_MODEL", ""))
    parser.add_argument("--base-url", default=os.getenv("LLM_BASE_URL", ""))
    parser.add_argument("--api-key-env", default="LLM_API_KEY")
    parser.add_argument("--max-retries", type=int, default=MAX_RETRIES)
    parser.add_argument("--budget-usd", type=float, default=None)
    parser.add_argument("--input-usd-per-m", type=float, default=None)
    parser.add_argument("--output-usd-per-m", type=float, default=None)
    parser.add_argument("--max-calls", type=int, default=0)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--failures", type=Path, default=None)
    parser.add_argument("--summary-out", type=Path, default=None)
    args = parser.parse_args()

    if args.batch_size != BATCH_SIZE:
        raise SystemExit(f"SSOT 锁定每批 {BATCH_SIZE} 道，不允许改成 {args.batch_size}")

    db_path = _guard_db(args.db)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"timeout": 30})
    session = sessionmaker(bind=engine)()
    try:
        items = collect_dishes(session, args.retry_failed, args.limit, args.shard_index, args.shard_count)
        api_key = os.getenv(args.api_key_env, "")
        key_present = bool(api_key)

        if args.dry_run or not key_present or not args.model or not args.base_url:
            plan = dry_run(items, args.model, args.budget_usd)
            plan.update(
                {
                    "generated_at": _now(),
                    "db": str(db_path),
                    "api_key_present": key_present,
                    "model_configured": bool(args.model),
                    "base_url_configured": bool(args.base_url),
                    "shard_index": args.shard_index,
                    "shard_count": args.shard_count,
                    "dry_run": bool(args.dry_run),
                    "blocked_reason": (
                        "missing_api_key_or_model_or_base_url"
                        if not (key_present and args.model and args.base_url)
                        else ("dry_run_requested" if args.dry_run else "")
                    ),
                }
            )
            if args.summary_out:
                args.summary_out.parent.mkdir(parents=True, exist_ok=True)
                args.summary_out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({k: plan[k] for k in ("dish_count", "batch_count", "max_calls_with_retries", "blocked_reason")}, ensure_ascii=False))
            return

        if args.budget_usd is None:
            raise SystemExit("未提供 --budget-usd，拒绝发起付费调用")
        if args.input_usd_per_m is None or args.output_usd_per_m is None:
            raise SystemExit("未提供输入/输出每百万 token 单价，无法执行硬预算熔断")
        tracker = BudgetTracker(args.budget_usd, args.input_usd_per_m, args.output_usd_per_m)
        batches = [items[index : index + BATCH_SIZE] for index in range(0, len(items), BATCH_SIZE)]
        if args.max_calls and len(batches) > args.max_calls:
            batches = batches[: args.max_calls]

        ledger_path = args.ledger or (db_path.parent / f"{db_path.stem}_tag_ledger.jsonl")
        failures_path = args.failures or (db_path.parent / f"{db_path.stem}_tag_failures.jsonl")
        success = 0
        failed = 0
        budget_exhausted = False
        for index, batch in enumerate(batches, start=1):
            if tracker.exhausted:
                budget_exhausted = True
                break
            prompt = build_user_prompt(batch)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            validated = None
            last_error = ""
            for attempt in range(1, args.max_retries + 1):
                if tracker.exhausted:
                    budget_exhausted = True
                    last_error = "budget_exhausted"
                    break
                try:
                    content, meta = call_model(args.base_url, api_key, args.model, messages)
                except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
                    last_error = f"transport_error:{type(exc).__name__}"
                    time.sleep(min(2 ** attempt, 8))
                    continue
                call_cost = tracker.add_usage(meta)
                if tracker.exhausted:
                    budget_exhausted = True
                validated, reason = validate_batch(content, batch)
                with open(ledger_path, "a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(
                            {
                                "batch": index,
                                "attempt": attempt,
                                "dish_ids": [row["dish_id"] for row in batch],
                                "prompt_version": PROMPT_VERSION,
                                "prompt_sha256": _sha(prompt),
                                "model": args.model,
                                "response_model": meta.get("model"),
                                "usage": meta.get("usage"),
                                "estimated_cost_usd": round(call_cost, 8),
                                "cumulative_cost_usd": round(tracker.spent_usd, 8),
                                "raw_response": content,
                                "valid": validated is not None,
                                "reason": reason,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                if validated is not None:
                    break
                last_error = reason
                time.sleep(min(2 ** attempt, 8))

            if validated is None and last_error == "budget_exhausted":
                break

            if validated is None:
                failed += len(batch)
                for row in batch:
                    dish = session.get(Dish, row["dish_id"])
                    dish.tagging_status = "FAILED"
                    dish.tagging_error = last_error[:400]
                    dish.llm_meta = {"model": args.model, "prompt_version": PROMPT_VERSION, "batch": index}
                    write_failure(
                        failures_path,
                        {
                            "batch": index,
                            "dish_id": row["dish_id"],
                            "dish_name": row["name"],
                            "reason": last_error,
                            "attempts": args.max_retries,
                        },
                    )
                session.commit()
                continue

            by_id = {row["dish_id"]: row for row in validated}
            for row in batch:
                dish = session.get(Dish, row["dish_id"])
                if dish.tagging_status == "SUCCESS":
                    continue
                result = by_id[row["dish_id"]]
                dish.dish_role = result["dish_role"]
                dish.feature_vector = result["feature_vector"]
                dish.allergen_tags = result["allergen_tags"]
                dish.tagging_status = "SUCCESS"
                dish.tagging_error = None
                dish.llm_meta = {
                    "model": args.model,
                    "prompt_version": PROMPT_VERSION,
                    "batch": index,
                }
                success += 1
            session.commit()

        summary = {
            "generated_at": _now(),
            "db": str(db_path),
            "model": args.model,
            "prompt_version": PROMPT_VERSION,
            "batch_size": BATCH_SIZE,
            "shard_index": args.shard_index,
            "shard_count": args.shard_count,
            "batches": len(batches),
            "success": success,
            "failed": failed,
            "ledger": str(ledger_path),
            "failures": str(failures_path),
            "budget_usd": args.budget_usd,
            "budget_exhausted": budget_exhausted,
            "spent_usd": round(tracker.spent_usd, 8),
            "api_calls": tracker.calls,
            "input_tokens": tracker.input_tokens,
            "output_tokens": tracker.output_tokens,
            "input_usd_per_m": args.input_usd_per_m,
            "output_usd_per_m": args.output_usd_per_m,
        }
        if args.summary_out:
            args.summary_out.parent.mkdir(parents=True, exist_ok=True)
            args.summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False))
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
