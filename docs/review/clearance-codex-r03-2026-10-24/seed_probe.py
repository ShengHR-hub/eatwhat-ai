"""Run the actual seeder main against copies and independent snapshot paths."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
BASE=OUT/'seed-cases'
BASE.mkdir(exist_ok=True)
good=json.loads((ROOT/'backend/scripts/benchmark_snapshot.json').read_text(encoding='utf-8'))

def digest(path):
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        return {'sha256':hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest(),
                'users':db.execute('SELECT count(*) FROM users').fetchone()[0],
                'benchmark':json.loads(db.execute('SELECT benchmark_json FROM algo_configs WHERE config_name="default_production"').fetchone()[0])}

def prepare(name,db_time,snapshot_time):
    case=BASE/name
    case.mkdir()
    target=case/'test.sqlite'
    with sqlite3.connect((ROOT/'backend/eatwhat.db').as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(target) as dst:
        src.backup(dst)
        value=copy.deepcopy(good);value['generated_at']=db_time
        dst.execute('UPDATE users SET nickname="REVIEW_DO_NOT_CLEAR" WHERE id=1')
        dst.execute('UPDATE algo_configs SET benchmark_json=?',(json.dumps(value),))
        dst.commit()
    snapshot=case/'snapshot.json'
    if snapshot_time is not None:
        value=copy.deepcopy(good);value['generated_at']=snapshot_time
        value['duplication_rate_curve']['ours_lambda_0.5'][-1]=0.1234
        snapshot.write_text(json.dumps(value),encoding='utf-8')
    return case,target,snapshot

wrapper=OUT/'seed_cli_wrapper.py'
wrapper.write_text('import os\nfrom pathlib import Path\nfrom backend.scripts import init_seed_data as seed\nseed.SNAPSHOT_PATH=Path(os.environ["REVIEW_SNAPSHOT"])\nseed.main()\n',encoding='utf-8')
results=[]
def run_case(name,db_time,snapshot_time,incoming=None,mutate=None,repeat=False):
    case,target,snapshot=prepare(name,db_time,snapshot_time)
    if mutate:
        value=json.loads(snapshot.read_text(encoding='utf-8'));mutate(value)
        snapshot.write_text(json.dumps(value),encoding='utf-8')
    args=[sys.executable,str(wrapper),'--force']
    if incoming is not None:
        (case/'incoming.json').write_text(json.dumps(incoming),encoding='utf-8')
        args+=['--benchmark-from',str(case/'incoming.json')]
    before=digest(target)
    snapshot_before=hashlib.sha256(snapshot.read_bytes()).hexdigest() if snapshot.exists() else None
    env=dict(os.environ,DATABASE_URL='sqlite:///'+target.as_posix(),REVIEW_SNAPSHOT=str(snapshot),PYTHONPATH=str(ROOT),PYTHONIOENCODING='utf-8')
    runs=[]
    for i in range(2 if repeat else 1):
        p=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
        (case/f'cli-{i}.log').write_text(p.stdout+p.stderr,encoding='utf-8')
        runs.append({'exit':p.returncode,'output':p.stdout+p.stderr})
    after=digest(target)
    results.append({'name':name,'db_time':db_time,'snapshot_time':snapshot_time,'runs':runs,
                    'before':before,'after':after,'database_unchanged':before==after,
                    'snapshot_unchanged':snapshot_before==(hashlib.sha256(snapshot.read_bytes()).hexdigest() if snapshot.exists() else None)})

run_case('stale-naive','2026-10-24T20:00:00','2026-10-20T00:00:00')
run_case('missing','2026-10-24T20:00:00',None)
broken=copy.deepcopy(good);broken['duplication_rate_curve']['ours_lambda_0.5']=[0.1]*5
run_case('bad-refresh','2026-10-24T20:00:00','2026-10-20T00:00:00',incoming=broken)
fresh=copy.deepcopy(good);fresh['generated_at']='2026-10-24T21:30:00'
run_case('repeat-fresh','2026-10-24T20:00:00','2026-10-20T00:00:00',incoming=fresh,repeat=True)
raw=json.loads((ROOT/'docs/review/stages/PC01/r03/data/benchmark_seed20261024.json').read_text(encoding='utf-8'))
run_case('raw-simulation-output','2026-10-24T20:00:00','2026-10-20T00:00:00',incoming=raw)
run_case('invalid-timestamp','2026-10-24T20:00:00','zz-not-a-date')
run_case('older-with-offset','2026-10-24T16:00:00+00:00','2026-10-24T23:00:00+08:00')
run_case('invalid-curve-sample','2026-10-24T20:00:00','2026-10-24T21:30:00',mutate=lambda v:(v['sample'].update(personas=0,rooms=-1),v['duplication_rate_curve'].update({'days':[14]*14,'ours_lambda_0.5':['NOT_A_NUMBER']*14})))
incoming=copy.deepcopy(good);incoming['generated_at']='2026-10-24T12:00:00'
run_case('rejected-after-snapshot-write','2026-10-24T20:00:00','2026-10-24T00:00:00',incoming=incoming)
(OUT/'seed-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{k:r[k] for k in ('name','database_unchanged','snapshot_unchanged')}|{'exits':[p['exit'] for p in r['runs']]} for r in results],ensure_ascii=False,indent=2))
