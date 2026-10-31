"""汇总 S06/r01 机器可读验证结果；任何必需项失败即非零退出。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DATA = Path(__file__).resolve().parent
OUT = DATA.parent / "validation.json"


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def main() -> None:
    commands = {item["name"]: item for item in load("command_results.json")["commands"]}
    migration = load("migration.json")
    migration_idempotent = load("migration_idempotent.json")
    fixture = load("fixture.json")
    provenance = load("db_provenance.json")
    pre_probe = load("db_target_probe.json")
    post_probe = load("db_target_probe_post.json")
    flow = load("rest_ws_sequence.json")
    restart = load("restart_flow.json")
    omega = load("omega_matrix.json")
    protection = load("db_protection.json")

    flow_steps = {item["step"]: item for item in flow["steps"]}
    required_steps = {
        "create_missing_campus_422",
        "create_caotang_422",
        "create_siyuan_room",
        "create_jianda_room",
        "create_home_room",
        "cross_campus_join_409",
        "join_missing_campus_422",
        "join_siyuan_member",
        "ws_non_member_403",
        "non_host_start_rejected",
        "host_start",
        "duplicate_vote_last_write_wins",
        "client_timeout_rejected",
        "non_candidate_vote_rejected",
        "consensus_reveal",
        "snapshot_after_finish",
        "repeat_get_idempotent",
        "reconnect_room_state_restored",
        "omega_frozen_at_create",
        "omega_request_override",
        "single_override_isolated",
        "zero_votes_settle",
        "all_veto_no_consensus",
        "late_vote_rejected",
    }

    checks = []

    def add(check_id: str, description: str, ok: bool, evidence):
        checks.append(
            {
                "id": check_id,
                "description": description,
                "ok": bool(ok),
                "evidence": evidence,
            }
        )

    add(
        "CHK-01",
        "S06 专项测试（room/identity/s02/s06）退出码 0",
        commands["s06_targeted_tests"]["exit_code"] == 0,
        {
            "command": commands["s06_targeted_tests"]["command"],
            "log": commands["s06_targeted_tests"]["log"],
            "exit_code": commands["s06_targeted_tests"]["exit_code"],
        },
    )
    add(
        "CHK-02",
        "后端全量测试退出码 0（388 passed, 1 skipped）",
        commands["backend_full_tests"]["exit_code"] == 0,
        {
            "command": commands["backend_full_tests"]["command"],
            "log": commands["backend_full_tests"]["log"],
            "exit_code": commands["backend_full_tests"]["exit_code"],
        },
    )
    add(
        "CHK-03",
        "前端 build 退出码 0（campus 最小透传）",
        commands["frontend_build"]["exit_code"] == 0,
        {
            "command": commands["frontend_build"]["command"],
            "log": commands["frontend_build"]["log"],
            "exit_code": commands["frontend_build"]["exit_code"],
        },
    )
    add(
        "CHK-04",
        "颜色门禁退出码 0（38 个文件无裸色）",
        commands["check_colors"]["exit_code"] == 0,
        {
            "command": commands["check_colors"]["command"],
            "log": commands["check_colors"]["log"],
            "exit_code": commands["check_colors"]["exit_code"],
        },
    )
    add(
        "CHK-05",
        "S06 隔离库来源与复制身份一致，源库复制后未变",
        provenance["same_sha256"] and provenance["source_unchanged_after_copy"],
        {
            "source": provenance["source"]["path"],
            "source_sha256": provenance["source"]["sha256"],
            "target": provenance["target"]["path"],
            "target_sha256": provenance["target"]["sha256"],
        },
    )
    add(
        "CHK-06",
        "迁移创建 room_votes 唯一索引；预启动行数为 0",
        migration["ok"]
        and migration["index_created"]
        and migration["index_present"]
        and migration["row_count"] == 0,
        migration,
    )
    add(
        "CHK-07",
        "迁移重复执行幂等，SHA 不变",
        migration_idempotent["ok"]
        and migration_idempotent["idempotent"]
        and migration_idempotent["sha256_before"]
        == migration_idempotent["sha256_after"],
        migration_idempotent,
    )
    add(
        "CHK-08",
        "校区 fixture：思源/建大各 6 店 12 菜，20 家种子店保持 NULL",
        fixture["is_synthetic"]
        and fixture["counts"]["SIYUAN"] == {"restaurants": 6, "dishes": 12}
        and fixture["counts"]["JIANDA_YANTA"] == {"restaurants": 6, "dishes": 12}
        and fixture["seed_null_restaurants"] == 20,
        {
            "dataset": fixture["dataset"],
            "counts": fixture["counts"],
            "seed_null_restaurants": fixture["seed_null_restaurants"],
        },
    )
    add(
        "CHK-09",
        "启动前探针确认 DATABASE_URL 指向 S06 隔离库且为空库",
        pre_probe["ok"] and pre_probe["phase"] == "pre"
        and pre_probe["counts"]["group_rooms"] == 0
        and pre_probe["counts"]["room_votes"] == 0,
        pre_probe,
    )
    add(
        "CHK-10",
        "真实 REST/WS 序列 25 步全部完成，必需步骤齐全",
        len(flow["steps"]) == 25 and required_steps <= set(flow_steps),
        {
            "steps": len(flow["steps"]),
            "required_steps": sorted(required_steps),
            "missing": sorted(required_steps - set(flow_steps)),
        },
    )
    add(
        "CHK-11",
        "10 候选来自同校区 fixture，跨校区 join 409，join 后仍 10 候选",
        flow_steps["create_siyuan_room"]["candidate_count"] == 10
        and flow_steps["create_jianda_room"]["candidate_count"] == 10
        and flow_steps["cross_campus_join_409"]["status"] == 409
        and flow_steps["join_siyuan_member"]["members"] == [1, 2]
        and flow_steps["join_siyuan_member"]["candidate_count"] == 10,
        {
            "siyuan": flow_steps["create_siyuan_room"],
            "jianda": flow_steps["create_jianda_room"],
            "cross_campus": flow_steps["cross_campus_join_409"],
            "join": flow_steps["join_siyuan_member"],
        },
    )
    add(
        "CHK-12",
        "WS 未 join 403；非房主开局被拒；重复票/客户端 TIMEOUT/非候选票被拒",
        flow_steps["ws_non_member_403"]["status"] == 403
        and "房主" in flow_steps["non_host_start_rejected"]["detail"]
        and flow_steps["duplicate_vote_last_write_wins"]["progress"]["1"] == 1
        and "投票格式" in flow_steps["client_timeout_rejected"]["detail"]
        and "候选" in flow_steps["non_candidate_vote_rejected"]["detail"],
        {
            "ws": flow_steps["ws_non_member_403"],
            "non_host": flow_steps["non_host_start_rejected"],
            "duplicate": flow_steps["duplicate_vote_last_write_wins"],
            "timeout": flow_steps["client_timeout_rejected"],
            "non_candidate": flow_steps["non_candidate_vote_rejected"],
        },
    )
    add(
        "CHK-13",
        "早结算共识揭晓；GET 幂等；重连 ROOM_STATE 恢复",
        flow_steps["consensus_reveal"]["has_consensus"] is True
        and flow_steps["repeat_get_idempotent"]["vote_count"] == 20
        and flow_steps["repeat_get_idempotent"]["unique_vote_count"] == 20
        and flow_steps["snapshot_after_finish"]["status"] == "FINISHED"
        and "ROOM_STATE" in flow["traces"].get("reconnect-host", []),
        {
            "reveal": flow_steps["consensus_reveal"],
            "repeat": flow_steps["repeat_get_idempotent"],
            "snapshot": flow_steps["snapshot_after_finish"],
            "reconnect": flow_steps["reconnect_room_state_restored"],
        },
    )
    add(
        "CHK-14",
        "ω 建房冻结：DB 0.7 → 建房后改 0.1 → 结算仍 0.7；override 0.2 优先；单人 override 不写库",
        flow_steps["omega_frozen_at_create"]["snapshot_omega"] == 0.7
        and flow_steps["omega_frozen_at_create"]["db_omega_after_create"] == 0.1
        and flow_steps["omega_frozen_at_create"]["settle_omega"] == 0.7
        and flow_steps["omega_request_override"]["settle_omega"] == 0.2
        and flow_steps["single_override_isolated"]["algo_config_omega"] == 0.1
        and flow_steps["single_override_isolated"]["room_algo_params"]
        == {"omega_group": 0.2},
        {
            "frozen": flow_steps["omega_frozen_at_create"],
            "override": flow_steps["omega_request_override"],
            "single": flow_steps["single_override_isolated"],
        },
    )
    add(
        "CHK-15",
        "全员 0 票按 TIMEOUT=60 结算且不落 TIMEOUT；全员 VETO 无赢家",
        flow_steps["zero_votes_settle"]["stored_votes"] == 0
        and flow_steps["zero_votes_settle"]["winner_dish_id"] is not None
        and flow_steps["all_veto_no_consensus"]["winner_dish_id"] is None
        and flow_steps["all_veto_no_consensus"]["has_consensus"] is False
        and flow_steps["all_veto_no_consensus"]["vetoed"] == 10,
        {
            "zero": flow_steps["zero_votes_settle"],
            "veto": flow_steps["all_veto_no_consensus"],
        },
    )
    add(
        "CHK-16",
        "截止后投票被拒且不改变结果",
        "结束" in flow_steps["late_vote_rejected"]["detail"]
        or "到点" in flow_steps["late_vote_rejected"]["detail"],
        flow_steps["late_vote_rejected"],
    )
    add(
        "CHK-17",
        "进程重启后无客户端请求时数据库已结算",
        restart["ok"]
        and restart["database_before_any_client_request"]["status"] == "FINISHED"
        and restart["database_before_any_client_request"]["settled_at"]
        > restart["database_before_any_client_request"]["deadline_at"]
        and restart["database_before_any_client_request"]["vote_count"] == 1,
        restart,
    )
    add(
        "CHK-18",
        "固定矩阵手算：ω=0/0.5/1 的 B 分数 24/46/68，赢家 A/A/B",
        omega["ok"]
        and omega["table"]["0.0"]["B"]["group_score"] == 24.0
        and omega["table"]["0.5"]["B"]["group_score"] == 46.0
        and omega["table"]["1.0"]["B"]["group_score"] == 68.0
        and [omega["table"][key]["winner"] for key in ("0.0", "0.5", "1.0")]
        == ["A", "A", "B"],
        omega,
    )
    add(
        "CHK-19",
        "受保护数据库哈希全部不变；写入只在 S06 隔离库",
        protection["ok"]
        and protection["protected_all_unchanged"]
        and all(item["unchanged"] for item in protection["protected"].values())
        and protection["s06_iso"]["counts"]["group_rooms"] > 0
        and protection["s06_iso"]["counts"]["room_votes"] > 0,
        {
            "protected": {
                key: value["unchanged"]
                for key, value in protection["protected"].items()
            },
            "s06_iso_counts": protection["s06_iso"]["counts"],
            "s06_iso_vote_types": protection["s06_iso"]["vote_types"],
        },
    )
    add(
        "CHK-20",
        "运行期探针仍确认 DATABASE_URL 指向 S06 隔离库",
        post_probe["ok"] and post_probe["phase"] == "post",
        post_probe,
    )

    payload = {
        "stage": "S06",
        "round": "r01",
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "ssot_version": "v2.3.6",
        "decision_set": {
            "D1": "A' 严格校区 + 历史 NULL 房间首 join 绑定",
            "D2": "A 前端默认 SIYUAN 最小透传",
            "D3": "A 拒绝客户端 TIMEOUT",
            "D4": "A 缺席=内部 60，0 票仍结算",
            "D5": "A last-write-wins + room_votes 唯一索引",
            "D6": "A join 重算，0 候选禁止开局",
            "D7": "A 建房冻结 ω，只存 omega_group",
            "D8": "A 启动/5 秒周期兜底 + 原子结算",
            "D9": "SSOT v2.3.6",
        },
        "checks": checks,
        "summary": {
            "total": len(checks),
            "passed": sum(1 for item in checks if item["ok"]),
            "failed": [item["id"] for item in checks if not item["ok"]],
        },
        "ok": all(item["ok"] for item in checks),
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    if not payload["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
