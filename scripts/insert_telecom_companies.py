import sys
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')
from scripts.db_connect import get_engine
from sqlalchemy import text

engine = get_engine()

NEW_COMPANIES = [
    ("Route Mobile Limited", "Telecom"),
    ("Tejas Networks Limited", "Telecom"),
    ("Sterlite Technologies Limited", "Telecom"),
    ("HFCL Limited", "Telecom"),
    ("Railtel Corporation of India Limited", "Telecom"),
    ("Mahanagar Telephone Nigam Limited", "Telecom"),
    ("Tata Communications Limited", "Telecom"),
    ("Vodafone Idea Limited", "Telecom"),
]

with engine.connect() as conn:
    sector_map = dict(conn.execute(text("SELECT sector_name, sector_id FROM sectors")).fetchall())

    inserted, skipped = [], []
    for i, (company_name, sector_name) in enumerate(NEW_COMPANIES, start=1):
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
            "bse": f"T{str(i).zfill(5)}",
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