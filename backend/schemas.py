import math
from datetime import datetime
from typing import Annotated, Dict, List, Literal, Optional

from pydantic import BaseModel, BeforeValidator, Field, field_validator, model_validator

ModeType = Literal["OUT_DINING", "HOME_COOKING"]
# v2.3.6：房间校区只开放两个已实测校区；草堂为预留，不接受请求。
CampusType = Literal["SIYUAN", "JIANDA_YANTA"]


def _reject_bool(value):
    """S02：Pydantic 会把 True/False 转成 1.0/0.0，数值边界不能接受布尔冒充。"""
    if isinstance(value, bool):
        raise ValueError("必须是数字，不能是布尔值")
    return value


NonBoolFloat = Annotated[float, BeforeValidator(_reject_bool)]
NonBoolInt = Annotated[int, BeforeValidator(_reject_bool)]

# 键名与 algorithms/vector_spec.STATUS_BUBBLE_RULES 一致；这里写死同样是为避免
# schemas → algorithms 的反向依赖，另有测试比对两边。
BUBBLE_IDS = (
    "exhausted",
    "broke_end_month",
    "craving_heavy",
    "light_healthy",
    "need_hot_soup",
    "lazy_one_pot",
)


def _check_bubble_ids(value: List[str]) -> List[str]:
    unknown = sorted({str(item) for item in value} - set(BUBBLE_IDS))
    if unknown:
        raise ValueError(f"未知气泡：{unknown}，只接受 {list(BUBBLE_IDS)}")
    return value


def _check_numeric_mapping_raw(value, label: str, *, allow_empty: bool = True):
    """在 Pydantic 数值转换之前检查原始 JSON，布尔和字符串都不能蒙混。"""
    if value is None:
        return value
    if not isinstance(value, dict):
        raise ValueError(f"{label} 必须是对象")
    if not allow_empty and not value:
        raise ValueError(f"{label} 不能为空对象")
    for key, raw in value.items():
        if isinstance(raw, bool):
            raise ValueError(f"{label}.{key} 必须是数字，不能是布尔值")
        if not isinstance(raw, (int, float)):
            raise ValueError(f"{label}.{key} 必须是数字")
    return value

# 审查 F08：沙盒覆盖参数只认这六个键，且每个键有自己的物理区间。
# 键名与 backend/algorithms/single_recommender.py 的 PARAM_KEYS 保持一致，
# 这里写死是为了避免 schemas → algorithms 的反向依赖。
PARAM_BOUNDS = {
    "lambda_decay": (0.1, 2.0),
    "omega_group": (0.0, 1.0),
    "alpha_taste": (0.0, 1.0),
    "beta_weather": (0.0, 1.0),
    "gamma_budget": (0.0, 1.0),
    "delta_status": (0.0, 1.0),
}
DishRole = Literal["MEAT", "VEG", "SOUP", "ONE_MEAL"]

RADAR_KEYS = ("taste", "weather", "budget", "freshness", "status")


class DemoUser(BaseModel):
    id: int
    nickname: str
    avatar: str
    persona_title: str
    base_vector: Dict[str, float]
    default_budget: float
    veto_tags: List[str]


class ProfileResponse(BaseModel):
    user_id: int
    nickname: str
    avatar: str
    persona_title: str
    base_vector: Dict[str, float]
    default_budget: float
    veto_tags: List[str]
    preferred_cuisines: List[str]
    favorite_dish_ids: List[int]
    blacklist_dish_ids: List[int]
    blacklist_restaurant_ids: List[int]
    achievements: Dict[str, float | int]


GENE_KEYS = (
    "spicy_level",
    "oily_level",
    "soup_level",
    "temp_fit",
    "satiety_level",
    "prep_speed",
    "social_fit",
    "comfort_level",
)


