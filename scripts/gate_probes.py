"""F12 颜色门禁反例探针（R2-04 / R2-05 / R3-02）。

不往真实 `frontend/src` 注入测试文件：复制同一份 checker 到
`docs/review/stages/PC03/r04/sandbox/`，保持 `frontend/src` 相对布局，
逐例运行真实 Node 子进程并断言退出码，最后清理探针文件。

用法：
    python scripts/gate_probes.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "docs" / "review" / "stages" / "PC03" / "r04"
SANDBOX = PACK / "sandbox"
SRC = SANDBOX / "frontend" / "src"

CASES = [
    # R2-04：不能被整行跳过
    ("wildcard", "styles/probe_wildcard.css", "* { color: #ff0000; }\n", 1),
    (
        "comment_then_code",
        "styles/probe_comment.css",
        "/* normal comment */ .x { color: #ff0000; }\n",
        1,
    ),
    (
        "token_then_code",
        "styles/probe_token.css",
        "--approved: #ffffff; .y { color: #ff0000; }\n",
        1,
    ),
    (
        "multiline_comment_then_code",
        "styles/probe_multi.css",
        "/* line one\n   line two */ .z { background: rgba(255, 0, 0, 0.4); }\n",
        1,
    ),
    # R2-05：非主题出口不能自造裸色令牌
    (
        "local_token_in_component",
        "components/bits/ProbeBusiness.vue",
        '<template><div class="x">x</div></template>\n'
        "<style scoped>\n.x { --local-red: #ff0000; color: var(--local-red); }\n</style>\n",
        1,
    ),
    (
        "alias_ok",
        "styles/probe_alias.css",
        ":root { --x-alias: var(--color-ink); }\n.a { color: var(--x-alias); }\n",
        0,
    ),
    # R3-02：JS 正则不能把后续裸色吞掉
    (
        "js_regex_then_color",
        "probe_regex.js",
        'const pattern = /[/*]/; const color = "#ff0000";\nexport { pattern, color };\n',
        1,
    ),
    # R3-02：CSS url() 里的 // 不能把后续裸色吞掉
    (
        "css_url_then_color",
        "styles/probe_url.css",
        ".x{background-image:url(https://example.com//a.png);color:#ff0000;}\n",
        1,
    ),
    # R3-02：Vue template 注释必须被正确忽略
    (
        "vue_html_comment_ok",
        "components/ProbeComment.vue",
        "<template><!-- color:#ff0000 --><p>ok</p></template>\n",
        0,
    ),
    # 合法 JS 的正则 / 除号 / 字符串不能误报，也不能被当成注释
    (
        "js_division_and_strings_ok",
        "probe_legal.js",
        'const ratio = 10 / 2; const url = "https://example.com//a";\n'
        "const re = /a\\/b/g; export { ratio, url, re };\n",
        0,
    ),
    # 合法 CSS 注释里的 URL / 色值字样不误报
    (
        "css_comment_url_ok",
        "styles/probe_comment_url.css",
        "/* url(https://example.com//a.png) color:#ff0000 */\n"
        ".x { color: var(--color-ink); }\n",
        0,
    ),
    # Vue script / style 块分别按 JS / CSS 词法处理
    (
        "vue_script_regex_then_color",
        "components/ProbeScript.vue",
        '<template><p>ok</p></template>\n<script setup>\n'
        'const re = /[/*]/; const color = "#ff0000";\n</script>\n',
        1,
    ),
    (
        "vue_style_url_then_color",
        "components/ProbeStyle.vue",
        '<template><p>ok</p></template>\n<style scoped>\n'
        ".x{background:url(https://example.com//a.png);color:#ff0000}\n</style>\n",
        1,
    ),
    # 旧反例保留：RGB / HSLA 大小写、非上游 bits、普通 Vue / JS 裸色
    ("uppercase_hex", "styles/probe_upper.css", ".x { color: #ABCDEF; }\n", 1),
    ("uppercase_rgb", "styles/probe_rgb.css", ".x { color: RGB(255 0 0); }\n", 1),
    ("uppercase_hsla", "styles/probe_hsla.css", ".x { color: HSLA(10,20%,30%,.5); }\n", 1),
    (
        "non_upstream_bits",
        "components/bits/BusinessCard.vue",
        "<template><div>x</div></template>\n<style scoped>.x{color:#00ff00}</style>\n",
        1,
    ),
    (
        "plain_vue_inline_style",
        "components/ProbeInline.vue",
        '<template><div style="color:#ff0000" /></template>\n',
        1,
    ),
    ("plain_js_literal", "probe_literal.js", 'export const color = "#ff0000"\n', 1),
    # 主题出口：多行令牌结束后同行的业务声明仍要查
    (
        "theme_multiline_token_then_code",
        "styles/main.css",
        ":root {\n  --probe-token:\n    #ffffff;\n}\n.x { color: #ff0000; }\n",
        1,
    ),
    (
        "theme_token_only_ok",
        "styles/main.css",
        ":root { --probe-token: #ffffff; }\n.x { color: var(--probe-token); }\n",
        0,
    ),
    # 精确上游豁免：同名目录里的其它文件不豁免
    (
        "upstream_exact_file_ok",
        "components/bits/Grainient.vue",
        '<template><div style="color:#ff0000">x</div></template>\n',
        0,
    ),
    # JS→CSS 桥文件本身豁免
    (
        "theme_bridge_ok",
        "utils/theme.js",
        'export const ink = readVar("--color-ink", "#17171A")\n',
        0,
    ),
]


def run_checker() -> tuple[int, str]:
    proc = subprocess.run(
        ["node", "scripts/check-colors.mjs"],
        cwd=SANDBOX,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    (SANDBOX / "scripts").mkdir(parents=True)
    SRC.mkdir(parents=True)
    shutil.copy2(ROOT / "scripts" / "check-colors.mjs", SANDBOX / "scripts" / "check-colors.mjs")

    baseline_code, baseline_out = run_checker()
    if baseline_code != 0:
        print(f"[FAIL] sandbox baseline: expect exit 0, got {baseline_code}\n{baseline_out}")
        return 1

    results = []
    failures = 0
    try:
        for name, rel, content, expect in CASES:
            path = SRC / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            try:
                code, output = run_checker()
            finally:
                path.unlink(missing_ok=True)
            ok = code == expect
            failures += 0 if ok else 1
            results.append(
                {
                    "case": name,
                    "path": f"frontend/src/{rel}",
                    "expect_exit": expect,
                    "exit": code,
                    "pass": ok,
                    "output": output.strip().splitlines()[:4],
                }
            )
            print(f"[{'PASS' if ok else 'FAIL'}] {name}: expect exit {expect}, got {code}")
            for line in results[-1]["output"]:
                print(f"    {line}")
    finally:
        for path in SRC.rglob("*"):
            if path.is_file() and path.name != ".gitkeep":
                path.unlink()
        for directory in sorted(SRC.rglob("*"), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()

    final_code, final_out = run_checker()
    print(f"\n[baseline] exit {final_code}: {final_out.strip()}")
    results.append(
        {
            "case": "sandbox_baseline",
            "expect_exit": 0,
            "exit": final_code,
            "pass": final_code == 0,
            "output": final_out.strip().splitlines()[:4],
        }
    )
    if final_code != 0:
        failures += 1

    out_path = PACK / "logs" / "gate_probes.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "checker": {
                    "path": "scripts/check-colors.mjs",
                    "sha256": _sha256(ROOT / "scripts" / "check-colors.mjs"),
                },
                "baseline_exit": baseline_code,
                "cases": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {out_path}")
    return 0 if failures == 0 else 1


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    sys.exit(main())
