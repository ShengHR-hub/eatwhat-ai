"""批次 1 种子数据：20 家门店/档口 + 60 道外食 + 40 道家常菜 + 4 个演示角色。"""

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from backend.database import Base, SessionLocal, engine
from backend.scripts.dish_images import DISH_IMAGE_PATHS
from backend.models import (
    AlgoConfig,
    Dish,
    EatingLog,
    FridgeInventory,
    GroupRoom,
    Restaurant,
    RoomVote,
    User,
    UserPreference,
    utcnow,
)

OUT_DINING = "OUT_DINING"
HOME_COOKING = "HOME_COOKING"


def fv(
    spicy: float,
    oily: float,
    soup: float,
    temp: float,
    satiety: float,
    prep: float,
    social: float,
    comfort: float,
) -> Dict[str, float]:
    return {
        "spicy_level": spicy,
        "oily_level": oily,
        "soup_level": soup,
        "temp_fit": temp,
        "satiety_level": satiety,
        "prep_speed": prep,
        "social_fit": social,
        "comfort_level": comfort,
    }


RESTAURANTS = [
    ("一食堂·川湘窗口", "CANTEEN", "川湘菜", 14.0, 4.4, 108.9301, 34.2402, 120, "校内一食堂二楼"),
    ("一食堂·粤式烧腊", "CANTEEN", "粤菜", 15.0, 4.5, 108.9302, 34.2403, 130, "校内一食堂一楼"),
    ("二食堂·牛肉面", "CANTEEN", "面食", 13.0, 4.3, 108.9305, 34.2406, 200, "校内二食堂一楼"),
    ("二食堂·麻辣烫", "CANTEEN", "麻辣烫", 16.0, 4.2, 108.9306, 34.2407, 210, "校内二食堂一楼"),
    ("二食堂·轻食沙拉", "CANTEEN", "轻食", 18.0, 4.6, 108.9307, 34.2408, 220, "校内二食堂二楼"),
    ("三食堂·家常小炒", "CANTEEN", "家常菜", 12.0, 4.5, 108.9310, 34.2411, 300, "校内三食堂一楼"),
    ("三食堂·粥粉面", "CANTEEN", "粥粉面", 11.0, 4.4, 108.9311, 34.2412, 310, "校内三食堂一楼"),
    ("三食堂·韩式石锅", "CANTEEN", "韩餐", 19.0, 4.3, 108.9312, 34.2413, 320, "校内三食堂二楼"),
    ("清真食堂·兰州拉面", "CANTEEN", "面食", 12.0, 4.6, 108.9315, 34.2416, 380, "清真食堂一楼"),
    ("教工食堂·砂锅炖菜", "CANTEEN", "炖菜", 17.0, 4.5, 108.9317, 34.2418, 420, "教工食堂二楼"),
    ("蜀香园川菜馆", "AMAP_POI", "川湘菜", 42.0, 4.6, 108.9420, 34.2480, 900, "学府路 88 号"),
    ("粤品轩茶餐厅", "AMAP_POI", "粤菜", 36.0, 4.5, 108.9450, 34.2470, 1100, "学府路 120 号"),
    ("老街牛肉面", "AMAP_POI", "面食", 22.0, 4.4, 108.9380, 34.2440, 700, "老街 12 号"),
    ("轻卡沙拉工坊", "AMAP_POI", "轻食", 30.0, 4.7, 108.9480, 34.2500, 1400, "大学城商业街 3 层"),
    ("阿香麻辣烫", "AMAP_POI", "麻辣烫", 28.0, 4.3, 108.9390, 34.2455, 800, "大学城商业街 1 层"),
    ("炭火烤肉屋", "AMAP_POI", "烤肉", 62.0, 4.6, 108.9510, 34.2520, 1800, "大学城商业街 5 层"),
    ("樱寿司日料", "AMAP_POI", "日料", 55.0, 4.5, 108.9530, 34.2530, 2100, "大学城商业街 4 层"),
    ("首尔炸鸡啤酒", "AMAP_POI", "韩餐", 46.0, 4.4, 108.9540, 34.2510, 2300, "大学城商业街 6 层"),
    ("江南小厨", "AMAP_POI", "江浙菜", 40.0, 4.5, 108.9470, 34.2460, 1300, "学府路 156 号"),
    ("暖心砂锅粥", "AMAP_POI", "粥品", 38.0, 4.6, 108.9410, 34.2495, 1000, "学府路 98 号"),
]

