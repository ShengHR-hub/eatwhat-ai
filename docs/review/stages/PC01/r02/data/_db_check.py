import json, sqlite3
from datetime import datetime, timezone

print("checked_at:", datetime.now(timezone.utc).isoformat())
db = sqlite3.connect("backend/eatwhat.db")
name, raw = db.execute("select config_name, benchmark_json from algo_configs").fetchone()
b = json.loads(raw)
print("config_name:", name)
print("top_level_keys:", sorted(b.keys()))
print("sample:", b["sample"])
curve = b["duplication_rate_curve"]
print("days_count:", len(curve["days"]), "ours_count:", len(curve["ours_lambda_0.5"]), "base_count:", len(curve["baseline_no_decay"]))
print("days:", curve["days"])
print("ours_lambda_0.5:", curve["ours_lambda_0.5"])
print("baseline_no_decay:", curve["baseline_no_decay"])
bars = b["group_satisfaction_bars"]
print("strategies:", bars["strategies"])
print("avg_scores:", bars["avg_scores"])
print("least_misery_scores:", bars["least_misery_scores"])

g = sqlite3.connect("docs/review/simulation/sim_seed20261024_groups.db")
print("group_rooms:", g.execute("select count(*) from group_rooms").fetchone()[0])
print("room_votes:", g.execute("select count(*) from room_votes").fetchone()[0])
print("vote_types:", dict(g.execute("select vote_type, count(*) from room_votes group by vote_type")))
print("members_per_room(min,max):", g.execute("select min(c), max(c) from (select room_code, count(distinct user_id) c from room_votes group by room_code)").fetchone())
print("cards_per_room(min,max):", g.execute("select min(c), max(c) from (select room_code, count(distinct dish_id) c from room_votes group by room_code)").fetchone())
print("demo_db_untouched_rooms:", db.execute("select count(*) from group_rooms").fetchone()[0])
