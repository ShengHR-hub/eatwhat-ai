"""S06 可复跑检查：实际执行测试/构建/门禁并记录 cwd、退出码、日志路径。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[6]
DATA = Path(__file__).resolve().parent
LOGS = DATA.parent / "logs"
OUT = DATA / "command_results.json"
DB_URL = "sqlite:///D:/EatWhat/backend/eatwhat_s06_r01_iso.db"

COMMANDS = (
    {
        "name": "s06_targeted_tests",
        "cwd": ROOT / "backend",
        "argv": [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_room.py",
            "tests/test_identity_s01.py",
            "tests/test_s02_numeric_bounds.py",
            "tests/test_s06_room_contract.py",
            "-q",
            "--basetemp",
            (Path(tempfile.gettempdir()) / "eatwhat-s06-targeted-final2").as_posix(),
        ],
        "log": "06_s06_targeted_tests.log",
    },
    {
        "name": "backend_full_tests",
        "cwd": ROOT / "backend",
        "argv": [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--basetemp",
            (Path(tempfile.gettempdir()) / "eatwhat-s06-full-final2").as_posix(),
        ],
        "log": "07_backend_full_tests.log",
    },
    {
        "name": "frontend_build",
        "cwd": ROOT / "frontend",
        "argv": ["npm", "run", "build"],
        "shell": True,
        "log": "08_frontend_build.log",
    },
    {
        "name": "check_colors",
        "cwd": ROOT,
        "argv": ["node", "scripts/check-colors.mjs"],
        "log": "08b_check_colors.log",
    },
    {
        "name": "db_target_probe_post",
        "cwd": ROOT,
        "argv": [
            sys.executable,
            "docs/review/stages/S06/r01/data/probe_db_target.py",
            "--allow-existing",
            "--output",
            "docs/review/stages/S06/r01/data/db_target_probe_post.json",
        ],
        "env": {"DATABASE_URL": DB_URL},
        "log": "04b_db_target_probe_post.log",
    },
    {
        "name": "migration_idempotent",
        "cwd": ROOT,
        "argv": [
            sys.executable,
            "-m",
            "backend.scripts.migrate_s06_room_contract",
            "--db",
            "backend/eatwhat_s06_r01_iso.db",
            "--json-out",
            "docs/review/stages/S06/r01/data/migration_idempotent.json",
        ],
        "log": "02b_migration_idempotent.log",
    },
    {
        "name": "omega_matrix_handcalc",
        "cwd": ROOT,
        "argv": [sys.executable, "docs/review/stages/S06/r01/data/omega_matrix_handcalc.py"],
        "log": "12_omega_matrix_handcalc.log",
    },
    {
        "name": "db_protection",
        "cwd": ROOT,
        "argv": [sys.executable, "docs/review/stages/S06/r01/data/probe_db_protection.py"],
        "log": "11_db_protection.log",
    },
)


def main() -> None:
    results = []
    for command in COMMANDS:
        env = os.environ.copy()
        env.update(command.get("env", {}))
        env["PYTHONIOENCODING"] = "utf-8"
        started = datetime.now(ZoneInfo("Asia/Shanghai"))
        completed = subprocess.run(
            command["argv"],
            cwd=command["cwd"],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=command.get("shell", False),
            timeout=600,
        )
        finished = datetime.now(ZoneInfo("Asia/Shanghai"))
        log_path = LOGS / command["log"]
        log_path.write_text(
            completed.stdout + completed.stderr + f"\n[exit_code] {completed.returncode}\n",
            encoding="utf-8",
        )
        tail = (completed.stdout + completed.stderr).strip().splitlines()[-6:]
        results.append(
            {
                "name": command["name"],
                "cwd": str(command["cwd"]),
                "command": " ".join(str(item) for item in command["argv"]),
                "started_at": started.isoformat(),
                "finished_at": finished.isoformat(),
                "exit_code": completed.returncode,
                "log": str(log_path.relative_to(DATA.parent)),
                "tail": tail,
            }
        )
        print(f"[{command['name']}] exit={completed.returncode}")

    payload = {
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "commands": results,
        "ok": all(item["exit_code"] == 0 for item in results),
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"ok": payload["ok"], "commands": len(results)}, ensure_ascii=False))
    if not payload["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
