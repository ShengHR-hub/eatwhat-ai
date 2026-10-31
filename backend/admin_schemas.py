"""G4 管理后台写入契约；不改动移动端既有 schemas。"""

from __future__ import annotations

import math
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .schemas import NonBoolFloat, NonBoolInt

Campus = Literal["SIYUAN", "JIANDA_YANTA", "JIANDA_CAOTANG"]
Mode = Literal["OUT_DINING", "HOME_COOKING"]
Role = Literal["MEAT", "VEG", "SOUP", "ONE_MEAL"]
FEATURE_KEYS = (
    "spicy_level",
    "oily_level",
    "soup_level",
    "temp_fit",
    "satiety_level",
    "prep_speed",
    "social_fit",
    "comfort_level",
)
APPLIANCES = {"炒锅", "电饭煲", "空气炸锅", "免开火凉拌", "一锅出"}


def _clean_text(value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError("不能为空白字符串")
    return text


def _clean_string_list(value: list[str]) -> list[str]:
    cleaned = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("数组元素必须是字符串")
        text = item.strip()
        if not text:
            raise ValueError("数组元素不能为空白")
        if len(text) > 64:
            raise ValueError("数组元素不能超过 64 字")
        cleaned.append(text)
    return cleaned


def _validate_vector(value: Optional[dict[str, float]]) -> Optional[dict[str, float]]:
    if value is None:
        return None
    if set(value) != set(FEATURE_KEYS):
        raise ValueError("feature_vector 必须且只能包含完整 8 维")
    result = {}
    for key in FEATURE_KEYS:
        raw = value[key]
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"{key} 必须是数字")
        number = float(raw)
        if not math.isfinite(number) or not 0 <= number <= 1:
            raise ValueError(f"{key} 必须是 0~1 的有限数字")
        result[key] = number
    return result


class AdminModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RestaurantFields(AdminModel):
    name: str = Field(min_length=1, max_length=128)
    source_type: Literal["AMAP_POI", "CANTEEN"] = "AMAP_POI"
    category: str = Field(default="", max_length=64)
    avg_price: Optional[NonBoolFloat] = Field(default=None, ge=0, le=100000)
    rating: Optional[NonBoolFloat] = Field(default=None, ge=0, le=5)
    longitude: Optional[NonBoolFloat] = Field(default=None, ge=-180, le=180)
    latitude: Optional[NonBoolFloat] = Field(default=None, ge=-90, le=90)
    distance_meters: Optional[NonBoolInt] = Field(default=None, ge=0, le=1000000)
    address: str = Field(default="", max_length=255)
    campus: Optional[Campus] = None
    source_dataset: Optional[str] = Field(default=None, max_length=64)
    source_record_id: Optional[str] = Field(default=None, max_length=64)
    source_url: Optional[str] = Field(default=None, max_length=255)
    data_version: Optional[str] = Field(default=None, max_length=64)
    is_synthetic: Optional[bool] = None

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value):
        return _clean_text(value) if isinstance(value, str) else value


class RestaurantCreate(RestaurantFields):
    pass


