"""Read-only independent reconstruction of saved meals, votes and metrics."""
import hashlib
import json
import math
from pathlib import Path
import random
import sqlite3
import sys
from collections import Counter, defaultdict

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
sys.path.insert(0,str(ROOT))
from backend.algorithms.simulate_personas import _four_member_metrics

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def ro(path):return sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def meal_curve(rows):
    last={};counts=defaultdict(lambda:[0,0]);bad_flags=0
    for r in rows:
        uid=r['user_id'];dup=uid in last and last[uid]==r['cuisine_type']
        if 'duplicated' in r:bad_flags+=dup!=r['duplicated']
        counts[r['day']][0]+=int(dup);counts[r['day']][1]+=1
        last[uid]=r['cuisine_type']
    num=den=0;curve=[]
    for day in sorted(counts):
        a,b=counts[day];num+=a;den+=b;curve.append(round(num/den,4))
    return {'rows':sum(v[1] for v in counts.values()),'days':len(counts),'daily_counts':dict(counts),'curve14':curve[:14],'bad_flags':bad_flags}

def groups(path,seed,omega=.5):
    with ro(path) as db:
        prefs={uid:json.loads(v) for uid,v in db.execute('SELECT user_id,base_vector FROM user_preferences')}
        vectors={did:json.loads(v) for did,v in db.execute('SELECT id,feature_vector FROM dishes_and_recipes')}
        votes=defaultdict(dict);counts=Counter()
        for room,uid,did,vote in db.execute('SELECT room_code,user_id,dish_id,vote_type FROM room_votes'):
            votes[room][(uid,did)]=vote;counts[vote]+=1
        rows=db.execute('SELECT room_code,member_user_ids,candidate_dish_ids,consensus_report,winner_dish_id FROM group_rooms ORDER BY room_code').fetchall()
    keys=tuple(next(iter(prefs.values())).keys())
    def prior(uid,did):
        a=[max(0.,min(1.,prefs[uid].get(k,.5))) for k in keys]
        b=[max(0.,min(1.,vectors[did].get(k,.5))) for k in keys]
        denominator=math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
        return round(max(0.,min(1.,sum(x*y for x,y in zip(a,b))/denominator))*100.,2) if denominator else 0.
    rng=random.Random(seed+1);percap=[[],[],[]];aggregatecap=[[],[],[]]
    member_mismatch=0;winner_mismatch=0;invalid=[];veto_random=0
    for code,members,cards,report,winner in rows:
        members=json.loads(members);cards=json.loads(cards);report=json.loads(report)
        vmap=votes[code]
        if len(members)!=4 or len(set(members))!=4 or len(cards)!=10 or len(set(cards))!=10 or any(u not in members or d not in cards or v not in ('SUPER_LIKE','LIKE','PASS','VETO') for (u,d),v in vmap.items()):invalid.append(code)
        scored=[]
        for did in cards:
            vals=[];masked=False
            item=next(d for d in report['dishes'] if d['dish_id']==did)
            for uid in members:
                vote=vmap.get((uid,did),'TIMEOUT')
                value=0. if vote=='VETO' else .4*prior(uid,did)+.6*{'SUPER_LIKE':120,'LIKE':100,'PASS':40,'TIMEOUT':60}[vote]
                rounded=round(value,2)
                actual=next(m for m in item['members'] if m['user_id']==uid)
                member_mismatch+=actual['vote_type']!=vote or actual['satisfaction']!=rounded
                masked|=vote=='VETO';vals.append(rounded)
            # Winner selection uses the production unrounded per-member score.
            raw=[0. if vmap.get((uid,did))=='VETO' else .4*prior(uid,did)+.6*{'SUPER_LIKE':120,'LIKE':100,'PASS':40,'TIMEOUT':60}[vmap.get((uid,did),'TIMEOUT')] for uid in members]
            scored.append((did,masked,vals,round(omega*sum(raw)/4+(1-omega)*min(raw),2),round(sum(raw)/4,2)))
        eligible=[s for s in scored if not s[1]]
        mixed=min(eligible,key=lambda s:(-s[3],s[0])) if eligible else None
        average=min(eligible,key=lambda s:(-s[4],s[0])) if eligible else None
        winner_mismatch+=(mixed[0] if mixed else None)!=winner or winner!=report['winner_dish_id']
        picked=rng.choice(cards);random_item=next(s for s in scored if s[0]==picked)
        veto_random+=random_item[1]
        for i,item in enumerate((mixed,average,random_item)):
            vals=item[2] if item else [0.]*4
            capped=[min(100.,v) for v in vals]
            percap[i].append([round(sum(capped)/4,2),round(min(capped),2)])
            aggregatecap[i].append([min(100.,sum(vals)/4),min(100.,min(vals))])
    bars=lambda sets:{'avg_scores':[round(sum(v[0] for v in s)/len(s),2) for s in sets],
                      'least_misery_scores':[round(sum(v[1] for v in s)/len(s),2) for s in sets]}
    per_room=Counter(len(votes[r[0]]) for r in rows)
    return {'rooms':len(rows),'votes':sum(counts.values()),'vote_types':dict(counts),'votes_per_room':dict(per_room),
            'invalid_rooms':invalid,'member_score_mismatches':member_mismatch,'winner_mismatches':winner_mismatch,
            'per_member_cap_bars':bars(percap),'post_aggregation_cap_bars':bars(aggregatecap),'random_veto_rooms':veto_random}

