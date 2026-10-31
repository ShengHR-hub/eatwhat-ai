"""生成空状态 Lottie（自绘）：一只空碗 + 三个上浮的小点。

为什么自绘：LottieFiles 的下载页要登录且被 Cloudflare 拦，本机取不到件；
meteocons（MIT）只有天气/气象图标，没有"空盘子"这种语义。
所以空状态这张图由本项目自绘，授权跟随仓库（MIT），JSON 全文本、可审计。

用法（仓库根）：python scripts/make_empty_state_lottie.py
输出：frontend/src/assets/lottie/empty-state.json
"""

import json
import math
from pathlib import Path

W = H = 128
OUT = Path("frontend/src/assets/lottie/empty-state.json")

# 碗：上宽下窄的圆角梯形，用贝塞尔近似
BOWL = {
    "v": [[28, 62], [100, 62], [92, 96], [64, 104], [36, 96]],
    "i": [[0, 0], [0, 0], [0, 8], [-6, 4], [-6, -4]],
    "o": [[0, 0], [0, 0], [0, 0], [6, 4], [6, -4]],
    "c": True,
}

# 碗沿：一条横线（用细长矩形表示）
RIM = {
    "v": [[26, 58], [102, 58], [102, 62], [26, 62]],
    "i": [[0, 0], [0, 0], [0, 0], [0, 0]],
    "o": [[0, 0], [0, 0], [0, 0], [0, 0]],
    "c": True,
}


def shape_layer(name, path, color, opacity=100, index=1):
    return {
        "ddd": 0,
        "ind": index,
        "ty": 4,
        "nm": name,
        "sr": 1,
        "ks": {
            "o": {"a": 0, "k": opacity},
            "r": {"a": 0, "k": 0},
            "p": {"a": 0, "k": [0, 0, 0]},
            "a": {"a": 0, "k": [0, 0, 0]},
            "s": {"a": 0, "k": [100, 100, 100]},
        },
        "ao": 0,
        "shapes": [
            {
                "ty": "gr",
                "it": [
                    {"ty": "sh", "ks": {"a": 0, "k": path}, "nm": "path"},
                    {
                        "ty": "st",
                        "c": {"a": 0, "k": color},
                        "o": {"a": 0, "k": 100},
                        "w": {"a": 0, "k": 3},
                        "lc": 2,
                        "lj": 2,
                        "nm": "stroke",
                    },
                    {"ty": "tr", "p": {"a": 0, "k": [0, 0]}, "a": {"a": 0, "k": [0, 0]},
                     "s": {"a": 0, "k": [100, 100]}, "r": {"a": 0, "k": 0}, "o": {"a": 0, "k": 100}},
                ],
                "nm": "group",
            }
        ],
        "ip": 0,
        "op": 60,
        "st": 0,
        "bm": 0,
    }


def bubble_layer(index, x, delay, radius):
    """上浮小圆点：从碗口升起、边升边淡出。"""
    def kf(t, value, easing=0):
        return {"t": t, "s": [value], "i": {"x": [0.4], "y": [1]}, "o": {"x": [0.6], "y": [0]}}

    return {
        "ddd": 0,
        "ind": index,
        "ty": 4,
        "nm": f"Dot {index}",
        "sr": 1,
        "ks": {
            "o": {
                "a": 1,
                "k": [
                    {"t": 0, "s": [0], "i": {"x": [0.4], "y": [1]}, "o": {"x": [0.6], "y": [0]}},
                    {"t": 8 + delay, "s": [90], "i": {"x": [0.4], "y": [1]}, "o": {"x": [0.6], "y": [0]}},
                    {"t": 44 + delay, "s": [0]},
                ],
            },
            "r": {"a": 0, "k": 0},
            "p": {
                "a": 1,
                "k": [
                    {"t": 0, "s": [x, 70, 0], "to": [0, -1.6, 0], "ti": [0, 0, 0]},
                    {"t": 44 + delay, "s": [x, 34, 0]},
                ],
            },
            "a": {"a": 0, "k": [0, 0, 0]},
            "s": {"a": 0, "k": [100, 100, 100]},
        },
        "ao": 0,
        "shapes": [
            {
                "ty": "gr",
                "it": [
                    {
                        "ty": "el",
                        "p": {"a": 0, "k": [0, 0]},
                        "s": {"a": 0, "k": [radius * 2, radius * 2]},
                        "nm": "ellipse",
                    },
                    {"ty": "fl", "c": {"a": 0, "k": [0, 0, 0, 1]}, "o": {"a": 0, "k": 100}, "r": 1, "nm": "fill"},
                    {"ty": "tr", "p": {"a": 0, "k": [0, 0]}, "a": {"a": 0, "k": [0, 0]},
                     "s": {"a": 0, "k": [100, 100]}, "r": {"a": 0, "k": 0}, "o": {"a": 0, "k": 100}},
                ],
                "nm": "group",
            }
        ],
        "ip": 0,
        "op": 60,
        "st": 0,
        "bm": 0,
    }


doc = {
    "v": "5.7.4",
    "fr": 30,
    "ip": 0,
    "op": 60,
    "w": W,
    "h": H,
    "nm": "eatwhat-empty-bowl",
    "ddd": 0,
    "assets": [],
    "layers": [
        bubble_layer(4, 50, 6, 3.4),
        bubble_layer(3, 64, 0, 4.2),
        bubble_layer(2, 78, 12, 3.0),
        shape_layer("Bowl", BOWL, [0, 0, 0, 1], index=3),
        shape_layer("Rim", RIM, [0, 0, 0, 1], index=1),
    ],
    "markers": [],
    "meta": {"g": "EatWhat 自绘（MIT）"},
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("wrote", OUT, OUT.stat().st_size, "bytes")
