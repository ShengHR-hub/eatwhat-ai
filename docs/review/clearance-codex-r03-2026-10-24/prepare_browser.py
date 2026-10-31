import json
import sqlite3
from pathlib import Path
import socket

out=Path(__file__).resolve().parent;root=out.parents[2]
for port in (5183,8023):
    with socket.socket() as sock:
        assert sock.connect_ex(('127.0.0.1',port))!=0, f'Port {port} is occupied'
target=out/'browser-isolated.sqlite'
assert not target.exists()
with sqlite3.connect((root/'backend/eatwhat.db').as_uri()+'?mode=ro',uri=True) as src, sqlite3.connect(target) as dst:
    src.backup(dst)
(out/'browser').mkdir(exist_ok=True)
print(json.dumps({'database':str(target),'frontend':5183,'backend':8023,'balance':'user confirmation remains in this conversation'},ensure_ascii=False))
