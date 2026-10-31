import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

out=Path(__file__).resolve().parent;root=out.parents[2]
sys.path.insert(0,str(root))
target=out/'benchmark-write.sqlite'
assert not target.exists()
os.environ['DATABASE_URL']='sqlite:///'+target.as_posix()
from backend.database import Base,engine,SessionLocal
from backend.models import AlgoConfig
from backend.algorithms import simulate_personas as sim
Base.metadata.create_all(engine)
payload=json.loads((out/'simulation-independent.json').read_text(encoding='utf-8'))
sim.write_benchmark(payload)
sim.write_benchmark(payload)
with SessionLocal() as session:
    rows=session.query(AlgoConfig).all()
    actual=rows[0].benchmark_json
    result={'real_write_benchmark_called_twice':True,'config_count':len(rows),
            'exact_four_keys':sorted(actual)==sorted(['generated_at','sample','duplication_rate_curve','group_satisfaction_bars']),
            'exact_independent_payload':actual=={k:v for k,v in payload.items() if k!='params'}}

box=out/'seed-sandbox';path=box/'disposable.sqlite'
db=sqlite3.connect(path)
fresh=json.loads(db.execute('SELECT benchmark_json FROM algo_configs').fetchone()[0])
fresh['generated_at']='NEWER_GOOD_REVIEW_SENTINEL';fresh['duplication_rate_curve']['ours_lambda_0.5'][13]=.0091
db.execute('UPDATE algo_configs SET benchmark_json=?',(json.dumps(fresh),));db.commit();db.close()
env={**os.environ,'DATABASE_URL':'sqlite:///'+path.as_posix(),'PYTHONPATH':str(root),'PYTHONIOENCODING':'utf-8'}
r=subprocess.run([sys.executable,str(box/'init_seed_data.py'),'--force'],cwd=root,env=env,encoding='utf-8',text=True,capture_output=True)
db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
after=json.loads(db.execute('SELECT benchmark_json FROM algo_configs').fetchone()[0]);db.close()
result['force_existing_newer_database']={'exit':r.returncode,'before_generated_at':fresh['generated_at'],
    'after_generated_at':after['generated_at'],'after_d14':after['duplication_rate_curve']['ours_lambda_0.5'][13],
    'newer_replaced_by_stale':after['generated_at']=='STALE_REVIEW_SENTINEL','output':r.stdout+r.stderr}
(out/'write-check-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
