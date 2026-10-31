import json
import os
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta

OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[2]
sys.path.insert(0,str(ROOT))
os.environ['DATABASE_URL']='sqlite:///'+(OUT/'cli-clean.sqlite').as_posix()
from backend.database import engine,Base,SessionLocal
from backend.models import EatingLog,Dish
from backend.scripts.init_seed_data import seed_all
from backend.algorithms import single_recommender as single

def dump(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

def cli():
    assert not (OUT/'cli-clean.sqlite').exists()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:seed_all(db)
    records=[]
    for scale in (40,400):
        if scale==400:
            with SessionLocal() as db:
                dishes=db.query(Dish).filter_by(mode_type='HOME_COOKING').all()
                for _ in range(9):
                    for dish in dishes:db.add(Dish(**{c.name:getattr(dish,c.name) for c in Dish.__table__.columns if c.name!='id'}))
                db.commit()
        for mode in ('HOME_COOKING','OUT_DINING'):
            runs={}
            for label,extra in [('batched',[]),('legacy',['--legacy'])]:
                args=[sys.executable,'-m','backend.scripts.measure_recommend_sql','--mode',mode,'--limit','100',*extra]
                r=subprocess.run(args,cwd=ROOT,env=os.environ,text=True,encoding='utf-8',capture_output=True)
                (OUT/f'cli-{scale}-{mode}-{label}.log').write_text(r.stdout+r.stderr,encoding='utf-8')
                assert r.returncode==0,r.stderr
                runs[label]=json.loads(r.stdout)
            records.append({'home_catalog':scale,'mode':mode,**runs,'same_top3':runs['batched']['top3']==runs['legacy']['top3'],'same_count':runs['batched']['returned']==runs['legacy']['returned']})
    dump('cli-results.json',records);print(json.dumps(records,ensure_ascii=False,indent=2))

def baseline_controls():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from backend.algorithms import simulate_personas as sim
    path=ROOT/'docs/review/simulation/sim_seed20261024_baseline.db'
    source=create_engine('sqlite:///file:'+path.as_posix()+'?mode=ro&uri=true')
    memory=create_engine('sqlite://')
    Base.metadata.create_all(memory)
    checks=[]
    original=single.compute_decay_weights
    with Session(source) as src,Session(memory) as db:
        sim._copy_catalog(src,db)
        personas=sim._seed_personas(db,random.Random(20261024),200)
        for day in (0,6,13,59):
            for uid in (1,2,31,120):
                query=sim.SIM_START+timedelta(days=day,hours=6)
                db.query(EatingLog).delete()
                histories=src.query(EatingLog).filter(EatingLog.user_id==uid,EatingLog.eaten_at<query).all()
                for log in histories:db.add(EatingLog(**{c.name:getattr(log,c.name) for c in EatingLog.__table__.columns if c.name!='id'}))
                db.commit()
                mode='OUT_DINING' if (uid+1)%2==0 else 'HOME_COOKING'
                params={'budget':personas[uid-1]['budget'],'weather_temp':22.,'weather_text':'晴','limit':10,'override_params':{'lambda_decay':.5}}
                shifted=single.recommend_single(db,uid,mode,now=query+timedelta(days=15),**params)
                single.compute_decay_weights=lambda db,uid,dishes,lam,now=None:{dish.id:1. for dish in dishes}
                try:direct=single.recommend_single(db,uid,mode,now=query,**params)
                finally:single.compute_decay_weights=original
                checks.append({'day':day+1,'uid':uid,'mode':mode,'past_meals':len(histories),'full_response_equal_to_decay_disabled':shifted==direct,
                               'all_shifted_weights_one':all(r['decay_weight']==1. for r in shifted['recommendations'])})
    memory.dispose();source.dispose()
    metric={}
    for arm in ('ours','baseline'):
        c=sqlite3.connect((ROOT/f'docs/review/simulation/sim_seed20261024_{arm}.db').as_uri()+'?mode=ro',uri=True)
        rows=c.execute("SELECT l.user_id,l.eaten_at,d.cuisine_type,l.mode_type FROM eating_logs l JOIN dishes_and_recipes d ON d.id=l.dish_id WHERE l.eaten_at<'2026-06-15' ORDER BY l.eaten_at,l.user_id,l.id").fetchall()
        last={};duplicates=0;transitions=0;home_family=0
        for uid,at,cuisine,mode in rows:
            duplicates+=uid in last and last[uid]==cuisine
            transitions+=uid in last
            home_family+=mode=='HOME_COOKING' and cuisine=='家常菜'
            last[uid]=cuisine
        metric[arm]={'days':14,'meals':len(rows),'duplicates':duplicates,'defined_transitions':transitions,'rate_per_meal':round(duplicates/len(rows),4),'rate_per_defined_transition':round(duplicates/transitions,4),'home_cuisine_family_count':home_family}
        c.close()
    r={'clock_shift_vs_explicit_decay_off':checks,'first14_metric':metric,
       'rank_vote_flat_priors':sim._vote_bands_for_member(random.Random(1),list(range(1,11)),{d:1. for d in range(1,11)})}
    dump('baseline-controls.json',r);print(json.dumps(r,ensure_ascii=False,indent=2))

if __name__=='__main__':{'cli':cli,'baseline':baseline_controls}[sys.argv[1]]()
