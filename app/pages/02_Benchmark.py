import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scripts.db_connect import get_engine
from sqlalchemy import text

st.set_page_config(page_title="Benchmark Chart", page_icon="📊", layout="wide")
st.title("📊 Competitive Benchmark Chart")
st.markdown("Compare companies in a sector — Revenue Growth vs ROCE")

engine = get_engine()

@st.cache_data
def get_benchmark_data(sector_name):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                c.company_name,
                c.market_cap,
                s.sector_name,
                r.roe,
                r.roce,
                r.net_margin,
                r.revenue_growth,
                r.ebitda_margin,
                r.debt_to_equity,
                b.total_score
            FROM financial_ratios r
            JOIN companies c ON r.company_id = c.company_id
            JOIN sectors s ON c.sector_id = s.sector_id
            LEFT JOIN benchmark_scores b ON b.company_id = c.company_id
                AND b.quarter = r.quarter
            WHERE s.sector_name = :sector
              AND r.quarter = 'Q4FY25'
              AND r.revenue_growth IS NOT NULL
              AND r.roce IS NOT NULL
        """), {"sector": sector_name})
        return pd.DataFrame(result.fetchall(), columns=[
            'company_name', 'market_cap', 'sector_name',
            'roe', 'roce', 'net_margin', 'revenue_growth',
            'ebitda_margin', 'debt_to_equity', 'total_score'
        ])

@st.cache_data
def get_sectors():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT sector_name FROM sectors ORDER BY sector_name"))
        return [row[0] for row in result.fetchall()]

# ── Controls ──────────────────────────────────────────
col1, col2 = st.columns([2, 2])
sectors = get_sectors()
selected_sector = col1.selectbox("Select Sector", sectors)
selected_company = col2.selectbox("Highlight Company (optional)", 
                                   ["None"] + get_benchmark_data(selected_sector)['company_name'].tolist())

df = get_benchmark_data(selected_sector)

if df.empty:
    st.warning("No data available for this sector.")
else:
    # Convert to float
    for col in ['market_cap', 'roce', 'revenue_growth', 'net_margin', 'total_score']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.dropna(subset=['roce', 'revenue_growth'])

    # Highlight selected company
    df['highlight'] = df['company_name'].apply(
        lambda x: '⭐ ' + x if x == selected_company else x
    )
    df['color'] = df['company_name'].apply(
        lambda x: 'Selected' if x == selected_company else 'Peer'
    )

    # ── Bubble Chart ──────────────────────────────────
    fig = px.scatter(
        df,
        x='revenue_growth',
        y='roce',
        size='market_cap',
        color='color',
        hover_name='company_name',
        hover_data={
            'revenue_growth': ':.1f',
            'roce':           ':.1f',
            'net_margin':     ':.1f',
            'total_score':    ':.1f',
            'market_cap':     ':,.0f',
            'color':          False
        },
        color_discrete_map={
            'Selected': '#FF4B4B',
            'Peer':     '#1f77b4'
        },
        size_max=80,
        title=f"Competitive Benchmark — {selected_sector}",
        labels={
            'revenue_growth': 'Revenue Growth % (YoY)',
            'roce':           'ROCE %',
            'market_cap':     'Market Cap (₹ Cr)'
        }
    )

    # Add company name labels
    for _, row in df.iterrows():
        fig.add_annotation(
            x=row['revenue_growth'],
            y=row['roce'],
            text=row['company_name'].split()[0],
            showarrow=False,
            yshift=20,
            font=dict(size=10)
        )

    # Add quadrant lines
    median_x = df['revenue_growth'].median()
    median_y = df['roce'].median()

    fig.add_hline(y=median_y, line_dash="dash", line_color="gray",
                  opacity=0.5, annotation_text=f"Median ROCE: {median_y:.1f}%",
                  annotation_position="right")
    fig.add_vline(x=median_x, line_dash="dash", line_color="gray",
                  opacity=0.5, annotation_text=f"Median Growth: {median_x:.1f}%",
                  annotation_position="top")

    fig.update_layout(
        height=600,
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    # ── Quadrant explanation ──────────────────────────
    st.markdown("---")
    q1, q2, q3, q4 = st.columns(4)
    q1.success("⭐ Top Right\nHigh Growth + High ROCE\n**Stars**")
    q2.info("💰 Top Left\nLow Growth + High ROCE\n**Cash Cows**")
    q3.warning("🚀 Bottom Right\nHigh Growth + Low ROCE\n**Growth Bets**")
    q4.error("⚠️ Bottom Left\nLow Growth + Low ROCE\n**Laggards**")

    # ── Data table ────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Sector Data Table")
    display = df[['company_name','revenue_growth','roce',
                  'net_margin','total_score']].copy()
    display.columns = ['Company','Rev Growth%','ROCE%','Net Margin%','Score/100']
    display = display.sort_values('Score/100', ascending=False)
    st.dataframe(display.set_index('Company'), use_container_width=True)