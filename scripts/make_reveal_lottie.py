"""生成揭晓页的 Lottie 插画 `frontend/src/assets/lottie/reveal.json`。

做法：直接**克隆 `empty-state.json` 里已验证可渲染的圆点图层**（`el` + `fl` + `tr`
这一套），只改名字、位置、大小与不透明度关键帧。之前自己从零拼 `rc`/`st`
图层，lottie-web 要么整层不渲染、要么画出一整块灰方块，所以这次不冒险。

图形：中心一个实心点 + 外圈 8 个点依次淡入，60 帧 @30fps，停播后保持最后一帧。
圆点使用静态坐标，只动画透明度；多段位置轨道在当前 light 播放器中会把图层移到 -999999。
点色纯黑（`[0,0,0,1]`），组件里统一 `filter: invert(1)` 反白，与天气图标一致。
"""

import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "src" / "assets" / "lottie" / "empty-state.json"
OUT = ROOT / "frontend" / "src" / "assets" / "lottie" / "reveal.json"

FRAMES = 60
CX = CY = 64
ORBIT = 26
DOTS = 8
EASE = {"i": {"x": [0.4], "y": [1]}, "o": {"x": [0.6], "y": [0]}}

src = json.loads(SRC.read_text(encoding="utf-8"))
template = src["layers"][0]


def dot_layer(index: int, x: float, y: float, size: float, appear: int) -> dict:
    """一个固定位置的圆点：按 appear 延迟淡入，随后保持可见。"""
    layer = copy.deepcopy(template)
    layer["ind"] = index
    layer["nm"] = f"dot-{index}"
    layer["ks"]["o"] = {
        "a": 1,
        "k": [
            {"t": 0, "s": [0], **EASE},
            {"t": appear, "s": [0], **EASE},
            {"t": appear + 8, "s": [90]},
        ],
    }
    layer["ks"]["r"] = {"a": 0, "k": 0}
    layer["ks"]["p"] = {"a": 0, "k": [x, y, 0]}
    layer["ks"]["a"] = {"a": 0, "k": [0, 0, 0]}
    layer["ks"]["s"] = {"a": 0, "k": [100, 100, 100]}
    layer["shapes"][0]["it"][0]["s"] = {"a": 0, "k": [size, size]}
    return layer


layers = [dot_layer(1, CX, CY, 11.0, 2)]

for i in range(DOTS):
    angle = math.radians((360 / DOTS) * i - 90)
    x = CX + math.cos(angle) * ORBIT
    y = CY + math.sin(angle) * ORBIT
    layers.append(dot_layer(i + 2, x, y, 4.6, 6 + i))

data = {
    "v": "5.9.0",
    "fr": 30,
    "ip": 0,
    "op": FRAMES,
    "w": 128,
    "h": 128,
    "nm": "reveal",
    "ddd": 0,
    "assets": [],
    "layers": layers,
    "markers": [],
}

OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(layers)} layers)")
