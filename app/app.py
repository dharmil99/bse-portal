import streamlit as st
import pandas as pd
from sqlalchemy import text
import sys
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')
from scripts.db_connect import get_engine
from app.theme import apply_theme, to_float

st.set_page_config(
    page_title="Eelanos Benchmarking Platform",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded"
)
apply_theme()

engine = get_engine()


@st.cache_data(ttl=300)
def load_stats():
    with engine.connect() as conn:
        companies = conn.execute(text("SELECT COUNT(*) FROM companies")).fetchone()[0]
        sectors   = conn.execute(text("SELECT COUNT(*) FROM sectors")).fetchone()[0]
        data_points = conn.execute(text("SELECT COUNT(*) FROM quarterly_results")).fetchone()[0]
        avg_score = conn.execute(text(
            "SELECT ROUND(AVG(total_score),1) FROM benchmark_scores"
        )).fetchone()[0]

        sector_data = pd.read_sql(text("""
            SELECT
                s.sector_name,
                COUNT(c.company_id) as companies,
                ROUND(AVG(r.roe),1) as avg_roe,
                ROUND(AVG(r.roce),1) as avg_roce,
                ROUND(AVG(r.net_margin),1) as avg_margin,
                ROUND(AVG(r.revenue_growth),1) as avg_growth,
                ROUND(AVG(b.total_score),1) as avg_score
            FROM sectors s
            JOIN companies c ON c.sector_id = s.sector_id
            JOIN financial_ratios r ON r.company_id = c.company_id
            JOIN benchmark_scores b ON b.company_id = c.company_id
                AND b.quarter = r.quarter
            WHERE r.quarter = 'Q4FY25'
            GROUP BY s.sector_name
            ORDER BY avg_score DESC
        """), conn)

        top3 = pd.read_sql(text("""
            SELECT c.company_name, s.sector_name, b.total_score,
                   r.revenue_growth, r.roce
            FROM benchmark_scores b
            JOIN companies c ON b.company_id = c.company_id
            JOIN sectors s ON c.sector_id = s.sector_id
            JOIN financial_ratios r ON r.company_id = c.company_id
                AND r.quarter = b.quarter
            WHERE b.quarter = 'Q4FY25'
            ORDER BY b.total_score DESC
            LIMIT 3
        """), conn)

    return companies, sectors, data_points, avg_score, sector_data, top3


companies, sectors, data_points, avg_score, sector_data, top3 = load_stats()

# ── HERO BANNER ───────────────────────────────────────
st.markdown(f"""
<div class="hero-banner">
    <div class="hero-badge">Eelanos Analytics · Confidential</div>
    <div class="hero-divider"></div>
    <div class="hero-title">Business Benchmarking &amp;<br>Competitive Intelligence Platform</div>
    <div class="hero-subtitle">
        Institutional-grade financial benchmarking for Indian listed companies.
        Identify performance gaps, benchmark against peers, and generate actionable insights.
    </div>
</div>
""", unsafe_allow_html=True)

# ── LIVE STATS ────────────────────────────────────────
st.markdown('<div class="section-header">Platform overview — live data</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
stat_items = [
    (c1, "Companies tracked", companies, False),
    (c2, "Sectors covered", sectors, False),
    (c3, "Data points loaded", f"{data_points:,}", False),
    (c4, "Years of history", "10", False),
    (c5, "Avg benchmark score", avg_score, True),
]
for col, label, value, accent in stat_items:
    with col:
        cls = "stat-card accent" if accent else "stat-card"
        st.markdown(f"""
        <div class="{cls}">
            <div class="stat-label">{label}</div>
            <div class="stat-number">{value}</div>
        </div>""", unsafe_allow_html=True)

# ── TOP 3 PERFORMERS ──────────────────────────────────
st.markdown('<div class="section-header">Top performing companies — Q4FY25</div>', unsafe_allow_html=True)

medal_labels = ["Rank 01", "Rank 02", "Rank 03"]
medal_classes = ["gold", "silver", "bronze"]

if not top3.empty:
    cols = st.columns(3)
    for idx, col in enumerate(cols):
        if idx < len(top3):
            row = top3.iloc[idx]
            with col:
                st.markdown(f"""
                <div class="rank-card {medal_classes[idx]}">
                    <div class="rank-medal">{medal_labels[idx]}</div>
                    <div class="rank-name">{row['company_name']}</div>
                    <div class="rank-sector">{row['sector_name']}</div>
                    <div class="rank-score">{to_float(row['total_score']):.0f}<span>/100</span></div>
                    <div class="rank-meta">ROCE {to_float(row['roce']):.1f}%  ·  Growth {to_float(row['revenue_growth']):.1f}%</div>
                </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── SECTOR OVERVIEW TABLE ─────────────────────────────
st.markdown('<div class="section-header">Sector performance summary — Q4FY25</div>', unsafe_allow_html=True)

if not sector_data.empty:
    sector_data.columns = ['Sector', 'Companies', 'Avg ROE%', 'Avg ROCE%',
                            'Avg Margin%', 'Avg Growth%', 'Avg Score']
    st.dataframe(
        sector_data.style
            .background_gradient(subset=['Avg Score'], cmap='YlOrBr')
            .background_gradient(subset=['Avg Growth%'], cmap='Greens')
            .format({
                'Avg ROE%':    '{:.1f}%',
                'Avg ROCE%':   '{:.1f}%',
                'Avg Margin%': '{:.1f}%',
                'Avg Growth%': '{:.1f}%',
                'Avg Score':   '{:.1f}'
            }),
        width='stretch',
        hide_index=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── PLATFORM CAPABILITIES ─────────────────────────────
st.markdown('<div class="section-header">Platform capabilities</div>', unsafe_allow_html=True)

features = [
    ("ti-search", "Company deep dive",
     "Search any BSE company. View full P&L, balance sheet, cash flow, efficiency ratios and ten-year trends in one place."),
    ("ti-chart-bubble", "Competitive benchmark",
     "Interactive bubble chart plotting revenue growth vs ROCE. Instantly identify stars, cash cows, and laggards in any sector."),
    ("ti-scale", "Peer comparison",
     "Select two to five companies for side-by-side ratio comparison with weighted performance indicators."),
    ("ti-building-factory-2", "Sector intelligence",
     "Sector-level averages, rankings and performance distribution across IT, banking, FMCG, pharma and automobile."),
    ("ti-trophy", "Benchmark scoring",
     "Proprietary 0–100 score based on ROE, ROCE, revenue growth, margins and debt levels weighted by strategic importance."),
    ("ti-chart-line", "Deep financials",
     "Full P&L, balance sheet and cash flow statements with ten years of history, expense breakdown and cash flow health check."),
]

row1 = st.columns(3)
row2 = st.columns(3)

for i, (icon, title, desc) in enumerate(features):
    col = row1[i] if i < 3 else row2[i - 3]
    with col:
        st.markdown(f"""
        <div class="feature-card">
            <div class="feature-icon"><i class="ti {icon}"></i></div>
            <div class="feature-title">{title}</div>
            <div class="feature-desc">{desc}</div>
        </div>""", unsafe_allow_html=True)
    if i == 2:
        st.markdown("<br>", unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/3.1.0/tabler-icons-outline.min.css">
<div class="platform-footer">
    <strong>Eelanos Business Benchmarking Platform</strong>
    &nbsp;·&nbsp; Data sourced from BSE India &amp; Screener.in
    &nbsp;·&nbsp; Updated quarterly &nbsp;·&nbsp;
    For internal use only
</div>
""", unsafe_allow_html=True)