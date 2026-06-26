import sys
import os
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_connect import get_engine

engine = get_engine()
conn = engine.connect()

# ── Pure math functions ────────────────────────────────────────────────────

def compute_net_margin(net_profit, revenue):
    try:
        if net_profit is None or revenue is None:
            return None
        if float(revenue) == 0:
            return None
        return round((float(net_profit) / float(revenue)) * 100, 2)
    except:
        return None

def compute_ebitda_margin(ebitda, revenue):
    try:
        if ebitda is None or revenue is None:
            return None
        if float(revenue) == 0:
            return None
        return round((float(ebitda) / float(revenue)) * 100, 2)
    except:
        return None

def compute_roe(net_profit, equity):
    try:
        if net_profit is None or equity is None:
            return None
        if float(equity) == 0:
            return None
        return round((float(net_profit) / float(equity)) * 100, 2)
    except:
        return None

def compute_roce(ebitda, total_assets, current_liab=0):
    capital_employed = (total_assets or 0) - (current_liab or 0)
    if not capital_employed or capital_employed == 0:
        return None
    return round((ebitda / capital_employed) * 100, 2)

def compute_de_ratio(total_debt, equity):
    try:
        if not equity or float(equity) == 0:
            return None
        return round(float(total_debt or 0) / float(equity), 2)
    except:
        return None

def compute_pe_ratio(price, eps):
    if not eps or eps == 0:
        return None
    return round(price / eps, 2)

def compute_asset_turnover(revenue, total_assets):
    if not total_assets or total_assets == 0:
        return None
    return round(revenue / total_assets, 2)

# ── From quarterly_results ─────────────────────────────────────────────────

def fetch_all_results():
    result = conn.execute(text("""
        SELECT
            q.result_id, q.company_id, c.company_name,
            q.quarter, q.period_end, q.revenue, q.net_profit,
            q.ebitda, q.total_debt, q.equity, q.total_assets,
            q.eps, c.market_cap
        FROM quarterly_results q
        JOIN companies c ON q.company_id = c.company_id
        ORDER BY q.company_id, q.period_end
    """))
    return result.fetchall()

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

        if not revenue:
            skipped += 1
            continue

        net_margin     = compute_net_margin(net_profit, revenue)
        ebitda_margin  = compute_ebitda_margin(ebitda, revenue)
        roe            = compute_roe(net_profit, equity)
        roce           = compute_roce(ebitda, total_assets)
        de_ratio       = compute_de_ratio(total_debt, equity)
        asset_turnover = compute_asset_turnover(revenue, total_assets)

        pe_ratio = None
        if net_profit and net_profit > 0 and market_cap:
            pe_ratio = round(float(market_cap) / float(net_profit), 2)

        try:
            conn.execute(text("""
                INSERT INTO financial_ratios
                    (company_id, quarter, roe, roce, debt_to_equity,
                     net_margin, pe_ratio)
                VALUES (:cid, :q, :roe, :roce, :de, :nm, :pe)
                ON DUPLICATE KEY UPDATE
                    roe=VALUES(roe), roce=VALUES(roce),
                    debt_to_equity=VALUES(debt_to_equity),
                    net_margin=VALUES(net_margin),
                    pe_ratio=VALUES(pe_ratio)
            """), {
                "cid": company_id, "q": quarter,
                "roe": roe, "roce": roce,
                "de": de_ratio, "nm": net_margin, "pe": pe_ratio
            })
            inserted += 1
        except Exception as e:
            print(f"  ERROR {company_name} {quarter}: {e}")
            skipped += 1

    conn.commit()
    print(f"Done! Inserted/updated: {inserted}  Skipped: {skipped}")

# ── From profit_loss (fallback for new companies) ─────────────────────────