class PreferenceUpdate(BaseModel):
    """偏好更新（审查 F08）：8 维向量必须落在 0~1、预算不能为负。

    向量的存储口径是 0~1（`vector_spec.normalize_vector` 用 clamp01），
    前端展示时 ×100；这里直接按存储口径校验，避免越界值一路流进余弦相似度。
    """

    base_vector: Optional[Dict[str, float]] = None
    default_budget: Optional[NonBoolFloat] = Field(default=None, ge=8, le=500)
    veto_tags: Optional[List[str]] = Field(default=None, max_length=20)
    preferred_cuisines: Optional[List[str]] = Field(default=None, max_length=20)

    @field_validator("base_vector", mode="before")
    @classmethod
    def _check_vector_raw(cls, value):
        # S02 方案 A：允许只传部分维度，但 {} 不构成有效更新。
        return _check_numeric_mapping_raw(
            value, "base_vector", allow_empty=False
        )

    @field_validator("base_vector")
    @classmethod
    def _check_vector(cls, value: Optional[Dict[str, float]]):
        if value is None:
            return value
        unknown = sorted(set(value) - set(GENE_KEYS))
        if unknown:
            raise ValueError(f"未知口味维度：{unknown}，只接受 {list(GENE_KEYS)}")
        cleaned: Dict[str, float] = {}
        for key, raw in value.items():
            number = float(raw)
            if not math.isfinite(number):
                raise ValueError(f"{key} 必须是有限数字")
            if number < 0.0 or number > 1.0:
                raise ValueError(f"{key} 必须在 0~1 之间（存储口径，前端展示 ×100）")
            cleaned[key] = number
        return cleaned

    @field_validator("veto_tags")
    @classmethod
    def _check_veto_tags(cls, value: Optional[List[str]]):
        if value is None:
            return value
        for tag in value:
            text = str(tag).strip()
            if not text:
                raise ValueError("忌口标签不能为空字符串")
            if len(text) > 16:
                raise ValueError(f"忌口标签「{text[:8]}…」超过 16 个字符")
        return [str(tag).strip() for tag in value]


class RedBlackListRequest(BaseModel):
    """红黑榜操作（v2.3.1 第五章）：红榜只允许菜品，黑榜分菜品与门店。"""

    target_type: Literal["DISH", "RESTAURANT"]
    target_id: NonBoolInt
    list_type: Literal["FAV", "BLACK"]
    action: Literal["ADD", "REMOVE"]


class RedBlackListResponse(BaseModel):
    favorite_dish_ids: List[int]
    blacklist_dish_ids: List[int]
    blacklist_restaurant_ids: List[int]


class WeatherResponse(BaseModel):
    temp: float
    weather_text: str
    capsule_tip: str
    source: str



def validate_override_params(value: Optional[Dict[str, float]]):
    """沙盒参数校验（F08/F10 共用）：只认 PARAM_BOUNDS 里的键，值必须有限且在区间内。"""
    if value is None:
        return value
    unknown = sorted(set(value) - set(PARAM_BOUNDS))
    if unknown:
        raise ValueError(f"未知参数：{unknown}，只接受 {list(PARAM_BOUNDS)}")
    cleaned: Dict[str, float] = {}
    for key, raw in value.items():
        number = float(raw)
        if not math.isfinite(number):
            raise ValueError(f"{key} 必须是有限数字")
        low, high = PARAM_BOUNDS[key]
        if number < low or number > high:
            raise ValueError(f"{key} 必须在 {low}~{high} 之间")
        cleaned[key] = number
    return cleaned

