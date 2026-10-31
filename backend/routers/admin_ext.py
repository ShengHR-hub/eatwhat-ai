"""管理后台扩展接口：用户管理 / 算法参数 / 打标队列 / 数据导入。

单独成文件而不是继续堆 admin.py：admin.py 已经承担 CRUD 与统计，
再塞四组互不相关的接口会很难读。这里只挂同一套 require_admin 鉴权。
"""
import csv
import io
import json
import os
import threading
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..config import DEFAULT_ALGO_PARAMS, current_algo_params, reload_algo_params
from ..database import SessionLocal, get_db
from ..deps import require_admin
from ..models import Dish, DishFeedback, EatingLog, RoomVote, SystemSetting, TaggingJob, User, UserPreference, utcnow
from ..scripts.llm_batch_tagger import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_user_prompt,
    call_model,
    validate_batch,
)

router = APIRouter(prefix="/admin", tags=["管理后台·扩展"], dependencies=[Depends(require_admin)])

ALGO_KEY = "algo_params"
ALGO_FIELDS = {
    "lambda_decay": "防腻衰减 λ",
    "omega_group": "群组混合权重 ω",
    "alpha_taste": "口味权重 α",
    "beta_weather": "天气权重 β",
    "gamma_budget": "预算权重 γ",
    "delta_status": "状态权重 δ",
}


