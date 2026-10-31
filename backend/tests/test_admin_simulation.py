"""仿真底表只读接口：管理员可见、聚合正确、普通用户拒绝。"""

from backend.models import (
    SimulationGroupResult,
    SimulationMealLog,
    SimulationRoom,
    SimulationRoomVote,
    SimulationRun,
)


def _seed(session_factory):
    with session_factory() as session:
        run = SimulationRun(
            name="api-run",
            seed=1,
            personas=2,
            days=1,
            meals_per_day=2,
            rooms_count=1,
            members_per_room=2,
            metrics={
                "duplication_rate_curve": {
                    "days": list(range(1, 15)),
                    "ours_lambda_0.5": [0.0] * 14,
                    "baseline_no_decay": [0.1] * 14,
                },
                "params": {"seed": 1},
                "repeat_metrics": {
                    "window_days": 14,
                    "by_arm": {
                        "ours": {"same_dish_rate": 0.1, "user_rate_box": [0, 0.05, 0.1, 0.15, 0.2]},
                        "baseline": {"same_dish_rate": 0.5, "user_rate_box": [0.4, 0.45, 0.5, 0.55, 0.6]},
                    },
                    "daily": {"days": list(range(1, 15)), "arms": {}},
                    "per_user": {"ours": [0.1], "baseline": [0.5]},
                },
            },
            meal_rows=4,
            room_rows=1,
            vote_rows=2,
        )
        session.add(run)
        session.flush()
        rows = [
            ("ours", 1, 1, True, 80.0),
            ("ours", 2, 2, False, 90.0),
            ("baseline", 1, 1, False, 70.0),
            ("baseline", 2, 2, False, 75.0),
        ]
        for arm, persona, meal, duplicated, score in rows:
            session.add(
                SimulationMealLog(
                    run_id=run.id,
                    arm=arm,
                    persona_id=persona,
                    day=1,
                    meal=meal,
                    mode_type="HOME_COOKING",
                    dish_id=100 + meal,
                    dish_name="测试菜",
                    cuisine_type="家常菜",
                    total_score=score,
                    decay_weight=1.0,
                    duplicated=duplicated,
                    candidate_count=10,
                )
            )
        session.add(
            SimulationRoom(
                run_id=run.id,
                room_code="000001",
                mode_type="HOME_COOKING",
                member_user_ids=[1, 2],
                candidate_dish_ids=[100, 101],
                winner_dish_id=100,
                votes_count=2,
            )
        )
        session.add_all(
            [
                SimulationRoomVote(
                    run_id=run.id, room_code="000001", user_id=1, dish_id=100, vote_type="LIKE"
                ),
                SimulationRoomVote(
                    run_id=run.id, room_code="000001", user_id=2, dish_id=101, vote_type="PASS"
                ),
            ]
        )
        session.add_all(
            [
                SimulationGroupResult(
                    run_id=run.id, strategy="mixed", avg_score=90.0, least_misery_score=80.0
                ),
                SimulationGroupResult(
                    run_id=run.id, strategy="random", avg_score=70.0, least_misery_score=40.0
                ),
            ]
        )
        session.commit()
        return run.id


def test_simulation_endpoints_aggregate(admin_client, session_factory):
    run_id = _seed(session_factory)

    listing = admin_client.get("/api/v1/admin/stats/simulation/runs")
    assert listing.status_code == 200, listing.text
    body = listing.json()
    assert body["total"] == 1
    assert body["items"][0]["meal_rows"] == 4

    detail = admin_client.get(f"/api/v1/admin/stats/simulation/runs/{run_id}")
    assert detail.status_code == 200, detail.text
    data = detail.json()
    assert data["meals"]["total"] == 4
    arms = {item["arm"]: item for item in data["meals"]["by_arm"]}
    assert arms["ours"]["rows"] == 2
    assert arms["ours"]["duplicate_rate"] == 0.5
    assert arms["baseline"]["duplicate_rate"] == 0.0
    assert data["rooms"]["total"] == 1
    assert data["rooms"]["votes"] == 2
    assert data["rooms"]["vote_types"] == {"LIKE": 1, "PASS": 1}
    assert len(data["group_results"]) == 2
    assert len(data["duplication_rate_curve"]["days"]) == 14
    assert data["repeat_metrics"]["window_days"] == 14
    assert data["repeat_metrics"]["by_arm"]["ours"]["same_dish_rate"] == 0.1


def test_simulation_endpoints_require_admin(admin_client, user_client, client, session_factory):
    run_id = _seed(session_factory)
    assert user_client.get("/api/v1/admin/stats/simulation/runs").status_code == 403
    assert client.get(f"/api/v1/admin/stats/simulation/runs/{run_id}").status_code in (401, 403)