result={'seeds':{},'group_checks':{},'snapshot':{}}
for seed in (20261024,7):
    data=ROOT/'docs/review/stages/PC01/r03/data'
    archive=read(data/f'benchmark_seed{seed}.json')
    detail=data/f'detail_seed{seed}.jsonl'
    arms=defaultdict(list)
    for line in detail.read_text(encoding='utf-8').splitlines():
        row=json.loads(line);arms[row['arm']].append(row)
    records={}
    for arm,rows in arms.items():
        records[arm]=meal_curve(rows)
        path=ROOT/f'docs/review/simulation/sim_seed{seed}_{arm}.db'
        with ro(path) as db:
            mealrows=db.execute('SELECT l.user_id,l.eaten_at,d.cuisine_type FROM eating_logs l JOIN dishes_and_recipes d ON l.dish_id=d.id ORDER BY l.eaten_at,l.id').fetchall()
            dayrows=[{'user_id':u,'day':int(at[8:10]) if at[5:7]=='06' else 30+int(at[8:10]),'cuisine_type':c} for u,at,c in mealrows]
            # SIM_START is June 1; the run spans June and July.
            records[arm]['database']=meal_curve(dayrows)
        key='ours_lambda_0.5' if arm=='ours' else 'baseline_no_decay'
        records[arm]['detail_curve_equal']=records[arm]['curve14']==archive['duplication_rate_curve'][key]
    result['seeds'][str(seed)]={'arms':records,'detail_sha256':sha(detail),'detail_rows':sum(len(v) for v in arms.values())}
    for suffix,rngseed in (('groups',seed),('absence',seed+7)):
        value=groups(ROOT/f'docs/review/simulation/sim_seed{seed}_{suffix}.db',rngseed,archive['params']['omega_val'])
        expected=archive['group_satisfaction_bars'] if suffix=='groups' else archive['params']['absence']
        value['bars_equal_to_archive']=all(value['per_member_cap_bars'][k]==expected[k] for k in ('avg_scores','least_misery_scores'))
        result['group_checks'][f'{seed}-{suffix}']=value

with ro(ROOT/'backend/eatwhat.db') as db:
    dbvalue=json.loads(db.execute('SELECT benchmark_json FROM algo_configs WHERE config_name="default_production"').fetchone()[0])
snapshot=read(ROOT/'backend/scripts/benchmark_snapshot.json')
archive=read(ROOT/'docs/review/stages/PC01/r03/data/benchmark_seed20261024.json')
archive4={k:v for k,v in archive.items() if k!='params'}
result['snapshot']={'keys':list(snapshot),'equal_archive':snapshot==archive4,'database_equal_archive':dbvalue==archive4}
fresh=OUT/'simulation-default'/f'detail_seed20261024.jsonl'
result['seeds']['20261024']['archived_detail_equal_independent']=sha(fresh)==result['seeds']['20261024']['detail_sha256']
old=ROOT/'docs/review/clearance-codex-r02-2026-10-24/simulation-default/sim_seed20261024_groups.db'
with ro(old) as db:
    report=json.loads(db.execute('SELECT consensus_report FROM group_rooms WHERE room_code="000001"').fetchone()[0])
item=next(i for i in report['dishes'] if i['dish_id']==52)
values=[m['satisfaction'] for m in item['members']]
result['r02_fixed_case']={'values':values,'r03_helper':_four_member_metrics(report,52),'uncapped_four_mean':sum(values)/4,'uncapped_four_min':min(values)}
result['r02_same_data_new_metrics']=groups(old,20261024)
(OUT/'data-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
