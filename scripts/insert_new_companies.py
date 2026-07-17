import sys
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')
from scripts.db_connect import get_engine
from sqlalchemy import text

engine = get_engine()

# (company_name, sector_name) — names match FILE_MAP exactly
NEW_COMPANIES = [
    ("Tata Elxsi Limited", "Information Technology"),
    ("Mphasis Limited", "Information Technology"),
    ("Coforge Limited", "Information Technology"),
    ("Persistent Systems Limited", "Information Technology"),
    ("LTIMindtree Limited", "Information Technology"),

    ("Varun Beverages Limited", "FMCG"),
    ("Colgate-Palmolive (India) Limited", "FMCG"),
    ("Godrej Consumer Products Limited", "FMCG"),
    ("Marico Limited", "FMCG"),
    ("Dabur India Limited", "FMCG"),

    ("Zydus Lifesciences Limited", "Pharmaceuticals"),
    ("Torrent Pharmaceuticals Limited", "Pharmaceuticals"),
    ("Aurobindo Pharma Limited", "Pharmaceuticals"),
    ("Lupin Limited", "Pharmaceuticals"),

    ("Bharat Petroleum Corporation Limited", "Energy"),
    ("GAIL (India) Limited", "Energy"),
    ("JSW Energy Limited", "Energy"),
    ("Tata Power Company Limited", "Energy"),
    ("Adani Green Energy Limited", "Energy"),

    ("NMDC Limited", "Metals & Mining"),
    ("Hindustan Copper Limited", "Metals & Mining"),
    ("Hindustan Zinc Limited", "Metals & Mining"),
    ("Jindal Steel & Power Limited", "Metals & Mining"),
    ("National Aluminium Company Limited", "Metals & Mining"),
    ("Steel Authority of India Limited", "Metals & Mining"),
    ("Vedanta Limited", "Metals & Mining"),

    ("Birla Corporation Limited", "Cement"),
    ("The Ramco Cements Limited", "Cement"),
    ("JK Lakshmi Cement Limited", "Cement"),
    ("JK Cement Limited", "Cement"),
    ("Ambuja Cements Limited", "Cement"),
    ("ACC Limited", "Cement"),
    ("Dalmia Bharat Limited", "Cement"),
    ("Shree Cement Limited", "Cement"),

    ("Kalyan Jewellers India Limited", "Consumer"),
    ("Whirlpool of India Limited", "Consumer"),
    ("Blue Star Limited", "Consumer"),
    ("Dixon Technologies (India) Limited", "Consumer"),
    ("Voltas Limited", "Consumer"),
    ("Havells India Limited", "Consumer"),
    ("Asian Paints Limited", "Consumer"),
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
            "bse": f"P{str(i).zfill(5)}",
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