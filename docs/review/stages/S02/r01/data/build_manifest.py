"""生成 S02/r01 SOURCE_MANIFEST.json（沿用 S00/S01 的清单口径）。"""

import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(".").resolve()
OUT = Path("docs/review/stages/S02/r01")
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tracked(path):
    return (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", path],
            capture_output=True,
        ).returncode
        == 0
    )


files = []


def add(path, kind):
    p = Path(path)
    files.append(
        {
            "path": p.as_posix(),
            "sha256": sha(p),
            "size": p.stat().st_size,
            "kind": kind,
            "git_tracked": tracked(p.as_posix()),
        }
    )


for pattern, kind in (
    ("backend/**/*.py", "backend"),
    ("frontend/src/**/*.js", "frontend"),
    ("frontend/src/**/*.vue", "frontend"),
    ("frontend/src/**/*.css", "frontend"),
    ("scripts/**/*.mjs", "gate_script"),
    ("scripts/**/*.py", "gate_script"),
):
    for p in sorted(Path(".").glob(pattern)):
        if "__pycache__" in p.parts or "node_modules" in p.parts:
            continue
        add(p, kind)

for p in (
    "requirements.txt",
    "pytest.ini",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/index.html",
    "frontend/vite.config.js",
    "frontend/tailwind.config.js",
    "frontend/postcss.config.js",
):
    add(p, "config_or_lock")

for p in (
    "AGENTS.md",
    "MASTER_SPEC.md",
    "BATCH4_PLAN.md",
    "MOBILE_VISUAL_SPEC.md",
    "WEATHERPILL_GLASS.md",
    "DASHBOARD_EXPANSION.md",
    "docs/AGENT_MEMORY.md",
    "docs/REVIEW_RULES.md",
    "docs/review/STAGE_STATUS.md",
    "docs/review/PRE_S10_REMEDIATION_PLAN.md",
    "docs/review/clearance-codex-s01-r01/REPORT.md",
):
    add(p, "contract_or_baseline_doc")

for p in (
    "backend/eatwhat.db",
    "backend/eatwhat_batch4.db",
    "backend/eatwhat_dev_pre00_r02.db",
):
    add(p, "database_baseline")

status_lines = subprocess.run(
    ["git", "status", "--porcelain"], capture_output=True, text=True
).stdout.splitlines()
diff = subprocess.run(["git", "diff", "--cached", "--binary"], capture_output=True).stdout

manifest = {
    "step": "S02",
    "round": "r01",
    "generated_at": NOW,
    "workspace": str(ROOT),
    "hash_algorithm": "sha256",
    "contract_version": "MASTER_SPEC v2.3.5",
    "git": {
        "branch": "master",
        "head": None,
        "commit_count": 0,
        "staged_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "status": {
            "staged": sum(1 for line in status_lines if len(line) > 1 and line[0] not in " ?"),
            "unstaged": sum(1 for line in status_lines if len(line) > 1 and line[1] not in " ?"),
            "untracked": sum(1 for line in status_lines if line.startswith("??")),
            "note": "仓库无 commit；本包不清理、不覆盖既有 staged/unstaged/untracked 变更",
        },
    },
    "files": files,
    "excluded": [
        "docs/review/stages/S02/r01/**（本包证据，自身不参与源码清单）",
        "docs/review/** 旧证据（由各自报告/manifest 固定，不在本清单内重算）",
        "**/__pycache__/**",
        "frontend/node_modules/**、frontend/dist/**（构建产物/依赖安装目录）",
        "backend/eatwhat_s02_r01_iso.db（本步隔离运行库副本；哈希与前后行数见 data/db_protection.json）",
        "backend/_pytest_*、.pytest-tmp-*（临时测试目录）",
    ],
}
manifest["manifest_fingerprint"] = hashlib.sha256(
    json.dumps(
        [(item["path"], item["sha256"]) for item in files],
        ensure_ascii=False,
        sort_keys=True,
    ).encode()
).hexdigest()
(OUT / "SOURCE_MANIFEST.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "files": len(files),
            "fingerprint": manifest["manifest_fingerprint"],
            "git": manifest["git"],
        },
        ensure_ascii=False,
        indent=2,
    )
)
