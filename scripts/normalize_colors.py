"""把前端里散落的颜色字面量归并到设计令牌（F12）。

规则（`AGENTS.md` 的「颜色只有一个出口」）：
- 组件与页面（`.vue` / `.js`）里只允许 `var(--…)`、`transparent`、`currentColor`；
- 颜色字面量只能出现在令牌出口：`src/styles/*.css`、`src/utils/theme.js`、
  `tailwind.config.js`，以及上游原样接入的 `components/bits/`（改不了别人的 shader）。

本脚本做机械化搬移，做完仍要看一遍 diff——脚本不懂设计意图。

用法：
    python scripts/normalize_colors.py            # 只报告，不改文件
    python scripts/normalize_colors.py --write    # 落盘
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "src"

# 允许出现颜色字面量的“令牌出口”
TOKEN_LAYERS = (
    "styles/",
    "utils/theme.js",
    "components/bits/",
)

RGB_TOKENS = {
    (255, 255, 255): "white",
    (0, 0, 0): "black",
    (23, 23, 26): "ink",
    (85, 85, 94): "steel",
    (244, 244, 245): "mist",
    (212, 212, 216): "silver",
    (58, 58, 64): "grain-a",
    (85, 85, 94): "steel",
    (26, 26, 26): "chrome",
    (34, 34, 38): "chrome-max",
    (18, 18, 21): "panel",
    (16, 16, 19): "sheet",
}

HEX_TOKENS = {
    "#17171a": "var(--color-ink)",
    "#55555e": "var(--color-steel)",
    "#ffffff": "var(--color-white)",
    "#fff": "var(--color-white)",
    "#f4f4f5": "var(--color-mist)",
    "#d4d4d8": "var(--color-silver)",
    "#e4e4e7": "var(--color-mist)",
    "#3a3a40": "var(--color-grain-a)",
    "#222226": "var(--color-chrome-max)",
    "#1a1a1a": "var(--color-chrome)",
    "#212121": "var(--color-ink)",
    "#a1a1aa": "var(--color-steel)",
    "#000000": "var(--color-black)",
    "#000": "var(--color-black)",
}

FUNC_RE = re.compile(r"rgba?\(\s*([^)]*?)\s*\)")
HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def _split_args(body: str) -> tuple[list[int], float | None]:
    if "/" in body:
        head, _, alpha = body.partition("/")
        parts = re.split(r"[\s,]+", head.strip())
        return [int(float(p)) for p in parts if p], float(alpha.strip())
    parts = [p for p in re.split(r"[\s,]+", body.replace(",", " ")) if p]
    nums = [float(p) for p in parts]
    if len(nums) == 4:
        return [int(n) for n in nums[:3]], nums[3]
    return [int(n) for n in nums[:3]], None


def _rewrite_rgb(match: re.Match[str]) -> str:
    if "var(--" in match.group(1):
        # 已经是令牌组合，别再动它
        return match.group(0)
    try:
        triple, alpha = _split_args(match.group(1))
    except (ValueError, IndexError):
        return match.group(0)
    token = RGB_TOKENS.get(tuple(triple))
    if token is None:
        return match.group(0)
    if alpha is None or abs(alpha - 1.0) < 1e-9:
        return f"rgb(var(--rgb-{token}))"
    text = ("%g" % alpha).rstrip("0").rstrip(".")
    return f"rgb(var(--rgb-{token}) / {text})"


def _rewrite_hex(match: re.Match[str]) -> str:
    return HEX_TOKENS.get(match.group(0).lower(), match.group(0))


def transform(text: str) -> str:
    return HEX_RE.sub(_rewrite_hex, FUNC_RE.sub(_rewrite_rgb, text))


def target_files() -> list[Path]:
    files = [*SRC.rglob("*.vue"), *SRC.rglob("*.js")]
    keep = []
    for path in files:
        rel = path.relative_to(SRC).as_posix()
        if any(rel.startswith(layer) for layer in TOKEN_LAYERS):
            continue
        keep.append(path)
    return sorted(keep)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="真正写回文件")
    args = parser.parse_args()

    changed = 0
    leftovers: list[str] = []
    for path in target_files():
        text = path.read_text(encoding="utf-8")
        new = transform(text)
        if new != text:
            changed += 1
            if args.write:
                path.write_text(new, encoding="utf-8")
        for match in FUNC_RE.findall(new):
            if "var(--" in match:
                continue
            leftovers.append(f"{path.relative_to(ROOT)}: rgb({match})")
        for match in HEX_RE.findall(new):
            leftovers.append(f"{path.relative_to(ROOT)}: {match}")

    print(f"{'WROTE' if args.write else 'DRY-RUN'}: {changed} 个文件需要改写")
    if leftovers:
        print("仍未归并（需要人工判断语义）：")
        for item in leftovers:
            print("  -", item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
