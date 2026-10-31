import hashlib
import json
from pathlib import Path
import re
from datetime import datetime

out=Path(__file__).resolve().parent;root=out.parents[2]
def load(name):return json.loads((out/name).read_text(encoding='utf-8'))
sim=load('simulation-verification.json')
assert all(sim['archived_equal'].values()) and sim['all_1000_consensus_inputs_paired']
assert sim['outer_total']==52000 and sim['observed_production_calls']['recommend_single']==48000
assert load('seed7-verification.json')['curve_equal'] and load('seed7-verification.json')['bars_equal']
assert all(x['matches'] for v in load('baseline.json')['manifests'].values() for x in v['files'])
assert load('r01-source-control.json')['only_clock_adapter_changed']
assert load('final-protection.json')['production_unchanged'] and not load('final-protection.json')['changed_source_files']
assert not (out/'must-not-exist.sqlite').exists()
assert all(r['entire_response_equal'] for r in load('r01-results.json')['records'])
assert all(r['same_top3'] and r['same_count'] for r in load('cli-results.json'))
assert load('write-check-results.json')['force_existing_newer_database']['newer_replaced_by_stale']
assert '6 passed' in (out/'query-pytest.log').read_text(encoding='utf-8-sig')
assert '131 passed' in (out/'pytest.log').read_text(encoding='utf-8-sig')
colors=load('color-results.json')
assert len(colors['astBusinessLiteralFindings'])==0 and all(c['valuesUnchanged'] for c in colors['materialChecks'])
assert len([p for p in colors['probes'] if not p['correct']])==4
documents=[out/'REPORT.md',*(root/f'docs/review/stages/{s}/r02/REVIEW.md' for s in ('PC01','PC02','PC03')),root/'docs/review/STAGE_STATUS.md']
links=[]
for doc in documents:
    text=doc.read_text(encoding='utf-8')
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if ':' in target or target.startswith('#'):continue
        path=(doc.parent/target.split('#')[0]).resolve()
        links.append({'from':doc.relative_to(root).as_posix(),'target':target,'exists':path.exists()})
assert all(l['exists'] for l in links),links
stage=(root/'docs/review/STAGE_STATUS.md').read_text(encoding='utf-8')
for row in stage.splitlines():
    if row.startswith('| S09 |'):assert '| LOCKED |' in row
    if row.startswith('| PC02 |'):assert '| PASS |' in row
    if row.startswith('| PC01 |') or row.startswith('| PC03 |'):assert '| CHANGES_REQUIRED |' in row
index={'generated_at_local':datetime.now().astimezone().isoformat(),'checks_passed':True,'links':links,'files':[]}
for f in sorted(out.rglob('*')):
    if not f.is_file() or '__pycache__' in f.parts or f.name=='evidence-index.json':continue
    index['files'].append({'path':f.relative_to(out).as_posix(),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
for doc in documents[1:]:index['files'].append({'path':doc.relative_to(root).as_posix(),'bytes':doc.stat().st_size,'sha256':hashlib.sha256(doc.read_bytes()).hexdigest()})
(out/'evidence-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checks_passed':True,'evidence_files':len(index['files']),'links_checked':len(links),'timestamp':index['generated_at_local']},ensure_ascii=False))
