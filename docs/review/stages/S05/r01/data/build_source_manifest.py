"""Generate the final SOURCE_MANIFEST.json for S05/r01.

Run LAST: after this file is written, no package file may change.
The source file list follows the S04/r03 manifest convention (154 paths),
re-hashed against the current working tree.
"""

import hashlib
import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"D:\EatWhat")
PKG = ROOT / "docs/review/stages/S05/r01"
CST = timezone(timedelta(hours=8))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*args):
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return proc


def kind(rel: str) -> str:
    if rel.startswith("backend/"):
        return "database" if rel.endswith(".db") else "backend"
    if rel.startswith("frontend/"):
        return "frontend"
    if rel.startswith("scripts/"):
        return "scripts"
    if rel.startswith("docs/"):
        return "docs"
    return "root"


def main():
    prev = json.loads((ROOT / "docs/review/stages/S04/r03/SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    paths = [f["path"] for f in prev["files"]]
    tracked = set(git("ls-files", "--cached").stdout.splitlines())

    files = []
    missing = []
    for rel in paths:
        p = ROOT / rel
        if not p.exists():
            missing.append(rel)
            continue
        files.append(
            {
                "path": rel,
                "sha256": sha(p),
                "size": p.stat().st_size,
                "kind": kind(rel),
                "git_tracked": rel in tracked,
            }
        )

    status = git("status", "--short").stdout
    status_lines = [ln for ln in status.splitlines() if ln.strip() and not ln.startswith("?? .pytest")]
    staged = subprocess.run(["git", "diff", "--cached", "--binary"], cwd=ROOT, capture_output=True)
    unstaged = subprocess.run(["git", "diff", "--binary"], cwd=ROOT, capture_output=True)

    pair_payload = json.dumps([[f["path"], f["sha256"]] for f in files], separators=(",", ":"), ensure_ascii=False)
    fingerprint = hashlib.sha256(pair_payload.encode()).hexdigest()

    inventory_path = PKG / "data/evidence_inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    validation_path = PKG / "validation.json"

    manifest = {
        "step": "S05",
        "round": "r01",
        "generated_at": datetime.now(CST).isoformat(),
        "workspace": str(ROOT),
        "hash_algorithm": "sha256",
        "contract_version": "MASTER_SPEC v2.3.5",
        "git": {
            "branch": git("branch", "--show-current").stdout.strip(),
            "head": None,
            "commit_count": 0,
            "status_total": len(status_lines),
            "status_sha256": hashlib.sha256("\n".join(status_lines).encode()).hexdigest(),
            "staged_diff_sha256": hashlib.sha256(staged.stdout).hexdigest(),
            "unstaged_diff_sha256": hashlib.sha256(unstaged.stdout).hexdigest(),
        },
        "s05_changed_files": [
            {
                "path": "frontend/src/views/mobile/Home.vue",
                "sha256": sha(ROOT / "frontend/src/views/mobile/Home.vue"),
            },
            {
                "path": "frontend/src/api/client.js",
                "sha256": sha(ROOT / "frontend/src/api/client.js"),
            },
            {
                "path": "scripts/sandbox-sync.mjs",
                "sha256": sha(ROOT / "scripts/sandbox-sync.mjs"),
            },
        ],
        "backend_changed": False,
        "files": files,
        "file_count": len(files),
        "missing_from_s04_list": missing,
        "evidence": {
            "directory": "docs/review/stages/S05/r01",
            "inventory": "data/evidence_inventory.json",
            "inventory_sha256": sha(inventory_path),
            "inventory_file_count": inventory["file_count"],
            "validation_sha256": sha(validation_path),
            "own_evidence_excluded_from_files": True,
        },
        "excluded": [
            "docs/review/stages/S05/r01/**（本包证据，自身不参与源码清单；完整性见 data/evidence_inventory.json）",
            "docs/review/** 旧证据（由各自报告/manifest 固定，不在本清单内重算）",
            "**/__pycache__/**",
            "frontend/node_modules/**、frontend/dist/**（构建产物/依赖安装目录）",
            "backend/eatwhat_s05_r01_iso.db（本轮隔离运行库副本；身份、隔离与前后状态见 data/db_protection.json）",
            "backend/_pytest_*、.pytest-*（临时测试目录）",
        ],
        "hash_recipe": "manifest_fingerprint = sha256 over compact JSON of [[path, sha256], ...] in files order",
        "manifest_fingerprint": fingerprint,
    }
    (PKG / "SOURCE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "file_count": len(files),
                "missing": missing,
                "fingerprint": fingerprint,
                "evidence_inventory": manifest["evidence"]["inventory_file_count"],
                "validation_sha256": manifest["evidence"]["validation_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
