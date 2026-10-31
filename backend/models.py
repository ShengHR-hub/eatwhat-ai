from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)



class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    nickname = Column(String(64), nullable=False)
    avatar = Column(String(255), default="")
    persona_title = Column(String(128), default="")
    is_demo_persona = Column(Boolean, default=True, nullable=False)
    # 角色：USER / ADMIN。管理后台接口只认 ADMIN，普通用户即使登录了也是 403。
    # server_default 是为了让已有行在迁移时直接拿到 USER，不需要逐行回填。
    role = Column(
        String(16), nullable=False, default="USER", server_default="USER", index=True
    )
    created_at = Column(DateTime, default=utcnow, nullable=False)


class AuthCredential(Base):
    __tablename__ = "auth_credentials"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    base_vector = Column(JSON, nullable=False, default=dict)
    default_budget = Column(Float, default=25.0, nullable=False)
    veto_tags = Column(JSON, nullable=False, default=list)
    preferred_cuisines = Column(JSON, nullable=False, default=list)
    favorite_dish_ids = Column(JSON, nullable=False, default=list)
    blacklist_dish_ids = Column(JSON, nullable=False, default=list)
    # 黑榜门店：外食模式下该门店全部菜品一并剔除（v2.3.1 新增）
    blacklist_restaurant_ids = Column(JSON, nullable=False, default=list)


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    source_type = Column(String(32), nullable=False)
    category = Column(String(64), default="")
    # v2.3.3：缺失保持 NULL，不填 0/4.5/500 伪默认
    avg_price = Column(Float, nullable=True, default=None)
    rating = Column(Float, nullable=True, default=None)
    longitude = Column(Float)
    latitude = Column(Float)
    distance_meters = Column(Integer, nullable=True, default=None)
    address = Column(String(255), default="")
    # v2.3.3/v2.3.4 来源追溯与校区（全部可空；导入时显式填写）
    source_dataset = Column(String(64), nullable=True)
    source_record_id = Column(String(64), nullable=True)
    source_url = Column(String(255), nullable=True)
    data_version = Column(String(64), nullable=True)
    is_synthetic = Column(Boolean, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    campus = Column(String(32), nullable=True)


class Dish(Base):
    __tablename__ = "dishes_and_recipes"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    mode_type = Column(String(16), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True)
    cuisine_type = Column(String(64), default="", index=True)
    dish_role = Column(String(16), nullable=False)
    price_or_cost = Column(Float, nullable=True, default=None)
    cook_minutes = Column(Integer, default=15)
    # JSON 数组，元素取值：炒锅 / 电饭煲 / 空气炸锅 / 免开火凉拌 / 一锅出
    appliance_tag = Column(JSON, nullable=False, default=lambda: ["炒锅"])
    ingredients_main = Column(JSON, nullable=False, default=list)
    ingredients_aux = Column(JSON, nullable=False, default=list)
    recipe_steps = Column(Text, default="")
    # v2.3.3：允许 NULL 表示未打标/失败；成功记录仍须完整 8 键
    # none_as_null=True 确保 SQL NULL，而不是 JSON 文本 'null'
    feature_vector = Column(JSON(none_as_null=True), nullable=True, default=None)
    image_url = Column(String(255), default="")
    # v2.3.3 来源、打标与软删除（全部可空）
    allergen_tags = Column(JSON(none_as_null=True), nullable=True)
    tagging_status = Column(String(16), nullable=True)
    tagging_error = Column(Text, nullable=True)
    llm_meta = Column(JSON(none_as_null=True), nullable=True)
    source_dataset = Column(String(64), nullable=True)
    source_record_id = Column(String(64), nullable=True)
    source_url = Column(String(255), nullable=True)
    data_version = Column(String(64), nullable=True)
    is_synthetic = Column(Boolean, nullable=True)
    deleted_at = Column(DateTime, nullable=True)


class FridgeInventory(Base):
    __tablename__ = "fridge_inventory"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ingredient_name = Column(String(64), nullable=False)
    category = Column(String(32), nullable=False)
    quantity_desc = Column(String(32), default="适量")
    expire_days = Column(Integer, default=3)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class EatingLog(Base):
    __tablename__ = "eating_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    dish_id = Column(Integer, ForeignKey("dishes_and_recipes.id"), nullable=False)
    mode_type = Column(String(16), nullable=False)
    cost_amount = Column(Float, default=0.0)
    weather_snapshot = Column(String(64), default="")
    status_bubbles = Column(JSON, nullable=False, default=list)
    eaten_at = Column(DateTime, default=utcnow, nullable=False, index=True)


class GroupRoom(Base):
    __tablename__ = "group_rooms"

    id = Column(Integer, primary_key=True)
    room_code = Column(String(10), unique=True, nullable=False, index=True)
    host_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mode_type = Column(String(16), nullable=False)
    status = Column(String(16), default="WAITING", nullable=False)
    member_user_ids = Column(JSON, nullable=False, default=list)
    candidate_dish_ids = Column(JSON, nullable=False, default=list)
    winner_dish_id = Column(Integer, nullable=True)
    consensus_report = Column(JSON, nullable=True)
    # —— v2.3.2 契约对齐（审查 F03/F05/F11）——
    # budget：建房时写入的预算上限，初筛与群组结算都用它
    budget = Column(Float, nullable=True)
    # algo_params：建房那一刻的算法参数快照（含沙盒 override）。
    # 房间 15 秒内可能跨多次请求，只有快照才能保证"开团时的参数"与"结算时的参数"一致。
    algo_params = Column(JSON, nullable=True)
    # deadline_at：15 秒倒计时的**服务端**截止时间。落库而不是只放在内存，
    # 这样"最后一个人断开""服务重启""刷新页面"都不会让这一局永远停在 SWIPING。
    deadline_at = Column(DateTime, nullable=True)
    # settled_at：结算时间。非空表示已经结算过，结算必须幂等（F03）
    settled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    # v2.3.4：建房写入；join 必须同校区，跨校区禁止拼桌
    campus = Column(String(32), nullable=True)


class RoomVote(Base):
    __tablename__ = "room_votes"
    # v2.3.6：同一成员对同一菜品只允许一行；重复投票更新该行。
    __table_args__ = (
        UniqueConstraint(
            "room_code",
            "user_id",
            "dish_id",
            name="uq_room_votes_room_user_dish",
        ),
    )

    id = Column(Integer, primary_key=True)
    room_code = Column(
        String(10), ForeignKey("group_rooms.room_code"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    dish_id = Column(Integer, ForeignKey("dishes_and_recipes.id"), nullable=False)
    vote_type = Column(String(16), nullable=False)
    voted_at = Column(DateTime, default=utcnow, nullable=False)


class AlgoConfig(Base):
    __tablename__ = "algo_configs"

    id = Column(Integer, primary_key=True)
    config_name = Column(String(64), default="default_production", nullable=False)
    lambda_decay = Column(Float, default=0.5, nullable=False)
    omega_group = Column(Float, default=0.5, nullable=False)
    alpha_taste = Column(Float, nullable=False, default=0.35)
    beta_weather = Column(Float, nullable=False, default=0.25)
    gamma_budget = Column(Float, nullable=False, default=0.20)
    delta_status = Column(Float, nullable=False, default=0.20)
    benchmark_json = Column(JSON, nullable=True)


class AdminAuditLog(Base):
    """管理后台写操作审计。

    为什么单独一张表而不是往 eating_logs 里塞：审计的对象是"谁改了什么数据"，
    与业务流水无关，混在一起会让统计口径和清理策略互相打架。

    只记录写操作（增删改），不记查询——查一次列表就写一行会让表迅速膨胀，
    而且查询本身不改变数据，审计价值低。
    """

    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # action 用「资源.动作」的固定格式，方便按前缀过滤，如 restaurant.delete
    action = Column(String(32), nullable=False, index=True)
    resource_type = Column(String(32), nullable=False, index=True)
    resource_id = Column(Integer, nullable=True, index=True)
    # summary 是给人看的一句话；detail 存原始 payload，方便追查改前改后
    summary = Column(String(255), default="")
    detail = Column(JSON, nullable=True)
    ip = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)


class SystemSetting(Base):
    """系统级键值配置。

    只存少量结构化配置（当前是算法参数），不承担业务数据。
    value 用 JSON 而不是多列：参数集会继续增加，每加一个键就改表结构不划算。
    """

    __tablename__ = "system_settings"

    key = Column(String(64), primary_key=True)
    value = Column(JSON, nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=utcnow, nullable=False)


class TaggingJob(Base):
    """批量打标任务。

    打标要调外部模型，一次可能几十秒到几分钟，不能占着 HTTP 请求不放；
    所以落一行任务记录，由后台线程推进，前端轮询 done/total。
    """

    __tablename__ = "tagging_jobs"

    id = Column(Integer, primary_key=True)
    status = Column(String(16), nullable=False, default="PENDING", index=True)  # PENDING/RUNNING/DONE/FAILED
    total = Column(Integer, nullable=False, default=0)
    done = Column(Integer, nullable=False, default=0)
    failed = Column(Integer, nullable=False, default=0)
    dish_ids = Column(JSON, nullable=False)
    message = Column(String(255), default="")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    finished_at = Column(DateTime, nullable=True)


class DishFeedback(Base):
    """吃完之后的满意度反馈。

    单独建表而不是给 eating_logs 加一列：同一道菜在不同时间可以有不同评价，
    「上次说好吃、这次说踩雷」本身就是有价值的信号，加列会把它压成最后一次。
    """

    __tablename__ = "dish_feedback"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    dish_id = Column(Integer, ForeignKey("dishes_and_recipes.id"), nullable=False, index=True)
    # 关联到具体那顿饭；允许为空以兼容历史数据
    log_id = Column(Integer, ForeignKey("eating_logs.id"), nullable=True, index=True)
    # 3=好吃 2=一般 1=踩雷，与「几星」同向，方便直接聚合
    rating = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)


# ══════════════════════════════════════════════════════════════
# 仿真实验底表（G3）
# 与真实业务表完全隔离：不参与推荐、防腻、足迹和真实统计，
# 只给论文实验页 / 大屏读取。一次导入一个 run，按 run_id 区分。
# ══════════════════════════════════════════════════════════════


class SimulationRun(Base):
    """一次仿真运行的元数据与聚合结果。"""

    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False, index=True)
    seed = Column(Integer, nullable=False)
    personas = Column(Integer, nullable=False, default=0)
    days = Column(Integer, nullable=False, default=0)
    meals_per_day = Column(Integer, nullable=False, default=0)
    rooms_count = Column(Integer, nullable=False, default=0)
    members_per_room = Column(Integer, nullable=False, default=0)
    lambda_decay = Column(Float, nullable=True)
    omega_group = Column(Float, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    imported_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    source_dir = Column(String(255), nullable=False, default="")
    # 重样率曲线、params 等非表格化结果；group bars 单独落表便于查询
    metrics = Column(JSON, nullable=False, default=dict)
    meal_rows = Column(Integer, nullable=False, default=0)
    room_rows = Column(Integer, nullable=False, default=0)
    vote_rows = Column(Integer, nullable=False, default=0)


class SimulationMealLog(Base):
    """仿真中的逐餐推荐结果；arm = ours / baseline。"""

    __tablename__ = "simulation_meal_logs"
    __table_args__ = (
        UniqueConstraint(
            "run_id", "arm", "persona_id", "day", "meal", name="uq_sim_meal"
        ),
        Index("ix_sim_meal_run_arm", "run_id", "arm"),
        Index("ix_sim_meal_run_day", "run_id", "day"),
    )

    id = Column(Integer, primary_key=True)
    run_id = Column(
        Integer,
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    arm = Column(String(16), nullable=False)
    # 仿真人设编号（1..200），不是真实 users.id
    persona_id = Column(Integer, nullable=False)
    day = Column(Integer, nullable=False)
    meal = Column(Integer, nullable=False)
    mode_type = Column(String(16), nullable=False)
    dish_id = Column(Integer, nullable=False)
    dish_name = Column(String(128), nullable=False, default="")
    cuisine_type = Column(String(64), nullable=False, default="")
    total_score = Column(Float, nullable=False, default=0.0)
    decay_weight = Column(Float, nullable=False, default=1.0)
    duplicated = Column(Boolean, nullable=False, default=False)
    candidate_count = Column(Integer, nullable=False, default=0)


class SimulationRoom(Base):
    """仿真中的群组房间；room_code 只在 run 内唯一。"""

    __tablename__ = "simulation_rooms"
    __table_args__ = (
        UniqueConstraint("run_id", "room_code", name="uq_sim_room"),
        Index("ix_sim_room_run_mode", "run_id", "mode_type"),
    )

    id = Column(Integer, primary_key=True)
    run_id = Column(
        Integer,
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_code = Column(String(10), nullable=False)
    mode_type = Column(String(16), nullable=False)
    member_user_ids = Column(JSON, nullable=False, default=list)
    candidate_dish_ids = Column(JSON, nullable=False, default=list)
    winner_dish_id = Column(Integer, nullable=True)
    votes_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=True)


class SimulationRoomVote(Base):
    """仿真中的逐票记录；保存原始票型，便于复算与画图。"""

    __tablename__ = "simulation_room_votes"
    __table_args__ = (
        UniqueConstraint(
            "run_id", "room_code", "user_id", "dish_id", name="uq_sim_vote"
        ),
        Index("ix_sim_vote_run_room", "run_id", "room_code"),
        Index("ix_sim_vote_run_type", "run_id", "vote_type"),
    )

    id = Column(Integer, primary_key=True)
    run_id = Column(
        Integer,
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_code = Column(String(10), nullable=False)
    user_id = Column(Integer, nullable=False)
    dish_id = Column(Integer, nullable=False)
    vote_type = Column(String(16), nullable=False)
    voted_at = Column(DateTime, nullable=True)


class SimulationGroupResult(Base):
    """不同群组策略的平均满意度 / 最低满意度。"""

    __tablename__ = "simulation_group_results"
    __table_args__ = (UniqueConstraint("run_id", "strategy", name="uq_sim_group"),)

    id = Column(Integer, primary_key=True)
    run_id = Column(
        Integer,
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    strategy = Column(String(64), nullable=False)
    avg_score = Column(Float, nullable=False, default=0.0)
    least_misery_score = Column(Float, nullable=False, default=0.0)
