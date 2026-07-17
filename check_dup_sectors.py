import sys
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')
from scripts.db_connect import get_engine
from sqlalchemy import text
engine = get_engine()
with engine.connect() as conn:
    rows = conn.execute(text('''
        SELECT sector_name, COUNT(*) as dup_count, GROUP_CONCAT(sector_id) as ids
        FROM sectors
        GROUP BY sector_name
        HAVING COUNT(*) > 1
        ORDER BY dup_count DESC
    ''')).fetchall()
    for r in rows:
        print(r[0], '->', r[1], 'duplicate rows, ids:', r[2])