def calculate_from_profit_loss():
    result = conn.execute(text("""
        SELECT DISTINCT c.company_id, c.company_name
        FROM companies c
        JOIN profit_loss pl ON pl.company_id = c.company_id
        WHERE c.company_id NOT IN (
            SELECT DISTINCT company_id FROM quarterly_results
            WHERE revenue IS NOT NULL AND equity IS NOT NULL
        )
    """))
    companies = result.fetchall()
    print(f"\nProcessing {len(companies)} companies from profit_loss table...")

    for company in companies:
        company_id   = company[0]
        company_name = company[1]

        rows = conn.execute(text("""
            SELECT pl.fiscal_year, pl.sales, pl.net_profit,
                   pl.interest, pl.depreciation,
                   bs.equity_capital, bs.reserves, bs.borrowings,
                   bs.total_assets, bs.other_liabilities
            FROM profit_loss pl
            LEFT JOIN balance_sheet bs
                ON bs.company_id = pl.company_id
               AND bs.fiscal_year = pl.fiscal_year
            WHERE pl.company_id = :cid
            ORDER BY pl.fiscal_year
        """), {"cid": company_id}).fetchall()

        for row in rows:
            fy           = row[0]
            sales        = row[1]
            net_profit   = row[2]
            interest     = row[3]
            depreciation = row[4]
            eq_capital   = row[5]
            reserves     = row[6]
            borrowings   = row[7]
            total_assets = row[8]
            other_liab   = row[9]

            if not sales:
                continue

            quarter = f"Q4{fy}"

            net_margin = compute_net_margin(net_profit, sales)

            ebitda = None
            if net_profit and interest and depreciation:
                try:
                    ebitda = float(net_profit) + float(interest) + float(depreciation)
                except:
                    pass
            ebitda_margin = compute_ebitda_margin(ebitda, sales)

            equity = None
            if eq_capital is not None and reserves is not None:
                try:
                    equity = float(eq_capital) + float(reserves)
                except:
                    pass

            roe = compute_roe(net_profit, equity)

            ebit = None
            if net_profit and interest:
                try:
                    ebit = float(net_profit) + float(interest)
                except:
                    pass

            cap_employed = None
            if equity is not None and borrowings is not None:
                try:
                    cap_employed = equity + float(borrowings)
                except:
                    pass

            roce = None
            if ebit and cap_employed and cap_employed != 0:
                roce = round(ebit / cap_employed * 100, 2)

            de_ratio = compute_de_ratio(borrowings, equity)

            try:
                conn.execute(text("""
                    INSERT INTO financial_ratios
                        (company_id, quarter, roe, roce,
                         debt_to_equity, net_margin)
                    VALUES (:cid, :q, :roe, :roce, :de, :nm)
                    ON DUPLICATE KEY UPDATE
                        roe=VALUES(roe),
                        roce=VALUES(roce),
                        debt_to_equity=VALUES(debt_to_equity),
                        net_margin=VALUES(net_margin)
                """), {
                    "cid":  company_id, "q": quarter,
                    "roe":  roe, "roce": roce,
                    "de":   de_ratio, "nm": net_margin,
                })
            except Exception as e:
                print(f"  ERROR {company_name} {quarter}: {e}")

        print(f"  OK: {company_name}")

    conn.commit()
    print("Done!")

# ── Summary ────────────────────────────────────────────────────────────────

def print_summary():
    result = conn.execute(text("""
        SELECT
            c.company_name, s.sector_name,
            r.quarter, r.roe, r.roce,
            r.debt_to_equity, r.net_margin, r.pe_ratio
        FROM financial_ratios r
        JOIN companies c ON r.company_id = c.company_id
        JOIN sectors s ON c.sector_id = s.sector_id
        WHERE r.quarter = 'Q4FY25'
        ORDER BY r.roe DESC
    """))
    rows = result.fetchall()

    print(f"\n{'Company':<30} {'Sector':<22} {'ROE':>8} {'ROCE':>6} {'D/E':>6} {'NM%':>6} {'PE':>8}")
    print("-" * 90)
    for row in rows:
        print(
            f"{str(row[0]):<30} "
            f"{str(row[1]):<22} "
            f"{str(row[3] or 'N/A'):>8} "
            f"{str(row[4] or 'N/A'):>6} "
            f"{str(row[5] or 'N/A'):>6} "
            f"{str(row[6] or 'N/A'):>6} "
            f"{str(row[7] or 'N/A'):>8}"
        )

# ── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("BSE Portal - Ratio Calculator")
    print("=" * 50)
    calculate_and_store_all()
    calculate_from_profit_loss()
    print_summary()
    conn.close()