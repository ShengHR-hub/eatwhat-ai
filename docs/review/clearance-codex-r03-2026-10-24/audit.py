"""Independent r03 review. Only writes into this review directory."""
import hashlib
import json
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from functools import wraps
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT))

def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def production_digest():
    with sqlite3.connect((ROOT / 'backend/eatwhat.db').as_uri() + '?mode=ro', uri=True) as db:
        db.execute('BEGIN')
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {'logical_sha256': hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest(),
                'counts': {t: db.execute('SELECT count(*) FROM "'+t+'"').fetchone()[0] for t in tables}}

def baseline():
    assert not (OUT/'baseline.json').exists(), 'Do not overwrite original baseline'
    manifests = {}
    for stage in ('PC01', 'PC03'):
        p = ROOT/f'docs/review/stages/{stage}/r03/SOURCE_MANIFEST.json'
        m = json.loads(p.read_text(encoding='utf-8-sig'))
        checks = [{'path':f['path'], 'expected':f['sha256'],
                   'actual':hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest()}
                  for f in m['files']]
        for f in checks:
            f['matches'] = f['expected'] == f['actual']
        manifests[stage] = {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(), 'files':checks}
    assert all(f['matches'] for s in manifests.values() for f in s['files']), manifests
    files = {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
             for folder in ('backend','frontend/src','scripts') for p in (ROOT/folder).rglob('*')
             if p.is_file() and p.suffix in ('.py','.js','.vue','.css','.mjs','.json') and '__pycache__' not in p.parts}
    dump('source-before.json',files)
    prior = json.loads((ROOT/'docs/review/clearance-codex-r02-2026-10-24/source-before.json').read_text(encoding='utf-8'))
    changed = [p for p,s in prior.items() if files.get(p)!=s]
    added = [p for p in files if p not in prior]
    result = {'at':datetime.now().astimezone().isoformat(),'manifests':manifests,
              'production':production_digest(),'source_changed_since_r02':changed,'new_source_since_r02':added}
    dump('baseline.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

def simulate(seed=20261024,lambda_val=.5,omega_val=.5):
    os.environ['DATABASE_URL'] = 'sqlite:///file:D:/EatWhat/backend/eatwhat.db?mode=ro&uri=true'
    from backend.algorithms import simulate_personas as sim
    from backend.algorithms import single_recommender as single
    from backend.algorithms import group_recommender as group
    counts = Counter()
    paired = []
    def count(name,fn):
        @wraps(fn)
        def wrapped(*args,**kw):
            counts[name]+=1
            result=fn(*args,**kw)
            if name=='recommend_single' and counts[name]%4000==0:
                print(datetime.now().isoformat(), 'PROGRESS',dict(counts),flush=True)
            return result
        return wrapped
    sim.recommend_single=count('recommend_single',single.recommend_single)
    single.compute_decay_weights=count('compute_decay_weights',single.compute_decay_weights)
    sim.shortlist_candidates=count('shortlist_candidates',group.shortlist_candidates)
    prior=count('member_prior_scores',group.member_prior_scores)
    sim.member_prior_scores=group.member_prior_scores=prior
    original=group.compute_group_consensus
    def consensus(db,members,cards,votes,**kwargs):
        counts['compute_group_consensus']+=1
        raw=json.dumps([members,cards,votes],sort_keys=True).encode()
        paired.append({'input_sha256':hashlib.sha256(raw).hexdigest(),'omega':kwargs['omega_group']})
        return original(db,members,cards,votes,**kwargs)
    sim.compute_group_consensus=consensus
    target=OUT/('simulation-default' if seed==20261024 else 'simulation-seed7')
    assert not target.exists(),'Never overwrite an earlier run'
    print('START',datetime.now().astimezone().isoformat(),'target',str(target),flush=True)
    result=sim.build_benchmark(seed=seed,lambda_val=lambda_val,omega_val=omega_val,data_dir=target)
    archived=json.loads((ROOT/f'docs/review/stages/PC01/r03/data/benchmark_seed{seed}.json').read_text(encoding='utf-8'))
    comparisons={k:result[k]==archived[k] for k in ('sample','duplication_rate_curve','group_satisfaction_bars')}
    group_equal=result['params']['group']==archived['params']['group']
    absence_equal=result['params']['absence']==archived['params']['absence']
    pairs_equal=len(paired)==2400 and all(paired[i]['input_sha256']==paired[i+1]['input_sha256'] for i in range(0,len(paired),2))
    prefix='simulation' if seed==20261024 else 'seed7'
    dump(prefix+'-independent.json',result)
    evidence={'at':datetime.now().astimezone().isoformat(),'production_calls':dict(counts),
              'archived_equal':comparisons,'group_equal':group_equal,'absence_equal':absence_equal,
              'paired_inputs_equal':pairs_equal,'pairs':paired,'outer_params':result['params']}
    dump(prefix+'-verification.json',evidence)
    print(json.dumps(evidence,ensure_ascii=False,indent=2),flush=True)
    assert all(comparisons.values()) and group_equal and absence_equal and pairs_equal

def final():
    source=json.loads((OUT/'source-before.json').read_text(encoding='utf-8'))
    changed=[p for p,s in source.items() if not (ROOT/p).exists() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=s]
    before=json.loads((OUT/'baseline.json').read_text(encoding='utf-8'))['production']
    now=production_digest()
    result={'at':datetime.now().astimezone().isoformat(),'changed_business_source_files':changed,
            'production_before':before,'production_after':now,'production_unchanged':before==now}
    dump('final-protection.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    assert not changed and before==now

if __name__=='__main__':
    {'baseline':baseline,'simulate':simulate,'simulate7':lambda:simulate(7,.8,.6),'final':final}[sys.argv[1]]()
