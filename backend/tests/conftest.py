import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import Base, get_db  # noqa: E402
from backend.main import app  # noqa: E402
from backend.scripts.init_seed_data import seed_all  # noqa: E402


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with factory() as session:
        seed_all(session)
        # v2.3.4：外食接口要求校区；测试库把种子店标成思源，生产种子仍保持 NULL。
        from backend.models import Restaurant

        session.query(Restaurant).update({Restaurant.campus: "SIYUAN"})
        session.commit()
    yield factory
    engine.dispose()


@pytest.fixture()
def campus_seed(session_factory):
    """S06 测试专用：把内存库里的 20 家种子店标成思源。

    生产种子/演示库保持 campus=NULL；这里只让房间用例具备一个明确校区，
    避免把 fixture 写进种子脚本或演示库。
    """
    from backend.models import Restaurant

    with session_factory() as session:
        session.query(Restaurant).update({Restaurant.campus: "SIYUAN"})
        session.commit()
    return "SIYUAN"


@pytest.fixture()
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def admin_client(session_factory):
    """带管理员 Bearer token 的客户端。

    §30 给管理接口加了鉴权（只认 Bearer + role=ADMIN，不认 X-User-Id），
    但 test_admin / test_admin_stats 仍用裸 client，导致整批 401。
    这里建一个 ADMIN 用户并签发真实 token，测试走与生产一致的鉴权链路。
    """
    from backend.models import AuthCredential, User
    from backend.routers.auth_local import _hash_password, _issue_token

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    with session_factory() as session:
        admin = session.query(User).filter(User.role == "ADMIN").first()
        if admin is None:
            admin = User(username="admin_fixture", nickname="测试管理员", role="ADMIN", is_demo_persona=False)
            session.add(admin)
            session.flush()
            session.add(AuthCredential(user_id=admin.id, password_hash=_hash_password("admin123")))
            session.commit()
        token = _issue_token(session, admin.id)

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app, headers={"Authorization": f"Bearer {token}"})
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def user_client(session_factory):
    """带普通用户（role=USER）Bearer token 的客户端。

    admin_client 只覆盖了「合法管理员」这一条路，鉴权负例（普通用户越权、
    无令牌访问）此前完全没有用例——require_admin 被误删也不会变红。
    """
    from backend.models import AuthCredential, User
    from backend.routers.auth_local import _hash_password, _issue_token

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    with session_factory() as session:
        user = session.query(User).filter(User.role == "USER").first()
        if user is None:
            user = User(username="plain_fixture", nickname="普通用户", role="USER", is_demo_persona=False)
            session.add(user)
            session.flush()
            session.add(AuthCredential(user_id=user.id, password_hash=_hash_password("user1234")))
            session.commit()
        token = _issue_token(session, user.id)

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app, headers={"Authorization": f"Bearer {token}"})
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
