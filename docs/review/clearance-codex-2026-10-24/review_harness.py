"""Independent review probes. Never imports the application before DB isolation."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
DB = OUT / 'review-isolated.sqlite'
os.environ['DATABASE_URL'] = 'sqlite:///' + DB.as_posix()


def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def demo_summary():
    path = ROOT / 'backend/eatwhat.db'
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    db.execute('BEGIN')
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    counts = {t: db.execute('SELECT COUNT(*) FROM "' + t + '"').fetchone()[0] for t in tables}
    digest = hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest()
    journal = db.execute('PRAGMA journal_mode').fetchone()[0]
    db.close()
    return {'path': str(path), 'opened': 'mode=ro, read transaction', 'journal_mode': journal,
            'logical_dump_sha256': digest, 'counts': counts}


def baseline():
    files = []
    for base in ['backend', 'frontend/src', 'scripts']:
        for p in sorted((ROOT / base).rglob('*')):
            if not p.is_file() or '__pycache__' in p.parts or p.suffix not in ['.py', '.js', '.mjs', '.vue', '.css', '.json']:
                continue
            files.append({'path': p.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    for n in ['MASTER_SPEC.md', 'BATCH4_PLAN.md', 'BATCH4_PRE_CLEARANCE.md', 'docs/REVIEW_RULES.md', 'frontend/tailwind.config.js', 'frontend/package.json', 'frontend/vite.config.js']:
        p = ROOT / n
        files.append({'path': n, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    save('SOURCE_MANIFEST.json', files)
    checked = []
    for pc in ['PC01', 'PC02', 'PC03']:
        p = ROOT / f'docs/review/stages/{pc}/r01/SOURCE_MANIFEST.json'
        data = json.loads(p.read_text(encoding='utf-8-sig'))
        mismatches = []
        for row in data['files']:
            f = ROOT / row['path']
            actual = hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None
            if actual != row['sha256']:
                mismatches.append({'path': row['path'], 'submitted': row['sha256'], 'actual': actual})
        checked.append({'step': pc, 'manifest_sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'files': len(data['files']), 'mismatches': mismatches})
    save('submitted-manifest-check.json', checked)
    save('demo-before.json', demo_summary())
    old = subprocess.run(['git', 'show', ':backend/algorithms/single_recommender.py'], cwd=ROOT, capture_output=True, check=True).stdout
    (OUT / 'index_single_recommender.py.txt').write_bytes(old)
    print(json.dumps({'manifests': checked, 'isolated_database': str(DB)}, ensure_ascii=False, indent=2))


def seed():
    assert not DB.exists(), 'Refuse to overwrite prior isolated review database'
    from backend.database import init_db, SessionLocal, engine
    from backend.scripts.init_seed_data import seed_all
    init_db()
    with SessionLocal() as s:
        counts = seed_all(s)
    print(json.dumps({'database': str(engine.url), 'seed_counts': counts}, ensure_ascii=False))


def simulation():
    from backend.algorithms import simulate_personas as sim
    from backend.database import SessionLocal
    from backend.models import AlgoConfig
    calls = {}
    def profiler(frame, event, arg):
        if event == 'call' and frame.f_code.co_name in ['recommend_single', 'compute_decay_weights', 'compute_group_consensus', 'shortlist_candidates']:
            k = frame.f_globals.get('__name__', '') + '.' + frame.f_code.co_name
            calls[k] = calls.get(k, 0) + 1
    flow = sim._run_single_agent_flow
    group = sim._run_group_flow
    rand = sim._run_random_strategy
    runs = []
    current = {}
    def audited_flow(*args, **kwargs):
        logs, rates = flow(*args, **kwargs)
        decay = kwargs.get('decay_lambda')
        label = 'baseline' if decay is None else 'decay'
        with gzip.open(OUT / f"meals-{current['tag']}-{label}.jsonl.gz", 'wt', encoding='utf-8') as f:
            for row in logs:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
        rates_recomputed = []
        for day in range(1, 15):
            subset = [x for x in logs if x['day'] <= day]
            rates_recomputed.append(round(sum(bool(x['duplicated']) for x in subset) / len(subset), 4))
        current.setdefault('flows', []).append({'label': label, 'rows': len(logs), 'persons': len({x['persona'] for x in logs}),
            'days': len({x['day'] for x in logs}), 'curve_recomputed_matches': rates_recomputed == rates[:14]})
        return logs, rates
    def wrap_group(fn, label):
        def wrapped(rng, *args, **kwargs):
            sampled = []
            original = rng.sample
            def spy(population, k, *a, **kw):
                result = original(population, k, *a, **kw)
                sampled.append([x.id if hasattr(x, 'id') else x for x in result])
                return result
            rng.sample = spy
            try:
                result = fn(rng, *args, **kwargs)
            finally:
                rng.sample = original
            current.setdefault('groups', []).append({'label': label, 'omega': kwargs.get('omega'),
                'sample_hash': hashlib.sha256(json.dumps(sampled).encode()).hexdigest(), 'first_case': sampled[:2],
                'calls': len(sampled), 'result': result})
            return result
        return wrapped
    sim._run_single_agent_flow = audited_flow
    sim._run_group_flow = wrap_group(group, 'scored')
    sim._run_random_strategy = wrap_group(rand, 'random')
    for tag, seed_num, lam, omega in [('default-a', 20261024, .5, .5), ('default-b', 20261024, .5, .5), ('seed7', 7, .8, .6)]:
        current = {'tag': tag, 'seed': seed_num, 'lambda': lam, 'omega': omega}
        start = time.perf_counter()
        sys.setprofile(profiler)
        try:
            payload = sim.build_benchmark(seed_num, lam, omega)
        finally:
            sys.setprofile(None)
        sim.write_benchmark(payload)
        with SessionLocal() as s:
            stored = s.query(AlgoConfig).filter_by(config_name='default_production').one().benchmark_json
        current.update({'elapsed_seconds': round(time.perf_counter()-start, 3), 'stored_equals_output': stored == {k:v for k,v in payload.items() if k != 'params'}})
        save('benchmark-' + tag + '.json', payload)
        runs.append(current)
        print(json.dumps(current, ensure_ascii=False), flush=True)
    a = json.loads((OUT/'benchmark-default-a.json').read_text(encoding='utf-8'))
    b = json.loads((OUT/'benchmark-default-b.json').read_text(encoding='utf-8'))
    save('r02-results.json', {'runs': runs, 'production_algorithm_calls': calls,
        'reproducible_excluding_generated_at': {k:v for k,v in a.items() if k!='generated_at'} == {k:v for k,v in b.items() if k!='generated_at'}})


if __name__ == '__main__':
    op = sys.argv[1]
    if op == 'baseline': baseline()
    elif op == 'seed': seed()
    elif op == 'simulation': simulation()
    elif op == 'final':
        result = demo_summary()
        save('demo-after.json', result)
        print(json.dumps({'demo_logical_unchanged': result == json.loads((OUT/'demo-before.json').read_text(encoding='utf-8'))}, ensure_ascii=False))
