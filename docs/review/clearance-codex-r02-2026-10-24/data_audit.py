"""Read-only reconstruction of archived experiments, and disposable seed/SQL probes."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
sys.path.insert(0,str(ROOT))
os.environ['DATABASE_URL']='sqlite:///file:D:/EatWhat/backend/eatwhat.db?mode=ro&uri=true'

def dump(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def readonly(path):
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    return db

def archived():
    summary={}
    for seed in (20261024,7):
        payload=json.loads((ROOT/f'docs/review/stages/PC01/r02/data/benchmark_seed{seed}.json').read_text(encoding='utf-8'))
        arms={}
        for arm in ('ours','baseline'):
            path=ROOT/f'docs/review/simulation/sim_seed{seed}_{arm}.db'
            db=readonly(path)
            rows=db.execute('SELECT l.user_id,l.eaten_at,d.cuisine_type,l.mode_type FROM eating_logs l JOIN dishes_and_recipes d ON d.id=l.dish_id ORDER BY l.eaten_at,l.user_id,l.id').fetchall()
            last={}; daily=defaultdict(lambda:[0,0]); by_mode=defaultdict(lambda:[0,0]); sequences=defaultdict(list)
            for r in rows:
                uid=r['user_id']; day=r['eaten_at'][:10]; cuisine=r['cuisine_type']
                duplicate=uid in last and last[uid]==cuisine
                daily[day][0]+=duplicate; daily[day][1]+=1
                by_mode[r['mode_type']][0]+=duplicate; by_mode[r['mode_type']][1]+=1
                sequences[uid].append(r['mode_type']); last[uid]=cuisine
            dup=meals=0; curves=[]
            for day,(d,n) in sorted(daily.items()):
                dup+=d; meals+=n; curves.append(round(dup/meals,4))
            column='ours_lambda_0.5' if arm=='ours' else 'baseline_no_decay'
            arms[arm]={'db':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'logs':len(rows),'users':len(last),'days':len(daily),
                'all_user_120_meals':all(len(s)==120 for s in sequences.values()),'all_mode_alternation':all(all(a!=b for a,b in zip(s,s[1:])) for s in sequences.values()),
                'curve_reconstructed':curves[:14],'archive_curve_equal':curves[:14]==payload['duplication_rate_curve'][column],
                'mode_dup_counts':by_mode,'cuisine_catalog':[dict(x) for x in db.execute('SELECT mode_type,cuisine_type,count(*) n FROM dishes_and_recipes GROUP BY mode_type,cuisine_type')]}
            db.close()
        group_path=ROOT/f'docs/review/simulation/sim_seed{seed}_groups.db'
        db=readonly(group_path)
        rooms=[dict(r) for r in db.execute('SELECT * FROM group_rooms ORDER BY room_code')]
        vote_rows=[dict(r) for r in db.execute('SELECT * FROM room_votes ORDER BY room_code,user_id,dish_id')]
        votes_by=defaultdict(list)
        for v in vote_rows:votes_by[v['room_code']].append({k:v[k] for k in ('user_id','dish_id','vote_type')})
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from backend.algorithms.group_recommender import compute_group_consensus
        engine=create_engine('sqlite:///file:'+group_path.as_posix()+'?mode=ro&uri=true')
        rng=random.Random(seed+1)
        stats={k:[0.,0.] for k in ('mixed','average','random')}
        variants={'random_vetoed_winners':0,'all_stored_reports_equal':True,'all_room_members4_cards10':True,'duplicate_or_invalid_votes':0,'planned_cells':0,'random_mean_with_veto_zeros':0.0}
        fixture_hash=hashlib.sha256()
        with Session(engine) as session:
            for room in rooms:
                members=json.loads(room['member_user_ids']); cards=json.loads(room['candidate_dish_ids']); votes=votes_by[room['room_code']]
                variants['all_room_members4_cards10'] &= len(set(members))==4 and len(set(cards))==10
                variants['planned_cells']+=len(members)*len(cards)
                valid={(m,c) for m in members for c in cards}
                seen=set()
                for v in votes:
                    key=(v['user_id'],v['dish_id'])
                    if key not in valid or key in seen:variants['duplicate_or_invalid_votes']+=1
                    seen.add(key)
                fixture_hash.update(json.dumps([room['room_code'],members,cards,votes],sort_keys=True).encode())
                reports={name:compute_group_consensus(session,members,cards,votes,omega_group=w) for name,w in [('mixed',payload['params']['omega_val']),('average',1.0)]}
                variants['all_stored_reports_equal'] &= json.loads(room['consensus_report'])==reports['mixed']
                for name,report in reports.items():
                    winner=next((d for d in report['dishes'] if d['dish_id']==report['winner_dish_id']),None)
                    if winner:
                        stats[name][0]+=min(100.,winner['mean_satisfaction']);stats[name][1]+=min(100.,winner['least_misery'])
                card=rng.choice(cards)
                r=next(d for d in reports['mixed']['dishes'] if d['dish_id']==card)
                variants['random_vetoed_winners']+=r['masked_by_veto']
                stats['random'][0]+=min(100.,r['mean_satisfaction']);stats['random'][1]+=min(100.,r['least_misery'])
                variants['random_mean_with_veto_zeros']+=min(100.,sum(m['satisfaction'] for m in r['members'])/len(members))
        variants['random_mean_with_veto_zeros']=round(variants['random_mean_with_veto_zeros']/len(rooms),2)
        bars={'avg_scores':[round(stats[k][0]/len(rooms),2) for k in stats], 'least_misery_scores':[round(stats[k][1]/len(rooms),2) for k in stats]}
        variants.update({'rooms':len(rooms),'stored_votes':len(vote_rows),'missing_cells':variants['planned_cells']-len(vote_rows),'vote_types':dict(Counter(v['vote_type'] for v in vote_rows)),
                        'fixture_sha256':fixture_hash.hexdigest(),'recomputed_bars':bars,'archive_bars_equal':all(bars[k]==payload['group_satisfaction_bars'][k] for k in bars)})
        summary[str(seed)]={'single':arms,'group':variants,'archived_params':payload['params']}
        engine.dispose();db.close()
    prod=readonly(ROOT/'backend/eatwhat.db')
    stored=json.loads(prod.execute("SELECT benchmark_json FROM algo_configs WHERE config_name='default_production'").fetchone()[0])
    snapshot=json.loads((ROOT/'backend/scripts/benchmark_snapshot.json').read_text(encoding='utf-8'))
    archived=json.loads((ROOT/'docs/review/stages/PC01/r02/data/benchmark_seed20261024.json').read_text(encoding='utf-8'))
    expected={k:v for k,v in archived.items() if k!='params'}
    summary['production']={'benchmark_equals_archive_four_keys':stored==expected,'snapshot_equals_archive_four_keys':snapshot==expected,
                           'groups':prod.execute('SELECT count(*) FROM group_rooms').fetchone()[0],'votes':prod.execute('SELECT count(*) FROM room_votes').fetchone()[0]}
    prod.close()
    dump('archived-data-results.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

def seed_guard():
    box=OUT/'seed-sandbox';box.mkdir()
    source=ROOT/'backend/scripts/init_seed_data.py'
    copy=box/'init_seed_data.py';copy.write_bytes(source.read_bytes())
    payload=json.loads((ROOT/'backend/scripts/benchmark_snapshot.json').read_text(encoding='utf-8'))
    payload['generated_at']='STALE_REVIEW_SENTINEL';payload['duplication_rate_curve']['ours_lambda_0.5'][13]=0.1234
    (box/'benchmark_snapshot.json').write_text(json.dumps(payload),encoding='utf-8')
    dbpath=box/'disposable.sqlite'
    env={**os.environ,'PYTHONPATH':str(ROOT),'DATABASE_URL':'sqlite:///'+dbpath.as_posix(),'PYTHONIOENCODING':'utf-8'}
    r=subprocess.run([sys.executable,str(copy),'--force'],cwd=ROOT,env=env,text=True,encoding='utf-8',capture_output=True)
    (OUT/'seed-guard-cli.log').write_text(r.stdout+r.stderr,encoding='utf-8')
    db=readonly(dbpath)
    actual=json.loads(db.execute('SELECT benchmark_json FROM algo_configs').fetchone()[0]);db.close()
    result={'copied_source_sha256':hashlib.sha256(copy.read_bytes()).hexdigest(),'original_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'cli_exit':r.returncode,'output':r.stdout+r.stderr,'stale_snapshot_accepted':actual['generated_at']=='STALE_REVIEW_SENTINEL','stale_d14_persisted':actual['duplication_rate_curve']['ours_lambda_0.5'][13]}
    dump('seed-guard-results.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))

def repeat_seed():
    from backend.algorithms import simulate_personas as sim
    target=OUT/'simulation-seed7';assert not target.exists()
    payload=sim.build_benchmark(seed=7,lambda_val=.8,days=14,data_dir=target)
    old=json.loads((ROOT/'docs/review/stages/PC01/r02/data/benchmark_seed7.json').read_text(encoding='utf-8'))
    dump('seed7-independent.json',payload)
    result={'scope':'200 users x 14 days x 2 meals per arm + 1000 rooms; archived 60-day tail not rerun',
            'curve_equal':payload['duplication_rate_curve']==old['duplication_rate_curve'],
            'bars_equal':payload['group_satisfaction_bars']==old['group_satisfaction_bars'],'actual_params':payload['params']}
    dump('seed7-verification.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':{'archived':archived,'seed_guard':seed_guard,'repeat_seed':repeat_seed}[sys.argv[1]]()
