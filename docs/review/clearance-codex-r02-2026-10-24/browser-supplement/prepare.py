import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from datetime import datetime

out=Path(__file__).resolve().parent;root=out.parents[3]
sys.path.insert(0,str(root/'docs/review/clearance-codex-r02-2026-10-24'))
from audit import production_digest
target=out/'ui-isolated.sqlite'
assert not target.exists(),'Do not overwrite earlier browser evidence'
manifests={}
for stage in ('PC01','PC02','PC03'):
    p=root/f'docs/review/stages/{stage}/r02/SOURCE_MANIFEST.json'
    m=json.loads(p.read_text(encoding='utf-8-sig'))
    checks=[{'path':f['path'],'matches':hashlib.sha256((root/f['path']).read_bytes()).hexdigest()==f['sha256']} for f in m['files']]
    assert all(f['matches'] for f in checks),checks
    manifests[stage]=checks
source=sqlite3.connect((root/'backend/eatwhat.db').as_uri()+'?mode=ro',uri=True)
destination=sqlite3.connect(target)
source.backup(destination)
destination.close();source.close()
result={'generated_at':datetime.now().astimezone().isoformat(),'approval':'User explicitly confirmed sufficient browser approval balance in reply on 2026-10-24',
        'database':str(target),'source_matches_submissions':manifests,'production_before':production_digest(),
        'frontend':'http://127.0.0.1:5182','backend':'http://127.0.0.1:8022'}
(out/'baseline.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
