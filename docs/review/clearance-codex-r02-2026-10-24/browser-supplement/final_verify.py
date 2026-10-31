"""Check browser evidence without changing application files."""
import hashlib
import json
import socket
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

OUT = Path(__file__).resolve().parent
REVIEW = OUT.parent
ROOT = OUT.parents[3]
sys.path.insert(0, str(REVIEW))
from audit import production_digest

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

before = load(OUT / 'baseline.json')
now = production_digest()
source = load(REVIEW / 'source-before.json')
changed = [p for p, sha in source.items()
           if not (ROOT / p).exists() or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != sha]
new_business = []
for folder in ('backend', 'frontend/src', 'scripts'):
    for p in (ROOT / folder).rglob('*'):
        if p.is_file() and p.suffix in ('.py', '.js', '.vue', '.css', '.mjs', '.json') and '__pycache__' not in p.parts:
            if p.relative_to(ROOT).as_posix() not in source:
                new_business.append(p.relative_to(ROOT).as_posix())

db = sqlite3.connect((OUT / 'ui-isolated.sqlite').as_uri() + '?mode=ro', uri=True)
isolated_counts = {t: db.execute('SELECT count(*) FROM "' + t + '"').fetchone()[0]
                   for t in ('eating_logs', 'group_rooms', 'room_votes', 'users', 'fridge_inventory')}
meal_rows = db.execute('SELECT * FROM eating_logs WHERE id > 9').fetchall()
meal_columns = [d[0] for d in db.execute('SELECT * FROM eating_logs LIMIT 0').description]
db.close()
ports = {}
for port in (5182, 8022):
    with socket.socket() as sock:
        sock.settimeout(1)
        ports[str(port)] = sock.connect_ex(('127.0.0.1', port)) != 0

summary = load(OUT / 'summary.json')
for case in summary['layoutChecks']:
    assert all(case[k] for k in ('noPageScroll', 'cardUnder60Percent', 'cardFullyBeforeCandidates', 'actionsAboveTab')), case
    if case['allRecordedCentersHit'] is not None:
        assert case['allRecordedCentersHit']
assert summary['swapVerified'] == {'before': ['番茄炒蛋'], 'after': ['洋葱炒蛋']}
assert summary['mealFootprintVerified']
assert summary['network']['responses'] == 123
assert all(not summary['network'][k] for k in ('httpNon2xx', 'loadingFailed', 'uncaughtExceptions', 'truncated'))
assert summary['console']['errorCount'] == 0
assert not changed and not new_business
assert now == before['production_before']
assert isolated_counts['eating_logs'] == 10 and len(meal_rows) == 1
assert isolated_counts['group_rooms'] == isolated_counts['room_votes'] == 0
assert all(ports.values()), ports
result = {'generated_at': datetime.now().astimezone().isoformat(),
          'production_before': before['production_before'], 'production_after': now,
          'production_unchanged': now == before['production_before'],
          'changed_source_files': changed, 'new_business_source_files': new_business,
          'isolated_counts': isolated_counts,
          'isolated_new_meals': [dict(zip(meal_columns, row)) for row in meal_rows],
          'cleanup': {'test_ports_closed': ports, 'viewport_reset': True,
                      'agent_tab_5_closed': True,
                      'browser_cleanup_evidence': 'Successful viewport.reset() and tab.close() in browser tool result; own server sessions stopped with Ctrl+C.'},
          'checks_passed': True}
(OUT / 'final-protection.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
