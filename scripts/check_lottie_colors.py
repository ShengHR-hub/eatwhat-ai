"""检查 Lottie JSON 里用到的颜色（判断是否需要反色）。"""
import glob
import json
import re

for f in sorted(glob.glob("frontend/src/assets/lottie/*.json")):
    s = open(f, encoding="utf-8").read()
    colors = set(re.findall(r'"k":\s*\[\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\s*\]', s))
    uniq = sorted({tuple(round(float(x), 3) for x in c) for c in colors})
    print(f, len(uniq), uniq[:6])
    d = json.load(open(f, encoding="utf-8"))
    print("   layers:", [layer.get("nm") for layer in d.get("layers", [])])
