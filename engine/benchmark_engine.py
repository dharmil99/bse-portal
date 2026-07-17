import sys
import os
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')

import pandas as pd
from sqlalchemy import text
from scripts.db_connect import get_engine

engine = get_engine()
conn = engine.connect()

RATIO_WEIGHTS = {
    "Net Profit Margin":       0.10,
    "EBITDA Margin":           0.10,
    "ROE":                     0.08,
    "ROCE":                    0.05,
    "Operating Profit Margin": 0.02,
    "Revenue Growth YoY":      0.10,
    "3Y Revenue CAGR":         0.08,
    "NP Growth YoY":           0.05,
    "EPS Growth YoY":          0.02,
    "Asset Turnover":          0.07,
    "Debtor Days":             0.05,
    "Inventory Turnover":      0.08,
    "Debt to Equity":          0.08,
    "Interest Coverage":       0.07,
    "Current Ratio":           0.05,
}

HIGHER_BETTER = {
    "Net Profit Margin": True, "EBITDA Margin": True,
    "ROE": True, "ROCE": True, "Operating Profit Margin": True,
    "Revenue Growth YoY": True, "3Y Revenue CAGR": True,
    "NP Growth YoY": True, "Asset Turnover": True,
    "Debtor Days": False, "Inventory Turnover": True,
    "Debt to Equity": False, "Interest Coverage": True,
    "EPS Growth YoY": True, "Current Ratio": True,
}


def tier_label(score):
    if score >= 85: return "Excellence Leader"
    if score >= 70: return "High Performer"
    if score >= 55: return "Above Average"
    if score >= 40: return "Average"
    if score >= 25: return "Below Average"
    return "Needs Improvement"


def get_unique_sector_names():
    """Group by NAME, not sector_id — the sectors table has many duplicate id rows per name."""
    result = conn.execute(text("SELECT DISTINCT sector_name FROM sectors ORDER BY sector_name"))
    return [row[0] for row in result.fetchall()]


def get_companies_in_sector(sector_name):
    """Companies whose sector, by NAME (across any duplicate sector_id), matches, and that have P&L data."""
    result = conn.execute(text("""
        SELECT DISTINCT c.company_id, c.company_name
        FROM companies c
        JOIN sectors s ON c.sector_id = s.sector_id
        JOIN profit_loss pl ON pl.company_id = c.company_id
        WHERE s.sector_name = :sname
        ORDER BY c.company_name
    """), {"sname": sector_name})
    return result.fetchall()


def fetch_company_data(company_id):
    pl = pd.read_sql(text("""
        SELECT fiscal_year, sales, net_profit, raw_material,
               employee_cost, depreciation, interest,
               profit_before_tax, other_income
        FROM profit_loss WHERE company_id = :cid
        ORDER BY fiscal_year
    """), conn, params={"cid": company_id})

    bs = pd.read_sql(text("""
        SELECT fiscal_year, equity_capital, reserves, borrowings,
               total_assets, net_block, receivables, inventory,
               cash_and_bank, other_liabilities
        FROM balance_sheet WHERE company_id = :cid
        ORDER BY fiscal_year
    """), conn, params={"cid": company_id})

    return pl, bs


def calculate_ratios(pl, bs):
    if pl is None or pl.empty:
        return {}

    ratios = {}
    merged = pd.merge(pl, bs, on="fiscal_year", how="inner")
    if merged.empty:
        return {}

    latest = merged.iloc[-1]
    prev   = merged.iloc[-2] if len(merged) > 1 else latest
    old3   = merged.iloc[-4] if len(merged) > 3 else merged.iloc[0]

    def safe_div(a, b, mult=1):
        try:
            if b and float(b) != 0:
                return round(float(a) / float(b) * mult, 2)
        except Exception:
            pass
        return None

    ratios["Net Profit Margin"] = safe_div(latest["net_profit"], latest["sales"], 100)
    ebitda = (latest["net_profit"] or 0) + (latest["interest"] or 0) + (latest["depreciation"] or 0)
    ratios["EBITDA Margin"] = safe_div(ebitda, latest["sales"], 100)
    equity = (latest.get("equity_capital") or 0) + (latest.get("reserves") or 0)
    ratios["ROE"] = safe_div(latest["net_profit"], equity, 100)
    capital_employed = equity + (latest.get("borrowings") or 0)
    ebit = (latest["net_profit"] or 0) + (latest["interest"] or 0)
    ratios["ROCE"] = safe_div(ebit, capital_employed, 100)
    ratios["Operating Profit Margin"] = safe_div(ebitda, latest["sales"], 100)

    ratios["Revenue Growth YoY"] = safe_div(latest["sales"] - prev["sales"], prev["sales"], 100)
    try:
        if old3["sales"] and float(old3["sales"]) != 0:
            ratios["3Y Revenue CAGR"] = round(
                ((float(latest["sales"]) / float(old3["sales"])) ** (1 / 3) - 1) * 100, 2)
        else:
            ratios["3Y Revenue CAGR"] = None
    except Exception:
        ratios["3Y Revenue CAGR"] = None

    try:
        prev_np = float(prev["net_profit"])
        curr_np = float(latest["net_profit"])
        ratios["NP Growth YoY"] = round((curr_np - prev_np) / abs(prev_np) * 100, 2) if prev_np != 0 else None
    except Exception:
        ratios["NP Growth YoY"] = None
    ratios["EPS Growth YoY"] = ratios["NP Growth YoY"]

    total_assets = float(latest.get("total_assets") or 0)
    if total_assets == 0:
        total_assets = sum(float(latest.get(k) or 0) for k in
                            ["net_block", "receivables", "inventory", "cash_and_bank"])
    ratios["Asset Turnover"] = safe_div(latest["sales"], total_assets) if total_assets else None
    ratios["Debtor Days"] = safe_div(latest.get("receivables") or 0, latest["sales"], 365)
    ratios["Inventory Turnover"] = safe_div(latest["sales"], latest.get("inventory")) if latest.get("inventory") else None

    ratios["Debt to Equity"] = safe_div(latest.get("borrowings"), equity)
    interest = float(latest.get("interest") or 0)
    ratios["Interest Coverage"] = safe_div(ebit, interest) if interest > 0 else None
    curr_assets = sum(float(latest.get(k) or 0) for k in ["receivables", "inventory", "cash_and_bank"])
    curr_liab = float(latest.get("other_liabilities") or 0)
    ratios["Current Ratio"] = safe_div(curr_assets, curr_liab) if curr_liab > 0 else None

    return ratios


