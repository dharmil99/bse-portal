import sys
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')
from scripts.db_connect import get_engine
from sqlalchemy import text
engine = get_engine()
with engine.connect() as conn:
    rows = conn.execute(text("SHOW COLUMNS FROM financial_ratios")).fetchall()
    for r in rows:
        print(r[0])
