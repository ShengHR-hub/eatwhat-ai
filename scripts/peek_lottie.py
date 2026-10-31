"""查看单个 Lottie JSON 的片段：颜色写法 + 文本层内容。"""
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "frontend/src/assets/lottie/empty-state.json"
raw = open(path, encoding="utf-8").read()
i = raw.find('"c"')
print("--- around first color ---")
print(raw[max(0, i - 100) : i + 240])

d = json.loads(raw)
print("--- text layers ---")
for layer in d.get("layers", []):
    t = layer.get("t")
    if t:
        print(json.dumps(t, ensure_ascii=False)[:400])
print("--- fonts ---")
print(json.dumps(d.get("fonts", {}), ensure_ascii=False)[:300])