# ══════════════════════════════════════════════════════════
# 1. 用户管理
# ══════════════════════════════════════════════════════════
@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None, max_length=64),
    role: Optional[str] = Query(None, max_length=16),
    db: Session = Depends(get_db),
):
    """用户列表：把「移动端注册了谁、各自多少数据」在后台显性化。

    流水与投票用子查询计数，避免逐个用户再查一次（N+1）。
    """
    query = db.query(User)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter((User.nickname.like(pattern)) | (User.username.like(pattern)))
    if role:
        query = query.filter(User.role == role.upper())

    total = query.count()
    rows = (
        query.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    ids = [row.id for row in rows]
    logs = dict(
        db.query(EatingLog.user_id, func.count(EatingLog.id))
        .filter(EatingLog.user_id.in_(ids))
        .group_by(EatingLog.user_id)
        .all()
    ) if ids else {}
    votes = dict(
        db.query(RoomVote.user_id, func.count(RoomVote.id))
        .filter(RoomVote.user_id.in_(ids))
        .group_by(RoomVote.user_id)
        .all()
    ) if ids else {}

    return {
        "total": total,
        "items": [
            {
                "user_id": row.id,
                "username": row.username,
                "nickname": row.nickname,
                "avatar": row.avatar or "",
                "role": row.role or "USER",
                "is_demo_persona": bool(row.is_demo_persona),
                "logs": int(logs.get(row.id, 0)),
                "votes": int(votes.get(row.id, 0)),
                "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
            }
            for row in rows
        ],
    }


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    role = str(payload.get("role", "")).upper()
    if role not in {"USER", "ADMIN"}:
        raise HTTPException(422, "角色只能是 USER 或 ADMIN")
    if user_id == admin_id and role != "ADMIN":
        raise HTTPException(409, "不能取消自己的管理员权限")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")

    before = user.role or "USER"
    user.role = role
    db.commit()
    record_audit(
        db,
        user_id=admin_id,
        action="user.update_role",
        resource_type="user",
        resource_id=user_id,
        summary=f"{user.nickname} 角色 {before} → {role}",
        detail={"before": before, "after": role},
        request=request,
    )
    return {"user_id": user_id, "role": role}


# ══════════════════════════════════════════════════════════
# 2. 算法参数
# ══════════════════════════════════════════════════════════
@router.get("/settings/algo")
def get_algo_settings(db: Session = Depends(get_db)):
    row = db.get(SystemSetting, ALGO_KEY)
    stored = row.value if row and isinstance(row.value, dict) else {}
    return {
        "current": current_algo_params(),
        "defaults": dict(DEFAULT_ALGO_PARAMS),
        "overridden": bool(stored),
        "fields": [{"key": key, "label": label} for key, label in ALGO_FIELDS.items()],
    }


@router.put("/settings/algo")
def update_algo_settings(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    """保存算法参数并立即热加载。

    校验范围 0–1：这些是加权系数，越界会让打分公式失去意义。
    """
    clean = {}
    for key, value in payload.items():
        if key not in DEFAULT_ALGO_PARAMS:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise HTTPException(422, f"{key} 必须是数字")
        if not 0 <= number <= 1:
            raise HTTPException(422, f"{key} 必须在 0–1 之间")
        clean[key] = number

    if not clean:
        raise HTTPException(422, "没有可保存的参数")

    before = current_algo_params()
    row = db.get(SystemSetting, ALGO_KEY)
    merged = {**before, **clean}
    # 四个权重必须至少有一个非 0：全 0 会让归一化除零（算法侧已加兜底退化成等权，
    # 但"保存成功却静默失效"比直接拒绝更糟），这里提前挡掉。
    weights = ("alpha_taste", "beta_weather", "gamma_budget", "delta_status")
    if sum(float(merged.get(k) or 0) for k in weights) <= 0:
        raise HTTPException(422, "四个权重不能同时为 0，至少保留一个大于 0")
    if row is None:
        row = SystemSetting(key=ALGO_KEY, value=merged, updated_by=admin_id, updated_at=utcnow())
        db.add(row)
    else:
        row.value = merged
        row.updated_by = admin_id
        row.updated_at = utcnow()
    db.commit()
    reload_algo_params(db)
    record_audit(
        db,
        user_id=admin_id,
        action="settings.update_algo",
        resource_type="setting",
        resource_id=None,
        summary="更新算法参数",
        detail={"before": before, "after": merged},
        request=request,
    )
    return {"current": current_algo_params()}


# ══════════════════════════════════════════════════════════
# 3. 打标任务队列
# ══════════════════════════════════════════════════════════
def _job_dict(row: TaggingJob) -> dict:
    return {
        "id": row.id,
        "status": row.status,
        "total": row.total,
        "done": row.done,
        "failed": row.failed,
        "message": row.message or "",
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
    }


def _run_tagging_job(job_id: int) -> None:
    """后台线程执行打标：每批 20 道，逐批更新进度。

    用独立 session：线程里不能复用请求的 session，请求结束就被关掉了。
    """
    db = SessionLocal()
    try:
        job = db.get(TaggingJob, job_id)
        if job is None:
            return
        job.status = "RUNNING"
        db.commit()

        base_url = os.getenv("LLM_BASE_URL", "").strip()
        api_key = os.getenv("LLM_API_KEY", "").strip()
        model = os.getenv("LLM_MODEL", "").strip()
        if not (base_url and api_key and model):
            job.status = "FAILED"
            job.message = "LLM 未配置（需要 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL），未发起调用"
            job.finished_at = utcnow()
            db.commit()
            return

        ids = list(job.dish_ids or [])
        for start in range(0, len(ids), 20):
            batch = ids[start:start + 20]
            rows = db.query(Dish).filter(Dish.id.in_(batch)).all()
            pending = [row for row in rows if row.tagging_status != "SUCCESS"]
            if not pending:
                job.done += len(batch)
                db.commit()
                continue

            items = [
                {
                    "dish_id": row.id,
                    "name": row.name,
                    "cuisine_type": row.cuisine_type or "",
                    "ingredients_main": row.ingredients_main or [],
                    "ingredients_aux": row.ingredients_aux or [],
                }
                for row in pending
            ]
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(items)},
            ]
            error = ""
            validated = None
            meta = {}
            try:
                content, meta = call_model(base_url, api_key, model, messages)
                validated, error = validate_batch(content, items)
            except Exception as exc:  # 网络/解析都可能失败，整批标记失败但不中断队列
                error = f"transport_error:{type(exc).__name__}"

            if validated is None:
                for row in pending:
                    row.tagging_status = "FAILED"
                    row.tagging_error = (error or "unknown_model_error")[:400]
                    row.llm_meta = {"model": model, "prompt_version": PROMPT_VERSION}
                job.failed += len(pending)
            else:
                results = {item["dish_id"]: item for item in validated}
                for row in pending:
                    result = results.get(row.id)
                    if not result:
                        job.failed += 1
                        continue
                    row.dish_role = result["dish_role"]
                    row.feature_vector = result["feature_vector"]
                    row.allergen_tags = result["allergen_tags"]
                    row.tagging_status = "SUCCESS"
                    row.tagging_error = None
                    row.llm_meta = {"model": meta.get("model") or model, "prompt_version": PROMPT_VERSION}
                job.done += len(pending)
            db.commit()

        job.status = "DONE"
        job.finished_at = utcnow()
        job.message = f"完成 {job.done} 道，失败 {job.failed} 道"
        db.commit()
    except Exception as exc:  # 线程里抛异常没人接，必须自己兜住并落状态
        try:
            job = db.get(TaggingJob, job_id)
            if job:
                job.status = "FAILED"
                job.message = f"{type(exc).__name__}: {exc}"[:240]
                job.finished_at = utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/tag-jobs")
