"""Project audit probes; all probe writes use a seeded temporary SQLite file.

Run from repository root: python docs/review/audit-2026-10-24/probe_backend.py
The corrected probes do not modify production source or backend/eatwhat.db.
See REPORT.md for the first-run isolation incident and its exact rollback.
"""

import hashlib
import json
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.algorithms.group_recommender import compute_group_consensus, shortlist_candidates
from backend.algorithms.single_recommender import recommend_single
from backend.database import Base, get_db
from backend.main import app
from backend.models import Dish, EatingLog, FridgeInventory, GroupRoom, RoomVote, UserPreference, utcnow
from backend.routers import group_room
from backend.scripts.init_seed_data import seed_all


def production_db_hash():
    path = ROOT / 'backend/eatwhat.db'
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


@contextmanager
def isolated():
    temp = tempfile.TemporaryDirectory(prefix='eatwhat-audit-')
    engine = create_engine(f"sqlite:///{Path(temp.name).as_posix()}/audit.db", connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    with factory() as db:
        seed_all(db)
    audit_app = FastAPI()
    audit_app.include_router(app.router)

    def override_db():
        with factory() as db:
            yield db

    audit_app.dependency_overrides[get_db] = override_db
    saved_factory, saved_hub, saved_seconds = group_room.SessionLocal, group_room.hub, group_room.SWIPE_SECONDS
    group_room.SessionLocal = factory
    group_room.hub = group_room.RoomHub()
    try:
        with TestClient(audit_app, raise_server_exceptions=False) as client:
            yield client, factory, engine
    finally:
        group_room.SessionLocal, group_room.hub, group_room.SWIPE_SECONDS = saved_factory, saved_hub, saved_seconds
        engine.dispose()
        temp.cleanup()


def until(ws, kind):
    for _ in range(100):
        message = ws.receive_json()
        if message.get('type') == kind:
            return message
    raise AssertionError(f'No {kind} message')


results = {}
before = production_db_hash()

with isolated() as (client, factory, _):
    with factory() as db:
        ids = [d.id for d in db.query(Dish).order_by(Dish.id).limit(2)]
        report = compute_group_consensus(db, [1], ids, [
            {'user_id': 1, 'dish_id': did, 'vote_type': 'VETO'} for did in ids
        ])
        results['all_veto_still_has_winner'] = report

with isolated() as (client, factory, _):
    data = client.post('/api/v1/recommend/single', headers={'X-User-Id': '2'},
        json={'mode_type': 'HOME_COOKING', 'limit': 100}).json()
    with factory() as db:
        veto = db.query(UserPreference).filter_by(user_id=2).one().veto_tags
        returned = {r['dish_id'] for r in data['recommendations']}
        sea = [dict(id=d.id, name=d.name, mains=d.ingredients_main, aux=d.ingredients_aux)
               for d in db.query(Dish).filter(Dish.id.in_(returned)).all()
               if any('虾' in s for s in (d.ingredients_main or []) + (d.ingredients_aux or []))]
        group_ids = {r['dish_id'] for r in shortlist_candidates(db, [2], 'HOME_COOKING', top_n=100)}
        results['seafood_veto_leak'] = {'veto_tags': veto, 'single_returned_shrimp_dishes': sea,
            'group_also_shortlists': [d['id'] for d in sea if d['id'] in group_ids]}

with isolated() as (client, factory, _):
    response = client.post('/api/v1/logs/checkin', headers={'X-User-Id': '1'},
        json={'user_id': 2, 'dish_id': 1, 'mode_type': 'OUT_DINING'})
    with factory() as db:
        row = db.get(EatingLog, response.json()['log_id'])
        results['header_identity_overridden'] = {'status': response.status_code, 'header_user': 1, 'saved_user': row.user_id}
    response = client.put('/api/v1/users/2/preferences', headers={'X-User-Id': '1'}, json={'veto_tags': ['audit-marker']})
    results['path_identity_overridden'] = {'status': response.status_code, 'saved_user': response.json().get('user_id'),
        'saved_veto_tags': response.json().get('veto_tags')}
    response = client.post('/api/v1/rooms', headers={'X-User-Id': '1'}, json={'host_user_id': 2, 'mode_type': 'OUT_DINING'})
    results['room_header_identity_overridden'] = {'status': response.status_code, 'host': response.json().get('host_user_id')}
    results['documented_create_endpoint'] = client.post('/api/v1/rooms/create', json={'mode_type': 'OUT_DINING'}).status_code

with isolated() as (client, factory, _):
    group_room.SWIPE_SECONDS = 1
    room = client.post('/api/v1/rooms', json={'mode_type': 'OUT_DINING'}).json()
    code = room['room_code']
    with client.websocket_connect(f'/ws/room/{code}/1') as ws:
        until(ws, 'MEMBER_SYNC')
        ws.send_json({'type': 'START_SWIPING'})
        started = until(ws, 'START_SWIPING')
    time.sleep(1.3)
    snapshot = client.get(f'/api/v1/rooms/{code}').json()
    with client.websocket_connect(f'/ws/room/{code}/1') as ws:
        reconnect = until(ws, 'MEMBER_SYNC')
    results['disconnect_cancels_deadline'] = {'room_code': code, 'after_deadline_status': snapshot['status'],
        'reconnect_message': reconnect, 'candidate_count': snapshot['candidate_count']}

with isolated() as (client, factory, _):
    code = client.post('/api/v1/rooms', json={'mode_type': 'OUT_DINING'}).json()['room_code']
    with client.websocket_connect(f'/ws/room/{code}/1') as ws:
        until(ws, 'MEMBER_SYNC')
        ws.send_json({'type': 'START_SWIPING'})
        started = until(ws, 'START_SWIPING')
        for dish in started['candidates']:
            ws.send_json({'type': 'SUBMIT_VOTE', 'dish_id': dish['dish_id'], 'vote_type': 'LIKE'})
        reveal = until(ws, 'CONSENSUS_REVEAL')
        winner = reveal['winner_dish_id']
        ws.send_json({'type': 'SUBMIT_VOTE', 'dish_id': winner, 'vote_type': 'VETO'})
        until(ws, 'PROGRESS_UPDATE')
        with factory() as db:
            vote = db.query(RoomVote).filter_by(room_code=code, user_id=1, dish_id=winner).one()
            results['post_reveal_votes_mutable'] = {'winner': winner, 'vote_now': vote.vote_type,
                'persisted_winner': db.query(GroupRoom).filter_by(room_code=code).one().winner_dish_id}
    snap = client.get(f'/api/v1/rooms/{code}').json()
    results['finished_snapshot_keys'] = {'status': snap['status'], 'keys': list(snap)}

with isolated() as (client, factory, _):
    with factory() as db:
        db.query(FridgeInventory).filter_by(user_id=2).delete()
        db.add(FridgeInventory(user_id=2, ingredient_name='鲜虾', category='肉禽蛋奶', expire_days=3,
            created_at=utcnow() - timedelta(days=30)))
        db.commit()
        dish = db.query(Dish).filter_by(name='白灼虾', mode_type='HOME_COOKING').one()
        did = dish.id
    fridge = client.get('/api/v1/fridge/2').json()
    shopping = client.post('/api/v1/fridge/shopping-list', headers={'X-User-Id': '2'}, json={'dish_ids': [did]}).json()
    results['expired_inventory_never_ages'] = {'fridge_after_30_days': fridge, 'shopping_list': shopping}

with isolated() as (client, factory, engine):
    response = client.put('/api/v1/users/1/preferences', json={'base_vector': {'spicy_level': 999}, 'default_budget': -100})
    results['invalid_preferences_persisted'] = {'status': response.status_code,
        'base_vector': response.json().get('base_vector'), 'default_budget': response.json().get('default_budget')}
    response = client.post('/api/v1/recommend/single', json={'mode_type': 'OUT_DINING', 'override_params': {'lambda_decay': -10000}})
    results['negative_decay_crash'] = {'status': response.status_code, 'body': response.text[:200]}
    response = client.post('/api/v1/logs/checkin', json={'dish_id': 1, 'mode_type': 'OUT_DINING', 'cost_amount': -999999})
    results['negative_checkin_amount'] = {'status': response.status_code,
        'weekly_expense': client.get('/api/v1/logs/stats/1').json().get('weekly_expense')}

with isolated() as (client, factory, engine):
    counters = {'all_selects': 0, 'fridge_selects': 0}

    def count_queries(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            counters['all_selects'] += 1
            if 'fridge_inventory' in statement:
                counters['fridge_selects'] += 1

    event.listen(engine, 'before_cursor_execute', count_queries)
    response = client.post('/api/v1/recommend/single', json={'mode_type': 'HOME_COOKING', 'limit': 10})
    results['home_recommendation_query_count'] = {'status': response.status_code, **counters}

with isolated() as (client, factory, engine):
    payload = {'mode_type': 'OUT_DINING', 'limit': 24}
    first = client.post('/api/v1/recommend/single', json=payload).json()['recommendations']
    second = client.post('/api/v1/recommend/single', json=payload).json()['recommendations']
    full = client.post('/api/v1/recommend/single', json={**payload, 'limit': 100}).json()['recommendations']
    seen = {row['dish_id'] for row in first}
    results['home_next_batch_repeats_top24'] = {
        'first_batch_count': len(first),
        'same_ranked_ids': [r['dish_id'] for r in first] == [r['dish_id'] for r in second],
        'next_batch_after_frontend_seen_filter': len([r for r in second if r['dish_id'] not in seen]),
        'still_eligible_outside_top24': len([r for r in full if r['dish_id'] not in seen]),
    }

after = production_db_hash()
assert before == after, 'Production database changed during the corrected audit probes'
results['production_db_untouched'] = {'before_sha256': before, 'after_sha256': after, 'unchanged': before == after}
output = Path(__file__).with_name('backend-results.json')
output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(results, ensure_ascii=False, indent=2))
