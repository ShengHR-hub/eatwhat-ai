"""打印 Lottie 里所有填充/描边颜色（ty=fl / ty=st 后面的 c.k）。"""
import glob
import json


def walk(node, out):
    if isinstance(node, dict):
        if node.get("ty") in ("fl", "st") and isinstance(node.get("c"), dict):
            out.append((node.get("ty"), node["c"].get("k")))
        for v in node.values():
            walk(v, out)
    elif isinstance(node, list):
        for v in node:
            walk(v, out)


for f in sorted(glob.glob("frontend/src/assets/lottie/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    out = []
    walk(d, out)
    print(f)
    for ty, k in out:
        print("  ", ty, k)
