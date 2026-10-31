import json
import os
from pathlib import Path
import random
import sys
from datetime import datetime, timedelta

OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parents[2]))
os.environ['DATABASE_URL']='sqlite:///:memory:'
from backend.database import init_db, SessionLocal
from backend.scripts.init_seed_data import seed_all
from backend.models import Dish, EatingLog
from backend.algorithms import simulate_personas as sim
from backend.algorithms.time_decay import compute_decay_weights
init_db()
results={}
with SessionLocal() as db:
    seed_all(db)
    db.query(EatingLog).filter_by(user_id=2).delete()
    dish=db.query(Dish).filter_by(mode_type='HOME_COOKING').first()
    now=datetime(2026,10,24,12)
    cases=[]
    for days_ago in [1,31]:
        db.query(EatingLog).filter_by(user_id=2).delete()
        db.add(EatingLog(user_id=2,dish_id=dish.id,mode_type=dish.mode_type,cost_amount=1,eaten_at=now-timedelta(days=days_ago)))
        db.commit()
        actual=compute_decay_weights(db,2,[dish],lambda_decay=.5,now=now)[dish.id]
        imitation=sim._decay_weight(dish,{dish.id:40-days_ago},{dish.cuisine_type:40-days_ago},
            {str(m).strip():40-days_ago for m in dish.ingredients_main},40,.5)
        cases.append({'days_since_only_exact_dish_log':days_ago,'production':actual,'simulation':imitation})
    results['decay_differences']=cases
    personas=sim._make_personas(random.Random(20261024))
    dishes=db.query(Dish).all()
    rng=random.Random(20261024)
    first=sim._run_group_flow(rng,personas,dishes,omega=1.0)
    second=sim._run_group_flow(rng,personas,dishes,omega=1.0)
    results['same_omega_sequential_control']={'first':first,'second':second,'equal':first==second}
    rng=random.Random(20261024)
    ids=[d.id for d in rng.sample(dishes,10)]
    modes=sorted({d.mode_type for d in dishes if d.id in ids})
    results['first_group_candidate_modes']={'dish_ids':ids,'modes':modes}
(OUT/'r02-semantic-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