# (名称, 菜系, 角色, 价格, 主料, 辅料, 8维向量, 门店下标)
OUT_DISHES = [
    ("麻辣香锅", "川湘菜", "ONE_MEAL", 18.0, ["午餐肉", "土豆", "藕片", "宽粉"], ["香菜", "辣椒", "花椒", "葱姜蒜"], fv(0.95, 0.85, 0.15, 0.45, 0.90, 0.70, 0.70, 0.85), 0),
    ("水煮肉片", "川湘菜", "MEAT", 16.0, ["猪里脊"], ["豆芽", "辣椒", "花椒", "葱姜蒜"], fv(0.90, 0.90, 0.55, 0.30, 0.80, 0.55, 0.65, 0.85), 0),
    ("辣子鸡", "川湘菜", "MEAT", 17.0, ["鸡腿肉"], ["干辣椒", "花椒", "葱姜蒜"], fv(0.85, 0.80, 0.10, 0.45, 0.70, 0.60, 0.60, 0.80), 0),
    ("干煸四季豆", "川湘菜", "VEG", 10.0, ["四季豆"], ["干辣椒", "花椒", "蒜"], fv(0.55, 0.65, 0.05, 0.50, 0.45, 0.65, 0.45, 0.55), 0),
    ("酸辣土豆丝", "川湘菜", "VEG", 8.0, ["土豆"], ["干辣椒", "醋", "葱"], fv(0.60, 0.45, 0.05, 0.55, 0.50, 0.80, 0.35, 0.55), 0),
    ("蜜汁叉烧饭", "粤菜", "ONE_MEAL", 16.0, ["叉烧", "米饭"], ["青菜", "蜜汁"], fv(0.05, 0.55, 0.20, 0.50, 0.80, 0.65, 0.40, 0.70), 1),
    ("白切鸡饭", "粤菜", "ONE_MEAL", 15.0, ["白切鸡", "米饭"], ["姜葱", "青菜"], fv(0.05, 0.30, 0.35, 0.50, 0.70, 0.60, 0.45, 0.55), 1),
    ("烧鸭饭", "粤菜", "ONE_MEAL", 16.0, ["烧鸭", "米饭"], ["青菜", "酸梅酱"], fv(0.05, 0.60, 0.20, 0.50, 0.80, 0.60, 0.45, 0.70), 1),
    ("清炒菜心", "粤菜", "VEG", 8.0, ["菜心"], ["蒜", "盐"], fv(0.00, 0.15, 0.10, 0.50, 0.30, 0.75, 0.30, 0.40), 1),
    ("例汤", "粤菜", "SOUP", 6.0, ["猪骨", "时蔬"], ["姜片", "盐"], fv(0.00, 0.20, 0.95, 0.30, 0.25, 0.85, 0.40, 0.60), 1),
    ("红烧牛肉面", "面食", "ONE_MEAL", 14.0, ["牛肉", "面条"], ["葱姜蒜", "香料"], fv(0.30, 0.55, 0.85, 0.30, 0.85, 0.55, 0.35, 0.75), 2),
    ("清汤牛肉面", "面食", "ONE_MEAL", 13.0, ["牛肉", "面条"], ["白萝卜", "葱"], fv(0.10, 0.25, 0.90, 0.30, 0.75, 0.60, 0.35, 0.60), 2),
    ("番茄鸡蛋面", "面食", "ONE_MEAL", 11.0, ["番茄", "鸡蛋", "面条"], ["葱", "盐"], fv(0.00, 0.30, 0.80, 0.40, 0.65, 0.70, 0.30, 0.65), 2),
    ("牛肉粉丝汤", "面食", "SOUP", 12.0, ["牛肉", "粉丝"], ["葱", "香菜"], fv(0.15, 0.35, 0.95, 0.30, 0.55, 0.70, 0.35, 0.65), 2),
    ("麻辣烫套餐", "麻辣烫", "ONE_MEAL", 15.0, ["午餐肉", "宽粉", "青菜"], ["辣椒", "花椒", "芝麻酱"], fv(0.80, 0.65, 0.75, 0.40, 0.85, 0.65, 0.55, 0.85), 3),
    ("番茄麻辣烫", "麻辣烫", "ONE_MEAL", 16.0, ["宽粉", "番茄", "青菜"], ["骨汤", "芝麻酱"], fv(0.35, 0.45, 0.80, 0.40, 0.80, 0.65, 0.55, 0.70), 3),
    ("骨汤麻辣烫", "麻辣烫", "ONE_MEAL", 17.0, ["宽粉", "豆皮", "青菜"], ["骨汤", "麻酱"], fv(0.50, 0.50, 0.85, 0.35, 0.80, 0.65, 0.55, 0.75), 3),
    ("鸡胸肉沙拉", "轻食", "ONE_MEAL", 18.0, ["鸡胸肉", "生菜", "玉米"], ["油醋汁", "小番茄"], fv(0.05, 0.10, 0.05, 0.75, 0.40, 0.85, 0.30, 0.35), 4),
    ("低脂鸡胸饭", "轻食", "ONE_MEAL", 19.0, ["鸡胸肉", "糙米饭", "西兰花"], ["黑胡椒", "盐"], fv(0.10, 0.15, 0.10, 0.60, 0.55, 0.80, 0.30, 0.35), 4),
    ("南瓜浓汤", "轻食", "SOUP", 8.0, ["南瓜"], ["牛奶", "黑胡椒"], fv(0.00, 0.20, 0.95, 0.35, 0.35, 0.75, 0.30, 0.60), 4),
    ("青椒肉丝", "家常菜", "MEAT", 12.0, ["猪里脊", "青椒"], ["葱姜蒜", "生抽"], fv(0.25, 0.55, 0.10, 0.50, 0.65, 0.85, 0.40, 0.60), 5),
    ("鱼香肉丝", "家常菜", "MEAT", 13.0, ["猪里脊", "木耳", "胡萝卜"], ["豆瓣酱", "醋", "葱姜蒜"], fv(0.35, 0.65, 0.15, 0.50, 0.70, 0.80, 0.45, 0.70), 5),
    ("宫保鸡丁", "家常菜", "MEAT", 14.0, ["鸡胸肉", "花生"], ["干辣椒", "葱姜蒜"], fv(0.55, 0.60, 0.10, 0.50, 0.70, 0.75, 0.55, 0.75), 5),
    ("麻婆豆腐", "家常菜", "VEG", 9.0, ["豆腐", "肉末"], ["豆瓣酱", "花椒", "葱姜蒜"], fv(0.75, 0.70, 0.35, 0.40, 0.55, 0.80, 0.45, 0.70), 5),
    ("西红柿炒蛋", "家常菜", "VEG", 9.0, ["番茄", "鸡蛋"], ["葱", "盐"], fv(0.00, 0.35, 0.20, 0.50, 0.55, 0.85, 0.35, 0.65), 5),
    ("紫菜蛋花汤", "家常菜", "SOUP", 5.0, ["紫菜", "鸡蛋"], ["虾皮", "盐"], fv(0.00, 0.10, 0.95, 0.30, 0.20, 0.90, 0.35, 0.55), 5),
    ("皮蛋瘦肉粥", "粥粉面", "ONE_MEAL", 10.0, ["大米", "皮蛋", "瘦肉"], ["葱", "姜"], fv(0.00, 0.15, 0.90, 0.25, 0.50, 0.80, 0.30, 0.65), 6),
    ("肠粉", "粥粉面", "ONE_MEAL", 9.0, ["米浆", "鸡蛋", "生菜"], ["生抽", "葱"], fv(0.05, 0.25, 0.20, 0.50, 0.45, 0.75, 0.30, 0.55), 6),
    ("云吞面", "粥粉面", "ONE_MEAL", 12.0, ["云吞", "面条", "虾仁"], ["海鲜", "葱花"], fv(0.00, 0.25, 0.85, 0.40, 0.65, 0.70, 0.35, 0.65), 6),
    ("干炒牛河", "粥粉面", "ONE_MEAL", 14.0, ["河粉", "牛肉", "豆芽"], ["葱", "生抽"], fv(0.10, 0.70, 0.10, 0.50, 0.80, 0.65, 0.45, 0.70), 6),
    ("石锅拌饭", "韩餐", "ONE_MEAL", 18.0, ["米饭", "牛肉", "蔬菜"], ["辣酱", "鸡蛋"], fv(0.35, 0.45, 0.20, 0.50, 0.80, 0.60, 0.50, 0.70), 7),
    ("部队锅", "韩餐", "ONE_MEAL", 22.0, ["午餐肉", "年糕", "泡菜", "方便面"], ["芝士", "辣酱"], fv(0.55, 0.65, 0.85, 0.35, 0.85, 0.45, 0.75, 0.80), 7),
    ("兰州牛肉拉面", "面食", "ONE_MEAL", 12.0, ["牛肉", "拉面"], ["香菜", "葱", "辣椒油"], fv(0.20, 0.30, 0.95, 0.30, 0.75, 0.65, 0.35, 0.70), 8),
    ("牛肉炒面片", "面食", "ONE_MEAL", 15.0, ["牛肉", "面片", "青椒"], ["葱姜蒜", "生抽"], fv(0.25, 0.55, 0.20, 0.50, 0.85, 0.60, 0.45, 0.70), 8),
    ("羊肉串", "烧烤", "MEAT", 10.0, ["羊肉"], ["孜然", "辣椒面"], fv(0.35, 0.60, 0.05, 0.45, 0.55, 0.60, 0.70, 0.75), 8),
    ("排骨莲藕汤", "炖菜", "SOUP", 16.0, ["排骨", "莲藕"], ["葱姜蒜", "盐"], fv(0.00, 0.30, 0.95, 0.25, 0.60, 0.40, 0.55, 0.75), 9),
    ("砂锅豆腐", "炖菜", "MEAT", 14.0, ["豆腐", "肉末", "粉丝"], ["葱姜蒜", "生抽"], fv(0.30, 0.45, 0.80, 0.30, 0.55, 0.55, 0.50, 0.65), 9),
    ("砂锅鸡", "炖菜", "MEAT", 20.0, ["鸡肉", "土豆"], ["葱姜蒜", "生抽"], fv(0.35, 0.50, 0.80, 0.30, 0.75, 0.45, 0.65, 0.75), 9),
    ("毛血旺", "川湘菜", "MEAT", 38.0, ["鸭血", "毛肚", "午餐肉"], ["香菜", "辣椒", "花椒", "葱姜蒜"], fv(0.95, 0.90, 0.70, 0.35, 0.80, 0.50, 0.75, 0.90), 10),
    ("水煮鱼", "川湘菜", "MEAT", 42.0, ["草鱼"], ["豆芽", "香菜", "辣椒", "花椒"], fv(0.90, 0.85, 0.65, 0.35, 0.75, 0.45, 0.70, 0.85), 10),
    ("回锅肉", "川湘菜", "MEAT", 32.0, ["五花肉", "青蒜"], ["豆瓣酱", "葱姜蒜"], fv(0.55, 0.85, 0.10, 0.45, 0.85, 0.55, 0.65, 0.85), 10),
    ("凉拌折耳根", "川湘菜", "VEG", 16.0, ["折耳根"], ["香菜", "辣椒", "醋", "蒜"], fv(0.65, 0.25, 0.00, 0.70, 0.30, 0.90, 0.40, 0.45), 10),
    ("虾饺皇", "粤菜", "ONE_MEAL", 26.0, ["虾仁", "澄面"], ["海鲜", "笋丁"], fv(0.00, 0.20, 0.20, 0.55, 0.45, 0.70, 0.45, 0.65), 11),
    ("白灼虾", "粤菜", "MEAT", 48.0, ["鲜虾"], ["海鲜", "姜葱"], fv(0.00, 0.10, 0.10, 0.60, 0.40, 0.75, 0.55, 0.60), 11),
    ("烧鹅拼饭", "粤菜", "ONE_MEAL", 32.0, ["烧鹅", "米饭"], ["青菜", "酸梅酱"], fv(0.00, 0.65, 0.20, 0.50, 0.85, 0.55, 0.55, 0.80), 11),
    ("老火靓汤", "粤菜", "SOUP", 18.0, ["猪骨", "玉米", "胡萝卜"], ["姜片", "盐"], fv(0.00, 0.20, 0.95, 0.25, 0.35, 0.40, 0.45, 0.75), 11),
    ("招牌牛腩面", "面食", "ONE_MEAL", 22.0, ["牛腩", "面条"], ["葱", "香料"], fv(0.15, 0.50, 0.90, 0.30, 0.85, 0.60, 0.40, 0.80), 12),
    ("酸菜牛肉面", "面食", "ONE_MEAL", 20.0, ["牛肉", "酸菜", "面条"], ["葱", "辣椒"], fv(0.30, 0.45, 0.88, 0.35, 0.80, 0.60, 0.40, 0.75), 12),
    ("藜麦鸡胸沙拉", "轻食", "ONE_MEAL", 28.0, ["鸡胸肉", "藜麦", "生菜"], ["油醋汁", "小番茄"], fv(0.05, 0.10, 0.05, 0.75, 0.50, 0.85, 0.35, 0.40), 13),
    ("三文鱼沙拉", "轻食", "ONE_MEAL", 36.0, ["三文鱼", "生菜", "牛油果"], ["海鲜", "油醋汁"], fv(0.00, 0.20, 0.05, 0.70, 0.50, 0.80, 0.45, 0.55), 13),
    ("全麦鸡肉卷", "轻食", "ONE_MEAL", 24.0, ["全麦饼", "鸡胸肉", "生菜"], ["酸奶酱", "番茄"], fv(0.10, 0.25, 0.10, 0.65, 0.60, 0.85, 0.40, 0.50), 13),
    ("招牌麻辣烫", "麻辣烫", "ONE_MEAL", 26.0, ["宽粉", "牛肉丸", "青菜"], ["香菜", "辣椒", "芝麻酱"], fv(0.80, 0.65, 0.75, 0.40, 0.90, 0.60, 0.60, 0.85), 14),
    ("五花肉烤肉套餐", "烤肉", "MEAT", 58.0, ["五花肉", "生菜", "米饭"], ["烤肉酱", "蒜片"], fv(0.30, 0.85, 0.15, 0.45, 0.95, 0.35, 0.95, 0.90), 15),
    ("烤牛肉拼盘", "烤肉", "MEAT", 68.0, ["牛肉", "洋葱"], ["烤肉酱", "黑胡椒"], fv(0.20, 0.65, 0.10, 0.50, 0.90, 0.40, 0.90, 0.85), 15),
    ("烤蔬菜拼盘", "烤肉", "VEG", 22.0, ["彩椒", "茄子", "金针菇"], ["蒜蓉", "橄榄油"], fv(0.10, 0.30, 0.05, 0.55, 0.40, 0.55, 0.80, 0.60), 15),
    ("三文鱼刺身", "日料", "MEAT", 58.0, ["三文鱼"], ["海鲜", "芥末", "酱油"], fv(0.00, 0.15, 0.05, 0.65, 0.35, 0.80, 0.60, 0.65), 16),
    ("鳗鱼饭", "日料", "ONE_MEAL", 48.0, ["鳗鱼", "米饭"], ["海鲜", "照烧汁"], fv(0.05, 0.55, 0.15, 0.50, 0.80, 0.60, 0.55, 0.80), 16),
    ("韩式炸鸡", "韩餐", "MEAT", 45.0, ["鸡肉"], ["甜辣酱", "芝麻"], fv(0.35, 0.80, 0.05, 0.50, 0.80, 0.55, 0.85, 0.90), 17),
    ("红烧狮子头", "江浙菜", "MEAT", 36.0, ["猪肉", "马蹄"], ["生抽", "冰糖", "葱姜蒜"], fv(0.05, 0.70, 0.25, 0.45, 0.80, 0.45, 0.65, 0.80), 18),
    ("猪肚鸡汤", "粥品", "SOUP", 42.0, ["猪肚", "鸡肉"], ["胡椒", "姜片"], fv(0.15, 0.35, 0.95, 0.25, 0.55, 0.40, 0.60, 0.80), 19),
]

