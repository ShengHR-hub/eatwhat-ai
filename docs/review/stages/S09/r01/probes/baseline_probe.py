"""S09 只读基线：环境、文件哈希、DB schema/行数、路由、外部依赖与素材台账。

不写数据库；不读取或输出任何 Key/Token 值，只记录是否存在。
输出：docs/review/stages/S09/r01/data/*.json 与 logs/02_baseline.log
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PACK = Path(__file__).resolve().parents[1]
DATA = PACK / "data"
LOGS = PACK / "logs"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, timeout=20):
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, cwd=ROOT,
        )
        return {
            "cmd": cmd,
            "exit": proc.returncode,
            "stdout": (proc.stdout or "").strip()[:2000],
            "stderr": (proc.stderr or "").strip()[:2000],
        }
    except Exception as exc:  # noqa: BLE001
        return {"cmd": cmd, "exit": None, "stdout": "", "stderr": "", "error": repr(exc)}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    DATA.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    now = datetime.now().astimezone()
    npm_cmd = shutil.which("npm") or "npm"
    env = {
        "captured_at": now.isoformat(timespec="seconds"),
        "timezone": str(now.tzinfo),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "node": run(["node", "--version"])["stdout"],
        "npm": run([npm_cmd, "--version"])["stdout"],
        "npm_path": npm_cmd,
        "cwd": str(ROOT),
    }
    git_head = run(["git", "rev-parse", "HEAD"])
    head_text = (git_head.get("stdout") or "").strip()
    env["git_head"] = head_text if len(head_text) == 40 and all(c in "0123456789abcdef" for c in head_text.lower()) else None
    env["git_head_raw"] = head_text or None
    env["git_head_error"] = git_head.get("stderr") or None
    git_status_proc = subprocess.run(
        ["git", "status", "--short"], capture_output=True, text=True,
        encoding="utf-8", errors="replace", cwd=ROOT,
    )
    status_text = git_status_proc.stdout or ""
    (DATA / "git_status_short.txt").write_text(status_text, encoding="utf-8")
    env["git_status_lines"] = len(status_text.splitlines())
    env["git_status_exit"] = git_status_proc.returncode
    env["git_status_stderr"] = (git_status_proc.stderr or "").strip()[:500]
    (DATA / "env.json").write_text(json.dumps(env, ensure_ascii=False, indent=2), encoding="utf-8")
    (LOGS / "02_baseline.log").write_text(
        json.dumps(env, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    hash_paths = [
        "AGENTS.md",
        "MASTER_SPEC.md",
        "BATCH4_PLAN.md",
        "DASHBOARD_EXPANSION.md",
        "docs/AGENT_MEMORY.md",
        "docs/REVIEW_RULES.md",
        "docs/review/STAGE_STATUS.md",
        "backend/models.py",
        "backend/config.py",
        "backend/main.py",
        "backend/scripts/init_seed_data.py",
        "backend/scripts/benchmark_snapshot.json",
        "backend/algorithms/simulate_personas.py",
        "backend/algorithms/single_recommender.py",
        "backend/algorithms/group_recommender.py",
        "docs/_data/dishes.json",
        "docs/DISH_IMAGES_LEDGER.md",
    ]
    hashes = []
    for rel in hash_paths:
        path = ROOT / rel
        hashes.append({
            "path": rel,
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else None,
            "sha256": sha256(path) if path.exists() else None,
        })
    (DATA / "file_hashes.json").write_text(
        json.dumps({"files": hashes}, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # DB 只读检查
    import sqlite3

    db_path = ROOT / "backend" / "eatwhat.db"
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        tables = [
            "users", "user_preferences", "restaurants", "dishes_and_recipes",
            "fridge_inventory", "eating_logs", "group_rooms", "room_votes", "algo_configs",
        ]
        counts = {t: con.execute(f"select count(*) from {t}").fetchone()[0] for t in tables}
        schema = {}
        for t in tables:
            schema[t] = [
                {"cid": row[0], "name": row[1], "type": row[2], "notnull": row[3], "default": row[4], "pk": row[5]}
                for row in con.execute(f"pragma table_info({t})").fetchall()
            ]
        source_type = dict(con.execute("select source_type,count(*) from restaurants group by source_type").fetchall())
        mode_type = dict(con.execute("select mode_type,count(*) from dishes_and_recipes group by mode_type").fetchall())
        row = con.execute(
            "select benchmark_json from algo_configs where config_name='default_production'"
        ).fetchone()
        benchmark = json.loads(row[0]) if row and row[0] else None
        db = {
            "path": str(db_path),
            "file_sha256": sha256(db_path),
            "counts": counts,
            "restaurants_by_source": source_type,
            "dishes_by_mode": mode_type,
            "benchmark_keys": sorted(benchmark) if benchmark else None,
            "benchmark_generated_at": benchmark.get("generated_at") if benchmark else None,
            "schema": schema,
            "has_allergen_tags": any(c["name"] == "allergen_tags" for c in schema["dishes_and_recipes"]),
            "has_soft_delete_columns": any(
                c["name"] in {"is_active", "deleted_at", "is_deleted", "status"}
                for c in schema["dishes_and_recipes"] + schema["restaurants"]
            ),
            "missing_stats_route_files": {
                "backend/scripts/fetch_amap_poi.py": not (ROOT / "backend/scripts/fetch_amap_poi.py").exists(),
                "backend/scripts/import_open_recipes.py": not (ROOT / "backend/scripts/import_open_recipes.py").exists(),
                "backend/scripts/llm_batch_tagger.py": not (ROOT / "backend/scripts/llm_batch_tagger.py").exists(),
                "backend/routers/admin_sandbox.py": not (ROOT / "backend/routers/admin_sandbox.py").exists(),
            },
        }
    finally:
        con.close()
    (DATA / "db_baseline.json").write_text(
        json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 路由清单
    from backend.main import app

    routes = []
    for r in app.routes:
        routes.append({
            "methods": sorted(getattr(r, "methods", []) or []),
            "path": getattr(r, "path", ""),
            "name": getattr(r, "name", ""),
        })
    (DATA / "routes.json").write_text(
        json.dumps({"routes": routes}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    expected_stats = [
        "/api/v1/admin/stats/overview",
        "/api/v1/admin/stats/geo",
        "/api/v1/admin/stats/calendar",
        "/api/v1/admin/stats/heatmap",
        "/api/v1/admin/stats/cuisine",
        "/api/v1/admin/stats/cuisine-trend",
        "/api/v1/admin/stats/personas",
        "/api/v1/admin/stats/scatter",
        "/api/v1/admin/stats/flow",
        "/api/v1/admin/stats/keywords",
        "/api/v1/admin/stats/race",
        "/api/v1/admin/stats/cooccurrence",
        "/api/v1/admin/stats/quality",
    ]
    actual_paths = {r["path"] for r in routes}
    (DATA / "route_gap.json").write_text(
        json.dumps(
            {
                "expected_stats_count": len(expected_stats),
                "expected": expected_stats,
                "present": [p for p in expected_stats if p in actual_paths],
                "missing": [p for p in expected_stats if p not in actual_paths],
                "admin_routes_present": [p for p in actual_paths if "/admin" in p],
                "note": "S09 只读核对；S14/S15 才实现。",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # 外部依赖/构建工具（只看存在性，不读取值）
    keys = {}
    for key in ("AMAP_API_KEY", "LLM_API_KEY", "LLM_BASE_URL", "DATABASE_URL"):
        value = os.getenv(key)
        keys[key] = {"present": bool(value), "length": len(value) if value else 0}
    build_tools = {
        "java": shutil.which("java"),
        "javac": shutil.which("javac"),
        "adb": shutil.which("adb"),
        "gradle": shutil.which("gradle"),
        "ANDROID_HOME": bool(os.getenv("ANDROID_HOME")),
        "ANDROID_SDK_ROOT": bool(os.getenv("ANDROID_SDK_ROOT")),
        "frontend_capacitor_config": [
            str(p.relative_to(ROOT)) for p in (ROOT / "frontend").glob("capacitor.config.*")
        ],
        "frontend_android_dir": (ROOT / "frontend" / "android").exists(),
    }
    build_tools["java_version"] = run(["java", "-version"])
    build_tools["javac_version"] = run(["javac", "-version"])
    build_tools["adb_version"] = run(["adb", "version"])
    build_tools["gradle_version"] = run(["gradle", "-v"], timeout=40)
    package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    build_tools["frontend_relevant_deps"] = {
        k: deps.get(k) for k in (
            "@capacitor/core", "@capacitor/cli", "@capacitor/android",
            "echarts", "echarts-wordcloud", "html2canvas", "axios",
        )
    }
    (DATA / "external_deps.json").write_text(
        json.dumps({"env_keys": keys, "build_tools": build_tools}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 素材台账摘要
    ledger = (ROOT / "docs" / "DISH_IMAGES_LEDGER.md").read_text(encoding="utf-8")
    raw = (ROOT / "docs" / "DISH_IMAGES_SOURCES_RAW.md").read_text(encoding="utf-8")
    assets = {
        "dish_image_ledger": {
            "path": "docs/DISH_IMAGES_LEDGER.md",
            "sha256": sha256(ROOT / "docs" / "DISH_IMAGES_LEDGER.md"),
            "lines": len(ledger.splitlines()),
            "xiaohongshu_mentions": ledger.lower().count("xiaohongshu"),
        },
        "dish_image_sources_raw": {
            "path": "docs/DISH_IMAGES_SOURCES_RAW.md",
            "sha256": sha256(ROOT / "docs" / "DISH_IMAGES_SOURCES_RAW.md"),
            "lines": len(raw.splitlines()),
            "xiaohongshu_mentions": raw.lower().count("xiaohongshu"),
        },
        "public_dishes_files": len(list((ROOT / "frontend" / "public" / "dishes").glob("*"))) if (ROOT / "frontend" / "public" / "dishes").exists() else 0,
    }
    (DATA / "assets_baseline.json").write_text(
        json.dumps(assets, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = {
        "captured_at": env["captured_at"],
        "versions": {"python": env["python"], "node": env["node"], "npm": env["npm"]},
        "git_head": env["git_head"],
        "db_counts": db["counts"],
        "restaurants_by_source": db["restaurants_by_source"],
        "dishes_by_mode": db["dishes_by_mode"],
        "has_allergen_tags": db["has_allergen_tags"],
        "has_soft_delete_columns": db["has_soft_delete_columns"],
        "routes": len(routes),
        "env_keys": keys,
        "build_tools": {k: build_tools[k] for k in ("java", "javac", "adb", "gradle", "ANDROID_HOME", "ANDROID_SDK_ROOT", "frontend_capacitor_config", "frontend_android_dir")},
        "frontend_relevant_deps": build_tools["frontend_relevant_deps"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
