from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import sys
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')
from scripts.db_connect import get_engine

app = FastAPI(title="BenchmarkIQ API", version="1.0")

# Allow Next.js to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = get_engine()

# ── ENDPOINT 1: Platform stats (homepage) ─────────────
@app.get("/api/stats")
def get_stats():
    with engine.connect() as conn:
        companies = conn.execute(text(
            "SELECT COUNT(*) FROM companies"
        )).fetchone()[0]

        sectors = conn.execute(text(
            "SELECT COUNT(*) FROM sectors"
        )).fetchone()[0]

        data_points = conn.execute(text(
            "SELECT COUNT(*) FROM quarterly_results"
        )).fetchone()[0]

        avg_score = conn.execute(text(
            "SELECT ROUND(AVG(total_score),1) FROM benchmark_scores"
        )).fetchone()[0]

    return {
        "companies": companies,
        "sectors": sectors,
        "data_points": data_points,
        "avg_score": float(avg_score) if avg_score else 0
    }

# ── ENDPOINT 2: All companies list ────────────────────
@app.get("/api/companies")
def get_companies():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT c.company_id, c.company_name, c.bse_code,
                   c.nse_symbol, c.market_cap, s.sector_name,
                   b.total_score, b.industry_rank
            FROM companies c
            JOIN sectors s ON c.sector_id = s.sector_id
            LEFT JOIN benchmark_scores b ON b.company_id = c.company_id
                AND b.quarter = 'Q4FY25'
            ORDER BY c.company_name
        """)).fetchall()

    return [
        {
            "id":           r[0],
            "name":         r[1],
            "bse_code":     r[2],
            "nse_symbol":   r[3],
            "market_cap":   float(r[4]) if r[4] else 0,
            "sector":       r[5],
            "score":        float(r[6]) if r[6] else 0,
            "rank":         r[7]
        }
        for r in rows
    ]

# ── ENDPOINT 3: Single company full profile ────────────
@app.get("/api/company/{company_id}")
def get_company(company_id: int):
    with engine.connect() as conn:
        # Basic info
        info = conn.execute(text("""
            SELECT c.company_name, c.bse_code, c.nse_symbol,
                   c.market_cap, s.sector_name
            FROM companies c
            JOIN sectors s ON c.sector_id = s.sector_id
            WHERE c.company_id = :id
        """), {"id": company_id}).fetchone()

        if not info:
            raise HTTPException(status_code=404, detail="Company not found")

        # Latest ratios
        ratios = conn.execute(text("""
            SELECT roe, roce, net_margin, debt_to_equity,
                   revenue_growth, cagr_3y, cagr_5y, ebitda_margin
            FROM financial_ratios
            WHERE company_id = :id AND quarter = 'Q4FY25'
        """), {"id": company_id}).fetchone()

        # Benchmark score
        score = conn.execute(text("""
            SELECT total_score, industry_rank, industry_percentile
            FROM benchmark_scores
            WHERE company_id = :id AND quarter = 'Q4FY25'
        """), {"id": company_id}).fetchone()

        # Revenue trend (last 8 quarters)
        trend = conn.execute(text("""
            SELECT quarter, revenue, net_profit, ebitda, eps
            FROM quarterly_results
            WHERE company_id = :id
            ORDER BY period_end DESC LIMIT 10
        """), {"id": company_id}).fetchall()

        # P&L history
        pl = conn.execute(text("""
            SELECT fiscal_year, sales, net_profit, interest,
                   depreciation, raw_material, employee_cost, tax
            FROM profit_loss
            WHERE company_id = :id
            ORDER BY fiscal_year
        """), {"id": company_id}).fetchall()

        # Balance sheet
        bs = conn.execute(text("""
            SELECT fiscal_year, equity_capital, reserves,
                   borrowings, total_assets, cash_and_bank,
                   receivables, inventory
            FROM balance_sheet
            WHERE company_id = :id
            ORDER BY fiscal_year
        """), {"id": company_id}).fetchall()

        # Cash flow
        cf = conn.execute(text("""
            SELECT fiscal_year, operating_cf,
                   investing_cf, financing_cf, net_cash_flow
            FROM cash_flow
            WHERE company_id = :id
            ORDER BY fiscal_year
        """), {"id": company_id}).fetchall()

    def f(v): return float(v) if v is not None else None

    return {
        "info": {
            "name":       info[0],
            "bse_code":   info[1],
            "nse_symbol": info[2],
            "market_cap": f(info[3]),
            "sector":     info[4]
        },
        "ratios": {
            "roe":            f(ratios[0]) if ratios else None,
            "roce":           f(ratios[1]) if ratios else None,
            "net_margin":     f(ratios[2]) if ratios else None,
            "debt_to_equity": f(ratios[3]) if ratios else None,
            "revenue_growth": f(ratios[4]) if ratios else None,
            "cagr_3y":        f(ratios[5]) if ratios else None,
            "cagr_5y":        f(ratios[6]) if ratios else None,
            "ebitda_margin":  f(ratios[7]) if ratios else None,
        } if ratios else {},
        "benchmark": {
            "score":      f(score[0]) if score else None,
            "rank":       score[1]    if score else None,
            "percentile": f(score[2]) if score else None,
        } if score else {},
        "trend": [
            {"quarter": r[0], "revenue": f(r[1]),
             "net_profit": f(r[2]), "ebitda": f(r[3]),
             "eps": f(r[4])}
            for r in reversed(trend)
        ],
        "pl": [
            {"year": r[0], "sales": f(r[1]),
             "net_profit": f(r[2]), "interest": f(r[3]),
             "depreciation": f(r[4]), "raw_material": f(r[5]),
             "employee_cost": f(r[6]), "tax": f(r[7])}
            for r in pl
        ],
        "balance_sheet": [
            {"year": r[0], "equity": f(r[1]),
             "reserves": f(r[2]), "borrowings": f(r[3]),
             "total_assets": f(r[4]), "cash": f(r[5]),
             "receivables": f(r[6]), "inventory": f(r[7])}
            for r in bs
        ],
        "cash_flow": [
            {"year": r[0], "operating": f(r[1]),
             "investing": f(r[2]), "financing": f(r[3]),
             "net": f(r[4])}
            for r in cf
        ]
    }

# ── ENDPOINT 4: Benchmark bubble chart data ────────────
@app.get("/api/benchmark/{sector_name}")
def get_benchmark(sector_name: str):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT c.company_id, c.company_name, c.market_cap,
                   r.roce, r.revenue_growth, r.net_margin,
                   r.roe, r.debt_to_equity,
                   b.total_score, b.industry_rank
            FROM financial_ratios r
            JOIN companies c ON r.company_id = c.company_id
            JOIN sectors s ON c.sector_id = s.sector_id
            LEFT JOIN benchmark_scores b ON b.company_id = c.company_id
                AND b.quarter = r.quarter
            WHERE s.sector_name = :sector
              AND r.quarter = 'Q4FY25'
              AND r.revenue_growth IS NOT NULL
              AND r.roce IS NOT NULL
        """), {"sector": sector_name}).fetchall()

    def f(v): return float(v) if v is not None else 0

    return [
        {
            "id":             r[0],
            "name":           r[1],
            "market_cap":     f(r[2]),
            "roce":           f(r[3]),
            "revenue_growth": f(r[4]),
            "net_margin":     f(r[5]),
            "roe":            f(r[6]),
            "debt_to_equity": f(r[7]),
            "score":          f(r[8]),
            "rank":           r[9]
        }
        for r in rows
    ]

