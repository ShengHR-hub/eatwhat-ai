import json
from pathlib import Path
import random
import sqlite3

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
results={}
for seed in (20261024,7):
    path=ROOT/f'docs/review/simulation/sim_seed{seed}_groups.db'
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    rng=random.Random(seed+1)
    reported_mean=[];reported_least=[];full_mean=[];full_least=[];examples=[]
    veto_count=0
    for code,cards_json,report_json in db.execute('SELECT room_code,candidate_dish_ids,consensus_report FROM group_rooms ORDER BY room_code'):
        cards=json.loads(cards_json);report=json.loads(report_json)
        selected=rng.choice(cards)
        dish=next(d for d in report['dishes'] if d['dish_id']==selected)
        values=[m['satisfaction'] for m in dish['members']]
        assert len(values)==4
        reported_mean.append(min(100.,dish['mean_satisfaction']));reported_least.append(min(100.,dish['least_misery']))
        full_mean.append(min(100.,sum(values)/4));full_least.append(min(100.,min(values)))
        if dish['masked_by_veto']:
            veto_count+=1
            if len(examples)<3:examples.append({'room':code,'random_dish':selected,'stored_dish_report':dish,'full_four_mean':sum(values)/4,'full_four_least':min(values)})
    results[str(seed)]={'rooms':len(full_mean),'random_winners_with_veto':veto_count,
        'reported':[round(sum(reported_mean)/len(full_mean),2),round(sum(reported_least)/len(full_mean),2)],
        'four_members_including_veto_zero':[round(sum(full_mean)/len(full_mean),2),round(sum(full_least)/len(full_mean),2)],'examples':examples,
        'note':'Reconstructs documented post-aggregation cap at 100; member values use archived production report precision.'}
    db.close()
(OUT/'random-metric-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
