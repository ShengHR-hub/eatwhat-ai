"""S10 真实高德 POI 与按校区合成食堂导入。

真实 POI 只读取 S09/r04 封存的 JSONL，不重新联网、不合成补足、不跨校区挪用。
食堂窗口为确定性合成数据，显式 `is_synthetic=1`，与真实 POI 分开计数。

示例：
  python -m backend.scripts.fetch_amap_poi pois --db backend/eatwhat_batch4.db \
      --campus SIYUAN --limit 30 --batch-id s10-sample
  python -m backend.scripts.fetch_amap_poi canteens --db backend/eatwhat_batch4.db \
      --campus SIYUAN --batch-id s10-sample
"""

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from backend.models import Restaurant
from backend.scripts.s10_common import (
    AMAP_DATASET,
    AMAP_DATA_VERSION,
    CAMPUS_CENTERS,
    CAMPUS_INPUTS,
    CAMPUS_NAMES,
    CANTEEN_ANCHORS,
    CANTEEN_BASE_NAMES,
    CANTEEN_DATASET,
    CANTEEN_DATA_VERSION,
    CAOTANG,
    DEFAULT_DB,
    SCRIPT_VERSION,
    ensure_import_db,
    haversine_m,
    load_jsonl,
    make_session,
    sha256_file,
    utc_now_iso,
    write_json,
    write_reject,
)


class RejectError(ValueError):
    def __init__(self, reason: str, retryable: bool = False):
        super().__init__(reason)
        self.reason = reason
        self.retryable = retryable


