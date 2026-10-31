"""扫描 r02 证据目录，把环境变量 AMAP_API_KEY 的值替换为 <redacted>；不打印 Key。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
DATA = PACK / "data"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    key = os.getenv("AMAP_API_KEY", "").strip()
    if not key:
        print("AMAP_API_KEY missing in process environment")
        return 1
    changed = []
    for p in sorted(PACK.rglob("*")):
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if key in text:
            n = text.count(key)
            p.write_text(text.replace(key, "<redacted>"), encoding="utf-8")
            changed.append({"path": str(p.relative_to(PACK)).replace("\\", "/"), "occurrences": n})
    report = {"changed": changed, "note": "Key value was replaced; no key is printed."}
    (DATA / "key_redaction_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