class SingleRecommendRequest(BaseModel):
    user_id: Optional[NonBoolInt] = None
    mode_type: ModeType
    # v2.3.4 §5.5.3：外食必须声明校区，缺失 422；下厨共享，可忽略。
    campus: Optional[CampusType] = None
    # 审查 F08：所有入参都收边界，越界一律 422，不让脏值走到算法里炸 500
    budget: Optional[NonBoolFloat] = Field(default=None, ge=0, le=2000)
    bubbles: List[str] = Field(default_factory=list, max_length=12)
    combo_mode: bool = False
    override_params: Optional[Dict[str, float]] = None
    weather_temp: Optional[NonBoolFloat] = Field(default=None, ge=-30, le=50)
    weather_text: Optional[str] = Field(default=None, max_length=32)
    max_distance_meters: Optional[NonBoolInt] = Field(default=None, ge=0, le=100000)
    limit: NonBoolInt = Field(default=10, ge=1, le=100)
    # 审查 F13：换一批/继续划时把已经看过的菜排掉，避免反复请求同一批 Top N
    exclude_dish_ids: List[NonBoolInt] = Field(
        default_factory=list, max_length=500, description="要排除的菜品 id"
    )

    @model_validator(mode="after")
    def _campus_required_for_out_dining(self):
        if self.mode_type == "OUT_DINING" and self.campus is None:
            raise ValueError("外食推荐必须指定校区（SIYUAN / JIANDA_YANTA）")
        return self

    @field_validator("bubbles")
    @classmethod
    def _check_bubbles(cls, value: List[str]):
        return _check_bubble_ids(value)

    @field_validator("override_params", mode="before")
    @classmethod
    def _check_override_raw(cls, value):
        return _check_numeric_mapping_raw(value, "override_params")

    @field_validator("override_params")
    @classmethod
    def _check_override_params(cls, value):
        """F08：未知键、非有限数、越界值一律拒绝。"""
        if value is None:
            return value
        for key, raw in value.items():
            if key not in PARAM_BOUNDS:
                raise ValueError(f"未知的算法参数：{key}")
            low, high = PARAM_BOUNDS[key]
            try:
                number = float(raw)
            except (TypeError, ValueError):
                raise ValueError(f"参数 {key} 必须是数字")
            if number != number or number in (float("inf"), float("-inf")):
                raise ValueError(f"参数 {key} 必须是有限数")
            if not (low <= number <= high):
                raise ValueError(f"参数 {key} 超出区间 [{low}, {high}]")
        return value



class Radar5D(BaseModel):
    taste: float
    weather: float
    budget: float
    freshness: float
    status: float


class RecommendationItem(BaseModel):
    dish_id: int
    name: str
    mode_type: str
    cuisine_type: str
    dish_role: str
    price: float
    restaurant_id: Optional[int] = None
    restaurant_name: Optional[str] = None
    total_score: float
    radar_5d: Radar5D
    decay_weight: float
    explain_reason: str
    feature_vector: Dict[str, float]
    # 供前端生成「主料 / 用时」的自然语言描述
    ingredients_main: List[str] = []
    cook_minutes: Optional[float] = None
    is_favorite: bool
    # 菜品示意图：仓库内相对路径（/dishes/xxx.jpg）。没有合适图时保持 None，
    # 前端据此走"无图占位"，不许用别的菜的图顶替（口径见 docs/DISH_IMAGES_PLAN.md）。
    image_url: Optional[str] = None


class ComboDish(BaseModel):
    dish_id: int
    name: str
    dish_role: str
    price: float
    score: float


class ComboResult(BaseModel):
    dish_ids: List[int]
    dishes: List[ComboDish]
    total_price: float
    avg_oily_level: float
    total_score: float


class SingleRecommendResponse(BaseModel):
    mode_type: str
    recommendations: List[RecommendationItem]
    combo: Optional[ComboResult] = None
    params_used: Dict[str, float]
    bubble_effects: Dict[str, List[str]]


class GroupConsensusMember(BaseModel):
    user_id: int
    satisfaction: float
    vote_type: str


class GroupConsensusDish(BaseModel):
    dish_id: int
    group_score: float
    mean_satisfaction: float
    least_misery: float
    masked_by_veto: bool
    members: List[GroupConsensusMember]


class GroupConsensusResponse(BaseModel):
    room_code: str
    winner_dish_id: Optional[int]
    winner_group_score: float
    omega_group: float
    dishes: List[GroupConsensusDish]


class AMAPSyncRequest(BaseModel):
    lat: float
    lng: float
    keywords: str = "美食"
    radius: int = 3000


class AuthRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=72)
    nickname: str = Field(default="", max_length=32)


class AuthLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=72)


class AuthUser(BaseModel):
    user_id: int
    username: str
    nickname: str
    avatar: str = ""
    # 前端据此决定登录后落到移动端还是管理后台；真正的权限仍由后端 require_admin 判定
    role: str = "USER"


