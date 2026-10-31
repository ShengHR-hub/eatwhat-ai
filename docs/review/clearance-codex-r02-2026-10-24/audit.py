"""Independent r02 review. Writes evidence only; production database is read-only."""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
from collections import Counter
from functools import wraps
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT))

def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def production_digest():
    db = sqlite3.connect((ROOT / 'backend/eatwhat.db').as_uri() + '?mode=ro', uri=True)
    db.execute('BEGIN')
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    result = {'logical_sha256': hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest(),
              'counts': {t: db.execute('SELECT count(*) FROM "'+t+'"').fetchone()[0] for t in tables},
              'journal_mode': db.execute('PRAGMA journal_mode').fetchone()[0]}
    db.close()
    return result

def baseline():
    results = {}
    for stage in ('PC01', 'PC02', 'PC03'):
        path = ROOT / f'docs/review/stages/{stage}/r02/SOURCE_MANIFEST.json'
        manifest = json.loads(path.read_text(encoding='utf-8-sig'))
        files=[]
        for item in manifest['files']:
            f = ROOT / item['path']
            actual=hashlib.sha256(f.read_bytes()).hexdigest()
            files.append({'path':item['path'],'expected':item['sha256'],'actual':actual,'matches':actual==item['sha256']})
        results[stage]={'manifest_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'files':files}
    code_files = sorted(p for folder in ('backend','frontend/src','scripts') for p in (ROOT/folder).rglob('*')
                        if p.is_file() and p.suffix in ('.py','.js','.vue','.css','.mjs','.json') and '__pycache__' not in p.parts)
    dump('source-before.json',{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in code_files})
    dump('baseline.json', {'manifests':results,'production':production_digest(),'python':sys.version})
    print(json.dumps(results,ensure_ascii=False,indent=2))
    print('PRODUCTION',production_digest())

def simulate():
    os.environ['DATABASE_URL']='sqlite:///file:D:/EatWhat/backend/eatwhat.db?mode=ro&uri=true'
    from backend.algorithms import simulate_personas as sim
    from backend.algorithms import single_recommender as single
    from backend.algorithms import group_recommender as group
    counts=Counter()
    def count(name, fn):
        @wraps(fn)
        def wrapper(*args,**kwargs):
            counts[name]+=1
            result=fn(*args,**kwargs)
            if name=='recommend_single' and counts[name]%4000==0:
                print('progress',dict(counts),flush=True)
            return result
        return wrapper
    sim.recommend_single=count('recommend_single',single.recommend_single)
    single.compute_decay_weights=count('compute_decay_weights',single.compute_decay_weights)
    sim.shortlist_candidates=count('shortlist_candidates',group.shortlist_candidates)
    prior=count('member_prior_scores',group.member_prior_scores)
    sim.member_prior_scores=group.member_prior_scores=prior
    original=group.compute_group_consensus
    paired=[]
    def consensus(db,members,cards,votes,**kwargs):
        counts['compute_group_consensus']+=1
        raw=json.dumps([members,cards,votes],sort_keys=True).encode()
        paired.append({'input_sha256':hashlib.sha256(raw).hexdigest(),'omega':kwargs['omega_group']})
        return original(db,members,cards,votes,**kwargs)
    sim.compute_group_consensus=consensus
    target=OUT/'simulation-default'
    assert not target.exists(), 'Never overwrite previous independent run'
    result=sim.build_benchmark(data_dir=target)
    archived=json.loads((ROOT/'docs/review/stages/PC01/r02/data/benchmark_seed20261024.json').read_text(encoding='utf-8'))
    comparisons={k:result[k]==archived[k] for k in ('sample','duplication_rate_curve','group_satisfaction_bars')}
    pairs_equal=len(paired)==2000 and all(paired[i]['input_sha256']==paired[i+1]['input_sha256'] for i in range(0,len(paired),2))
    dump('simulation-independent.json',result)
    dump('simulation-verification.json',{'observed_production_calls':dict(counts),'outer_reported_calls':result['params']['calls'],
        'outer_total':sum(result['params']['calls'].values()),'archived_equal':comparisons,'all_1000_consensus_inputs_paired':pairs_equal,'paired_inputs':paired})
    print(json.dumps({'observed_calls':dict(counts),'archived_equal':comparisons,'pairs_equal':pairs_equal,'result':result},ensure_ascii=False,indent=2))

def final():
    before=json.loads((OUT/'source-before.json').read_text(encoding='utf-8'))
    changed=[p for p,sha in before.items() if not (ROOT/p).exists() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=sha]
    initial=json.loads((OUT/'baseline.json').read_text(encoding='utf-8'))['production']
    now=production_digest()
    result={'changed_source_files':changed,'production_before':initial,'production_after':now,'production_unchanged':initial==now}
    dump('final-protection.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    {'baseline':baseline,'simulate':simulate,'final':final}[sys.argv[1]]()
