"""汇总 S04/r01 机器可读验收摘要（validation.json）。

只读取本包内已生成的数据/日志，不重新运行测试，不修改被测代码。
"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("D:/EatWhat")
OUT = ROOT / "docs" / "review" / "stages" / "S04" / "r01"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def load(path, default=None):
    p = OUT / path
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def pytest_summary(path):
    p = OUT / path
    if not p.exists():
        return {"exists": False}
    text = p.read_text(encoding="utf-8", errors="replace")
    last = [line for line in text.splitlines() if " passed" in line]
    counts = {}
    if last:
        match = re.search(r"(\d+) passed", last[-1])
        if match:
            counts["passed"] = int(match.group(1))
        match = re.search(r"(\d+) failed", last[-1])
        if match:
            counts["failed"] = int(match.group(1))
        match = re.search(r"(\d+) skipped", last[-1])
        if match:
            counts["skipped"] = int(match.group(1))
        counts["summary_line"] = last[-1].strip()
    return {"exists": True, "counts": counts}


def main():
    fixed = load("data/fixed_samples.json", {})
    probe = load("data/live_api_probe.json", {})
    protection = load("data/db_protection.json", {})
    decision = load("data/decision_n04.json", None)

    acceptance = [
        {
            "id": "S04-C1",
            "requirement": "海鲜忌口别名覆盖主辅料；鱼香肉丝/豆腐/党参不误判；单人 API 与群组 shortlist 同口径",
            "self_test": "PASS" if (
                fixed.get("all_match")
                and probe.get("sets_equal")
                and probe.get("db_state_unchanged")
            ) else "FAIL",
            "evidence": [
                "logs/00_red_f01.log（修复前红灯：鱼漏判、党参误判）",
                "logs/01_s04_target.log",
                "data/live_api_probe.json",
                "data/fixed_samples.json#veto_matrix",
            ],
        },
        {
            "id": "S04-C2",
            "requirement": "全 VETO 无赢家；部分 VETO 只从存活集选；零分/同分/无票矩阵有独立期望",
            "self_test": "PASS" if all(
                row["match"] for row in fixed.get("group_consensus", [])
            ) else "FAIL",
            "evidence": [
                "logs/01_s04_target.log",
                "data/fixed_samples.json#group_consensus",
            ],
        },
        {
            "id": "S04-C3",
            "requirement": "衰减公式与 14/15 天边界；R=0.4/0.6；120/100/40；ω 0/0.5/1；四权重归一化；原始分排序与展示封顶",
            "self_test": "PASS" if (
                all(row["match"] for row in fixed.get("decay", []))
                and fixed.get("single_formula", {}).get("match")
            ) else "FAIL",
            "evidence": [
                "logs/01_s04_target.log",
                "data/fixed_samples.json#decay",
                "data/fixed_samples.json#single_formula",
            ],
        },
        {
            "id": "S04-C4",
            "requirement": "Top-20 角色枚举；预算；平均油腻度≤0.65；无解；采购合并；lazy_one_pot 无速度门槛",
            "self_test": "PASS" if all(
                row["match"] for row in fixed.get("combo", [])
            ) else "FAIL",
            "evidence": [
                "logs/01_s04_target.log",
                "data/fixed_samples.json#combo",
            ],
        },
        {
            "id": "S04-C5",
            "requirement": "feature_vector=NULL 不被 normalize_vector(None) 静默补 0.5 后参与推荐",
            "self_test": (
                "PASS"
                if decision and decision.get("implemented")
                else "BLOCKED_PENDING_USER_DECISION"
            ),
            "evidence": (
                [
                    "data/decision_n04.json",
                    "data/live_api_probe.json#null_vector",
                    "logs/01_s04_target.log",
                    "logs/10_backend_pytest_full.log",
                ]
                if decision
                else ["决策卡 D-S04-01 待用户确认"]
            ),
        },
    ]

    payload = {
        "step": "S04",
        "round": "r01",
        "generated_at": NOW,
        "state": "SUBMITTED_FOR_REVIEW" if all(
            item["self_test"] == "PASS" for item in acceptance
        ) else "BLOCKED_PENDING_DECISION",
        "contract": "MASTER_SPEC v2.3.5",
        "findings": {
            "F01": {
                "status": "SELF_TEST_PASS_PENDING_CODEX",
                "changes": [
                    "veto_rules：补单字「鱼」精确别名",
                    "veto_rules：去掉「参」词尾规则（避免党参/人参误判），补「刺参」别名",
                    "veto_rules：find_hit/explain 共用 _search，消除第二套匹配",
                ],
                "evidence": "data/live_api_probe.json、data/fixed_samples.json#veto_matrix",
            },
            "F02": {
                "status": "SELF_TEST_PASS_PENDING_CODEX",
                "changes": ["group_recommender：删除 VETO 的死分值赋值，掩码语义显式化"],
                "evidence": "data/fixed_samples.json#group_consensus",
            },
            "N04": {
                "status": (
                    "SELF_TEST_PASS_PENDING_CODEX"
                    if decision and decision.get("implemented")
                    else "OPEN_PENDING_USER_DECISION"
                ),
                "decision": decision,
            },
        },
        "acceptance": acceptance,
        "tests": {
            "s04_target": pytest_summary("logs/01_s04_target.log"),
            "backend_full": pytest_summary("logs/10_backend_pytest_full.log"),
            "red_f01": pytest_summary("logs/00_red_f01.log"),
        },
        "probe": {
            "sets_equal": probe.get("sets_equal"),
            "db_state_unchanged": probe.get("db_state_unchanged"),
            "protected_unchanged": probe.get("protected_unchanged"),
            "api_status": (probe.get("api") or {}).get("status"),
            "group_candidate_count": (probe.get("group_shortlist") or {}).get(
                "candidate_count"
            ),
            "null_vector": probe.get("null_vector"),
        },
        "fixed_samples": {
            "all_match": fixed.get("all_match"),
            "veto_rows": len(fixed.get("veto_matrix", [])),
            "decay_rows": len(fixed.get("decay", [])),
            "group_rows": len(fixed.get("group_consensus", [])),
            "combo_rows": len(fixed.get("combo", [])),
        },
        "db_protection": {
            "passed": protection.get("passed"),
            "protected_unchanged": all(
                item.get("unchanged")
                for item in (protection.get("protected") or {}).values()
            ),
            "schema_matches_source": protection.get("schema_matches_source"),
        },
        "known_limitations": [
            "缺席票 TIMEOUT=60 为现有实现口径，SSOT 未定义；房间级语义留给 S06",
            "VOTE_SCORES 仍保留 VETO=-999 作为枚举键（group_room.VALID_VOTE_TYPES 依赖它），属于 F11/S06 的口径整改项；本次已删除推荐侧对它的读取",
            "单字别名从严匹配：蟹味菇/贝贝南瓜/蚝油会被海鲜忌口挡掉，属于既有过敏从严取舍；本次只修了明确的「参」词尾误判",
            "真实房间 WebSocket 广播、断线恢复与前端揭晓不在本步，留 S06/S07",
            "未改前端/`/admin`；未跑 npm build 或浏览器门禁",
            "campus 过滤（N02）与 deleted_at 软删除（N03）不在 S04 范围",
        ],
        "scope_out": [
            "S05–S10",
            "S06/S07 房间协议与真实划卡",
            "`/admin`、APK",
            "前端改动",
        ],
    }
    (OUT / "validation.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "state": payload["state"],
                "acceptance": {item["id"]: item["self_test"] for item in acceptance},
                "all_match": fixed.get("all_match"),
                "probe_sets_equal": probe.get("sets_equal"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if payload["state"] == "SUBMITTED_FOR_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
