import sys
import os
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.db_connect import get_engine

engine = get_engine()
conn = engine.connect()

def compute_revenue_growth(rev_current, rev_previous):
    if not rev_previous or rev_previous == 0:
        return None
    return round(((float(rev_current) - float(rev_previous)) / float(rev_previous)) * 100, 2)

def compute_cagr(rev_end, rev_start, years):
    if not rev_start or rev_start == 0 or not rev_end:
        return None
    if rev_end <= 0 or rev_start <= 0:
        return None
    return round(((float(rev_end) / float(rev_start)) ** (1 / years) - 1) * 100, 2)

def get_company_revenues(company_id):
    # First try quarterly_results
    result = conn.execute(text("""
        SELECT quarter, period_end, revenue
        FROM quarterly_results
        WHERE company_id = :cid AND revenue IS NOT NULL
        ORDER BY period_end ASC
    """), {"cid": company_id})
    rows = result.fetchall()
    
    # If not found, fall back to profit_loss table
    if len(rows) < 2:
        result2 = conn.execute(text("""
            SELECT 
                CONCAT('Q4', fiscal_year) as quarter,
                CONCAT('20', SUBSTRING(fiscal_year, 3), '-03-31') as period_end,
                sales as revenue
            FROM profit_loss
            WHERE company_id = :cid AND sales IS NOT NULL
            ORDER BY fiscal_year ASC
        """), {"cid": company_id})
        rows = result2.fetchall()
    
    return rows

def calculate_growth_for_all():
    # Get all companies
    companies = conn.execute(text(
        "SELECT company_id, company_name FROM companies ORDER BY company_id"
    )).fetchall()

    print(f"Calculating growth metrics for {len(companies)} companies...")
    print("=" * 55)

    for company in companies:
        company_id   = company[0]
        company_name = company[1]

        revenues = get_company_revenues(company_id)

        if len(revenues) < 2:
            print(f"  SKIP {company_name}: not enough data")
            continue

        # Build dict: year -> revenue
        rev_by_year = {}
        for row in revenues:
            year = str(row[1])[:4]  # "2025-03-31" -> "2025"
            rev_by_year[year] = row[2]

        years_sorted = sorted(rev_by_year.keys())

        for i, year in enumerate(years_sorted):
            quarter = f"Q4FY{str(year)[2:]}"
            rev_current = rev_by_year[year]

            # Revenue Growth YoY
            rev_growth = None
            if i > 0:
                prev_year = years_sorted[i - 1]
                rev_growth = compute_revenue_growth(
                    rev_current, rev_by_year[prev_year]
                )

            # 3-Year CAGR
            cagr_3y = None
            if i >= 3:
                year_3ago = years_sorted[i - 3]
                cagr_3y = compute_cagr(
                    rev_current, rev_by_year[year_3ago], 3
                )

            # 5-Year CAGR
            cagr_5y = None
            if i >= 5:
                year_5ago = years_sorted[i - 5]
                cagr_5y = compute_cagr(
                    rev_current, rev_by_year[year_5ago], 5
                )

            # EBITDA Margin — try quarterly_results first, then profit_loss
            qr = conn.execute(text("""
                SELECT ebitda, revenue FROM quarterly_results
                WHERE company_id = :cid AND quarter = :q
            """), {"cid": company_id, "q": quarter}).fetchone()

            ebitda_margin = None
            if qr and qr[0] and qr[1] and float(qr[1]) != 0:
                ebitda_margin = round((float(qr[0]) / float(qr[1])) * 100, 2)
            else:
                # Fall back to profit_loss
                fy = f"FY{quarter[4:]}"
                pl_row = conn.execute(text("""
                    SELECT net_profit, interest, depreciation, sales
                    FROM profit_loss
                    WHERE company_id = :cid AND fiscal_year = :fy
                """), {"cid": company_id, "fy": fy}).fetchone()
                if pl_row and pl_row[3] and float(pl_row[3]) != 0:
                    np  = float(pl_row[0] or 0)
                    int_= float(pl_row[1] or 0)
                    dep = float(pl_row[2] or 0)
                    rev = float(pl_row[3])
                    ebitda_margin = round((np + int_ + dep) / rev * 100, 2)
                    
            # Update financial_ratios table
            try:
                conn.execute(text("""
                    INSERT INTO financial_ratios
                        (company_id, quarter, revenue_growth,
                         cagr_3y, cagr_5y, ebitda_margin)
                    VALUES
                        (:cid, :q, :rg, :c3, :c5, :em)
                    ON DUPLICATE KEY UPDATE
                        revenue_growth = VALUES(revenue_growth),
                        cagr_3y        = VALUES(cagr_3y),
                        cagr_5y        = VALUES(cagr_5y),
                        ebitda_margin  = VALUES(ebitda_margin)
                """), {
                    "cid": company_id,
                    "q":   quarter,
                    "rg":  rev_growth,
                    "c3":  cagr_3y,
                    "c5":  cagr_5y,
                    "em":  ebitda_margin
                })
            except Exception as e:
                print(f"  ERROR {company_name} {quarter}: {e}")

        conn.commit()
        print(f"  OK: {company_name} — {len(years_sorted)} years processed")

    print("\n" + "=" * 55)
    print("Growth metrics calculation complete!")

def print_growth_summary():
    result = conn.execute(text("""
        SELECT
            c.company_name,
            s.sector_name,
            r.quarter,
            r.revenue_growth,
            r.cagr_3y,
            r.cagr_5y,
            r.ebitda_margin
        FROM financial_ratios r
        JOIN companies c ON r.company_id = c.company_id
        JOIN sectors s ON c.sector_id = s.sector_id
        WHERE r.quarter = 'Q4FY25'
          AND r.revenue_growth IS NOT NULL
        ORDER BY r.revenue_growth DESC
    """))
    rows = result.fetchall()

    print(f"\n{'Company':<30} {'Sector':<22} {'YoY%':>6} {'3Y CAGR':>8} {'5Y CAGR':>8} {'EBITDA%':>8}")
    print("-" * 90)
    for row in rows:
        print(
            f"{str(row[0]):<30} "
            f"{str(row[1]):<22} "
            f"{str(row[3] or 'N/A'):>6} "
            f"{str(row[4] or 'N/A'):>8} "
            f"{str(row[5] or 'N/A'):>8} "
            f"{str(row[6] or 'N/A'):>8}"
        )

if __name__ == "__main__":
    calculate_growth_for_all()
    print_growth_summary()
    conn.close()