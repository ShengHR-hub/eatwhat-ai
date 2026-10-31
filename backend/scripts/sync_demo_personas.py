"""把 init_seed_data 里的 4 个 demo 人设同步到现有库。

只更新 users / user_preferences 的展示字段与偏好，不重建、不删除业务数据。
用法：
    python -m backend.scripts.sync_demo_personas --dry-run
    python -m backend.scripts.sync_demo_personas
"""
from __future__ import annotations

import argparse
import json
from typing import Optional

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Dish, Restaurant, User, UserPreference
from .init_seed_data import PERSONAS


def _dish_ids(session: Session, names: list[str]) -> list[int]:
    ids: list[int] = []
    for name in names:
        row = (
            session.query(Dish.id)
            .filter(Dish.name == name, Dish.deleted_at.is_(None))
            .order_by(Dish.id)
            .first()
        )
        if row is not None:
            ids.append(int(row[0]))
    return ids


def _restaurant_ids(session: Session, names: list[str]) -> list[int]:
    ids: list[int] = []
    for name in names:
        row = (
            session.query(Restaurant.id)
            .filter(Restaurant.name == name, Restaurant.deleted_at.is_(None))
            .order_by(Restaurant.id)
            .first()
        )
        if row is not None:
            ids.append(int(row[0]))
    return ids


def sync_demo_personas(session: Session, *, dry_run: bool = False) -> list[dict]:
    updated = []
    for persona in PERSONAS:
        user = (
            session.query(User)
            .filter(
                User.username == persona["username"],
                User.is_demo_persona.is_(True),
            )
            .first()
        )
        if user is None:
            updated.append({"username": persona["username"], "status": "missing"})
            continue
        prefs = (
            session.query(UserPreference)
            .filter(UserPreference.user_id == user.id)
            .first()
        )
        if prefs is None:
            updated.append({"username": persona["username"], "status": "no_preferences"})
            continue

        user.nickname = persona["nickname"]
        user.avatar = persona["avatar"]
        user.persona_title = persona["persona_title"]
        prefs.base_vector = dict(persona["vector"])
        prefs.default_budget = float(persona["budget"])
        prefs.veto_tags = list(persona["veto"])
        prefs.preferred_cuisines = list(persona["cuisines"])
        prefs.favorite_dish_ids = _dish_ids(session, list(persona["favorite"]))
        prefs.blacklist_dish_ids = _dish_ids(session, list(persona["blacklist"]))
        prefs.blacklist_restaurant_ids = _restaurant_ids(
            session, list(persona.get("blacklist_restaurants") or [])
        )
        updated.append(
            {
                "username": persona["username"],
                "nickname": persona["nickname"],
                "status": "updated",
            }
        )

    if dry_run:
        session.rollback()
    else:
        session.commit()
    return updated


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="同步 demo 人设到现有库")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    session = SessionLocal()
    try:
        result = sync_demo_personas(session, dry_run=args.dry_run)
    finally:
        session.close()
    print(json.dumps({"dry_run": args.dry_run, "items": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
