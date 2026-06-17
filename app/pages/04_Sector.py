import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scripts.db_connect import get_engine
from sqlalchemy import text

st.set_page_config(page_title="Sector Analysis", page_icon="🏭", layout="wide")
st.title("🏭 Sector Analysis")

engine = get_engine()

@st.cache_data
def get_sector_data(sector):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT c.company_name, r.roe, r.roce, r.net_margin,
                   r.revenue_growth, r.ebitda_margin, r.debt_to_equity,
                   b.total_score, b.industry_rank
            FROM financial_ratios r
            JOIN companies c ON r.company_id = c.company_id
            JOIN sectors s ON c.sector_id = s.sector_id
            LEFT JOIN benchmark_scores b ON b.company_id = c.company_id
                AND b.quarter = r.quarter
            WHERE s.sector_name = :s AND r.quarter = 'Q4FY25'
        """), {"s": sector})
        return pd.DataFrame(result.fetchall(), columns=[
            'Company','ROE%','ROCE%','Net Margin%',
            'Rev Growth%','EBITDA Margin%','Debt/Equity',
            'Score/100','Rank'
        ])

@st.cache_data
def get_sectors():
    with engine.connect() as conn:
        r = conn.execute(text("SELECT sector_name FROM sectors ORDER BY sector_name"))
        return [row[0] for row in r.fetchall()]

col1, col2 = st.columns([2,2])
sector = col1.selectbox("Select Sector", get_sectors())
metric = col2.selectbox("Rank By", ['Score/100','ROE%','ROCE%','Net Margin%','Rev Growth%'])

df = get_sector_data(sector)

if df.empty:
    st.warning("No data available.")
else:
    for col in ['ROE%','ROCE%','Net Margin%','Rev Growth%','EBITDA Margin%','Score/100']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.sort_values(metric, ascending=False).reset_index(drop=True)
    df.index += 1

    # ── Sector averages ───────────────────────────────
    st.markdown("---")
    st.subheader(f"📊 {sector} Sector Averages")
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Avg ROE %",        f"{df['ROE%'].mean():.1f}%")
    m2.metric("Avg ROCE %",       f"{df['ROCE%'].mean():.1f}%")
    m3.metric("Avg Net Margin %", f"{df['Net Margin%'].mean():.1f}%")
    m4.metric("Avg Rev Growth %", f"{df['Rev Growth%'].mean():.1f}%")

    # ── Ranked table ──────────────────────────────────
    st.markdown("---")
    st.subheader(f"🏆 Companies Ranked by {metric}")
    st.dataframe(
        df[['Company','Score/100','ROE%','ROCE%','Net Margin%','Rev Growth%']]
          .style.highlight_max(axis=0, color='#d4edda')
                .highlight_min(axis=0, color='#f8d7da'),
        use_container_width=True
    )

    # ── Bar chart ─────────────────────────────────────
    fig = px.bar(df, x='Company', y=metric,
                 color=metric, color_continuous_scale='Blues',
                 title=f"{sector} — {metric} Ranking")
    fig.update_layout(height=400, plot_bgcolor='white')
    st.plotly_chart(fig, use_container_width=True)