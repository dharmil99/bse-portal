"""
ratio_calculator.py
-------------------
Reads quarterly_results from MySQL, computes financial ratios,
and stores them in the financial_ratios table.
Run from: C:\Users\Jignesh\Desktop\bse_portal\scripts\
Usage:    python ratio_calculator.py
"""

import sys
import os
import pandas as pd
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_connect import get_engine


# ─────────────────────────────────────────────
# RATIO FUNCTIONS (all return None if data missing)
# ─────────────────────────────────────────────

def compute_net_margin(net_profit, revenue):
    """Net Profit / Revenue × 100"""
    try:
        if revenue and revenue != 0:
            return round((net_profit / revenue) * 100, 4)
    except Exception:
        pass
    return None


def compute_roe(net_profit, equity):
    """Return on Equity = Net Profit / Equity × 100"""
    try:
        if equity and equity != 0:
            return round((net_profit / equity) * 100, 4)
    except Exception:
        pass
    return None


def compute_roce(ebitda, total_assets, current_liabilities=None):
    """
    Return on Capital Employed = EBIT / Capital Employed × 100
    Capital Employed = Total Assets − Current Liabilities
    If current_liabilities not available, use Total Assets as proxy.
    """
    try:
        if total_assets and total_assets != 0:
            capital_employed = total_assets
            if current_liabilities:
                capital_employed = total_assets - current_liabilities
            if capital_employed != 0:
                return round((ebitda / capital_employed) * 100, 4)
    except Exception:
        pass
    return None


def compute_de(total_debt, equity):
    """Debt-to-Equity = Total Debt / Equity"""
    try:
        if equity and equity != 0:
            return round(total_debt / equity, 4)
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("BSE Portal — Ratio Calculator")
    print("=" * 60)

    try:
        engine = get_engine()
        conn   = engine.connect()
    except Exception as e:
        print(f"❌ Cannot connect to MySQL: {e}")
        sys.exit(1)

    # Fetch all rows from quarterly_results
    try:
        df = pd.read_sql(text(
            "SELECT company_id, quarter, revenue, net_profit, ebitda, "
            "       total_debt, equity, total_assets "
            "FROM quarterly_results"
        ), conn)
    except Exception as e:
        print(f"❌ Failed to read quarterly_results: {e}")
        conn.close()
        sys.exit(1)

    print(f"Found {len(df)} rows in quarterly_results\n")

    inserted = 0
    skipped  = 0

    for _, row in df.iterrows():
        try:
            net_margin = compute_net_margin(row["net_profit"], row["revenue"])
            roe        = compute_roe(row["net_profit"], row["equity"])
            roce       = compute_roce(row["ebitda"], row["total_assets"])
            de         = compute_de(row["total_debt"], row["equity"])

            conn.execute(text(
                "INSERT INTO financial_ratios "
                "(company_id, quarter, roe, roce, debt_to_equity, net_margin) "
                "VALUES (:cid, :q, :roe, :roce, :de, :nm) "
                "ON DUPLICATE KEY UPDATE "
                "  roe=VALUES(roe), roce=VALUES(roce), "
                "  debt_to_equity=VALUES(debt_to_equity), net_margin=VALUES(net_margin)"
            ), {
                "cid":  int(row["company_id"]),
                "q":    row["quarter"],
                "roe":  roe,
                "roce": roce,
                "de":   de,
                "nm":   net_margin,
            })
            inserted += 1

        except Exception as e:
            print(f"  ⚠️  company_id={row['company_id']} {row['quarter']}: {e}")
            skipped += 1

    conn.commit()
    conn.close()

    print(f"✅ Ratios computed: {inserted}   ⚠️  Skipped: {skipped}")
    print("\nSample check — run this in MySQL Workbench to verify:")
    print("  SELECT c.company_name, r.quarter, r.roe, r.roce, r.net_margin")
    print("  FROM financial_ratios r")
    print("  JOIN companies c ON c.company_id = r.company_id")
    print("  LIMIT 10;")
    print("=" * 60)