class AuthResponse(BaseModel):
    token: str
    user: AuthUser


class CheckinRequest(BaseModel):
    user_id: Optional[NonBoolInt] = None
    dish_id: NonBoolInt = Field(ge=1)
    mode_type: ModeType
    bubbles: List[str] = Field(default_factory=list, max_length=12)
    # 审查 F08：花费不允许负数，快照串限长，避免脏数据进库
    cost_amount: Optional[NonBoolFloat] = Field(default=None, ge=0, le=100000)
    weather_snapshot: str = Field(default="", max_length=64)

    @field_validator("bubbles")
    @classmethod
    def _check_bubbles(cls, value: List[str]):
        return _check_bubble_ids(value)


class CheckinResponse(BaseModel):
    log_id: int
    new_decay_weight: float


class CoolingDish(BaseModel):
    dish_id: int
    name: str
    last_eaten_at: datetime
    days_since: int
    decay_weight: float
    cooling_percent: float
    status: Literal["COOLING", "WARMING", "READY"]


class CuisinePieItem(BaseModel):
    name: str
    value: int


class LogStatsResponse(BaseModel):
    cooling_dishes: List[CoolingDish]
    weekly_expense: float
    meals_this_week: int
    cuisine_pie_data: List[CuisinePieItem]


class TimelineItem(BaseModel):
    log_id: int
    dish_id: int
    # 0 表示还没评价；3=好吃 2=一般 1=踩雷
    rating: int = 0
    dish_name: str
    restaurant_name: str = ""
    mode_type: str
    cost_amount: float = 0.0
    weather_snapshot: str = ""
    status_bubbles: List[str] = []
    eaten_at: datetime


class TimelineResponse(BaseModel):
    items: List[TimelineItem]


class OkResponse(BaseModel):
    ok: bool = True


class DishBrief(BaseModel):
    """目录只读视图：红黑榜、忌口台把 id 翻成名字用。"""

    dish_id: int
    name: str
    mode_type: str
    cuisine_type: str = ""
    dish_role: str = ""
    price: float = 0.0
    appliance_tag: List[str] = []
    image_url: Optional[str] = None


class RestaurantBrief(BaseModel):
    restaurant_id: int
    name: str
    category: str = ""
    avg_price: float = 0.0

# —— 模块 3：虚拟冰箱（批次 3）——
FridgeCategory = Literal["肉禽蛋奶", "新鲜果蔬", "冷冻速食", "豆制品与干货"]


class FridgeItem(BaseModel):
    id: int
    ingredient_name: str
    category: str
    quantity_desc: str = "适量"
    expire_days: int = 3
    is_expiring_soon: bool = False


class FridgeListResponse(BaseModel):
    user_id: int
    items: List[FridgeItem]


class ScanItem(BaseModel):
    ingredient_name: str = Field(min_length=1, max_length=32)
    category: FridgeCategory = "新鲜果蔬"
    quantity_desc: str = Field(default="适量", max_length=32)
    expire_days: NonBoolInt = Field(default=3, ge=0, le=365)
    confidence: float = Field(default=0.8, ge=0, le=1)


class ScanResponse(BaseModel):
    items: List[ScanItem]
    source: str = "vision"
    model: str = ""


class ScanImportRequest(BaseModel):
    items: List[ScanItem] = Field(min_length=1, max_length=20)


class FridgeUpsertRequest(BaseModel):
    """录入 / 删除同一条接口：REMOVE 只按 ingredient_name 定位，幂等。"""

    ingredient_name: str = Field(min_length=1, max_length=32)
    category: FridgeCategory = "新鲜果蔬"
    quantity_desc: str = Field(default="适量", max_length=32)
    expire_days: NonBoolInt = Field(default=3, ge=0, le=365)
    action: Literal["ADD", "REMOVE"] = "ADD"

    @field_validator("ingredient_name", mode="before")
    @classmethod
    def _strip_name(cls, value):
        # S02：只含空白的名字会被 strip 成空串写进库，必须在入口拒绝。
        if isinstance(value, str):
            text = value.strip()
            if not text:
                raise ValueError("食材名不能为空")
            return text
        return value

    @field_validator("quantity_desc", mode="before")
    @classmethod
    def _strip_quantity(cls, value):
        if isinstance(value, str):
            text = value.strip()
            if not text:
                raise ValueError("数量描述不能为空")
            return text
        return value


