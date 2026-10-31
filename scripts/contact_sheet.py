"""把 frontend/public/dishes/ 的成品图拼成带标签的接触印样，供人工挑错。

用法：python scripts/contact_sheet.py [每行张数] [每张宽]
产物：docs/review/dishes/dishes-sheet-1.png ...（每 24 张一张）
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("frontend/public/dishes")
LEDGER = Path("docs/_data/image_ledger.json")
DEST = Path("docs/review/dishes")

per_row = int(sys.argv[1]) if len(sys.argv) > 1 else 4
cell_w = int(sys.argv[2]) if len(sys.argv) > 2 else 300
cell_h = int(cell_w * 9 / 16) + 26
per_sheet = per_row * int(per_row * 1.5) or 24

ledger = {}
if LEDGER.exists():
    ledger = {e["file"]: e for e in json.loads(LEDGER.read_text(encoding="utf-8"))}

files = sorted(p for p in OUT.glob("*.jpg"))
if not files:
    raise SystemExit("还没有成品图")

try:
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 15)
except Exception:  # noqa: BLE001
    font = ImageFont.load_default()

rows = math.ceil(len(files) / per_row)
sheets = math.ceil(len(files) / per_sheet)
DEST.mkdir(parents=True, exist_ok=True)

page = 0
for s in range(sheets):
    chunk = files[s * per_sheet : (s + 1) * per_sheet]
    n_rows = math.ceil(len(chunk) / per_row)
    canvas = Image.new("RGB", (per_row * cell_w, n_rows * cell_h), (24, 24, 27))
    draw = ImageDraw.Draw(canvas)
    for i, path in enumerate(chunk):
        img = Image.open(path).convert("RGB").resize((cell_w, int(cell_w * 9 / 16)), Image.LANCZOS)
        x = (i % per_row) * cell_w
        y = (i // per_row) * cell_h
        canvas.paste(img, (x, y))
        meta = ledger.get(path.name, {})
        label = f'{meta.get("name", "?")}  {path.name[:18]}'
        draw.text((x + 6, y + cell_w * 9 / 16 + 4), label, fill=(235, 235, 240), font=font)
    page += 1
    out = DEST / f"dishes-sheet-{page}.png"
    canvas.save(out, "PNG", optimize=True)
    print(out, canvas.size, f"({len(chunk)} imgs)")

print("total", len(files), "ledger", len(ledger))
