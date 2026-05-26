import sqlite3
import json

conn = sqlite3.connect("data/jobs.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

q1 = cursor.execute("SELECT * FROM questions WHERE id='Q_G0_DOMAIN_001'").fetchone()
q2 = cursor.execute("SELECT * FROM questions WHERE id='Q_G0_SUBDOMAIN_001'").fetchone()

if q1:
    print("Q_G0_DOMAIN_001:")
    d = dict(q1)
    for k, v in d.items():
        if k in ("options", "scoring", "role_targets"):
            try:
                v = json.loads(v)
            except:
                pass
        print(f"  {k}: {v}")

if q2:
    print("\nQ_G0_SUBDOMAIN_001:")
    d = dict(q2)
    for k, v in d.items():
        if k in ("options", "scoring", "role_targets"):
            try:
                v = json.loads(v)
            except:
                pass
        print(f"  {k}: {v}")

conn.close()