class ShoppingListRequest(BaseModel):
    user_id: Optional[NonBoolInt] = None
    dish_ids: List[NonBoolInt] = Field(default_factory=list)


class ShoppingItem(BaseModel):
    ingredient: str
    category: str = ""
    used_by: List[str] = Field(default_factory=list)
    from_fridge: bool = False


class ShoppingListResponse(BaseModel):
    owned_ingredients: List[ShoppingItem]
    to_buy_ingredients: List[ShoppingItem]

# —— 模块 4：多人干饭房间（批次 3 后半）——
class RoomMemberBrief(BaseModel):
    user_id: int
    nickname: str
    avatar: str = "🍚"
    is_host: bool = False
    progress: int = 0


class RoomCandidate(BaseModel):
    dish_id: int
    name: str
    price: float = 0.0
    cuisine_type: str = ""
    restaurant_name: str = ""
    image_url: Optional[str] = None
    # 菜品自身的八维风味向量：房间与单人卡统一用雷达图展示，不依赖菜品图片。
    feature_vector: Optional[Dict[str, float]] = None
    # 当前查看者的五维个人匹配分；不同成员看到的值不同。
    my_match: Optional[Radar5D] = None


class RoomSnapshot(BaseModel):
    """房间快照：既是 create/join 的响应，也是 GET 的响应。

    v2.3.2 契约（审查 F05/F11）：刷新/断线重进必须能恢复全部现场 ——
    候选、本人已投票、服务端截止时间、赢家详情、共识报告，一个都不能少。
    """

    room_code: str
    host_user_id: int
    mode_type: str
    # v2.3.6：房间校区与建房时冻结的有效 ω（只读，用于恢复/追溯）
    campus: Optional[str] = None
    omega_group: Optional[float] = None
    # WAITING | SWIPING | FINISHED（规格第 200 行，不再用 REVEALED）
    status: str
    members: List[RoomMemberBrief] = []
    candidates: List[RoomCandidate] = []
    candidate_count: int = 0
    winner_dish_id: Optional[int] = None
    winner_dish: Optional[RoomCandidate] = None
    consensus_report: Optional[dict] = None
    has_consensus: bool = False
    # 服务端截止时间（毫秒时间戳）与剩余时间，前端只用这两个，不自己算
    deadline_at: Optional[str] = None
    remaining_ms: int = 0
    my_votes: Dict[int, str] = {}
    budget: Optional[float] = None
    swipe_seconds: int = 15


class RoomCreateRequest(BaseModel):
    """建房（规格第 315 行 / v2.3.6）：模式 + 必填校区 + 可选预算 + 可选 ω 快照。"""

    mode_type: Literal["OUT_DINING", "HOME_COOKING"] = "OUT_DINING"
    campus: CampusType
    host_user_id: Optional[NonBoolInt] = None
    # 规格第 315 行：建房就带预算，候选在建房时一次算好
    budget: Optional[NonBoolFloat] = Field(default=None, ge=8, le=500)
    # F10 收口：房间要跨请求存活，沙盒参数必须在建房时快照下来，
    # 否则「开团时调了 ω」和「结算时读 DB 的 ω」是两条不同的链路。
    override_params: Optional[Dict[str, float]] = None

    @field_validator("override_params", mode="before")
    @classmethod
    def _check_override_raw(cls, value):
        return _check_numeric_mapping_raw(value, "override_params")

    @field_validator("override_params")
    @classmethod
    def _check_override(cls, value):
        return validate_override_params(value)


class RoomJoinRequest(BaseModel):
    user_id: Optional[NonBoolInt] = None
    # v2.3.6：join 必须声明校区，后端与房间校区严格比对，不一致 409。
    campus: CampusType