def create_tag_job(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    ids = payload.get("dish_ids") or []
    if not isinstance(ids, list) or not ids:
        raise HTTPException(422, "dish_ids 不能为空")
    try:
        # 非数字 id 以前直接 int() 抛 ValueError → 500
        ids = [int(item) for item in ids][:500]
    except (TypeError, ValueError):
        raise HTTPException(422, "dish_ids 必须全是整数")

    rows = db.query(Dish).filter(Dish.id.in_(ids)).all()
    if not rows:
        raise HTTPException(404, "菜品不存在")

    job = TaggingJob(
        status="PENDING",
        total=len(rows),
        dish_ids=[row.id for row in rows],
        created_by=admin_id,
        created_at=utcnow(),
        message="排队中",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    threading.Thread(target=_run_tagging_job, args=(job.id,), daemon=True).start()
    # 批量打标最多改 500 道菜的 feature_vector，此前完全没有审计记录。
    record_audit(
        db,
        user_id=admin_id,
        action="dish.llm_tag_job",
        resource_type="dish",
        resource_id=None,
        summary=f"创建打标任务 #{job.id}（{job.total} 道）",
        detail={"job_id": job.id, "dish_ids": [row.id for row in rows][:50], "total": job.total},
        request=request,
    )
    return _job_dict(job)


@router.get("/tag-jobs")
def list_tag_jobs(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    rows = db.query(TaggingJob).order_by(TaggingJob.id.desc()).limit(limit).all()
    return {"items": [_job_dict(row) for row in rows]}


@router.get("/tag-jobs/{job_id}")
def get_tag_job(job_id: int, db: Session = Depends(get_db)):
    row = db.get(TaggingJob, job_id)
    if row is None:
        raise HTTPException(404, "任务不存在")
    return _job_dict(row)


# ══════════════════════════════════════════════════════════
# 4. 数据导入
# ══════════════════════════════════════════════════════════
# 与 algorithms/combo_optimizer.ROLES 保持一致：套餐只在 MEAT/VEG/SOUP 里分桶。
_DISH_ROLES = ("MEAT", "VEG", "SOUP", "ONE_MEAL")

IMPORT_FIELDS = [
    {"key": "name", "label": "名称", "required": True},
    {"key": "cuisine_type", "label": "菜系", "required": False},
    {"key": "dish_role", "label": "角色", "required": False},
    {"key": "price_or_cost", "label": "价格/成本", "required": False},
    {"key": "ingredients_main", "label": "主料（逗号分隔）", "required": False},
    {"key": "cook_minutes", "label": "做菜分钟", "required": False},
]


def _read_table(filename: str, content: bytes) -> tuple[list[str], list[dict]]:
    """解析 CSV / XLSX 为「表头 + 行字典」。只读，不落库。"""
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook

        book = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = book.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            raise HTTPException(422, "表格是空的")
        header = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
        body = [
            {header[i]: (row[i] if i < len(row) else None) for i in range(len(header))}
            for row in rows[1:]
        ]
        return header, body

    # 中文 Excel 默认导出 GBK；用 errors="replace" 会静默把菜名变成乱码入库。
    text = None
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise HTTPException(422, "无法识别文件编码，请另存为 UTF-8 或 GBK 后重试")

    reader = csv.DictReader(io.StringIO(text))
    header = [item.strip() for item in (reader.fieldnames or [])]
    # 表头 strip 了、行字典的键也必须 strip，否则 mapping 拿到的列名与 row 的键对不上，
    # 表现是"预览正常、提交后 0 条"。
    return header, [
        {(k or "").strip(): v for k, v in row.items() if k is not None}
        for row in reader
    ]


@router.post("/import/preview")
async def preview_import(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(413, "文件超过 8MB")
    header, body = _read_table(file.filename, content)
    if len(body) > 2000:
        raise HTTPException(413, "单次最多导入 2000 行，请拆分文件")
    return {
        "filename": file.filename,
        "columns": header,
        # rows 返回全量：commit 靠它写库，只给前 8 行会导致大文件只导入 8 条
        "rows": body,
        "preview_rows": body[:8],
        "total_rows": len(body),
        "target_fields": IMPORT_FIELDS,
    }


@router.post("/import/commit")
def commit_import(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    """按字段映射写入菜品。

    只写菜品：门店导入涉及校区归属与坐标校验，口径还没定，先不做半成品。
    """
    mapping = payload.get("mapping") or {}
    rows = payload.get("rows") or []
    if not mapping.get("name"):
        raise HTTPException(422, "必须映射「名称」字段")
    if not rows:
        raise HTTPException(422, "没有可导入的行")

    created = 0
    skipped = 0
    errors = []

    def reject(row_no, field, raw, reason):
        """记一条可定位的失败行；errors 以前声明后从未 append，接口等于在撒谎。"""
        errors.append(
            {"row": row_no, "field": field, "value": str(raw)[:40], "reason": reason}
        )

    for index, row in enumerate(rows, start=1):
        name = str(row.get(mapping.get("name"), "") or "").strip()
        if not name:
            reject(index, "name", "", "名称为空")
            skipped += 1
            continue
        if len(name) > 128:
            reject(index, "name", name, "名称超过 128 字符")
            skipped += 1
            continue
        exists = db.query(Dish).filter(Dish.name == name, Dish.deleted_at.is_(None)).first()
        if exists:
            skipped += 1
            continue

        def pick(key):
            source = mapping.get(key)
            return row.get(source) if source else None

        raw_price = pick("price_or_cost")
        price = None
        if raw_price not in (None, ""):
            try:
                price = float(raw_price)
            except (TypeError, ValueError):
                # 以前这里静默写 None，后续预算过滤会把它当免费菜。
                reject(index, "price_or_cost", raw_price, "不是数字")
                skipped += 1
                continue
            if price < 0:
                reject(index, "price_or_cost", raw_price, "价格为负")
                skipped += 1
                continue

        role_raw = str(pick("dish_role") or "").strip().upper()
        if role_raw and role_raw not in _DISH_ROLES:
            # 非法角色进不了套餐分桶，等于导入即隐形。
            reject(index, "dish_role", role_raw, f"角色必须是 {'/'.join(_DISH_ROLES)}")
            skipped += 1
            continue
        # dish_role 是 NOT NULL：没映射角色时给中性值 ONE_MEAL（既不算荤也不算素，
        # 不会进套餐分桶），否则整批 INSERT 直接 IntegrityError。
        dish_role = role_raw or "ONE_MEAL"

        cook_raw = pick("cook_minutes")
        cook_minutes = 15
        if cook_raw not in (None, ""):
            try:
                cook_minutes = int(float(cook_raw))
                if cook_minutes <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                reject(index, "cook_minutes", cook_raw, "做菜分钟必须是正整数，已按 15 处理")
                cook_minutes = 15

        main = pick("ingredients_main")
        if isinstance(main, str):
            main = [item.strip() for item in main.replace("，", ",").split(",") if item.strip()]
        elif not isinstance(main, list):
            main = []

        dish = Dish(
            name=name,
            mode_type="HOME_COOKING",
            cuisine_type=(str(pick("cuisine_type")).strip() if pick("cuisine_type") else None),
            dish_role=dish_role,
            price_or_cost=price,
            cook_minutes=cook_minutes,
            ingredients_main=main,
            ingredients_aux=[],
            appliance_tag=["炒锅"],
            tagging_status="PENDING",
            is_synthetic=1,
            source_dataset="admin_import",
            data_version="import-v1",
        )
        db.add(dish)
        created += 1

    if created:
        db.commit()
    record_audit(
        db,
        user_id=admin_id,
        action="dish.import",
        resource_type="dish",
        resource_id=None,
        summary=f"导入菜品 新增 {created} 条，跳过 {skipped} 条，失败 {len(errors)} 条",
        detail={"created": created, "skipped": skipped, "errors": errors[:5]},
        request=request,
    )
    return {"created": created, "skipped": skipped, "errors": errors[:5]}


@router.get("/users/{user_id}/overview")
def user_overview(user_id: int, db: Session = Depends(get_db)):
    """单个用户的画像：后台此前只能看聚合统计，看不到「这个人喜欢什么」。

    一次返回偏好向量、预算、菜系分布、满意度分布与最近决策，
    避免前端为一张画像页连打五六个接口。
    """
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")

    prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    logs = (
        db.query(EatingLog)
        .filter(EatingLog.user_id == user_id)
        .order_by(EatingLog.eaten_at.desc())
        .limit(50)
        .all()
    )
    log_ids = [row.id for row in logs]

    # 菜系分布：按流水关联的菜品统计
    cuisine_rows = (
        db.query(Dish.cuisine_type, func.count(EatingLog.id))
        .join(EatingLog, EatingLog.dish_id == Dish.id)
        .filter(EatingLog.user_id == user_id)
        .group_by(Dish.cuisine_type)
        .order_by(func.count(EatingLog.id).desc())
        .limit(6)
        .all()
    )

    ratings = dict(
        db.query(DishFeedback.log_id, DishFeedback.rating)
        .filter(DishFeedback.log_id.in_(log_ids))
        .all()
    ) if log_ids else {}
    rating_dist = {3: 0, 2: 0, 1: 0}
    for value in ratings.values():
        if value in rating_dist:
            rating_dist[value] += 1

    dish_names = dict(
        db.query(Dish.id, Dish.name).filter(Dish.id.in_({row.dish_id for row in logs})).all()
    ) if logs else {}

    total_expense = sum(float(row.cost_amount or 0) for row in logs)

    return {
        "user": {
            "user_id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "avatar": user.avatar or "",
            "role": user.role or "USER",
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "preference": {
            "base_vector": (prefs.base_vector if prefs else {}) or {},
            "default_budget": float(prefs.default_budget) if prefs else 0.0,
            "veto_tags": list(prefs.veto_tags or []) if prefs else [],
            "preferred_cuisines": list(prefs.preferred_cuisines or []) if prefs else [],
            "favorite_count": len(prefs.favorite_dish_ids or []) if prefs else 0,
            "blacklist_count": len(prefs.blacklist_dish_ids or []) if prefs else 0,
        },
        "summary": {
            "logs_total": len(logs),
            "total_expense": round(total_expense, 1),
            "avg_cost": round(total_expense / len(logs), 1) if logs else 0.0,
            "rated_count": sum(rating_dist.values()),
            "avg_rating": round(
                sum(k * v for k, v in rating_dist.items()) / max(1, sum(rating_dist.values())), 2
            ) if sum(rating_dist.values()) else 0.0,
        },
        "cuisine_top": [{"name": name or "未标注", "count": count} for name, count in cuisine_rows],
        "rating_dist": [
            {"rating": 3, "label": "好吃", "count": rating_dist[3]},
            {"rating": 2, "label": "一般", "count": rating_dist[2]},
            {"rating": 1, "label": "踩雷", "count": rating_dist[1]},
        ],
        "recent_logs": [
            {
                "log_id": row.id,
                "dish_id": row.dish_id,
                "dish_name": dish_names.get(row.dish_id, "已删除菜品"),
                "mode_type": row.mode_type,
                "cost_amount": float(row.cost_amount or 0),
                "eaten_at": row.eaten_at.isoformat() if row.eaten_at else None,
                "rating": int(ratings.get(row.id, 0)),
            }
            for row in logs[:12]
        ],
    }
