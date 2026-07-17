import sys
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')
from scripts.db_connect import get_engine
from sqlalchemy import text
engine = get_engine()
with engine.connect() as conn:
    rows = conn.execute(text('''
        SELECT s.sector_name, COUNT(c.company_id) as company_count
        FROM sectors s
        LEFT JOIN companies c ON c.sector_id = s.sector_id
        GROUP BY s.sector_name
        ORDER BY company_count DESC
    ''')).fetchall()
    for r in rows:
        print(r[0], '->', r[1])