def percentile_rank(value, all_values, higher_better=True):
    valid = [v for v in all_values if v is not None]
    if not valid or value is None:
        return 50.0
    if higher_better:
        rank = sum(1 for v in valid if v <= value) / len(valid) * 100
    else:
        rank = sum(1 for v in valid if v >= value) / len(valid) * 100
    return round(rank, 1)


def run_sector(sector_name, quarter="Q4FY25"):
    companies = get_companies_in_sector(sector_name)
    if len(companies) < 2:
        print(f"  Skipping {sector_name} — only {len(companies)} company with data")
        return []

    all_ratios = {}
    for cid, cname in companies:
        pl, bs = fetch_company_data(cid)
        all_ratios[cid] = calculate_ratios(pl, bs)

    percentile_scores = {}
    for ratio in RATIO_WEIGHTS.keys():
        all_vals = [all_ratios[cid].get(ratio) for cid, _ in companies]
        for cid, _ in companies:
            val = all_ratios[cid].get(ratio)
            score = percentile_rank(val, all_vals, HIGHER_BETTER[ratio])
            percentile_scores.setdefault(cid, {})[ratio] = score

    total_scores = {}
    for cid, _ in companies:
        score = sum(percentile_scores[cid].get(r, 50) * w for r, w in RATIO_WEIGHTS.items())
        total_scores[cid] = round(score, 1)

    ranked = sorted(total_scores.items(), key=lambda x: x[1], reverse=True)
    n = len(ranked)

    results = []
    for rank_pos, (cid, score) in enumerate(ranked, start=1):
        cname = dict(companies)[cid]
        industry_percentile = round(100 - ((rank_pos - 1) / n * 100), 1) if n > 1 else 100.0
        p = percentile_scores[cid]
        results.append({
            "company_id": cid, "company_name": cname, "quarter": quarter,
            "total_score": score, "industry_rank": rank_pos,
            "total_peers": n, "industry_percentile": industry_percentile,
            "revenue_growth_score": p.get("Revenue Growth YoY"),
            "roe_score": p.get("ROE"), "roce_score": p.get("ROCE"),
            "margin_score": p.get("Net Profit Margin"), "debt_score": p.get("Debt to Equity"),
        })
    return results


def benchmark_all_companies(quarter="Q4FY25"):
    sector_names = get_unique_sector_names()
    print(f"Recomputing benchmark_scores (15-ratio methodology, grouped by sector NAME) for {quarter}...")
    print("=" * 70)

    all_results = []
    for sector_name in sector_names:
        print(f"\n{sector_name}")
        results = run_sector(sector_name, quarter)
        for r in results:
            print(f"  {r['industry_rank']:>2}. {r['company_name']:<35} {r['total_score']:>6.1f}  {tier_label(r['total_score'])}")
            try:
                conn.execute(text("""
                    INSERT INTO benchmark_scores
                    (company_id, quarter, revenue_growth_score,
                     roe_score, roce_score, margin_score, debt_score,
                     total_score, industry_rank, industry_percentile)
                    VALUES (:cid, :q, :rg, :roe, :roce, :nm, :de,
                            :total, :rank, :pct)
                    ON DUPLICATE KEY UPDATE
                        revenue_growth_score=VALUES(revenue_growth_score),
                        roe_score=VALUES(roe_score),
                        roce_score=VALUES(roce_score),
                        margin_score=VALUES(margin_score),
                        debt_score=VALUES(debt_score),
                        total_score=VALUES(total_score),
                        industry_rank=VALUES(industry_rank),
                        industry_percentile=VALUES(industry_percentile)
                """), {
                    "cid": r["company_id"], "q": r["quarter"],
                    "rg": r["revenue_growth_score"], "roe": r["roe_score"],
                    "roce": r["roce_score"], "nm": r["margin_score"], "de": r["debt_score"],
                    "total": r["total_score"], "rank": r["industry_rank"], "pct": r["industry_percentile"],
                })
            except Exception as e:
                print(f"    DB error for {r['company_name']}: {e}")
        all_results.extend(results)

    conn.commit()
    print(f"\nDone — {len(all_results)} companies recomputed and stored using the 15-ratio methodology, correctly grouped by sector name.")


if __name__ == "__main__":
    benchmark_all_companies()
    conn.close()