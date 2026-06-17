import sys
import os
import pandas as pd
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.db_connect import get_engine

engine = get_engine()
conn = engine.connect()

def get_sector_ratios(sector_id, quarter="Q4FY25"):
    """Fetch all companies in a sector with their ratios."""
    result = conn.execute(text("""
        SELECT
            c.company_id,
            c.company_name,
            c.market_cap,
            r.roe,
            r.roce,
            r.net_margin,
            r.debt_to_equity,
            r.revenue_growth,
            r.cagr_3y,
            r.ebitda_margin
        FROM financial_ratios r
        JOIN companies c ON r.company_id = c.company_id
        WHERE c.sector_id = :sid
          AND r.quarter = :q
          AND r.revenue_growth IS NOT NULL
    """), {"sid": sector_id, "q": quarter})
    rows = result.fetchall()
    df = pd.DataFrame(rows, columns=[
        'company_id', 'company_name', 'market_cap',
        'roe', 'roce', 'net_margin', 'debt_to_equity',
        'revenue_growth', 'cagr_3y', 'ebitda_margin'
    ])
    return df

def compute_percentile(value, series):
    """
    What percentage of companies does this value beat?
    Example: ROE=20 in [5,10,15,20,25] → beats 3 out of 5 → 60th percentile
    """
    if value is None or pd.isna(value):
        return None
    clean = series.dropna()
    if len(clean) == 0:
        return None
    below = (clean < float(value)).sum()
    return round((below / len(clean)) * 100, 1)

def benchmark_company(company_id, quarter="Q4FY25"):
    """
    Benchmark a company against all peers in its sector.
    Returns percentile ranks for each metric.
    """
    # Get company sector
    sector = conn.execute(text("""
        SELECT c.sector_id, c.company_name, s.sector_name
        FROM companies c
        JOIN sectors s ON c.sector_id = s.sector_id
        WHERE c.company_id = :cid
    """), {"cid": company_id}).fetchone()

    if not sector:
        return None

    sector_id   = sector[0]
    company_name = sector[1]
    sector_name  = sector[2]

    # Get all companies in sector
    df = get_sector_ratios(sector_id, quarter)

    if df.empty or company_id not in df['company_id'].values:
        return None

    # Get this company's row
    company_row = df[df['company_id'] == company_id].iloc[0]

    # Calculate percentile for each metric
    percentiles = {
        'roe':            compute_percentile(company_row['roe'],            df['roe']),
        'roce':           compute_percentile(company_row['roce'],           df['roce']),
        'net_margin':     compute_percentile(company_row['net_margin'],     df['net_margin']),
        'revenue_growth': compute_percentile(company_row['revenue_growth'], df['revenue_growth']),
        'ebitda_margin':  compute_percentile(company_row['ebitda_margin'],  df['ebitda_margin']),
        # For debt — lower is better, so invert
        'debt':           None if company_row['debt_to_equity'] is None
                          else round(100 - compute_percentile(
                              company_row['debt_to_equity'], df['debt_to_equity']
                          ), 1)
    }

    # Compute benchmark score (weighted)
    def w(pct, weight):
        return (pct or 0) * weight

    total_score = round(
        w(percentiles['revenue_growth'], 0.25) +
        w(percentiles['roe'],            0.20) +
        w(percentiles['roce'],           0.20) +
        w(percentiles['net_margin'],     0.20) +
        w(percentiles['debt'],           0.15),
        1
    )

    # Industry rank
    rank = int(df['revenue_growth'].rank(ascending=False)[
        df['company_id'] == company_id
    ].values[0])

    return {
        'company_id':   company_id,
        'company_name': company_name,
        'sector_name':  sector_name,
        'quarter':      quarter,
        'total_score':  total_score,
        'industry_rank': rank,
        'total_peers':  len(df),
        'percentiles':  percentiles,
        'ratios':       company_row.to_dict()
    }

def score_label(score):
    if score >= 80: return "🏆 Industry Leader"
    if score >= 60: return "✅ Above Average"
    if score >= 40: return "➡️ Average"
    if score >= 20: return "⚠️ Below Average"
    return "🔴 Needs Attention"

def benchmark_all_companies(quarter="Q4FY25"):
    """Run benchmark for all companies and store in DB."""
    companies = conn.execute(text(
        "SELECT company_id FROM companies"
    )).fetchall()

    print(f"Benchmarking {len(companies)} companies for {quarter}...")
    print("=" * 60)

    results = []
    for row in companies:
        result = benchmark_company(row[0], quarter)
        if result:
            results.append(result)
            # Store in benchmark_scores table
            try:
                p = result['percentiles']
                conn.execute(text("""
                    INSERT INTO benchmark_scores
                    (company_id, quarter, revenue_growth_score,
                     roe_score, roce_score, margin_score, debt_score,
                     total_score, industry_rank, industry_percentile)
                    VALUES (:cid, :q, :rg, :roe, :roce, :nm, :de,
                            :total, :rank, :pct)
                    ON DUPLICATE KEY UPDATE
                        total_score=VALUES(total_score),
                        industry_rank=VALUES(industry_rank),
                        industry_percentile=VALUES(industry_percentile)
                """), {
                    "cid":   result['company_id'],
                    "q":     quarter,
                    "rg":    p['revenue_growth'],
                    "roe":   p['roe'],
                    "roce":  p['roce'],
                    "nm":    p['net_margin'],
                    "de":    p['debt'],
                    "total": result['total_score'],
                    "rank":  result['industry_rank'],
                    "pct":   round(100 - (result['industry_rank'] /
                             result['total_peers'] * 100), 1)
                })
            except Exception as e:
                print(f"  DB error for {result['company_name']}: {e}")

    conn.commit()

    # Print summary
    results.sort(key=lambda x: x['total_score'], reverse=True)
    print(f"\n{'Company':<32} {'Sector':<22} {'Score':>6} {'Rank'} {'Label'}")
    print("-" * 85)
    for r in results:
        print(
            f"{r['company_name']:<32} "
            f"{r['sector_name']:<22} "
            f"{r['total_score']:>6.1f}  "
            f"{r['industry_rank']}/{r['total_peers']}  "
            f"{score_label(r['total_score'])}"
        )

    print(f"\n✅ Benchmark scores stored in database!")

if __name__ == "__main__":
    benchmark_all_companies()
    conn.close()