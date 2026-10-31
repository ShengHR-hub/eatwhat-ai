"""PRE-00/r02 真实文件身份探针（只读原库，写操作只落在明确副本上）。"""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import backend.scripts.migrate_pre00_runtime_schema as migration  # noqa: E402

DEMO = (ROOT / "backend" / "eatwhat.db").resolve()
BATCH4 = (ROOT / "backend" / "eatwhat_batch4.db").resolve()
TMP = ROOT / "backend"


def state(path: Path) -> dict:
    with open(path, "rb") as handle:
        import hashlib

        digest = hashlib.sha256()
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        rows = {
            table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("users", "restaurants", "dishes_and_recipes", "eating_logs")
        }
    finally:
        connection.close()
    return {
        "sha256": digest.hexdigest(),
        "schema": migration.schema_fingerprint(path),
        "rows": rows,
    }


def link_probe(name: str, protected: Path, constant: str, before: dict) -> dict:
    alias = TMP / f"_pre00_r02_{name}_alias.db"
    if alias.exists():
        alias.unlink()
    os.link(protected, alias)
    samefile = os.path.samefile(alias, protected)
    resolved_equal = alias.resolve() == protected.resolve()
    old = getattr(migration, constant)
    setattr(migration, constant, protected)
    try:
        try:
            migration._guard_path(alias)
            guard = {"raised": False, "error": None}
        except SystemExit as exc:
            guard = {"raised": True, "error": str(exc)}
    finally:
        setattr(migration, constant, old)
        alias.unlink()
    after = state(protected)
    return {
        "protected": str(protected),
        "alias": str(alias),
        "alias_deleted": not alias.exists(),
        "samefile": samefile,
        "resolved_paths_equal": resolved_equal,
        "guard": guard,
        "state_before": before,
        "state_after": after,
        "state_unchanged": before == after,
    }


def symlink_probe(name: str, protected: Path, constant: str, before: dict) -> dict:
    alias = TMP / f"_pre00_r02_{name}_symlink.db"
    if alias.exists():
        alias.unlink()
    try:
        alias.symlink_to(protected)
    except (OSError, NotImplementedError) as exc:
        return {"supported": False, "reason": f"{type(exc).__name__}: {exc}"}
    samefile = os.path.samefile(alias, protected)
    resolved_equal = alias.resolve() == protected.resolve()
    old = getattr(migration, constant)
    setattr(migration, constant, protected)
    try:
        try:
            migration._guard_path(alias)
            guard = {"raised": False, "error": None}
        except SystemExit as exc:
            guard = {"raised": True, "error": str(exc)}
    finally:
        setattr(migration, constant, old)
        alias.unlink()
    after = state(protected)
    return {
        "supported": True,
        "samefile": samefile,
        "resolved_paths_equal": resolved_equal,
        "guard": guard,
        "state_unchanged": before == after,
    }


def cli_hardlink_case(name: str, source: Path, constant: str) -> dict:
    copy = TMP / f"_pre00_r02_{name}_copy.db"
    alias = TMP / f"_pre00_r02_{name}_copy_alias.db"
    for path in (copy, alias):
        if path.exists():
            path.unlink()
    copy.write_bytes(source.read_bytes())
    os.link(copy, alias)
    before = state(copy)
    code = (
        "import sys; from pathlib import Path; "
        "import backend.scripts.migrate_pre00_runtime_schema as m; "
        f"m.{constant}=Path(r'{copy.resolve()}'); "
        f"sys.argv=['migrate', '--db', r'{alias}']; "
        "m.main()"
    )
    process = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    after = state(copy)
    result = {
        "copy": str(copy),
        "alias": str(alias),
        "samefile": os.path.samefile(copy, alias),
        "resolved_paths_equal": copy.resolve() == alias.resolve(),
        "exit_code": process.returncode,
        "stdout": process.stdout.strip(),
        "stderr_tail": "\n".join(process.stderr.strip().splitlines()[-3:]),
        "state_before": before,
        "state_after": after,
        "state_unchanged": before == after,
    }
    copy.unlink()
    alias.unlink()
    return result


def main() -> dict:
    demo_before = state(DEMO)
    batch4_before = state(BATCH4)
    report = {
        "originals_before": {"demo": demo_before, "s10": batch4_before},
        "hardlink_real_alias": {
            "demo": link_probe("demo", DEMO, "DEMO_DB", demo_before),
            "s10": link_probe("s10", BATCH4, "BATCH4_DB", batch4_before),
        },
        "symlink_real_alias": {
            "demo": symlink_probe("demo", DEMO, "DEMO_DB", demo_before),
            "s10": symlink_probe("s10", BATCH4, "BATCH4_DB", batch4_before),
        },
        "cli_hardlink_on_copies": {
            "demo": cli_hardlink_case("demo", DEMO, "DEMO_DB"),
            "s10": cli_hardlink_case("s10", BATCH4, "BATCH4_DB"),
        },
        "originals_after": {"demo": state(DEMO), "s10": state(BATCH4)},
    }
    report["originals_unchanged"] = (
        report["originals_before"] == report["originals_after"]
    )
    return report


if __name__ == "__main__":
    payload = main()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    Path("docs/review/stages/PRE-00/r02/data/guard_probe.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if not payload["originals_unchanged"]:
        raise SystemExit(1)
