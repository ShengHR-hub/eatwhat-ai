"""S09/r04 封存只读复核：读取 manifest 与冻结快照，不写任何文件。"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

R04 = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    manifest_path = R04 / "SOURCE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    listed = {item["path"]: item for item in manifest.get("files", [])}
    mismatches = []
    for rel, item in listed.items():
        path = R04 / rel
        if not path.exists():
            mismatches.append({"path": rel, "reason": "missing"})
        elif path.stat().st_size != item.get("bytes") or sha256(path) != item.get("sha256"):
            mismatches.append({"path": rel, "reason": "size_or_sha"})

    manifest_rel = manifest_path.relative_to(R04).as_posix()
    extras = []
    for path in R04.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(R04).as_posix()
        if rel == manifest_rel or rel in listed:
            continue
        extras.append(rel)

    manifest_mtime = manifest_path.stat().st_mtime
    post_seal_writes = []
    for path in R04.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(R04).as_posix()
        if rel == manifest_rel:
            continue
        if path.stat().st_mtime > manifest_mtime + 1.0:
            post_seal_writes.append(rel)

    validation = json.loads((R04 / "validation.json").read_text(encoding="utf-8"))
    evidence = json.loads((R04 / "data/r04_evidence.json").read_text(encoding="utf-8"))
    history = evidence.get("mismatch_history", {})
    three = {}
    for key, item in history.items():
        rel = item.get("snapshot_path")
        path = R04 / rel if rel else None
        actual = sha256(path) if path and path.exists() else None
        three[key] = {
            "snapshot_path": rel,
            "recorded_sha256": item.get("sha256"),
            "actual_sha256": actual,
            "recorded_bytes": item.get("bytes"),
            "actual_bytes": path.stat().st_size if path and path.exists() else None,
            "ok": bool(path and path.exists() and actual == item.get("sha256") and path.stat().st_size == item.get("bytes")),
        }

    ok = (
        not mismatches
        and not extras
        and not post_seal_writes
        and manifest.get("pack") == "S09/r04"
        and validation.get("ok") is True
        and evidence.get("checks_ok") is True
        and all(item.get("ok") for item in three.values())
    )
    payload = {
        "ok": ok,
        "pack": manifest.get("pack"),
        "manifest_entries": len(listed),
        "mismatches": mismatches,
        "extra_files_not_in_manifest": extras,
        "post_seal_writes": post_seal_writes,
        "three_mismatch_files": three,
        "validation_ok": validation.get("ok"),
        "evidence_checks_ok": evidence.get("checks_ok"),
        "manifest_sha256": sha256(manifest_path),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
