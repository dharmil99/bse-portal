import sys
import os
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_connect import get_engine

engine = get_engine()
conn = engine.connect()

# ── Pure math functions — each checks for divide by zero ──────────────────

def compute_net_margin(net_profit, revenue):
    if not revenue or revenue == 0:
        return None
    return round((net_profit / revenue) * 100, 2)

def compute_ebitda_margin(ebitda, revenue):
    if not revenue or revenue == 0:
        return None
    return round((ebitda / revenue) * 100, 2)

def compute_roe(net_profit, equity):
    if not equity or equity == 0:
        return None
    return round((net_profit / equity) * 100, 2)

def compute_roce(ebitda, total_assets, current_liab=0):
    capital_employed = (total_assets or 0) - (current_liab or 0)
    if not capital_employed or capital_employed == 0:
        return None
    return round((ebitda / capital_employed) * 100, 2)

def compute_de_ratio(total_debt, equity):
    if not equity or equity == 0:
        return None
    return round((total_debt or 0) / equity, 2)

def compute_pe_ratio(price, eps):
    if not eps or eps == 0:
        return None
    return round(price / eps, 2)

def compute_asset_turnover(revenue, total_assets):
    if not total_assets or total_assets == 0:
        return None
    return round(revenue / total_assets, 2)

# ── Fetch all quarterly results from DB ───────────────────────────────────

def fetch_all_results():
    result = conn.execute(text("""
        SELECT 
            q.result_id,
            q.company_id,
            c.company_name,
            q.quarter,
            q.period_end,
            q.revenue,
            q.net_profit,
            q.ebitda,
            q.total_debt,
            q.equity,
            q.total_assets,
            q.eps,
            c.market_cap
        FROM quarterly_results q
        JOIN companies c ON q.company_id = c.company_id
        ORDER BY q.company_id, q.period_end
    """))
    return result.fetchall()

# ── Calculate and store ratios for every row ──────────────────────────────

def calculate_and_store_all():
    rows = fetch_all_results()
    print(f"Processing {len(rows)} quarterly result rows...")

    inserted = 0
    skipped  = 0

    for row in rows:
        company_id   = row[1]
        company_name = row[2]
        quarter      = row[3]
        revenue      = row[5]
        net_profit   = row[6]
        ebitda       = row[7]
        total_debt   = row[8]
        equity       = row[9]
        total_assets = row[10]
        eps          = row[11]
        market_cap   = row[12]

        # Skip if no revenue (can't calculate meaningful ratios)
        if not revenue:
            skipped += 1
            continue

        # Calculate all ratios
        net_margin     = compute_net_margin(net_profit, revenue)
        ebitda_margin  = compute_ebitda_margin(ebitda, revenue)
        roe            = compute_roe(net_profit, equity)
        roce           = compute_roce(ebitda, total_assets)
        de_ratio       = compute_de_ratio(total_debt, equity)
        asset_turnover = compute_asset_turnover(revenue, total_assets)

        # PE ratio using market cap / (net_profit) approximation
        # Real PE = stock price / EPS — we use market cap proxy here
        pe_ratio = None
        if net_profit and net_profit > 0 and market_cap:
            pe_ratio = round(market_cap / net_profit, 2)

        try:
            conn.execute(text("""
                INSERT INTO financial_ratios
                (company_id, quarter, roe, roce, debt_to_equity,
                 net_margin, pe_ratio)
                VALUES (:cid, :q, :roe, :roce, :de, :nm, :pe)
                ON DUPLICATE KEY UPDATE
                    roe=VALUES(roe),
                    roce=VALUES(roce),
                    debt_to_equity=VALUES(debt_to_equity),
                    net_margin=VALUES(net_margin),
                    pe_ratio=VALUES(pe_ratio)
            """), {
                "cid":  company_id,
                "q":    quarter,
                "roe":  roe,
                "roce": roce,
                "de":   de_ratio,
                "nm":   net_margin,
                "pe":   pe_ratio
            })
            inserted += 1
        except Exception as e:
            print(f"  ERROR {company_name} {quarter}: {e}")
            skipped += 1

    conn.commit()
    print(f"Done! Inserted/updated: {inserted}  Skipped: {skipped}")

# ── Print a summary table after calculating ───────────────────────────────

def print_summary():
    result = conn.execute(text("""
        SELECT 
            c.company_name,
            s.sector_name,
            r.quarter,
            r.roe,
            r.roce,
            r.debt_to_equity,
            r.net_margin,
            r.pe_ratio
        FROM financial_ratios r
        JOIN companies c ON r.company_id = c.company_id
        JOIN sectors s ON c.sector_id = s.sector_id
        WHERE r.quarter = 'Q4FY25'
        ORDER BY r.roe DESC
    """))
    rows = result.fetchall()

    print(f"\n{'Company':<30} {'Sector':<22} {'ROE':>6} {'ROCE':>6} {'D/E':>6} {'NM%':>6} {'PE':>7}")
    print("-" * 85)
    for row in rows:
        print(
            f"{str(row[0]):<30} "
            f"{str(row[1]):<22} "
            f"{str(row[3] or 'N/A'):>6} "
            f"{str(row[4] or 'N/A'):>6} "
            f"{str(row[5] or 'N/A'):>6} "
            f"{str(row[6] or 'N/A'):>6} "
            f"{str(row[7] or 'N/A'):>7}"
        )

# ── Run ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("BSE Portal - Ratio Calculator")
    print("=" * 50)
    calculate_and_store_all()
    print_summary()
    conn.close()