import sys
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')
from scripts.db_connect import get_engine
from sqlalchemy import text

engine = get_engine()

# (company_name, sector_name) — sectors taken from FILE_MAP comments in full_loader.py
MISSING_COMPANIES = [
    ("Apollo Hospitals Enterprise Limited", "Pharmaceuticals"),
    ("Max Healthcare Institute Limited", "Pharmaceuticals"),

    ("Endurance Technologies Limited", "Automobile"),
    ("Minda Corporation Limited", "Automobile"),
    ("Samvardhana Motherson International Limited", "Automobile"),
    ("Sona BLW Precision Forgings Limited", "Automobile"),
    ("TVS Motor Company Limited", "Automobile"),

    ("HDFC Life Insurance Company Limited", "Banking"),
    ("Jio Financial Services Limited", "Banking"),
    ("SBI Life Insurance Company Limited", "Banking"),

    ("Larsen & Toubro Limited", "Infrastructure"),

    ("Oil and Natural Gas Corporation Limited", "Energy"),
    ("Power Grid Corporation of India Limited", "Energy"),

    ("Tata Consumer Products Limited", "FMCG"),
]

with engine.connect() as conn:
    sector_map = dict(conn.execute(text("SELECT sector_name, sector_id FROM sectors")).fetchall())

    inserted, skipped = [], []
    for i, (company_name, sector_name) in enumerate(MISSING_COMPANIES, start=1):
        if sector_name not in sector_map:
            skipped.append((company_name, f"sector '{sector_name}' not found"))
            continue
        exists = conn.execute(text(
            "SELECT company_id FROM companies WHERE company_name = :name"
        ), {"name": company_name}).fetchone()
        if exists:
            skipped.append((company_name, "already exists"))
            continue
        conn.execute(text("""
            INSERT INTO companies (company_name, bse_code, sector_id, market_cap)
            VALUES (:name, :bse, :sid, NULL)
        """), {
            "name": company_name,
            "bse": f"M{str(i).zfill(5)}",
            "sid": sector_map[sector_name],
        })
        inserted.append(company_name)

    conn.commit()
    print(f"Inserted {len(inserted)} companies:")
    for n in inserted:
        print(f"  + {n}")
    if skipped:
        print(f"\nSkipped {len(skipped)}:")
        for n, r in skipped:
            print(f"  - {n}: {r}")