# (名称, 菜系, 角色, 成本, 分钟, 厨具, 主料, 辅料, 向量, 步骤)
HOME_DISHES = [
    ("番茄炒蛋", "家常菜", "VEG", 8.0, 10, "炒锅", ["番茄", "鸡蛋"], ["葱", "盐"], fv(0.00, 0.35, 0.20, 0.50, 0.55, 0.85, 0.35, 0.65), "番茄切块，鸡蛋打散；热锅炒蛋盛出，再炒番茄回锅调味。"),
    ("青椒土豆丝", "家常菜", "VEG", 6.0, 12, "炒锅", ["土豆", "青椒"], ["醋", "花椒"], fv(0.55, 0.50, 0.05, 0.55, 0.50, 0.80, 0.35, 0.55), "土豆切丝泡水，青椒切丝；热油爆花椒后大火快炒，出锅前淋醋。"),
    ("蒜蓉西兰花", "家常菜", "VEG", 7.0, 10, "炒锅", ["西兰花"], ["蒜", "盐"], fv(0.00, 0.15, 0.10, 0.55, 0.35, 0.75, 0.30, 0.45), "西兰花焯水；爆香蒜末后下锅快炒，加盐出锅。"),
    ("手撕包菜", "家常菜", "VEG", 6.0, 10, "炒锅", ["包菜"], ["干辣椒", "醋"], fv(0.30, 0.45, 0.05, 0.50, 0.40, 0.75, 0.35, 0.50), "包菜手撕成片；热锅爆干辣椒，大火快炒并沿锅边淋醋。"),
    ("麻婆豆腐", "川湘菜", "VEG", 9.0, 15, "炒锅", ["豆腐", "肉末"], ["豆瓣酱", "花椒", "葱姜蒜"], fv(0.75, 0.70, 0.35, 0.40, 0.55, 0.80, 0.45, 0.70), "豆腐切块焯水；炒香肉末与豆瓣酱，加水下豆腐，勾芡撒花椒。"),
    ("鱼香茄子", "川湘菜", "VEG", 8.0, 15, "炒锅", ["茄子"], ["豆瓣酱", "蒜", "醋", "葱姜蒜"], fv(0.40, 0.70, 0.15, 0.50, 0.55, 0.75, 0.40, 0.65), "茄子切条煎软；爆香蒜末豆瓣酱，调入鱼香汁翻炒收汁。"),
    ("可乐鸡翅", "家常菜", "MEAT", 15.0, 25, "炒锅", ["鸡翅", "可乐"], ["姜", "生抽"], fv(0.00, 0.55, 0.10, 0.50, 0.65, 0.55, 0.60, 0.80), "鸡翅煎至两面金黄；倒入可乐与生抽，中小火收汁。"),
    ("红烧排骨", "家常菜", "MEAT", 22.0, 40, "炒锅", ["排骨"], ["冰糖", "生抽", "葱姜蒜"], fv(0.05, 0.70, 0.20, 0.45, 0.80, 0.40, 0.65, 0.80), "排骨焯水；炒糖色后下排骨上色，加热水小火炖 30 分钟收汁。"),
    ("宫保鸡丁", "川湘菜", "MEAT", 14.0, 20, "炒锅", ["鸡胸肉", "花生"], ["干辣椒", "葱姜蒜"], fv(0.55, 0.60, 0.10, 0.50, 0.70, 0.75, 0.55, 0.75), "鸡丁腌制；爆香干辣椒，下鸡丁与花生快炒，淋入宫保汁。"),
    ("回锅肉", "川湘菜", "MEAT", 18.0, 30, "炒锅", ["五花肉", "青蒜"], ["豆瓣酱", "葱姜蒜"], fv(0.55, 0.85, 0.10, 0.45, 0.85, 0.55, 0.65, 0.85), "五花肉煮后切片；煸出油后加豆瓣酱与青蒜翻炒。"),
    ("清蒸鲈鱼", "家常菜", "MEAT", 25.0, 25, "炒锅", ["鲈鱼"], ["葱姜蒜", "蒸鱼豉油"], fv(0.00, 0.15, 0.15, 0.50, 0.55, 0.45, 0.60, 0.65), "鲈鱼处理干净放姜片；水开后蒸 10 分钟，淋豉油撒葱丝。"),
    ("白灼虾", "粤菜", "MEAT", 28.0, 12, "炒锅", ["鲜虾"], ["姜", "葱"], fv(0.00, 0.10, 0.10, 0.60, 0.40, 0.75, 0.55, 0.60), "水中加姜葱煮开；下虾煮至变色捞出，配蘸料。"),
    ("香菇滑鸡", "家常菜", "MEAT", 16.0, 25, "炒锅", ["鸡腿肉", "香菇"], ["葱姜蒜"], fv(0.10, 0.45, 0.30, 0.45, 0.70, 0.50, 0.55, 0.70), "鸡块腌制，香菇泡发；同炒后加水焖 15 分钟收汁。"),
    ("洋葱炒蛋", "家常菜", "VEG", 7.0, 10, "炒锅", ["洋葱", "鸡蛋"], ["盐"], fv(0.00, 0.35, 0.15, 0.50, 0.50, 0.85, 0.35, 0.60), "洋葱切丝，鸡蛋打散；先炒蛋盛出，再炒洋葱回锅。"),
    ("韭菜炒鸡蛋", "家常菜", "VEG", 7.0, 8, "炒锅", ["韭菜", "鸡蛋"], ["盐"], fv(0.10, 0.40, 0.10, 0.50, 0.50, 0.85, 0.35, 0.60), "韭菜切段，鸡蛋炒散；下韭菜大火快炒调味。"),
    ("酸辣白菜", "家常菜", "VEG", 5.0, 10, "炒锅", ["白菜"], ["干辣椒", "醋", "蒜"], fv(0.55, 0.35, 0.10, 0.55, 0.35, 0.80, 0.30, 0.50), "白菜切片；爆香蒜与干辣椒，大火快炒后淋醋。"),
    ("干煸豆角", "川湘菜", "VEG", 8.0, 15, "炒锅", ["豆角"], ["花椒", "干辣椒"], fv(0.50, 0.60, 0.05, 0.50, 0.40, 0.65, 0.40, 0.50), "豆角煸至表皮起皱；下花椒干辣椒炒香。"),
    ("蒜蓉生菜", "家常菜", "VEG", 5.0, 8, "炒锅", ["生菜"], ["蒜", "蚝油"], fv(0.00, 0.15, 0.05, 0.55, 0.30, 0.85, 0.30, 0.45), "蒜末爆香；下生菜大火快炒，淋蚝油出锅。"),
    ("西芹百合", "家常菜", "VEG", 8.0, 10, "炒锅", ["西芹", "百合"], ["盐"], fv(0.00, 0.15, 0.05, 0.55, 0.30, 0.80, 0.35, 0.45), "西芹切段、百合掰瓣焯水；大火快炒加盐。"),
    ("冬瓜排骨汤", "家常菜", "SOUP", 18.0, 45, "炒锅", ["冬瓜", "排骨"], ["葱姜蒜"], fv(0.00, 0.30, 0.95, 0.25, 0.55, 0.40, 0.50, 0.70), "排骨焯水后炖 30 分钟；下冬瓜再煮 10 分钟调味。"),
    ("番茄蛋汤", "家常菜", "SOUP", 6.0, 12, "炒锅", ["番茄", "鸡蛋"], ["葱", "盐"], fv(0.00, 0.20, 0.95, 0.35, 0.40, 0.85, 0.35, 0.60), "番茄炒软加水煮开；淋入蛋液，撒葱花。"),
    ("紫菜蛋花汤", "家常菜", "SOUP", 4.0, 8, "炒锅", ["紫菜", "鸡蛋"], ["虾皮", "盐"], fv(0.00, 0.10, 0.95, 0.30, 0.20, 0.90, 0.35, 0.55), "水开下紫菜虾皮；淋蛋液成蛋花，调味。"),
    ("玉米排骨汤", "家常菜", "SOUP", 20.0, 50, "炒锅", ["玉米", "排骨"], ["葱姜蒜"], fv(0.00, 0.30, 0.95, 0.25, 0.60, 0.40, 0.50, 0.75), "排骨焯水；与玉米同炖 40 分钟，加盐。"),
    ("菌菇鸡汤", "家常菜", "SOUP", 22.0, 45, "炒锅", ["菌菇", "鸡肉"], ["葱姜蒜"], fv(0.00, 0.20, 0.95, 0.25, 0.45, 0.40, 0.55, 0.70), "鸡肉焯水；与菌菇同炖 35 分钟，调味。"),
    ("电饭煲焖饭", "家常菜", "ONE_MEAL", 10.0, 35, "电饭煲", ["大米", "腊肠", "土豆"], ["生抽"], fv(0.10, 0.40, 0.10, 0.50, 0.80, 0.70, 0.50, 0.70), "食材切丁与米同入锅；加水按煮饭键，跳闸后焖 10 分钟。"),
    ("腊肠煲仔饭", "粤菜", "ONE_MEAL", 12.0, 40, "电饭煲", ["大米", "腊肠"], ["生抽", "青菜"], fv(0.10, 0.55, 0.10, 0.50, 0.85, 0.60, 0.50, 0.80), "米加水煮至半熟；铺腊肠继续焖，出锅淋豉油配青菜。"),
    ("电饭煲茶叶蛋", "家常菜", "ONE_MEAL", 6.0, 40, "电饭煲", ["鸡蛋", "茶叶"], ["生抽", "八角"], fv(0.00, 0.25, 0.05, 0.50, 0.40, 0.70, 0.45, 0.60), "鸡蛋煮熟敲裂；与茶叶香料同煮 20 分钟浸泡入味。"),
    ("电饭煲红烧肉", "家常菜", "MEAT", 20.0, 50, "电饭煲", ["五花肉"], ["冰糖", "生抽", "葱姜蒜"], fv(0.05, 0.75, 0.20, 0.45, 0.85, 0.40, 0.65, 0.85), "五花肉焯水；与调料同入电饭煲，煮饭键两次后收汁。"),
    ("电饭煲青菜粥", "家常菜", "ONE_MEAL", 5.0, 35, "电饭煲", ["大米", "青菜"], ["盐"], fv(0.00, 0.10, 0.95, 0.25, 0.40, 0.80, 0.30, 0.55), "大米加水煮粥；出锅前加青菜碎与盐。"),
    ("空气炸锅鸡翅", "家常菜", "MEAT", 16.0, 25, "空气炸锅", ["鸡翅"], ["生抽", "黑胡椒"], fv(0.20, 0.55, 0.05, 0.50, 0.60, 0.70, 0.65, 0.80), "鸡翅腌制 15 分钟；200 度烤 18 分钟中途翻面。"),
    ("空气炸锅薯条", "家常菜", "VEG", 5.0, 22, "空气炸锅", ["土豆"], ["盐", "番茄酱"], fv(0.00, 0.45, 0.05, 0.55, 0.60, 0.70, 0.50, 0.65), "土豆切条泡水沥干；拌油 200 度烤 18 分钟。"),
    ("空气炸锅烤茄子", "家常菜", "VEG", 7.0, 20, "空气炸锅", ["茄子"], ["蒜", "生抽"], fv(0.30, 0.40, 0.10, 0.50, 0.40, 0.70, 0.40, 0.60), "茄子剖开刷油；200 度烤 15 分钟，铺蒜蓉再烤 3 分钟。"),
    ("空气炸锅三文鱼", "家常菜", "MEAT", 30.0, 18, "空气炸锅", ["三文鱼"], ["黑胡椒", "柠檬"], fv(0.00, 0.20, 0.05, 0.60, 0.55, 0.70, 0.60, 0.65), "三文鱼抹盐黑胡椒；190 度烤 12 分钟，挤柠檬汁。"),
    ("凉拌黄瓜", "家常菜", "VEG", 4.0, 8, "免开火凉拌", ["黄瓜"], ["香菜", "蒜", "醋"], fv(0.35, 0.15, 0.05, 0.70, 0.30, 0.90, 0.40, 0.55), "黄瓜拍碎；加蒜末香菜醋拌匀。"),
    ("凉拌木耳", "家常菜", "VEG", 5.0, 10, "免开火凉拌", ["木耳"], ["香菜", "蒜", "醋"], fv(0.30, 0.10, 0.05, 0.70, 0.30, 0.90, 0.35, 0.50), "木耳泡发焯水过凉；加蒜香菜醋拌匀。"),
    ("凉拌豆腐丝", "家常菜", "VEG", 6.0, 8, "免开火凉拌", ["豆腐丝"], ["香菜", "花生", "醋"], fv(0.30, 0.20, 0.05, 0.65, 0.40, 0.90, 0.35, 0.50), "豆腐丝焯水过凉；加香菜花生与调料拌匀。"),
    ("凉拌鸡丝", "家常菜", "MEAT", 12.0, 12, "免开火凉拌", ["鸡胸肉"], ["香菜", "蒜", "生抽"], fv(0.30, 0.20, 0.05, 0.65, 0.50, 0.85, 0.40, 0.55), "鸡胸煮熟撕丝；加蒜末香菜生抽拌匀。"),
    ("一锅出番茄牛腩", "家常菜", "MEAT", 24.0, 45, ["炒锅", "一锅出"], ["牛腩", "番茄"], ["葱姜蒜"], fv(0.05, 0.45, 0.70, 0.35, 0.85, 0.40, 0.65, 0.85), "牛腩焯水；与番茄调料同入锅，小火炖 35 分钟。"),
    ("一锅出土豆炖鸡", "家常菜", "MEAT", 18.0, 40, "一锅出", ["鸡腿肉", "土豆"], ["葱姜蒜", "生抽"], fv(0.20, 0.50, 0.65, 0.35, 0.85, 0.40, 0.65, 0.80), "鸡块煎香；加土豆与调料，加水炖 25 分钟。"),
    ("一锅出咖喱饭", "家常菜", "ONE_MEAL", 14.0, 35, "一锅出", ["大米", "咖喱块", "土豆"], ["洋葱", "胡萝卜"], fv(0.25, 0.50, 0.50, 0.45, 0.90, 0.45, 0.60, 0.80), "蔬菜与鸡肉炒香加水；放咖喱块煮稠，浇在米饭上。"),
]

