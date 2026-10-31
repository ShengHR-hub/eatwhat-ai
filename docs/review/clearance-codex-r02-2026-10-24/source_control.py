import hashlib
import json
from pathlib import Path

out=Path(__file__).resolve().parent;root=out.parents[2]
src=(root/'backend/algorithms/single_recommender.py').read_text(encoding='utf-8')
src=src.replace('from datetime import datetime\n','').replace('    now: Optional[datetime] = None,\n','')
comment='    # `now`：仿真实验（R02）要按历史时刻重放决策，衰减查询必须能用可控时钟。\n    # 生产调用不传，等价于 datetime.utcnow()；这不是算法改动，只是把时点变成参数。\n\n'
assert comment in src
src=src.replace(comment,'').replace('params["lambda_decay"], now=now','params["lambda_decay"]')
old=json.loads((root/'docs/review/stages/PC02/r01/SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
expected=old['files'][0]['sha256']
hashes={style:hashlib.sha256(s.encode()).hexdigest() for style,s in [('lf',src),('crlf',src.replace('\n','\r\n'))]}
result={'method':'Remove only R02 now adapter from current source, compare r01 manifest SHA256','expected_r01':expected,'reconstructed':hashes,'only_clock_adapter_changed':expected in hashes.values()}
(out/'r01-source-control.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
