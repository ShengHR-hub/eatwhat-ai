"""管理员角色开关。

管理后台接口只认 ADMIN 角色 + 真实登录 token，所以第一个管理员必须先手工授予。
这是有意为之：如果注册接口能选角色，等于谁都能把自己设成管理员。

    # 看现状
    python -m backend.scripts.grant_admin --list

    # 授予（账号必须已存在，且已注册过密码）
    python -m backend.scripts.grant_admin --username testuser

    # 收回
    python -m backend.scripts.grant_admin --username testuser --revoke
"""

from __future__ import annotations

import argparse
import sys

from ..database import SessionLocal
from ..models import AuthCredential, User

ADMIN_ROLE = "ADMIN"
USER_ROLE = "USER"


def _list(db) -> int:
    rows = db.query(User).order_by(User.id).all()
    if not rows:
        print("（没有任何用户）")
        return 0
    print(f"{'id':>4}  {'username':<20} {'nickname':<16} {'role':<8} 密码")
    for row in rows:
        has_pwd = (
            db.query(AuthCredential).filter(AuthCredential.user_id == row.id).first()
            is not None
        )
        print(
            f"{row.id:>4}  {row.username:<20} {row.nickname:<16} "
            f"{(row.role or USER_ROLE):<8} {'已设' if has_pwd else '未设'}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="授予/收回管理员角色")
    parser.add_argument("--username", help="目标账号用户名")
    parser.add_argument("--revoke", action="store_true", help="收回管理员角色")
    parser.add_argument("--list", action="store_true", help="列出所有用户与角色")
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        if args.list:
            return _list(db)

        if not args.username:
            print("[x] 需要 --username，或用 --list 查看现有账号", file=sys.stderr)
            return 2

        user = db.query(User).filter(User.username == args.username).first()
        if user is None:
            print(f"[x] 用户 {args.username!r} 不存在", file=sys.stderr)
            return 1

        credential = (
            db.query(AuthCredential).filter(AuthCredential.user_id == user.id).first()
        )
        if credential is None and not args.revoke:
            print(
                f"[x] {args.username} 还没注册密码，先在前端注册一次再授权"
                "（否则拿不到 token，给了管理员也进不去）",
                file=sys.stderr,
            )
            return 1

        target = USER_ROLE if args.revoke else ADMIN_ROLE
        if (user.role or USER_ROLE) == target:
            print(f"[i] {args.username} 已经是 {target}，无需改动")
            return 0

        user.role = target
        db.commit()
        print(f"[✓] {args.username}（id={user.id}）角色：{target}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
