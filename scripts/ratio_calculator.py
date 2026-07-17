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
    # equity must be equity_capital + reserves (not just face-value equity_capital)
    try:
        if net_profit is None or equity is None:
            return None
        if float(equity) == 0:
            return None
        return round((float(net_profit) / float(equity)) * 100, 2)
    except:
        return None

def compute_roce(ebit, capital_employed):
    # capital_employed = equity + borrowings
    try:
        if ebit is None or capital_employed is None:
            return None
        if float(capital_employed) == 0:
            return None
        return round((float(ebit) / float(capital_employed)) * 100, 2)
    except:
        return None

def compute_de_ratio(total_debt, equity):
    try:
        if not equity or float(equity) == 0:
            return None
        return round(float(total_debt or 0) / float(equity), 2)
    except:
        return None

def compute_asset_turnover(revenue, total_assets):
    if not total_assets or total_assets == 0:
        return None
    return round(revenue / total_assets, 2)

# ── From quarterly_results joined to balance_sheet ────────────────────────

def fetch_all_results():
    result = conn.execute(text("""
        SELECT
            q.company_id,
            c.company_name,
            q.quarter,
            q.period_end,
            q.revenue,
            q.net_profit,
            q.ebitda,
            q.total_debt,
            q.total_assets,
            q.eps,
            c.market_cap,
            COALESCE(bs.equity_capital, 0) + COALESCE(bs.reserves, 0) AS true_equity,
            COALESCE(bs.borrowings, q.total_debt, 0)                   AS borrowings
        FROM quarterly_results q
        JOIN companies c ON q.company_id = c.company_id
        LEFT JOIN balance_sheet bs
            ON  bs.company_id  = q.company_id
            AND bs.fiscal_year = CONCAT('FY', RIGHT(q.quarter, 2))
        ORDER BY q.company_id, q.period_end
    """))
    return result.fetchall()


def calculate_and_store_all():
    rows = fetch_all_results()
    print(f"Processing {len(rows)} quarterly result rows...")

    inserted = 0
    skipped  = 0

    for row in rows:
        company_id   = row[0]
        company_name = row[1]
        quarter      = row[2]
        revenue      = row[4]
        net_profit   = row[5]
        ebitda       = row[6]
        total_assets = row[8]
        market_cap   = row[10]
        true_equity  = row[11]
        borrowings   = row[12]

        if not revenue:
            skipped += 1
            continue

        net_margin    = compute_net_margin(net_profit, revenue)
        ebitda_margin = compute_ebitda_margin(ebitda, revenue)

        # ROE = net_profit / (equity_capital + reserves)
        roe = compute_roe(net_profit, true_equity if true_equity and float(true_equity) > 0 else None)

        # EBIT proxy using net_profit (quarterly data doesn't have interest separately)
        ebit = float(net_profit) if net_profit is not None else None

        # Capital employed = equity + borrowings
        cap_employed = None
        if true_equity is not None and borrowings is not None:
            try:
                cap_employed = float(true_equity) + float(borrowings)
            except:
                pass

        roce     = compute_roce(ebit, cap_employed)
        de_ratio = compute_de_ratio(borrowings, true_equity if true_equity and float(true_equity) > 0 else None)

        pe_ratio = None
        if net_profit and float(net_profit) > 0 and market_cap:
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


# ── From profit_loss + balance_sheet (covers ALL companies) ───────────────

