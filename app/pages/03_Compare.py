import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scripts.db_connect import get_engine
from sqlalchemy import text

st.set_page_config(page_title="Peer Comparison", page_icon="⚖️", layout="wide")
st.title("⚖️ Peer Comparison")
st.markdown("Compare 2–5 companies side by side")

engine = get_engine()

@st.cache_data
def get_companies():
    with engine.connect() as conn:
        r = conn.execute(text("SELECT company_name FROM companies ORDER BY company_name"))
        return [row[0] for row in r.fetchall()]

@st.cache_data
def get_comparison_data(companies):
    with engine.connect() as conn:
        placeholders = ','.join([f':c{i}' for i in range(len(companies))])
        params = {f'c{i}': name for i, name in enumerate(companies)}
        result = conn.execute(text(f"""
            SELECT c.company_name, s.sector_name,
                   r.roe, r.roce, r.net_margin, r.debt_to_equity,
                   r.revenue_growth, r.cagr_3y, r.ebitda_margin,
                   b.total_score
            FROM financial_ratios r
            JOIN companies c ON r.company_id = c.company_id
            JOIN sectors s ON c.sector_id = s.sector_id
            LEFT JOIN benchmark_scores b ON b.company_id = c.company_id
                AND b.quarter = r.quarter
            WHERE c.company_name IN ({placeholders})
              AND r.quarter = 'Q4FY25'
        """), params)
        return pd.DataFrame(result.fetchall(), columns=[
            'Company', 'Sector', 'ROE%', 'ROCE%', 'Net Margin%',
            'Debt/Equity', 'Rev Growth%', '3Y CAGR%',
            'EBITDA Margin%', 'Score/100'
        ])

# ── Company selector ──────────────────────────────────
all_companies = get_companies()
selected = st.multiselect(
    "Select 2 to 5 companies to compare",
    options=all_companies,
    max_selections=5
)

if len(selected) < 2:
    st.info("Please select at least 2 companies to compare.")
else:
    df = get_comparison_data(tuple(selected))

    if df.empty:
        st.warning("No data found.")
    else:
        # ── Score comparison ──────────────────────────
        st.markdown("---")
        st.subheader("🏆 Benchmark Scores")
        cols = st.columns(len(df))
        for i, (_, row) in enumerate(df.iterrows()):
            score = float(row['Score/100']) if row['Score/100'] else 0
            if score >= 60:
                cols[i].success(f"**{row['Company'].split()[0]}**\n\n{score:.0f}/100")
            elif score >= 40:
                cols[i].warning(f"**{row['Company'].split()[0]}**\n\n{score:.0f}/100")
            else:
                cols[i].error(f"**{row['Company'].split()[0]}**\n\n{score:.0f}/100")

        # ── Ratio table ───────────────────────────────
        st.markdown("---")
        st.subheader("📊 Side-by-Side Ratio Comparison")

        numeric_cols = ['ROE%','ROCE%','Net Margin%','Debt/Equity',
                        'Rev Growth%','3Y CAGR%','EBITDA Margin%','Score/100']

        display = df.set_index('Company')[numeric_cols].T
        display = display.apply(pd.to_numeric, errors='coerce')

        def color_cells(val):
            if pd.isna(val):
                return ''
            row_max = display.loc[display.index == display.index[0]].max(axis=1)
            return ''

        st.dataframe(
            display.style.highlight_max(axis=1, color='#d4edda')
                         .highlight_min(axis=1, color='#f8d7da'),
            use_container_width=True
        )
        st.caption("🟢 Green = highest value in row | 🔴 Red = lowest value in row")

        # ── Bar chart comparison ──────────────────────
        st.markdown("---")
        st.subheader("📈 Visual Comparison")

        metric = st.selectbox("Select metric to visualize",
                              ['ROE%','ROCE%','Net Margin%','Rev Growth%','EBITDA Margin%'])

        chart_df = df[['Company', metric]].copy()
        chart_df[metric] = pd.to_numeric(chart_df[metric], errors='coerce')
        chart_df = chart_df.dropna()

        fig = px.bar(
            chart_df,
            x='Company',
            y=metric,
            color='Company',
            title=f"{metric} Comparison",
            text=metric
        )