import os
import sys
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')

import pandas as pd
from sqlalchemy import text
from scripts.db_connect import get_engine

engine = get_engine()

OUTPUT_PATH = r'C:\Users\Jignesh\Desktop\bse_portal\BenchmarkIQ_Excellence_Model_Filled.xlsx'

RATIO_WEIGHTS = {
    # Profitability = 35%
    "Net Profit Margin":       0.10,
    "EBITDA Margin":           0.10,
    "ROE":                     0.08,
    "ROCE":                    0.05,
    "Operating Profit Margin": 0.02,
    # Growth = 25%
    "Revenue Growth YoY":      0.10,
    "3Y Revenue CAGR":         0.08,
    "NP Growth YoY":           0.05,
    "EPS Growth YoY":          0.02,
    # Efficiency = 20%
    "Asset Turnover":          0.07,
    "Debtor Days":             0.05,
    "Inventory Turnover":      0.08,
    # Safety = 20%
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

def get_all_sectors():
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT DISTINCT sector_name FROM sectors ORDER BY sector_name"
        ))
        return [row[0] for row in result.fetchall()]

def get_companies_by_sector(sector_name):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT c.company_name
            FROM companies c
            JOIN sectors s ON c.sector_id = s.sector_id
            JOIN profit_loss pl ON pl.company_id = c.company_id
            WHERE s.sector_name = :sector
            ORDER BY c.company_name
        """), {"sector": sector_name})
        return [row[0] for row in result.fetchall()]

def fetch_company_data(company_name):
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT company_id FROM companies WHERE company_name = :name"
        ), {"name": company_name}).fetchone()
        if not result:
            return None, None, None
        cid = result[0]

        pl = pd.read_sql(text("""
            SELECT fiscal_year, sales, net_profit, raw_material,
                   employee_cost, depreciation, interest,
                   profit_before_tax, other_income
            FROM profit_loss WHERE company_id = :cid
            ORDER BY fiscal_year
        """), conn, params={"cid": cid})

        bs = pd.read_sql(text("""
            SELECT fiscal_year, equity_capital, reserves, borrowings,
                   total_assets, net_block, receivables, inventory,
                   cash_and_bank, other_liabilities
            FROM balance_sheet WHERE company_id = :cid
            ORDER BY fiscal_year
        """), conn, params={"cid": cid})

        fr = pd.read_sql(text("""
            SELECT quarter, roe, roce, debt_to_equity, net_margin,
                   ebitda_margin, revenue_growth, cagr_3y
            FROM financial_ratios WHERE company_id = :cid
            ORDER BY quarter DESC LIMIT 1
        """), conn, params={"cid": cid})

    return pl, bs, fr

def calculate_ratios(pl, bs, fr):
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
        except:
            pass
        return None

    # Profitability
    ratios["Net Profit Margin"]       = safe_div(latest["net_profit"], latest["sales"], 100)
    ebitda = (latest["net_profit"] or 0) + (latest["interest"] or 0) + (latest["depreciation"] or 0)
    ratios["EBITDA Margin"]           = safe_div(ebitda, latest["sales"], 100)
    equity = (latest.get("equity_capital") or 0) + (latest.get("reserves") or 0)
    ratios["ROE"]                     = safe_div(latest["net_profit"], equity, 100)
    capital_employed = equity + (latest.get("borrowings") or 0)
    ebit = (latest["net_profit"] or 0) + (latest["interest"] or 0)
    ratios["ROCE"]                    = safe_div(ebit, capital_employed, 100)
    ratios["Operating Profit Margin"] = safe_div(ebitda, latest["sales"], 100)

    # Growth
    ratios["Revenue Growth YoY"] = safe_div(latest["sales"] - prev["sales"], prev["sales"], 100)
    try:
        if old3["sales"] and float(old3["sales"]) != 0:
            ratios["3Y Revenue CAGR"] = round(
                ((float(latest["sales"]) / float(old3["sales"])) ** (1/3) - 1) * 100, 2)
        else:
            ratios["3Y Revenue CAGR"] = None
    except:
        ratios["3Y Revenue CAGR"] = None

    try:
        prev_np = float(prev["net_profit"])
        curr_np = float(latest["net_profit"])
        ratios["NP Growth YoY"] = round((curr_np - prev_np) / abs(prev_np) * 100, 2) if prev_np != 0 else None
    except:
        ratios["NP Growth YoY"] = None
    ratios["EPS Growth YoY"] = ratios["NP Growth YoY"]

    # Efficiency
    total_assets = float(latest.get("total_assets") or 0)
    if total_assets == 0:
        total_assets = sum(float(latest.get(k) or 0) for k in
                          ["net_block", "receivables", "inventory", "cash_and_bank"])
    ratios["Asset Turnover"]     = safe_div(latest["sales"], total_assets) if total_assets else None
    ratios["Debtor Days"]        = safe_div(latest.get("receivables") or 0, latest["sales"], 365)
    ratios["Inventory Turnover"] = safe_div(latest["sales"], latest.get("inventory")) if latest.get("inventory") else None

    # Safety
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
        return 50
    if higher_better:
        rank = sum(1 for v in valid if v <= value) / len(valid) * 100
    else:
        rank = sum(1 for v in valid if v >= value) / len(valid) * 100
    return round(rank, 1)

def tier_label(score):
    if score >= 85:   return "🏆 Excellence Leader"
    elif score >= 70: return "🥇 High Performer"
    elif score >= 55: return "🟢 Above Average"
    elif score >= 40: return "🟡 Average"
    elif score >= 25: return "🟠 Below Average"
    else:             return "🔴 Needs Improvement"

def run_excellence_model(companies, sector_name):
    """Run excellence model for a list of companies in a sector."""
    all_ratios = {}
    for company in companies:
        pl, bs, fr = fetch_company_data(company)
        ratios = calculate_ratios(pl, bs, fr)
        all_ratios[company] = ratios

    ratio_names = list(RATIO_WEIGHTS.keys())
    percentile_scores = {}

    for ratio in ratio_names:
        all_vals = [all_ratios[c].get(ratio) for c in companies]
        for company in companies:
            val = all_ratios[company].get(ratio)
            score = percentile_rank(val, all_vals, HIGHER_BETTER[ratio])
            if company not in percentile_scores:
                percentile_scores[company] = {}
            percentile_scores[company][ratio] = score

    total_scores = {}
    for company in companies:
        score = sum(
            percentile_scores[company].get(r, 50) * w
            for r, w in RATIO_WEIGHTS.items()
        )
        total_scores[company] = round(score, 1)

    ranked = sorted(total_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked, all_ratios, percentile_scores

def main():
    print("📊 BenchmarkIQ Excellence Model — All Sectors")
    print("=" * 55)

    sectors = get_all_sectors()
    all_results = []

    with pd.ExcelWriter(OUTPUT_PATH, engine='openpyxl') as writer:
        for sector in sectors:
            companies = get_companies_by_sector(sector)
            if len(companies) < 2:
                print(f"\n⚠️  Skipping {sector} — only {len(companies)} company")
                continue

            print(f"\n🏭 {sector} ({len(companies)} companies)")
            print("-" * 50)

            ranked, all_ratios, percentile_scores = run_excellence_model(companies, sector)

            for i, (company, score) in enumerate(ranked):
                print(f"  {i+1:2}. {company:<35} {score:5.1f}  {tier_label(score)}")
                all_results.append({
                    "Sector": sector,
                    "Rank": i+1,
                    "Company": company,
                    "Excellence Score": score,
                    "Tier": tier_label(score).split(" ", 1)[1],
                    **{r: round(all_ratios[company].get(r) or 0, 2) for r in RATIO_WEIGHTS.keys()}
                })

            # Save each sector as a separate sheet
            sector_rows = [r for r in all_results if r["Sector"] == sector]
            df_sector = pd.DataFrame(sector_rows)
            sheet_name = sector[:31]  # Excel sheet name max 31 chars
            df_sector.to_excel(writer, index=False, sheet_name=sheet_name)

        # Save all sectors combined sheet
        df_all = pd.DataFrame(all_results)
        df_all.to_excel(writer, index=False, sheet_name="All Sectors")

    print(f"\n✅ Saved to: {OUTPUT_PATH}")
    print(f"   Sheets: {[s[:31] for s in sectors if len(get_companies_by_sector(s)) >= 2] + ['All Sectors']}")

if __name__ == "__main__":
    main()