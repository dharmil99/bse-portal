from db_connect import get_engine
from sqlalchemy import text
import pandas as pd

print("Starting...")

engine = get_engine()
print("Engine created")

conn = engine.connect()
print("Connected!")

# Insert sector
conn.execute(text("INSERT IGNORE INTO sectors (sector_name, industry) VALUES ('Information Technology', 'IT Services')"))
conn.commit()
print("Sector inserted")

# Get sector_id
r = conn.execute(text("SELECT sector_id FROM sectors LIMIT 1"))
sector_id = r.fetchone()[0]
print("Sector ID:", sector_id)

# Insert company
conn.execute(text("INSERT IGNORE INTO companies (bse_code, nse_symbol, company_name, sector_id, market_cap) VALUES ('500209', 'INFY', 'Infosys Limited', 1, 621000.00)"))
conn.commit()
print("Company inserted")

# Load CSV
df = pd.read_csv(r"C:\Users\Jignesh\Desktop\bse_portal\data\clean\infosys_clean.csv", index_col=0)
print("CSV loaded. Years:", df.columns.tolist())

# Insert each year
for year in df.columns:
    revenue    = float(df.loc['Sales', year])
    net_profit = float(df.loc['Net profit', year])
    eps        = float(df.loc['EPS', year])
    quarter    = f"Q4FY{str(year)[2:]}"
    period     = f"{year}-03-31"
    conn.execute(text("INSERT IGNORE INTO quarterly_results (company_id, quarter, period_end, revenue, net_profit, eps) VALUES (1, :q, :p, :r, :n, :e)"),
        {"q": quarter, "p": period, "r": revenue, "n": net_profit, "e": eps})
    print(f"Inserted {quarter}: Revenue={revenue}")

conn.commit()
print("All done!")

conn.close()