# ── ENDPOINT 5: Sector list ────────────────────────────
@app.get("/api/sectors")
def get_sectors():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT s.sector_name,
                   COUNT(c.company_id) as companies,
                   ROUND(AVG(r.roe),1) as avg_roe,
                   ROUND(AVG(r.roce),1) as avg_roce,
                   ROUND(AVG(r.net_margin),1) as avg_margin,
                   ROUND(AVG(r.revenue_growth),1) as avg_growth,
                   ROUND(AVG(b.total_score),1) as avg_score
            FROM sectors s
            JOIN companies c ON c.sector_id = s.sector_id
            JOIN financial_ratios r ON r.company_id = c.company_id
            LEFT JOIN benchmark_scores b ON b.company_id = c.company_id
                AND b.quarter = r.quarter
            WHERE r.quarter = 'Q4FY25'
            GROUP BY s.sector_name
            ORDER BY avg_score DESC
        """)).fetchall()

    def f(v): return float(v) if v is not None else 0

    return [
        {
            "sector":     r[0],
            "companies":  r[1],
            "avg_roe":    f(r[2]),
            "avg_roce":   f(r[3]),
            "avg_margin": f(r[4]),
            "avg_growth": f(r[5]),
            "avg_score":  f(r[6])
        }
        for r in rows
    ]

# ── ENDPOINT 6: Top performers leaderboard ─────────────
@app.get("/api/leaderboard")
def get_leaderboard():
    with engine.connect() as conn:
        def top(metric, col):
            rows = conn.execute(text(f"""
                SELECT c.company_name, s.sector_name,
                       r.{col}, b.total_score
                FROM financial_ratios r
                JOIN companies c ON r.company_id = c.company_id
                JOIN sectors s ON c.sector_id = s.sector_id
                LEFT JOIN benchmark_scores b
                    ON b.company_id = c.company_id
                    AND b.quarter = r.quarter
                WHERE r.quarter = 'Q4FY25'
                  AND r.{col} IS NOT NULL
                ORDER BY r.{col} DESC LIMIT 5
            """)).fetchall()
            return [{"name": r[0], "sector": r[1],
                     "value": float(r[2]),
                     "score": float(r[3]) if r[3] else 0}
                    for r in rows]

        return {
            "top_roe":    top("ROE",            "roe"),
            "top_roce":   top("ROCE",           "roce"),
            "top_margin": top("Net Margin",      "net_margin"),
            "top_growth": top("Revenue Growth",  "revenue_growth"),
        }

# ── ENDPOINT 7: Peer comparison ────────────────────────
@app.get("/api/compare")
def compare_companies(ids: str):
    id_list = [int(x) for x in ids.split(",")]
    with engine.connect() as conn:
        result = []
        for cid in id_list:
            row = conn.execute(text("""
                SELECT c.company_name, s.sector_name,
                       r.roe, r.roce, r.net_margin,
                       r.debt_to_equity, r.revenue_growth,
                       r.cagr_3y, r.ebitda_margin,
                       b.total_score
                FROM financial_ratios r
                JOIN companies c ON r.company_id = c.company_id
                JOIN sectors s ON c.sector_id = s.sector_id
                LEFT JOIN benchmark_scores b
                    ON b.company_id = c.company_id
                    AND b.quarter = r.quarter
                WHERE r.company_id = :id
                  AND r.quarter = 'Q4FY25'
            """), {"id": cid}).fetchone()

            if row:
                def f(v): return float(v) if v is not None else None
                result.append({
                    "name":           row[0],
                    "sector":         row[1],
                    "roe":            f(row[2]),
                    "roce":           f(row[3]),
                    "net_margin":     f(row[4]),
                    "debt_to_equity": f(row[5]),
                    "revenue_growth": f(row[6]),
                    "cagr_3y":        f(row[7]),
                    "ebitda_margin":  f(row[8]),
                    "score":          f(row[9]),
                })
    return result