def _number_or_none(value, field: str, low: float, high: float):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise RejectError(f"{field}_not_number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RejectError(f"{field}_not_number") from exc
    if not math.isfinite(number) or not low <= number <= high:
        raise RejectError(f"{field}_out_of_range")
    return number


def validate_poi(row: dict, campus: str) -> dict:
    if "__parse_error__" in row:
        raise RejectError("json_parse_error")
    source_id = str(row.get("id") or "").strip()
    if not source_id:
        raise RejectError("missing_poi_id")
    name = str(row.get("name") or "").strip()
    if not name:
        raise RejectError("missing_name")
    if len(name) > 128:
        raise RejectError("name_too_long")
    typecode = str(row.get("typecode") or "")
    if not typecode.startswith("05"):
        raise RejectError("non_food_typecode")
    if row.get("campus") != campus:
        raise RejectError("campus_mismatch")
    if row.get("is_synthetic") != 0:
        raise RejectError("synthetic_flag_not_zero")
    dataset = row.get("source_dataset") or AMAP_DATASET
    if dataset != AMAP_DATASET:
        raise RejectError("source_dataset_mismatch")

    location = str(row.get("location") or "")
    try:
        lon_text, lat_text = location.split(",")
        lon, lat = float(lon_text), float(lat_text)
    except (ValueError, AttributeError) as exc:
        raise RejectError("bad_location") from exc
    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise RejectError("bad_location")
    if not (73.0 <= lon <= 136.0 and 3.0 <= lat <= 54.0):
        raise RejectError("location_out_of_china_bounds")
    center = CAMPUS_CENTERS[campus]
    distance = haversine_m((lon, lat), center)
    if distance > 3000.5:
        raise RejectError("outside_3km")
    if row.get("_distance_m") is not None:
        try:
            claimed = float(row["_distance_m"])
        except (TypeError, ValueError) as exc:
            raise RejectError("bad_distance_m") from exc
        if not math.isfinite(claimed) or abs(claimed - distance) > 1.0:
            raise RejectError("distance_mismatch")

    rating = _number_or_none(row.get("rating"), "rating", 0.0, 5.0)
    cost = _number_or_none(row.get("cost"), "cost", 0.0, 100000.0)
    raw_type = str(row.get("type") or "")
    category = raw_type.split(";")[-1].strip() if raw_type else ""
    return {
        "name": name,
        "source_type": "AMAP_POI",
        "category": category[:64],
        "avg_price": cost,
        "rating": rating,
        "longitude": round(lon, 6),
        "latitude": round(lat, 6),
        "distance_meters": int(round(distance)),
        "address": str(row.get("address") or "")[:255],
        "source_dataset": dataset,
        "source_record_id": source_id,
        "source_url": None,
        "data_version": AMAP_DATA_VERSION,
        "is_synthetic": 0,
        "deleted_at": None,
        "campus": campus,
        "_tag_missing": row.get("tag") in (None, ""),
        "_raw": row,
    }


def _find_existing(db, source_type: str, campus: str, dataset: str, source_id: str):
    return db.execute(
        select(Restaurant.id).where(
            Restaurant.source_type == source_type,
            Restaurant.campus == campus,
            Restaurant.source_dataset == dataset,
            Restaurant.source_record_id == source_id,
        )
    ).scalar_one_or_none()


def _insert(db, payload: dict):
    clean = {key: value for key, value in payload.items() if not key.startswith("_")}
    row = Restaurant(**clean)
    with db.begin_nested():
        db.add(row)
        db.flush()
    return row


def _preflight_campus_file(path: Path) -> None:
    for _, row in load_jsonl(path):
        if row.get("campus") == CAOTANG:
            raise SystemExit("检测到草堂校区数据，按 S10 停止条件中止：出现草堂校区数据")


def import_pois(
    db,
    campus: str,
    input_path: Path,
    batch_id: str,
    limit: int = 0,
    reject_path: Path = None,
    allow_rejects: bool = False,
) -> dict:
    if campus not in CAMPUS_CENTERS:
        raise SystemExit(f"未知校区 {campus}")
    _preflight_campus_file(input_path)

    summary = {
        "kind": "AMAP_POI",
        "campus": campus,
        "batch_id": batch_id,
        "input_file": str(input_path),
        "input_sha256": sha256_file(input_path),
        "input_bytes": input_path.stat().st_size,
        "dataset": AMAP_DATASET,
        "data_version": AMAP_DATA_VERSION,
        "script_version": SCRIPT_VERSION,
        "started_at": utc_now_iso(),
        "scanned": 0,
        "inserted": 0,
        "existing": 0,
        "duplicate_in_input": 0,
        "rejected": 0,
        "failures": 0,
        "by_campus": {},
        "by_source_type": {},
        "missing_fields": {"rating": 0, "cost": 0, "tag": 0},
        "reject_reasons": {},
    }
    seen = set()
    for line_no, raw in load_jsonl(input_path):
        if limit and summary["scanned"] >= limit:
            break
        summary["scanned"] += 1
        try:
            payload = validate_poi(raw, campus)
            source_id = payload["source_record_id"]
            if source_id in seen:
                summary["duplicate_in_input"] += 1
                continue
            seen.add(source_id)
            existing = _find_existing(
                db, "AMAP_POI", campus, AMAP_DATASET, source_id
            )
            if existing is not None:
                summary["existing"] += 1
                continue
            _insert(db, payload)
            summary["inserted"] += 1
            summary["by_campus"][campus] = summary["by_campus"].get(campus, 0) + 1
            summary["by_source_type"]["AMAP_POI"] = (
                summary["by_source_type"].get("AMAP_POI", 0) + 1
            )
            if payload["rating"] is None:
                summary["missing_fields"]["rating"] += 1
            if payload["avg_price"] is None:
                summary["missing_fields"]["cost"] += 1
            if payload["_tag_missing"]:
                summary["missing_fields"]["tag"] += 1
        except RejectError as exc:
            summary["rejected"] += 1
            summary["reject_reasons"][exc.reason] = (
                summary["reject_reasons"].get(exc.reason, 0) + 1
            )
            if reject_path is not None:
                write_reject(
                    reject_path,
                    {
                        "batch_id": batch_id,
                        "kind": "AMAP_POI",
                        "campus": campus,
                        "input_file": str(input_path),
                        "line_no": line_no,
                        "reason": exc.reason,
                        "retryable": exc.retryable,
                        "raw": raw,
                    },
                )
        except Exception as exc:  # noqa: BLE001 - 失败必须落盘，不能静默丢
            # `_insert` 的 savepoint 已回滚，外层事务仍可继续；这里不能 rollback，
            # 否则会丢掉本批次此前已成功插入的行。
            summary["failures"] += 1
            summary["reject_reasons"][f"db_error:{type(exc).__name__}"] = (
                summary["reject_reasons"].get(f"db_error:{type(exc).__name__}", 0) + 1
            )
            if reject_path is not None:
                write_reject(
                    reject_path,
                    {
                        "batch_id": batch_id,
                        "kind": "AMAP_POI",
                        "campus": campus,
                        "input_file": str(input_path),
                        "line_no": line_no,
                        "reason": f"db_error:{type(exc).__name__}",
                        "retryable": True,
                        "raw": raw,
                    },
                )
    db.commit()
    summary["finished_at"] = utc_now_iso()
    summary["ok"] = summary["rejected"] == 0 and summary["failures"] == 0
    return summary


def canteen_rows(campus: str, limit: int = 0):
    if campus not in CAMPUS_CENTERS:
        raise SystemExit(f"未知校区 {campus}")
    center = CAMPUS_CENTERS[campus]
    index = 0
    for building in range(4):
        anchor = CANTEEN_ANCHORS[campus][building]
        distance = int(round(haversine_m(anchor, center)))
        for floor in range(1, 6):
            for window in range(1, 11):
                index += 1
                if limit and index > limit:
                    return
                yield {
                    "name": (
                        f"{CANTEEN_BASE_NAMES[campus][building]}·"
                        f"{floor}F·{window:02d}号窗口"
                    ),
                    "source_type": "CANTEEN",
                    "category": "校园食堂",
                    "avg_price": None,
                    "rating": None,
                    "longitude": anchor[0],
                    "latitude": anchor[1],
                    "distance_meters": distance,
                    "address": f"{CAMPUS_NAMES[campus]}校内合成食堂窗口（演示占位，非真实采集）",
                    "source_dataset": CANTEEN_DATASET,
                    "source_record_id": f"canteen-{index:03d}",
                    "source_url": None,
                    "data_version": CANTEEN_DATA_VERSION,
                    "is_synthetic": 1,
                    "deleted_at": None,
                    "campus": campus,
                }


def import_canteens(
    db,
    campus: str,
    batch_id: str,
    limit: int = 0,
    reject_path: Path = None,
) -> dict:
    real_pois = db.execute(
        select(Restaurant.longitude, Restaurant.latitude).where(
            Restaurant.campus == campus,
            Restaurant.source_type == "AMAP_POI",
            Restaurant.is_synthetic == 0,
            Restaurant.longitude.is_not(None),
            Restaurant.latitude.is_not(None),
        )
    ).all()
    if not real_pois:
        raise SystemExit("导入合成食堂前必须先导入该校区真实 POI（用于锚点距离校验）")
    for anchor in CANTEEN_ANCHORS[campus]:
        nearest = min(
            haversine_m(anchor, (row.longitude, row.latitude)) for row in real_pois
        )
        if nearest < 100.0:
            raise SystemExit(
                f"{campus} 合成食堂锚点 {anchor} 距真实 POI {nearest:.1f}m < 100m，拒绝导入"
            )

    summary = {
        "kind": "CANTEEN",
        "campus": campus,
        "batch_id": batch_id,
        "dataset": CANTEEN_DATASET,
        "data_version": CANTEEN_DATA_VERSION,
        "script_version": SCRIPT_VERSION,
        "started_at": utc_now_iso(),
        "planned": limit or 200,
        "scanned": 0,
        "inserted": 0,
        "existing": 0,
        "duplicate_in_input": 0,
        "rejected": 0,
        "failures": 0,
        "by_campus": {},
        "by_source_type": {},
        "anchor_min_distance_to_real_poi_m": {
            f"{lon:.6f},{lat:.6f}": round(
                min(
                    haversine_m((lon, lat), (row.longitude, row.latitude))
                    for row in real_pois
                ),
                3,
            )
            for lon, lat in CANTEEN_ANCHORS[campus]
        },
        "reject_reasons": {},
    }
    seen = set()
    for payload in canteen_rows(campus, limit):
        summary["scanned"] += 1
        source_id = payload["source_record_id"]
        if source_id in seen:
            summary["duplicate_in_input"] += 1
            continue
        seen.add(source_id)
        if _find_existing(db, "CANTEEN", campus, CANTEEN_DATASET, source_id):
            summary["existing"] += 1
            continue
        try:
            _insert(db, payload)
            summary["inserted"] += 1
            summary["by_campus"][campus] = summary["by_campus"].get(campus, 0) + 1
            summary["by_source_type"]["CANTEEN"] = (
                summary["by_source_type"].get("CANTEEN", 0) + 1
            )
        except Exception as exc:  # noqa: BLE001
            # savepoint 已回滚；保留外层已成功行。
            summary["failures"] += 1
            summary["reject_reasons"][f"db_error:{type(exc).__name__}"] = (
                summary["reject_reasons"].get(f"db_error:{type(exc).__name__}", 0) + 1
            )
            if reject_path is not None:
                write_reject(
                    reject_path,
                    {
                        "batch_id": batch_id,
                        "kind": "CANTEEN",
                        "campus": campus,
                        "reason": f"db_error:{type(exc).__name__}",
                        "retryable": True,
                        "raw": payload,
                    },
                )
    db.commit()
    summary["finished_at"] = utc_now_iso()
    summary["ok"] = summary["rejected"] == 0 and summary["failures"] == 0
    return summary


def import_rejects(db, reject_path: Path, batch_id: str, retry_log: Path) -> dict:
    summary = {
        "kind": "RETRY",
        "batch_id": batch_id,
        "source_rejects": str(reject_path),
        "scanned": 0,
        "imported": 0,
        "rejected_again": 0,
        "reasons": {},
        "started_at": utc_now_iso(),
    }
    remaining = []
    for _, record in load_jsonl(reject_path):
        summary["scanned"] += 1
        kind = record.get("kind")
        campus = record.get("campus")
        raw = record.get("raw")
        try:
            if kind == "AMAP_POI":
                payload = validate_poi(raw, campus)
                existing = _find_existing(
                    db, "AMAP_POI", campus, AMAP_DATASET, payload["source_record_id"]
                )
            elif kind == "CANTEEN":
                payload = dict(raw)
                existing = _find_existing(
                    db, "CANTEEN", campus, CANTEEN_DATASET, payload["source_record_id"]
                )
            else:
                raise RejectError("unknown_reject_kind")
            if existing is None:
                _insert(db, payload)
                summary["imported"] += 1
            else:
                summary["imported"] += 1
        except RejectError as exc:
            summary["rejected_again"] += 1
            summary["reasons"][exc.reason] = summary["reasons"].get(exc.reason, 0) + 1
            remaining.append({**record, "reason": exc.reason})
        except Exception as exc:  # noqa: BLE001
            # savepoint 已回滚；保留外层已成功行。
            summary["rejected_again"] += 1
            reason = f"db_error:{type(exc).__name__}"
            summary["reasons"][reason] = summary["reasons"].get(reason, 0) + 1
            remaining.append({**record, "reason": reason})
    db.commit()
    if retry_log.exists():
        retry_log.unlink()
    for record in remaining:
        write_reject(retry_log, record)
    summary["finished_at"] = utc_now_iso()
    summary["remaining"] = len(remaining)
    summary["ok"] = len(remaining) == 0
    return summary


def _db_sha(path: Path) -> str:
    return sha256_file(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="S10 真实 POI / 合成食堂导入")
    sub = parser.add_subparsers(dest="mode", required=True)

    for name in ("pois", "canteens", "retry"):
        item = sub.add_parser(name)
        item.add_argument("--db", type=Path, default=DEFAULT_DB)
        item.add_argument("--batch-id", default="")
        item.add_argument("--summary-out", type=Path, default=None)
        item.add_argument("--reject-out", type=Path, default=None)
        if name in ("pois", "canteens"):
            item.add_argument("--campus", required=True)
            item.add_argument("--limit", type=int, default=0)
        if name == "pois":
            item.add_argument("--input", type=Path, default=None)
            item.add_argument("--allow-rejects", action="store_true")
        if name == "retry":
            item.add_argument("--rejects", type=Path, required=True)
            item.add_argument("--retry-log", type=Path, required=True)

    args = parser.parse_args()
    db_path = ensure_import_db(args.db)
    batch_id = args.batch_id or f"s10-{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    db_sha_before = _db_sha(db_path) if db_path.exists() else None
    engine, Session = make_session(db_path)
    db = Session()
    try:
        if args.mode == "pois":
            input_path = args.input or CAMPUS_INPUTS[args.campus]
            summary = import_pois(
                db,
                args.campus,
                Path(input_path),
                batch_id,
                limit=args.limit,
                reject_path=args.reject_out,
                allow_rejects=args.allow_rejects,
            )
        elif args.mode == "canteens":
            summary = import_canteens(
                db,
                args.campus,
                batch_id,
                limit=args.limit,
                reject_path=args.reject_out,
            )
        else:
            summary = import_rejects(db, args.rejects, batch_id, args.retry_log)
    finally:
        db.close()
        engine.dispose()

    summary["db"] = str(db_path)
    summary["db_sha256_before"] = db_sha_before
    summary["db_sha256_after"] = _db_sha(db_path)
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.summary_out:
        write_json(args.summary_out, summary)
    print(text)
    if args.mode != "retry" and not summary["ok"] and not getattr(args, "allow_rejects", False):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