class RestaurantUpdate(AdminModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    source_type: Optional[Literal["AMAP_POI", "CANTEEN"]] = None
    category: Optional[str] = Field(default=None, max_length=64)
    avg_price: Optional[NonBoolFloat] = Field(default=None, ge=0, le=100000)
    rating: Optional[NonBoolFloat] = Field(default=None, ge=0, le=5)
    longitude: Optional[NonBoolFloat] = Field(default=None, ge=-180, le=180)
    latitude: Optional[NonBoolFloat] = Field(default=None, ge=-90, le=90)
    distance_meters: Optional[NonBoolInt] = Field(default=None, ge=0, le=1000000)
    address: Optional[str] = Field(default=None, max_length=255)
    campus: Optional[Campus] = None
    source_dataset: Optional[str] = Field(default=None, max_length=64)
    source_record_id: Optional[str] = Field(default=None, max_length=64)
    source_url: Optional[str] = Field(default=None, max_length=255)
    data_version: Optional[str] = Field(default=None, max_length=64)
    is_synthetic: Optional[bool] = None

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value):
        return _clean_text(value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("至少提供一个待修改字段")
        return self


class DishFields(AdminModel):
    name: str = Field(min_length=1, max_length=128)
    mode_type: Mode
    restaurant_id: Optional[NonBoolInt] = Field(default=None, ge=1)
    cuisine_type: str = Field(default="", max_length=64)
    dish_role: Role = "ONE_MEAL"
    price_or_cost: Optional[NonBoolFloat] = Field(default=None, ge=0, le=100000)
    cook_minutes: NonBoolInt = Field(default=15, ge=1, le=1440)
    appliance_tag: list[str] = Field(default_factory=lambda: ["炒锅"], max_length=5)
    ingredients_main: list[str] = Field(default_factory=list, max_length=50)
    ingredients_aux: list[str] = Field(default_factory=list, max_length=50)
    recipe_steps: str = Field(default="", max_length=20000)
    feature_vector: Optional[dict[str, float]] = None
    image_url: str = Field(default="", max_length=255)
    allergen_tags: Optional[list[str]] = Field(default=None, max_length=30)
    source_dataset: Optional[str] = Field(default=None, max_length=64)
    source_record_id: Optional[str] = Field(default=None, max_length=64)
    source_url: Optional[str] = Field(default=None, max_length=255)
    data_version: Optional[str] = Field(default=None, max_length=64)
    is_synthetic: Optional[bool] = None

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value):
        return _clean_text(value) if isinstance(value, str) else value

    @field_validator("appliance_tag")
    @classmethod
    def check_appliances(cls, value):
        cleaned = _clean_string_list(value)
        unknown = sorted(set(cleaned) - APPLIANCES)
        if unknown:
            raise ValueError(f"未知厨具：{unknown}")
        return list(dict.fromkeys(cleaned))

    @field_validator("ingredients_main", "ingredients_aux", "allergen_tags")
    @classmethod
    def clean_lists(cls, value):
        return _clean_string_list(value) if value is not None else value

    @field_validator("feature_vector", mode="before")
    @classmethod
    def check_vector(cls, value):
        return _validate_vector(value)

    @model_validator(mode="after")
    def check_restaurant_binding(self):
        if self.mode_type == "OUT_DINING" and self.restaurant_id is None:
            raise ValueError("外食菜品必须绑定 restaurant_id")
        if self.mode_type == "HOME_COOKING" and self.restaurant_id is not None:
            raise ValueError("下厨菜谱不能绑定 restaurant_id")
        return self


class DishCreate(DishFields):
    pass


class DishUpdate(AdminModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    mode_type: Optional[Mode] = None
    restaurant_id: Optional[NonBoolInt] = Field(default=None, ge=1)
    cuisine_type: Optional[str] = Field(default=None, max_length=64)
    dish_role: Optional[Role] = None
    price_or_cost: Optional[NonBoolFloat] = Field(default=None, ge=0, le=100000)
    cook_minutes: Optional[NonBoolInt] = Field(default=None, ge=1, le=1440)
    appliance_tag: Optional[list[str]] = Field(default=None, max_length=5)
    ingredients_main: Optional[list[str]] = Field(default=None, max_length=50)
    ingredients_aux: Optional[list[str]] = Field(default=None, max_length=50)
    recipe_steps: Optional[str] = Field(default=None, max_length=20000)
    feature_vector: Optional[dict[str, float]] = None
    image_url: Optional[str] = Field(default=None, max_length=255)
    allergen_tags: Optional[list[str]] = Field(default=None, max_length=30)
    source_dataset: Optional[str] = Field(default=None, max_length=64)
    source_record_id: Optional[str] = Field(default=None, max_length=64)
    source_url: Optional[str] = Field(default=None, max_length=255)
    data_version: Optional[str] = Field(default=None, max_length=64)
    is_synthetic: Optional[bool] = None

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value):
        return _clean_text(value) if isinstance(value, str) else value

    @field_validator("appliance_tag")
    @classmethod
    def check_appliances(cls, value):
        if value is None:
            return value
        cleaned = _clean_string_list(value)
        unknown = sorted(set(cleaned) - APPLIANCES)
        if unknown:
            raise ValueError(f"未知厨具：{unknown}")
        return list(dict.fromkeys(cleaned))

    @field_validator("ingredients_main", "ingredients_aux", "allergen_tags")
    @classmethod
    def clean_lists(cls, value):
        return _clean_string_list(value) if value is not None else value

    @field_validator("feature_vector", mode="before")
    @classmethod
    def check_vector(cls, value):
        return _validate_vector(value)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("至少提供一个待修改字段")
        return self


class LlmTagRequest(AdminModel):
    dish_ids: list[NonBoolInt] = Field(min_length=1, max_length=20)

    @field_validator("dish_ids")
    @classmethod
    def unique_positive_ids(cls, value):
        if any(item < 1 for item in value):
            raise ValueError("dish_id 必须为正整数")
        if len(set(value)) != len(value):
            raise ValueError("dish_ids 不能重复")
        return value
