"""Real API SQL and latency probes against a disposable database only."""
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time
import types
from datetime import datetime, timedelta

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT))
DB = OUT / 'review-sql.sqlite'
assert not DB.exists(), 'Refuse to overwrite prior probe database'
os.environ['DATABASE_URL'] = 'sqlite:///' + DB.as_posix()
from sqlalchemy import event
from fastapi.testclient import TestClient
from backend.database import init_db, engine, SessionLocal
from backend.scripts.init_seed_data import seed_all
from backend.algorithms import single_recommender as current
from backend.algorithms.fridge_clock import is_expired, remaining_days
from backend.models import Dish, FridgeInventory
from backend.main import app
from backend.routers import recommend as route

init_db()
with SessionLocal() as db:
    seed_all(db)


def reference_status(db, user_id, dish):
    # Independently expressed per-dish implementation retaining existing F09 semantics.
    mains = {str(m).strip() for m in (dish.ingredients_main or []) if str(m).strip()}
    if not mains:
        return 0.0
    inventory = db.query(FridgeInventory).filter_by(user_id=user_id).all()
    matched = 0.0
    for main in mains:
        for item in inventory:
            name = str(item.ingredient_name).strip()
            if not name or is_expired(item):
                continue
            if name in main or main in name:
                matched += 2.0 if remaining_days(item) <= 2 else 1.0
                break
    return round(min(100.0, 100.0 * matched / len(mains)), 2)


src = (ROOT / 'backend/algorithms/single_recommender.py').read_text(encoding='utf-8')
prefetch = '''    fridge_index: Sequence[tuple[str, float]] = (
        _fridge_index(db, user_id) if mode_type == "HOME_COOKING" else ()
    )'''
assert src.count(prefetch) == 1
assert src.count('status = _fridge_status_from_index(fridge_index, dish)') == 1
reference = types.ModuleType('backend.algorithms._review_reference')
reference.__package__ = 'backend.algorithms'
exec(compile(src.replace(prefetch, '').replace('status = _fridge_status_from_index(fridge_index, dish)',
    'status = reference_status(db, user_id, dish)'), '<review_per_dish_reference>', 'exec'), reference.__dict__)
reference.reference_status = reference_status

client = TestClient(app)
records = []


def api_request(implementation, mode, tag):
    statements = []
    def listener(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            statements.append({'sql': statement, 'parameters': repr(parameters)})
    route.recommend_single = implementation
    event.listen(engine, 'before_cursor_execute', listener)
    start = time.perf_counter()
    try:
        response = client.post('/api/v1/recommend/single', headers={'X-User-Id':'2'}, json={'user_id':2,'mode_type':mode,'limit':100})
    finally:
        elapsed = (time.perf_counter() - start) * 1000
        event.remove(engine, 'before_cursor_execute', listener)
        route.recommend_single = current.recommend_single
    assert response.status_code == 200, response.text
    (OUT / f'sql-{tag}.json').write_text(json.dumps(statements, ensure_ascii=False, indent=2), encoding='utf-8')
    return response.json(), {'selects':len(statements), 'fridge_selects':sum('fridge_inventory' in x['sql'] for x in statements), 'elapsed_ms':round(elapsed,3)}


for scale in ['40', '400']:
    if scale == '400':
        with SessionLocal() as db:
            originals = db.query(Dish).filter_by(mode_type='HOME_COOKING').all()
            for _ in range(9):
                for dish in originals:
                    values = {c.name:getattr(dish,c.name) for c in Dish.__table__.columns if c.name != 'id'}
                    db.add(Dish(**values))
            db.commit()
    for mode in ['HOME_COOKING', 'OUT_DINING']:
        before, bcount = api_request(reference.recommend_single, mode, f'{scale}-{mode}-per-dish')
        after, acount = api_request(current.recommend_single, mode, f'{scale}-{mode}-batched')
        latencies = {'per_dish':[], 'batched':[]}
        for k in range(7):
            for label, impl in [('per_dish',reference.recommend_single), ('batched',current.recommend_single)]:
                _, stats = api_request(impl, mode, f'{scale}-{mode}-{label}-timing')
                latencies[label].append(stats['elapsed_ms'])
        records.append({'pool_home':int(scale), 'mode':mode, 'returned':len(after['recommendations']),
            'before':bcount, 'after':acount, 'entire_response_equal':before==after,
            'latencies_ms':latencies, 'median_ms':{k:round(statistics.median(v),3) for k,v in latencies.items()}})

with SessionLocal() as db:
    db.query(FridgeInventory).filter_by(user_id=2).delete()
    now = datetime.utcnow()
    db.add_all([
        FridgeInventory(user_id=2, ingredient_name='fresh',category='review',expire_days=5,created_at=now),
        FridgeInventory(user_id=2, ingredient_name='soon',category='review',expire_days=2,created_at=now),
        FridgeInventory(user_id=2, ingredient_name='expired',category='review',expire_days=1,created_at=now-timedelta(days=2)),
    ])
    db.commit()
    index = current._fridge_index(db,2)
    cases=[]
    for mains, expected in [([],0),(['missing'],0),(['fresh','missing','other'],33.33),(['soon','missing','other'],66.67),(['expired','missing'],0),(['fresh','soon','missing'],100)]:
        dish=Dish(ingredients_main=mains)
        actual=current._fridge_status_from_index(index,dish)
        cases.append({'mains':mains,'expected':expected,'actual':actual,'matches_reference':actual==reference_status(db,2,dish)})
        assert actual == expected

result={'database':str(engine.url),'method':'actual POST /api/v1/recommend/single; event listener covers dependency and route SELECTs; independently expressed F09-aware per-dish reference; 7 alternating timed calls each', 'records':records, 'inventory_cases':cases}
(OUT/'r01-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
client.close()
