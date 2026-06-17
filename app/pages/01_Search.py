import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scripts.db_connect import get_engine
from sqlalchemy import text

st.set_page_config(page_title="Company Search", page_icon="🔍", layout="wide")
st.title("🔍 Company Search")

engine = get_engine()

@st.cache_data
def get_all_companies():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT c.company_name, c.bse_code, c.nse_symbol, 
                   s.sector_name, c.market_cap
            FROM companies c
            JOIN sectors s ON c.sector_id = s.sector_id
            ORDER BY c.company_name
        """))
        return pd.DataFrame(result.fetchall(),
            columns=['company_name','bse_code','nse_symbol','sector_name','market_cap'])

@st.cache_data
def get_company_details(company_name):
    with engine.connect() as conn:
        # Get ratios
        ratios = conn.execute(text("""
            SELECT r.quarter, r.roe, r.roce, r.net_margin,
                   r.debt_to_equity, r.revenue_growth, r.cagr_3y,
                   r.cagr_5y, r.ebitda_margin, r.pe_ratio
            FROM financial_ratios r
            JOIN companies c ON r.company_id = c.company_id
            WHERE c.company_name = :name
            ORDER BY r.quarter
        """), {"name": company_name})
        ratios_df = pd.DataFrame(ratios.fetchall(),
            columns=['quarter','roe','roce','net_margin','debt_to_equity',
                     'revenue_growth','cagr_3y','cagr_5y','ebitda_margin','pe_ratio'])

        # Get quarterly results
        results = conn.execute(text("""
            SELECT q.quarter, q.revenue, q.net_profit, q.ebitda, q.eps
            FROM quarterly_results q
            JOIN companies c ON q.company_id = c.company_id
            WHERE c.company_name = :name
            ORDER BY q.period_end
        """), {"name": company_name})
        results_df = pd.DataFrame(results.fetchall(),
            columns=['quarter','revenue','net_profit','ebitda','eps'])

        # Get benchmark score
        score = conn.execute(text("""
            SELECT b.total_score, b.industry_rank, b.industry_percentile
            FROM benchmark_scores b
            JOIN companies c ON b.company_id = c.company_id
            WHERE c.company_name = :name
            ORDER BY b.computed_at DESC
            LIMIT 1
        """), {"name": company_name})
        score_row = score.fetchone()

        return ratios_df, results_df, score_row

# ── Search bar ────────────────────────────────────────
companies_df = get_all_companies()
company_list = companies_df['company_name'].tolist()

selected = st.selectbox(
    "Search for a company",
    options=[""] + company_list,
    placeholder="Type company name..."
)

if selected:
    ratios_df, results_df, score_row = get_company_details(selected)
    company_info = companies_df[companies_df['company_name'] == selected].iloc[0]

    # ── Company header ────────────────────────────────
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f"### {selected}")
    col2.metric("BSE Code", company_info['bse_code'])
    col3.metric("Sector", company_info['sector_name'])
    col4.metric("Market Cap (Cr)", f"₹{float(company_info['market_cap']):,.0f}")

    # ── Benchmark Score ───────────────────────────────
    if score_row:
        score = float(score_row[0])
        rank  = score_row[1]
        st.markdown("---")
        st.subheader("🏆 Benchmark Score")
        sc1, sc2, sc3 = st.columns(3)

        if score >= 80:
            label = "🏆 Industry Leader"
            color = "green"
        elif score >= 60:
            label = "✅ Above Average"
            color = "green"
        elif score >= 40:
            label = "➡️ Average"
            color = "orange"
        elif score >= 20:
            label = "⚠️ Below Average"
            color = "orange"
        else:
            label = "🔴 Needs Attention"
            color = "red"

        sc1.metric("Score", f"{score:.1f} / 100")
        sc2.metric("Sector Rank", f"#{rank}")
        sc3.metric("Label", label)

    # ── Latest Ratios ─────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Latest Financial Ratios (Q4FY25)")

    if not ratios_df.empty:
        latest = ratios_df[ratios_df['quarter'] == 'Q4FY25']
        if not latest.empty:
            r = latest.iloc[0]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("ROE %",          f"{r['roe']:.1f}%" if r['roe'] else "N/A")
            m2.metric("ROCE %",         f"{r['roce']:.1f}%" if r['roce'] else "N/A")
            m3.metric("Net Margin %",   f"{r['net_margin']:.1f}%" if r['net_margin'] else "N/A")
            m4.metric("Debt/Equity",    f"{r['debt_to_equity']:.2f}" if r['debt_to_equity'] else "N/A")

            m5, m6, m7, m8 = st.columns(4)
            m5.metric("Revenue Growth %", f"{r['revenue_growth']:.1f}%" if r['revenue_growth'] else "N/A")
            m6.metric("3Y CAGR %",        f"{r['cagr_3y']:.1f}%" if r['cagr_3y'] else "N/A")
            m7.metric("5Y CAGR %",        f"{r['cagr_5y']:.1f}%" if r['cagr_5y'] else "N/A")
            m8.metric("EBITDA Margin %",  f"{r['ebitda_margin']:.1f}%" if r['ebitda_margin'] else "N/A")

    # ── Revenue Trend Chart ───────────────────────────
    st.markdown("---")
    st.subheader("📈 Revenue & Profit Trend")

    if not results_df.empty:
        fig = px.line(
            results_df,
            x='quarter',
            y=['revenue', 'net_profit'],
            title=f"{selected} — Revenue vs Net Profit (₹ Crores)",
            labels={'value': '₹ Crores', 'variable': 'Metric'},
            markers=True,
            color_discrete_map={
                'revenue': '#1f77b4',
                'net_profit': '#2ca02c'
            }
        )
        fig.update_layout(height=400, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    # ── Historical Ratios Table ───────────────────────
    st.markdown("---")
    st.subheader("📋 Historical Ratios")
    if not ratios_df.empty:
        display_df = ratios_df[['quarter','roe','roce','net_margin',
                                 'revenue_growth','ebitda_margin']].copy()
        display_df.columns = ['Quarter','ROE%','ROCE%','Net Margin%',
                               'Rev Growth%','EBITDA Margin%']
        st.dataframe(display_df.set_index('Quarter'), use_container_width=True)
        # --- AI Insights ---
st.divider()
st.subheader("🤖 AI Consultant Insights")
st.caption("AI-powered analysis based on this company's financials")

if st.button("✨ Generate AI Analysis"):
    try:
        import sys
        sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')
        from engine.ai_insights import generate_insights

        # Build ratios dict from what's already on the page
        ratios = {
            "net_margin":     latest_ratios.get("net_margin", 0),
            "ebitda_margin":  latest_ratios.get("ebitda_margin", 0),
            "roce":           latest_ratios.get("roce", 0),
            "debt_to_equity": latest_ratios.get("debt_to_equity", 0),
        }
        scores = {
            "total_score": latest_score.get("total_score", 0),
            "label":       latest_score.get("label", "N/A"),
        }

        with st.spinner("Analyzing with Claude AI..."):
            insight = generate_insights(selected_company, selected_sector, ratios, scores)
        st.markdown(insight)

    except Exception as e:
        st.info("🔑 AI Insights requires Anthropic API credits. Coming soon!")