PERSONAS = [
    {
        "username": "chuan_yu",
        "nickname": "四川小熊猫",
        "avatar": "🌶️",
        "persona_title": "川渝麻辣派",
        "vector": fv(0.95, 0.85, 0.45, 0.50, 0.70, 0.55, 0.75, 0.80),
        "budget": 28.0,
        "veto": ["折耳根"],
        "cuisines": ["川湘菜", "麻辣烫"],
        "favorite": ["麻辣香锅", "水煮鱼"],
        "blacklist": ["白切鸡饭"],
    },
    {
        "username": "yue_cai",
        "nickname": "广州双马尾",
        "avatar": "🍵",
        "persona_title": "广府清淡爱汤派",
        "vector": fv(0.05, 0.20, 0.90, 0.50, 0.50, 0.45, 0.60, 0.65),
        "budget": 30.0,
        "veto": ["海鲜", "香菜"],
        "cuisines": ["粤菜", "粥粉面"],
        "favorite": ["老火靓汤", "白切鸡饭", "排骨莲藕汤"],
        "blacklist": ["麻辣香锅"],
    },
    {
        "username": "chi_tu",
        "nickname": "山西老醋坛",
        "avatar": "🍜",
        "persona_title": "晋面高饱腹派",
        "vector": fv(0.40, 0.35, 0.40, 0.65, 0.90, 0.55, 0.45, 0.50),
        "budget": 18.0,
        "veto": ["海鲜"],
        "cuisines": ["面食", "家常菜"],
        "favorite": ["兰州牛肉拉面", "青椒肉丝"],
        "blacklist": ["五花肉烤肉套餐"],
    },
    {
        "username": "jian_shen",
        "nickname": "河北热露露",
        "avatar": "🥟",
        "persona_title": "冀味咸香实在派",
        "vector": fv(0.20, 0.35, 0.50, 0.45, 0.85, 0.60, 0.55, 0.65),
        "budget": 20.0,
        "veto": ["海鲜"],
        "cuisines": ["面食", "家常菜"],
        "favorite": ["兰州牛肉拉面", "番茄炒蛋"],
        "blacklist": ["五花肉烤肉套餐"],
        "blacklist_restaurants": ["炭火烤肉屋"],
    },
]