def calculate_from_profit_loss():
    result = conn.execute(text("""
        SELECT DISTINCT c.company_id, c.company_name
        FROM companies c
        JOIN profit_loss pl ON pl.company_id = c.company_id
    """))
    companies = result.fetchall()
    print(f"\nProcessing {len(companies)} companies from profit_loss + balance_sheet...")

    for company in companies:
        company_id   = company[0]
        company_name = company[1]

        rows = conn.execute(text("""
            SELECT
                pl.fiscal_year,
                pl.sales,
                pl.net_profit,
                pl.interest,
                pl.depreciation,
                COALESCE(bs.equity_capital, 0) AS eq_capital,
                COALESCE(bs.reserves, 0)       AS reserves,
                COALESCE(bs.borrowings, 0)     AS borrowings,
                bs.total_assets,
                bs.other_liabilities
            FROM profit_loss pl
            LEFT JOIN balance_sheet bs
                ON  bs.company_id  = pl.company_id
                AND bs.fiscal_year = pl.fiscal_year
            WHERE pl.company_id = :cid
            ORDER BY pl.fiscal_year
        """), {"cid": company_id}).fetchall()

        prev_sales = None

        for row in rows:
            fy           = row[0]
            sales        = row[1]
            net_profit   = row[2]
            interest     = row[3]
            depreciation = row[4]
            eq_capital   = float(row[5] or 0)
            reserves     = float(row[6] or 0)
            borrowings   = float(row[7] or 0)
            total_assets = row[8]

            if not sales:
                prev_sales = None
                continue

            quarter = f"Q4{fy}"

            net_margin = compute_net_margin(net_profit, sales)

            # EBITDA = net profit + interest + depreciation
            ebitda = None
            if net_profit is not None and interest is not None and depreciation is not None:
                try:
                    ebitda = float(net_profit) + float(interest) + float(depreciation)
                except:
                    pass
            ebitda_margin = compute_ebitda_margin(ebitda, sales)

            # True equity = equity_capital + reserves  ← THE KEY FIX
            true_equity = eq_capital + reserves

            roe = compute_roe(net_profit, true_equity if true_equity > 0 else None)

            # EBIT = net_profit + interest
            ebit = None
            if net_profit is not None and interest is not None:
                try:
                    ebit = float(net_profit) + float(interest)
                except:
                    pass

            # Capital employed = equity + borrowings
            cap_employed = true_equity + borrowings
            roce = compute_roce(ebit, cap_employed if cap_employed > 0 else None)

            de_ratio = compute_de_ratio(borrowings, true_equity if true_equity > 0 else None)

            # Revenue growth YoY
            revenue_growth = None
            if prev_sales and float(prev_sales) != 0 and sales:
                try:
                    revenue_growth = round((float(sales) - float(prev_sales)) / float(prev_sales) * 100, 2)
                except:
                    pass
            prev_sales = sales

            try:
                conn.execute(text("""
                    INSERT INTO financial_ratios
                        (company_id, quarter, roe, roce,
                         debt_to_equity, net_margin, revenue_growth)
                    VALUES (:cid, :q, :roe, :roce, :de, :nm, :rg)
                    ON DUPLICATE KEY UPDATE
                        roe=VALUES(roe),
                        roce=VALUES(roce),
                        debt_to_equity=VALUES(debt_to_equity),
                        net_margin=VALUES(net_margin),
                        revenue_growth=VALUES(revenue_growth)
                """), {
                    "cid":  company_id,
                    "q":    quarter,
                    "roe":  roe,
                    "roce": roce,
                    "de":   de_ratio,
                    "nm":   net_margin,
                    "rg":   revenue_growth,
                })
            except Exception as e:
                print(f"  ERROR {company_name} {quarter}: {e}")

        print(f"  OK: {company_name}")

    conn.commit()
    print("Done!")


# ── Summary ────────────────────────────────────────────────────────────────

def print_summary():
    latest_q = conn.execute(text("""
        SELECT MAX(quarter) FROM financial_ratios
    """)).fetchone()[0]

    result = conn.execute(text("""
        SELECT
            c.company_name, s.sector_name,
            r.quarter, r.roe, r.roce,
            r.debt_to_equity, r.net_margin, r.pe_ratio
        FROM financial_ratios r
        JOIN companies c ON r.company_id = c.company_id
        JOIN sectors s ON c.sector_id = s.sector_id
        WHERE r.quarter = :q
        ORDER BY r.roe DESC
        LIMIT 30
    """), {"q": latest_q})
    rows = result.fetchall()

    print(f"\nShowing latest quarter: {latest_q}")
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
    calculate_from_profit_loss()
    print_summary()
    conn.close()