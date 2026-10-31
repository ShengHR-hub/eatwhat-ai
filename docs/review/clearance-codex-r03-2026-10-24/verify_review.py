"""Verify the independent review's evidence and document links; no business writes."""
import hashlib
import json
from pathlib import Path
import re
import socket
from PIL import Image

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
read = lambda p: json.loads((OUT / p).read_text(encoding='utf-8'))

for file in ('simulation-verification.json', 'seed7-verification.json'):
    value = read(file)
    assert all(value['archived_equal'].values())
    assert value['group_equal'] and value['absence_equal'] and value['paired_inputs_equal']
    assert value['production_calls']['recommend_single'] == 48000
    assert value['production_calls']['compute_group_consensus'] == 2400
    assert len(value['pairs']) == 2400

data = read('data-results.json')
assert data['snapshot']['equal_archive'] and data['snapshot']['database_equal_archive']
assert data['seeds']['20261024']['archived_detail_equal_independent']
for seed in ('20261024', '7'):
    assert data['seeds'][seed]['detail_rows'] == 48000
    group = data['group_checks'][seed + '-groups']
    assert group['rooms'] == 1000 and group['votes'] == 40000
    assert group['votes_per_room'] == {'40': 1000}
    assert not group['invalid_rooms']
    assert group['member_score_mismatches'] == group['winner_mismatches'] == 0
    assert group['bars_equal_to_archive']
assert data['r02_fixed_case']['r03_helper'] == [66.35, 0.0]

seeds = {v['name']: v for v in read('seed-results.json')}
for case in ('invalid-timestamp', 'older-with-offset', 'invalid-curve-sample'):
    assert seeds[case]['runs'][0]['exit'] == 0
    assert not seeds[case]['database_unchanged']
assert seeds['rejected-after-snapshot-write']['runs'][0]['exit'] == 1
assert seeds['rejected-after-snapshot-write']['database_unchanged']
assert not seeds['rejected-after-snapshot-write']['snapshot_unchanged']

colors = read('color-results.json')
assert colors['production']['exit'] == 0
assert not colors['astBusinessLiteralFindings']
assert len(colors['probes']) == 22
assert sum(p['correct'] for p in colors['probes']) == 19
assert all(p['syntaxValid'] and p['checkerExit'] == 0 for p in read('syntax-results.json'))

baseline = read('baseline.json')
for manifest in baseline['manifests'].values():
    assert all(p['matches'] for p in manifest['files'])
    for item in manifest['files']:
        target = OUT / 'AGENT_MEMORY-before-review.md' if item['path'] == 'docs/AGENT_MEMORY.md' else ROOT / item['path']
        assert hashlib.sha256(target.read_bytes()).hexdigest() == item['expected'], item['path']

protection = read('final-protection.json')
assert protection['production_unchanged']
assert not protection['changed_business_source_files']
assert protection['production_after']['counts']['group_rooms'] == 0
assert protection['production_after']['counts']['room_votes'] == 0

for height, card_height in ((844, 422), (667, 261)):
    geometry = read(f'browser/home-390x{height}.json')
    assert geometry['width'] == 390 and geometry['height'] == geometry['scrollHeight'] == height
    assert geometry['card']['height'] == card_height <= height * .6
    assert geometry['nav']['y'] - geometry['actionBox']['bottom'] == 8
    assert all(hit['hit'] for hit in geometry['actions'])
    with Image.open(OUT / f'browser/home-390x{height}.jpg') as screenshot:
        assert screenshot.format == 'JPEG' and screenshot.size == (390, height)

actions = read('browser/actions.json')
assert any(a.get('url', '').endswith('/m/footprint') and '这周都吃了什么' in a.get('state', '') for a in actions)
assert any(a.get('url', '').endswith('/m/profile') and '饮食基因' in a.get('state', '') for a in actions)
assert 'radio "下厨" [checked]' in (OUT / 'browser/cooking.txt').read_text(encoding='utf-8')
assert any(p['truncated'] for p in read('browser/events.json'))

assert '140 passed' in (OUT / 'pytest-workspace-temp.log').read_text(encoding='utf-8')
assert '6 passed' in (OUT / 'query-pytest.log').read_text(encoding='utf-8')
assert 'built in 7.04s' in (OUT / 'build.log').read_text(encoding='utf-8')
assert not (OUT / 'must-not-exist.sqlite').exists()
for port in (8023, 5183):
    with socket.socket() as sock:
        assert sock.connect_ex(('127.0.0.1', port)) != 0, f'Own server still active on {port}'

documents = [OUT / 'REPORT.md', ROOT / 'docs/review/stages/PC01/r03/REVIEW.md',
             ROOT / 'docs/review/stages/PC03/r03/REVIEW.md', ROOT / 'docs/review/STAGE_STATUS.md']
checked_links = 0
for document in documents:
    body = document.read_text(encoding='utf-8')
    for link in re.findall(r'\]\(([^)]+)\)', body):
        if '://' in link or link.startswith('#'):
            continue
        target = document.parent / link.split('#')[0]
        if target in (OUT / 'review-validation.json', OUT / 'evidence-index.json'):
            continue  # Written below, after all evidence assertions succeed.
        assert target.exists(), (document, link)
        checked_links += 1
status = documents[-1].read_text(encoding='utf-8')
for stage in ('PC01', 'PC03'):
    assert f'| {stage} |' in status
    assert 'CHANGES_REQUIRED' in next(line for line in status.splitlines() if line.startswith(f'| {stage} |'))
assert 'LOCKED' in next(line for line in status.splitlines() if line.startswith('| S09 |'))

result = {'verification': 'PASS', 'document_links_checked': checked_links,
          'conclusions': {'PC01': 'FAIL', 'PC02': 'PASS_RETAINED', 'PC03': 'FAIL'},
          'S09': 'LOCKED', 'batch4': 'LOCKED', 'own_servers_stopped': True,
          'production_unchanged': True, 'business_source_unchanged': True}
(OUT / 'review-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
files = [p for p in OUT.iterdir() if p.is_file() and p.name != 'evidence-index.json']
for folder in ('browser', 'simulation-default', 'simulation-seed7'):
    files += [p for p in (OUT / folder).iterdir() if p.is_file()]
index = [{'path': str(p.relative_to(ROOT)).replace('\\', '/'), 'bytes': p.stat().st_size,
          'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]
(OUT / 'evidence-index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