FRIDGE = {
    "chuan_yu": [("牛肉", "肉禽蛋奶", 2), ("土豆", "新鲜果蔬", 5), ("面条", "豆制品与干货", 30)],
    "yue_cai": [("鸡蛋", "肉禽蛋奶", 2), ("青菜", "新鲜果蔬", 1), ("番茄", "新鲜果蔬", 3), ("豆腐", "豆制品与干货", 1)],
    "chi_tu": [("鸡蛋", "肉禽蛋奶", 4), ("大米", "豆制品与干货", 60)],
    "jian_shen": [("鸡胸肉", "肉禽蛋奶", 1), ("西兰花", "新鲜果蔬", 2), ("鸡蛋", "肉禽蛋奶", 5)],
}

LOGS = {
    "chuan_yu": [("麻辣香锅", 0, "雨", ["craving_heavy"]), ("水煮鱼", 3, "晴", []), ("兰州牛肉拉面", 6, "晴", [])],
    "yue_cai": [("白切鸡饭", 1, "晴", []), ("排骨莲藕汤", 2, "小雨", ["need_hot_soup"])],
    "chi_tu": [("麻辣烫套餐", 2, "晴", ["broke_end_month"]), ("兰州牛肉拉面", 5, "晴", [])],
    "jian_shen": [("鸡胸肉沙拉", 1, "晴", []), ("番茄炒蛋", 2, "晴", [])],
}

