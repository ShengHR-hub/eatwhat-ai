"""汇总 S04/r02 机器可读验收摘要（validation.json）。

只读取本包内已生成的数据/日志，不重新运行测试，不修改被测代码。
"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("D:/EatWhat")
OUT = ROOT / "docs" / "review" / "stages" / "S04" / "r02"
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
    decision_f01 = load("data/decision_f01.json", None)
    decision_n04 = load("data/decision_n04.json", None)

    specific = (probe.get("specific_tag") or {})
    category = (probe.get("category_tag") or {})
    null_vector = (probe.get("null_vector") or {})

    acceptance = [
        {
            "id": "S04-C1",
            "requirement": (
                "具体标签只匹配自身/同义词组；类别标签只展开本类；"
                "单人与群组同口径；鱼香肉丝/豆腐/党参不误判"
            ),
            "self_test": "PASS" if (
                fixed.get("all_match")
                and specific.get("sets_equal")
                and category.get("sets_equal")
                and probe.get("db_state_unchanged")
            ) else "FAIL",
            "evidence": [
                "logs/00_red_specific_tag.log",
                "logs/01_s04_target.log",
                "data/live_api_probe.json#specific_tag",
                "data/live_api_probe.json#category_tag",
                "data/fixed_samples.json#veto_matrix",
            ],
        },
        {
            "id": "S04-C2",
            "requirement": (
                "全 VETO 无赢家；部分 VETO 只从存活集选；"
                "存活候选同分稳定（52.8）；零分存活候选不可达"
            ),
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
            "requirement": (
                "衰减公式与 14/15 天边界；R=0.4/0.6；120/100/40；"
                "ω 0/0.5/1；四权重归一化；原始分排序与展示封顶"
            ),
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
            "requirement": (
                "Top-20 角色枚举；预算；平均油腻度≤0.65；无解；采购合并；"
                "lazy_one_pot 无速度门槛"
            ),
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
            "requirement": (
                "feature_vector=NULL 不进入单人/群组候选、先验与结算；"
                "不回退默认 0.5；空候选保持现有空结果/无共识语义"
            ),
            "self_test": (
                "PASS"
                if decision_n04
                and decision_n04.get("implemented")
                and null_vector.get("api_returned") is False
                and null_vector.get("shortlist_returned") is False
                and null_vector.get("specific_api_returned") is False
                and null_vector.get("specific_shortlist_returned") is False
                else "FAIL"
            ),
            "evidence": [
                "data/decision_n04.json",
                "data/live_api_probe.json#null_vector",
                "logs/01_s04_target.log",
                "logs/10_backend_pytest_full.log",
            ],
        },
    ]

    payload = {
        "step": "S04",
        "round": "r02",
        "generated_at": NOW,
        "state": "SUBMITTED_FOR_REVIEW" if all(
            item["self_test"] == "PASS" for item in acceptance
        ) else "BLOCKED",
        "contract": (
            "MASTER_SPEC v2.3.5（未改 SSOT；D-S04-02 具体/类别标签语义见包内决策）"
        ),
        "findings": {
            "F01": {
                "status": "SELF_TEST_PASS_PENDING_CODEX",
                "r01_issue": "S04-F01-SEM-01：具体食材标签被扩成整个类别",
                "changes": [
                    "veto_rules：新增 CATEGORY_TAGS（海鲜/海味/内脏/牛奶/辣）",
                    "veto_rules：新增 SPECIFIC_SYNONYMS；具体标签只在本组内展开",
                    "veto_rules：expand_tags 不再把别名反查成类别",
                    "单人与群组继续共用 veto_rules",
                ],
                "evidence": [
                    "data/decision_f01.json",
                    "data/live_api_probe.json#specific_tag",
                    "data/fixed_samples.json#veto_matrix",
                ],
            },
            "F02": {
                "status": "SELF_TEST_PASS_PENDING_CODEX",
                "r01_issue": "S04-F02-EVIDENCE-01：零分同分名称与自报不符",
                "changes": [
                    "测试改名 test_s04_survivor_tie_is_stable",
                    "固定样本新增 survivor_tie（52.8）",
                    "说明合法非空成员下 R>=24，零分存活候选不可达；排序逻辑未改",
                ],
                "evidence": [
                    "backend/tests/test_s04_algorithms.py::test_s04_survivor_tie_is_stable",
                    "data/fixed_samples.json#group_consensus",
                ],
            },
            "N04": {
                "status": "SELF_TEST_PASS_PENDING_CODEX",
                "decision": decision_n04,
            },
        },
        "acceptance": acceptance,
        "decisions": {
            "D-S04-01": decision_n04,
            "D-S04-02": decision_f01,
        },
        "tests": {
            "s04_target": pytest_summary("logs/01_s04_target.log"),
            "backend_full": pytest_summary("logs/10_backend_pytest_full.log"),
            "red_specific_tag": pytest_summary("logs/00_red_specific_tag.log"),
        },
        "probe": {
            "category_sets_equal": category.get("sets_equal"),
            "specific_sets_equal": specific.get("sets_equal"),
            "category_expected_keep": category.get("expected_keep"),
            "specific_expected_keep": specific.get("expected_keep"),
            "specific_expected_drop": specific.get("expected_drop"),
            "null_vector": null_vector,
            "db_state_unchanged": probe.get("db_state_unchanged"),
            "protected_unchanged": probe.get("protected_unchanged"),
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
            "具体标签只对 SPECIFIC_SYNONYMS 中显式列出的组展开；未列出的具体食材只做精确匹配（D-S04-02）",
            "类别标签只有 海鲜/海味/内脏/牛奶/辣 五项；其他标签不享受类别展开",
            "单字从严匹配的既有取舍：蟹味菇/贝贝南瓜/蚝油仍可能被相应类别或同义词组挡掉",
            "缺席票 TIMEOUT=60 为现有实现口径，SSOT 未定义；房间级语义留给 S06",
            "VOTE_SCORES 仍保留 VETO=-999 作为枚举键（group_room.VALID_VOTE_TYPES 依赖），属于 F11/S06 口径项；推荐侧不读取",
            "存活候选同分样本为 52.8；合法非空成员下个体 R>=24，零分存活候选不可达",
            "真实房间 WebSocket、断线恢复、前端揭晓未验，留 S06/S07",
            "未改前端/`/admin`；未跑 npm build 或浏览器门禁",
            "SSOT 与 AGENT_MEMORY 未改；D-S04-02 决策只记录在本包",
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
                "acceptance": {
                    item["id"]: item["self_test"] for item in acceptance
                },
                "all_match": fixed.get("all_match"),
                "specific_sets_equal": specific.get("sets_equal"),
                "category_sets_equal": category.get("sets_equal"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if payload["state"] == "SUBMITTED_FOR_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
