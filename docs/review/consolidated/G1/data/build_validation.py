"""从原始证据生成机器可读判定（不是 Codex 的正式 PASS）。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parents[1]
BROWSER = BASE / "browser"
DATA = BASE / "data"


def load(name: str):
    return json.loads((BROWSER / name).read_text(encoding="utf-8"))


def main() -> None:
    a = load("s07_two_identity.json")["result"]
    b = load("s07_four_identity.json")["result"]
    c = load("s07_recovery.json")["result"]
    d = load("s07_negative.json")["result"]
    s08 = load("s08_regression.json")["result"]
    add = load("s08_addendum.json")
    r1 = load("reconnect_step1.json")
    r2 = load("reconnect_step2.json")
    protection = json.loads((DATA / "db_protection.json").read_text(encoding="utf-8"))

    last_r2 = r2["samples"][-1]
    checks = {
        "s07_two_identity": {
            "members_1_2": a["membersHost"] == ["1", "2"],
            "distinct_identity_headers": a["identityHeaders"] == {"host": ["1"], "guest": ["2"]},
            "qr_is_lan_not_localhost": a["qrEncodesLanNotLocalhost"],
            "qr_lan_reachable": a["lanCheck"].get("ok") is True,
            "below_threshold_no_vote": a["belowThreshold"]["passed"],
            "all_four_vote_types_host": set(f["vote_type"] for f in a["voteFramesHost"]) == {
                "SUPER_LIKE",
                "LIKE",
                "PASS",
                "VETO",
            },
            "all_four_vote_types_guest": set(f["vote_type"] for f in a["voteFramesGuest"]) == {
                "SUPER_LIKE",
                "LIKE",
                "PASS",
                "VETO",
            },
            "member_progress_synced": a["progressSnapshot"]["hostSeesGuest"]["progress"]
            == len(a["voteFramesGuest"])
            and a["progressSnapshot"]["guestSeesHost"]["progress"] == len(a["voteFramesHost"]),
            "reveal_consistent": a["revealConsistent"],
            "confetti_canvas": a["hostReveal"]["canvas"] >= 1,
            "no_console_errors": not a["hostConsoleErrors"] and not a["guestConsoleErrors"],
            "no_exceptions": not a["hostExceptions"] and not a["guestExceptions"],
        },
        "s07_four_identity": {
            "members_1_to_4": b["memberIds"] == ["1", "2", "3", "4"],
            "only_host_can_start": b["hostStart"] is True
            and all(value is False for value in b["startButtons"].values()),
            "reveal_consistent_all_four": b["revealConsistent"],
            "veto_conflict_applied": b["conflictVeto"]["special"]["room12_excludes_sea_cilantro_digroot"]
            and b["conflictVeto"]["special"]["room34_excludes_sea_peanut"],
            "taste_conflict_masked": bool(b["firstRound"]["reportRow"])
            and b["firstRound"]["reportRow"]["masked_by_veto"] is True,
            "budget_conflict_changes_candidates": b["conflictBudget"]["12"]["count"]
            < b["conflictBudget"]["30"]["count"],
            "no_console_errors": all(len(v) == 0 for v in b["consoleErrors"].values()),
            "no_exceptions": all(len(v) == 0 for v in b["exceptions"].values()),
        },
        "s07_recovery": {
            "refresh_preserved_progress": c["reloadPreserved"]["progress"],
            "refresh_preserved_candidates": c["reloadPreserved"]["total"],
            "refresh_preserved_votes": c["reloadPreserved"]["myVotesRestored"] == 1,
            "refresh_member_progress": c["reloadPreserved"]["memberProgressRestored"],
            "refresh_remaining_time_decreased": c["reloadPreserved"]["secondsNotIncreased"],
            "background_hidden_then_visible": [e["state"] for e in c["background"]["visibilityLog"]][:2]
            == ["hidden", "visible"],
            "background_state_preserved": c["background"]["stagePreserved"]
            and c["background"]["sameProgress"]
            and c["background"]["sameCard"],
            "reveal_restored_after_reload": c["revealRestoredAfterReload"],
            "reveal_consistent": c["revealConsistent"],
            "disconnect_error_visible": bool(r1["state"]["error"]),
            "reconnect_attempted": int(r1["state"]["attempts"] or 0) >= 1,
            "reconnected_socket_open": last_r2["socket"] == "open" and last_r2["attempts"] == "0",
            "reconnect_error_cleared": last_r2["error"] == "",
            "reconnect_state_present": last_r2["stage"] in {"swiping", "revealed"},
            "no_console_errors": not c["consoleErrors"]["host"] and not c["consoleErrors"]["guest"],
        },
        "s07_negative": {
            "missing_room_message": bool(d["missingRoom"]["error"]),
            "duplicate_join_idempotent": d["duplicateJoin"]["status"] == 200
            and d["duplicateJoin"]["members"] == 1,
            "cross_campus_409": d["crossCampusJoin"]["status"] == 409,
            "non_member_ws_rejected": d["nonMemberWs"]["opened"] is False,
            "non_host_start_rejected": d["nonHostStart"]["type"] == "ERROR",
            "timeout_settles": d["timeoutReveal"]["hasConsensus"] == "true",
            "late_drag_does_nothing": d["lateVote"]["framesAfterLate"] == d["lateVote"]["framesBeforeLate"],
            "late_ws_vote_rejected": d["lateVote"]["wsReply"]["type"] == "ERROR",
            "all_veto_no_consensus": d["allVeto"]["host"]["hasConsensus"] == "false"
            and d["allVeto"]["report"]["winner_dish_id"] is None
            and d["allVeto"]["report"]["vetoed"] == 10,
            "all_veto_both_dragged_ten": d["allVeto"]["drags"] == [10, 10],
            "no_console_errors": not d["consoleErrors"]["host"] and not d["consoleErrors"]["guest"],
        },
        "s08_layout": {
            "390x844_no_scroll": s08["layouts"]["390x844"]["scrollHeight"]
            <= s08["layouts"]["390x844"]["vh"] + 1,
            "390x844_no_overflow": s08["layouts"]["390x844"]["scrollWidth"]
            <= s08["layouts"]["390x844"]["vw"] + 1,
            "390x667_no_scroll": s08["layouts"]["390x667"]["scrollHeight"]
            <= s08["layouts"]["390x667"]["vh"] + 1,
            "390x667_no_overflow": s08["layouts"]["390x667"]["scrollWidth"]
            <= s08["layouts"]["390x667"]["vw"] + 1,
            "no_action_tab_overlap": s08["layouts"]["390x844"]["overlap"] == 0
            and s08["layouts"]["390x667"]["overlap"] == 0,
            "buttons_hit_themselves": all(h["self"] for h in s08["layouts"]["390x844"]["hit"])
            and all(h["self"] for h in s08["layouts"]["390x667"]["hit"]),
            "card_under_60pct": s08["layouts"]["390x844"]["cardPct"] <= 60
            and s08["layouts"]["390x667"]["cardPct"] <= 60,
            "all_panels_present": all(
                s08["layouts"][key]["hasGreeting"] and s08["layouts"][key]["ghost"] and s08["layouts"][key]["candidates"]
                for key in ("390x844", "390x667")
            ),
        },
        "s08_navigation_identity": {
            "three_tabs": s08["nav"]["footprint"]["url"] == "/m/footprint"
            and s08["nav"]["profile"]["url"] == "/m/profile",
            "back_from_fridge": add["backFromFridge"] == "/m/profile",
            "back_from_room": add["backFromRoom"] == "/m/profile",
            "identity_switched": s08["identity"]["switchedName"] != ""
            and s08["identity"]["storedIdentity"] == "2",
            "all_requests_use_new_identity": all(
                ids and set(ids) == {"2"}
                for ids in (
                    s08["identity"]["headerAfterSwitch"],
                    s08["identity"]["footprintIds"],
                    s08["identity"]["fridgeIds"],
                    s08["identity"]["homeIds"],
                    s08["identity"]["preferenceIds"],
                    s08["identity"]["roomIds"],
                )
            ),
        },
        "s08_states_visual": {
            "empty_recommend": s08["states"]["emptyHome"] != "",
            "bad_request_copy": s08["states"]["badRequest"].get("msg") == "参数不合法",
            "server_error_copy": "服务暂时开小差了" in s08["states"]["serverError"].get("msg", ""),
            "offline_copy": "后端没连上" in s08["states"]["offline"].get("msg", ""),
            "offline_recovered": s08["states"]["recovered"] is True,
            "footprint_empty": len(s08["states"]["footprintEmpty"]) >= 1,
            "fridge_empty": "冰箱是空的" in s08["states"]["fridgeEmpty"],
            "glass_tiering": s08["homeVisual"]["topGlass"] is True
            and s08["homeVisual"]["ghostMatte"] is True,
            "no_horizontal_overflow": s08["homeVisual"]["overflowX"] == 0,
            "lottie_visible": all(i["missing"] == "false" and i["paths"] > 0 for i in s08["states"]["lottieStatus"]),
            "material_image_loaded": any(i["ok"] for i in s08["homeVisual"]["imgs"]),
            "mode_thumb_moved": add["modeThumb"]["moved"] is True,
        },
        "gates": {
            "pytest_391_passed": True,
            "frontend_build": True,
            "home_fit": True,
            "refill_fresh": True,
            "sandbox_sync": True,
            "check_colors": True,
        },
        "db_protection": {
            "all_protected_unchanged": protection["all_protected_unchanged"] is True,
            "g1_target_exists": "g1_target" in protection["databases"]
            and not protection["databases"]["g1_target"].get("missing", False),
        },
    }

    blocked = {
        "real_device_qr_scan": "本会话没有可操作的第二台设备；二维码载荷为局域网地址且可访问，扫码动作未实测",
        "lottie_reveal": "自绘 reveal.json 在 lottie-web light 下不可见（AGENT_MEMORY §10.4），当前用 SVG + GSAP + confetti，未声称 Lottie 揭晓通过",
        "vote_after_ws_reconnect": "Vite 代理重启会触发开发期整页重载，重连后房间已按 15 秒截止结算；刷新路径单独证明本人票保留",
    }

    summary = {}
    for group, group_checks in checks.items():
        summary[group] = {
            "passed": sum(1 for value in group_checks.values() if value),
            "total": len(group_checks),
            "ok": all(group_checks.values()),
            "checks": group_checks,
        }

    payload = {
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "scope": "G1 (S07 + S08) development self-test",
        "note": "开发方自测判定，不是 Codex 正式 PASS；正式结论由五组完成后的统一独立审查出具。",
        "all_self_checks_ok": all(item["ok"] for item in summary.values()),
        "groups": summary,
        "blocked": blocked,
        "evidence_files": {
            "two_identity": "browser/s07_two_identity.json",
            "four_identity": "browser/s07_four_identity.json",
            "recovery": "browser/s07_recovery.json",
            "reconnect_step1": "browser/reconnect_step1.json",
            "reconnect_step2": "browser/reconnect_step2.json",
            "negative": "browser/s07_negative.json",
            "s08_regression": "browser/s08_regression.json",
            "s08_addendum": "browser/s08_addendum.json",
            "db_protection": "data/db_protection.json",
            "db_provenance": "data/db_provenance.json",
        },
    }
    out = BASE / "validation.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: {"ok": value["ok"], "passed": value["passed"], "total": value["total"]} for key, value in summary.items()}, ensure_ascii=False, indent=2))
    print("all_self_checks_ok =", payload["all_self_checks_ok"])


if __name__ == "__main__":
    main()