SNAPSHOT_PATH = Path(__file__).with_name("benchmark_snapshot.json")

# SSOT 第三章锁定的四个键与形状（R2-01 / R3-01 校验用）
BENCHMARK_KEYS = {
    "generated_at",
    "sample",
    "duplication_rate_curve",
    "group_satisfaction_bars",
}
SAMPLE_KEYS = {"personas", "days", "meals_per_day", "rooms", "members_per_room"}
CURVE_POINTS = 14
BAR_SERIES = ("avg_scores", "least_misery_scores")


class BenchmarkSnapshotError(RuntimeError):
    """快照缺失 / 结构不对 / 时间不合法 / 比库里旧——都必须在清库之前抛出。"""


def _reject_json_constant(value: str) -> None:
    raise BenchmarkSnapshotError(f"benchmark JSON 含不允许的常量 {value}")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BenchmarkSnapshotError(f"benchmark JSON 含重复键 {key!r}")
        result[key] = value
    return result


def _loads(text: str):
    try:
        return json.loads(
            text,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_unique_object,
        )
    except json.JSONDecodeError as exc:
        raise BenchmarkSnapshotError(f"benchmark JSON 解析失败：{exc}") from exc


def _read_payload(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise BenchmarkSnapshotError(f"快照不是 UTF-8 文本：{path}") from exc
    except OSError as exc:
        raise BenchmarkSnapshotError(f"无法读取快照 {path}：{exc}") from exc
    return _loads(text)


def _parse_generated_at(value: object, field: str = "generated_at") -> datetime:
    """把 ISO 8601 时间统一成带时区的 UTC 时刻。

    无时区时间按**运行环境本地时区**解释——生成端 `datetime.now()` 就是本地时间；
    带 `Z` / `+08:00` 等偏移的时间先归一化再比较，禁止用字符串字典序。
    """
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkSnapshotError(f"{field} 必须是非空 ISO 8601 字符串，收到 {value!r}")
    raw = value.strip()
    if raw.endswith(("Z", "z")):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise BenchmarkSnapshotError(f"{field} 不是合法的 ISO 8601 时间：{value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone(timezone.utc)


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BenchmarkSnapshotError(f"{field} 必须是数值，收到 {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise BenchmarkSnapshotError(f"{field} 必须是有限数值，收到 {value!r}")
    return number


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BenchmarkSnapshotError(f"{field} 必须是整数，收到 {value!r}")
    if value <= 0:
        raise BenchmarkSnapshotError(f"{field} 必须是正整数，收到 {value!r}")
    return value


def validate_benchmark(payload: object, *, allow_params: bool = False) -> dict:
    """校验四键结构与数值范围，不合法直接抛错（不是警告）。

    `allow_params=True` 用于导入完整仿真输出（四键 + `params`）；返回值始终只含
    SSOT 锁定的四个键，`params` 不会写进快照或 `algo_configs`。
    """
    if not isinstance(payload, dict):
        raise BenchmarkSnapshotError("benchmark 必须是 JSON 对象")
    keys = set(payload)
    allowed_sets = {frozenset(BENCHMARK_KEYS)}
    if allow_params:
        allowed_sets.add(frozenset(BENCHMARK_KEYS | {"params"}))
    if frozenset(keys) not in allowed_sets:
        allowed = sorted(BENCHMARK_KEYS | ({"params"} if allow_params else set()))
        raise BenchmarkSnapshotError(
            f"benchmark 键集合不对：{sorted(keys)}，要求 {allowed}"
            + ("（四键，或四键 + params）" if allow_params else "")
        )
    if "params" in payload and not isinstance(payload["params"], dict):
        raise BenchmarkSnapshotError("benchmark.params 必须是 JSON 对象")

    _parse_generated_at(payload["generated_at"])

    sample = payload["sample"]
    if not isinstance(sample, dict):
        raise BenchmarkSnapshotError("benchmark.sample 必须是 JSON 对象")
    if set(sample) != SAMPLE_KEYS:
        raise BenchmarkSnapshotError(
            f"benchmark.sample 键集合不对：{sorted(sample)}，要求 {sorted(SAMPLE_KEYS)}"
        )
    for field in SAMPLE_KEYS:
        _positive_int(sample[field], f"sample.{field}")

    curve = payload["duplication_rate_curve"]
    if not isinstance(curve, dict):
        raise BenchmarkSnapshotError("benchmark.duplication_rate_curve 必须是 JSON 对象")
    if set(curve) != {"days", "ours_lambda_0.5", "baseline_no_decay"}:
        raise BenchmarkSnapshotError(
            "benchmark.duplication_rate_curve 键集合不对："
            f"{sorted(curve)}"
        )
    days = curve["days"]
    if not isinstance(days, list) or len(days) != CURVE_POINTS:
        raise BenchmarkSnapshotError(
            f"duplication_rate_curve.days 应为 {CURVE_POINTS} 个点"
        )
    for index, day in enumerate(days, start=1):
        if isinstance(day, bool) or not isinstance(day, int) or day != index:
            raise BenchmarkSnapshotError(
                f"duplication_rate_curve.days 必须是 1..{CURVE_POINTS} 的连续整数，"
                f"第 {index} 项为 {day!r}"
            )
    for series in ("ours_lambda_0.5", "baseline_no_decay"):
        values = curve[series]
        if not isinstance(values, list) or len(values) != CURVE_POINTS:
            raise BenchmarkSnapshotError(
                f"duplication_rate_curve.{series} 应为 {CURVE_POINTS} 个点"
            )
        for index, value in enumerate(values, start=1):
            number = _number(value, f"duplication_rate_curve.{series}[{index}]")
            if not 0.0 <= number <= 1.0:
                raise BenchmarkSnapshotError(
                    f"duplication_rate_curve.{series}[{index}] 超出 0~1：{number}"
                )

    bars = payload["group_satisfaction_bars"]
    if not isinstance(bars, dict):
        raise BenchmarkSnapshotError("benchmark.group_satisfaction_bars 必须是 JSON 对象")
    if set(bars) != {"strategies", "avg_scores", "least_misery_scores"}:
        raise BenchmarkSnapshotError(
            f"benchmark.group_satisfaction_bars 键集合不对：{sorted(bars)}"
        )
    strategies = bars["strategies"]
    if not isinstance(strategies, list) or len(strategies) != 3:
        raise BenchmarkSnapshotError("group_satisfaction_bars.strategies 应为 3 项")
    if not all(isinstance(item, str) for item in strategies):
        raise BenchmarkSnapshotError("group_satisfaction_bars.strategies 必须全是字符串")
    mixed_prefix = "mixed_omega_"
    if not strategies[0].startswith(mixed_prefix):
        raise BenchmarkSnapshotError(
            f"第 1 个策略必须是 {mixed_prefix}<omega>，收到 {strategies[0]!r}"
        )
    omega_text = strategies[0][len(mixed_prefix):]
    try:
        omega_value = float(omega_text)
    except ValueError as exc:
        raise BenchmarkSnapshotError(
            f"mixed 策略的 omega 不是数值：{strategies[0]!r}"
        ) from exc
    if not math.isfinite(omega_value) or not 0.0 <= omega_value <= 1.0:
        raise BenchmarkSnapshotError(
            f"mixed 策略的 omega 超出 0~1：{strategies[0]!r}"
        )
    if strategies[1] != "average_omega_1.0":
        raise BenchmarkSnapshotError(
            f"第 2 个策略必须是 average_omega_1.0，收到 {strategies[1]!r}"
        )
    if strategies[2] != "random":
        raise BenchmarkSnapshotError(
            f"第 3 个策略必须是 random，收到 {strategies[2]!r}"
        )
    for series in BAR_SERIES:
        values = bars[series]
        if not isinstance(values, list) or len(values) != 3:
            raise BenchmarkSnapshotError(f"{series} 应为 3 项")
        for index, value in enumerate(values):
            number = _number(value, f"{series}[{index}]")
            if not 0.0 <= number <= 100.0:
                raise BenchmarkSnapshotError(f"{series}[{index}] 超出 0~100：{number}")
    return {
        key: payload[key]
        for key in (
            "generated_at",
            "sample",
            "duplication_rate_curve",
            "group_satisfaction_bars",
        )
    }


def load_benchmark(path: Optional[Path] = None) -> dict:
    path = Path(path) if path else SNAPSHOT_PATH
    if not path.exists():
        raise BenchmarkSnapshotError(
            f"缺少仿真快照 {path}，先跑 backend/algorithms/simulate_personas.py"
        )
    return validate_benchmark(_read_payload(path))


def _db_benchmark_generated_at(db: Session) -> Optional[str]:
    row = (
        db.query(AlgoConfig)
        .filter(AlgoConfig.config_name == "default_production")
        .one_or_none()
    )
    if row is None or row.benchmark_json is None:
        return None
    if not isinstance(row.benchmark_json, dict):
        raise BenchmarkSnapshotError("库内 benchmark_json 必须是 JSON 对象")
    generated_at = row.benchmark_json.get("generated_at")
    if generated_at is None or generated_at == "":
        raise BenchmarkSnapshotError("库内 benchmark.generated_at 缺失")
    return generated_at


def _db_benchmark_time(db: Session) -> Optional[datetime]:
    raw = _db_benchmark_generated_at(db)
    if raw is None:
        return None
    return _parse_generated_at(raw, "库内 benchmark.generated_at")


def ensure_benchmark_ready(
    db: Session,
    snapshot_path: Optional[Path] = None,
    incoming_path: Optional[Path] = None,
    allow_stale: bool = False,
) -> dict:
    """**破坏性操作之前**的唯一入口：校验 → 落后检查 → 持久化。

    顺序是硬约束（R3-01）：incoming 与当前快照、库内时间的全部检查通过之后，
    才允许写快照；任何拒绝路径都保证数据库与目标快照未被改动。
    `--allow-stale-benchmark` 只跳过“比库内旧”的比较，不跳过结构与时间合法性校验。
    """
    target = Path(snapshot_path) if snapshot_path else SNAPSHOT_PATH
    db_time = _db_benchmark_time(db)

    if incoming_path:
        incoming_path = Path(incoming_path)
        fresh = validate_benchmark(_read_payload(incoming_path), allow_params=True)
        fresh_time = _parse_generated_at(
            fresh["generated_at"], "incoming.generated_at"
        )
        if target.exists():
            current = load_benchmark(target)
            current_time = _parse_generated_at(
                current["generated_at"], "当前快照 generated_at"
            )
            if fresh_time < current_time:
                raise BenchmarkSnapshotError(
                    "待刷新的快照比现有快照更旧："
                    f"{fresh['generated_at']} < {current['generated_at']}"
                )
        if not allow_stale and db_time is not None and fresh_time < db_time:
            raise BenchmarkSnapshotError(
                "拒绝用旧快照覆盖较新的库内曲线："
                f"快照 {fresh['generated_at']} < 库内 "
                f"{_db_benchmark_generated_at(db)}"
                "（若确要用旧快照，加 --allow-stale-benchmark）"
            )
        # 所有检查通过后才持久化；先把内容写到 tmp 并回读校验，再替换目标。
        # 这样即使写入/替换失败，目标快照也保持原样。
        tmp = target.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(fresh, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            check = load_benchmark(tmp)
            if check["generated_at"] != fresh["generated_at"]:
                raise BenchmarkSnapshotError("刷新写入回读不一致，快照未替换")
            tmp.replace(target)
        finally:
            if tmp.exists():
                tmp.unlink()
        reloaded = load_benchmark(target)
        if reloaded["generated_at"] != fresh["generated_at"]:
            raise BenchmarkSnapshotError("刷新后回读不一致，快照未真正落盘")
        print(f"[benchmark] 快照已刷新 -> {target} @ {reloaded['generated_at']}")
        return reloaded

    payload = load_benchmark(target)
    payload_time = _parse_generated_at(
        payload["generated_at"], "快照 generated_at"
    )
    if not allow_stale and db_time is not None and payload_time < db_time:
        raise BenchmarkSnapshotError(
            "拒绝用旧快照覆盖较新的库内曲线："
            f"快照 {payload['generated_at']} < 库内 "
            f"{_db_benchmark_generated_at(db)}"
            "（若确要用旧快照，加 --allow-stale-benchmark）"
        )
    return payload


def _clear_all(db: Session) -> None:
    for model in (
        RoomVote,
        GroupRoom,
        EatingLog,
        FridgeInventory,
        UserPreference,
        Dish,
        Restaurant,
        AlgoConfig,
        User,
    ):
        db.query(model).delete()
    db.commit()


def seed_all(
    db: Session,
    now: Optional[datetime] = None,
    benchmark: Optional[dict] = None,
) -> Dict[str, int]:
    now = now or utcnow()
    benchmark = benchmark or load_benchmark()
    restaurants: List[Restaurant] = []
    # 种子门店必须带校区：外食推荐按 campus 过滤（v2.3.4），
    # 不写 campus 的话，新库跑完这个脚本，任一校区的外食候选都是 0，
    # 只能再手工跑迁移脚本补救（tests/conftest.py 就是靠改校区才跑通的）。
    # 种子坐标是演示值、不落在任一校区真实中心，所以按序号对半分，
    # 保证两个校区都有数据可演示。
    campus_split = len(RESTAURANTS) // 2
    for index, (
        name,
        source_type,
        category,
        avg_price,
        rating,
        lon,
        lat,
        distance,
        address,
    ) in enumerate(RESTAURANTS):
        restaurant = Restaurant(
            name=name,
            source_type=source_type,
            category=category,
            avg_price=avg_price,
            rating=rating,
            longitude=lon,
            latitude=lat,
            distance_meters=distance,
            address=address,
            campus=("SIYUAN" if index < campus_split else "JIANDA_YANTA"),
        )
        db.add(restaurant)
        restaurants.append(restaurant)
    db.flush()

    dish_by_name: Dict[str, Dish] = {}
    restaurant_by_name: Dict[str, Restaurant] = {r.name: r for r in restaurants}
    for name, cuisine, role, price, mains, aux, vector, restaurant_index in OUT_DISHES:
        dish = Dish(
            name=name,
            mode_type=OUT_DINING,
            restaurant_id=restaurants[restaurant_index].id,
            cuisine_type=cuisine,
            dish_role=role,
            price_or_cost=price,
            cook_minutes=15,
            appliance_tag=["炒锅"],
            ingredients_main=mains,
            ingredients_aux=aux,
            recipe_steps="",
            feature_vector=vector,
            # 未下载/无合适图时为 None（前端走无图占位），不许拿别的菜顶
            image_url=DISH_IMAGE_PATHS.get(name),
        )
        db.add(dish)
        dish_by_name.setdefault(name, dish)

    for (
        name,
        cuisine,
        role,
        cost,
        minutes,
        appliance,
        mains,
        aux,
        vector,
        steps,
    ) in HOME_DISHES:
        dish = Dish(
            name=name,
            mode_type=HOME_COOKING,
            restaurant_id=None,
            cuisine_type=cuisine,
            dish_role=role,
            price_or_cost=cost,
            cook_minutes=minutes,
            # v2.3.1：appliance_tag 为 JSON 数组，历史单值在此统一升为单元素数组
            appliance_tag=[appliance] if isinstance(appliance, str) else list(appliance),
            ingredients_main=mains,
            ingredients_aux=aux,
            recipe_steps=steps,
            feature_vector=vector,
            image_url=DISH_IMAGE_PATHS.get(name),
        )
        db.add(dish)
        dish_by_name.setdefault(name, dish)
    db.flush()

    for persona in PERSONAS:
        user = User(
            username=persona["username"],
            nickname=persona["nickname"],
            avatar=persona["avatar"],
            persona_title=persona["persona_title"],
            is_demo_persona=True,
            created_at=now,
        )
        db.add(user)
        db.flush()
        prefs = UserPreference(
            user_id=user.id,
            base_vector=persona["vector"],
            default_budget=persona["budget"],
            veto_tags=persona["veto"],
            preferred_cuisines=persona["cuisines"],
            favorite_dish_ids=[
                dish_by_name[name].id
                for name in persona["favorite"]
                if name in dish_by_name
            ],
            blacklist_dish_ids=[
                dish_by_name[name].id
                for name in persona["blacklist"]
                if name in dish_by_name
            ],
            # v2.3.1：门店黑榜，外食模式下整店剔除
            blacklist_restaurant_ids=[
                restaurant_by_name[name].id
                for name in persona.get("blacklist_restaurants", [])
                if name in restaurant_by_name
            ],
        )
        db.add(prefs)

        for ingredient, category, expire_days in FRIDGE.get(persona["username"], []):
            db.add(
                FridgeInventory(
                    user_id=user.id,
                    ingredient_name=ingredient,
                    category=category,
                    quantity_desc="适量",
                    expire_days=expire_days,
                    created_at=now,
                )
            )

        for dish_name, days_ago, weather, bubbles in LOGS.get(persona["username"], []):
            dish = dish_by_name.get(dish_name)
            if dish is None:
                continue
            db.add(
                EatingLog(
                    user_id=user.id,
                    dish_id=dish.id,
                    mode_type=dish.mode_type,
                    cost_amount=float(dish.price_or_cost or 0.0),
                    weather_snapshot=weather,
                    status_bubbles=bubbles,
                    eaten_at=now - timedelta(days=days_ago),
                )
            )

    db.add(
        AlgoConfig(
            config_name="default_production",
            lambda_decay=0.5,
            omega_group=0.5,
            alpha_taste=0.35,
            beta_weather=0.25,
            gamma_budget=0.20,
            delta_status=0.20,
            benchmark_json=benchmark,
        )
    )
    db.commit()

    return {
        "restaurants": len(RESTAURANTS),
        "out_dining_dishes": len(OUT_DISHES),
        "home_cooking_dishes": len(HOME_DISHES),
        "dishes": len(OUT_DISHES) + len(HOME_DISHES),
        "users": len(PERSONAS),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化食刻演示数据库")
    parser.add_argument("--force", action="store_true", help="清空现有数据后重建")
    parser.add_argument(
        "--benchmark-from",
        type=Path,
        default=None,
        help=(
            "用这份仿真结果刷新 benchmark 快照后再播种；可直接传完整仿真输出"
            "（四键 + params，params 会被剥离），会校验并与库内曲线比较新旧"
        ),
    )
    parser.add_argument(
        "--allow-stale-benchmark",
        action="store_true",
        help="允许用比库内更旧的快照覆盖（默认拒绝；结构与时间合法性仍校验）",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        help="使用指定快照文件（默认 backend/scripts/benchmark_snapshot.json，隔离复验用）",
    )
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(User).count()
        if existing and not args.force:
            print(f"数据库已有 {existing} 个用户，跳过。使用 --force 重建。")
            return
        # R2-01：任何清库动作之前，先刷新并校验快照；失败就在破坏数据前中止。
        benchmark = ensure_benchmark_ready(
            db,
            snapshot_path=args.snapshot,
            incoming_path=args.benchmark_from,
            allow_stale=args.allow_stale_benchmark,
        )
        if args.force:
            _clear_all(db)
        counts = seed_all(db, benchmark=benchmark)
        print(
            "种子数据完成: "
            f"门店 {counts['restaurants']} 家, "
            f"外食菜品 {counts['out_dining_dishes']} 道, "
            f"家常菜谱 {counts['home_cooking_dishes']} 道, "
            f"演示角色 {counts['users']} 个。"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
