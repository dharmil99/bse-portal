import streamlit as st


def apply_theme():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600&family=Inter:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    footer {visibility: hidden;}

    /* ── App background: deep charcoal navy ───────────────── */
    .stApp {
        background-color: #0B1220;
    }

    [data-testid="stAppViewContainer"] > .main {
        background-color: #0B1220;
    }

    [data-testid="block-container"] {
        padding-top: 2rem;
    }

    /* ── Sidebar stays light for nav clarity ───────────────── */
    [data-testid="stSidebar"] {
        background-color: #FAF9F6;
        border-right: 1px solid #E8E5DC;
    }
    [data-testid="stSidebar"] * {
        color: #0B1220 !important;
        font-family: 'Inter', sans-serif !important;
    }
    [data-testid="stSidebarNav"] a {
        font-size: 14px;
    }
    [data-testid="stSidebarNav"] a:hover {
        background-color: #F0EDE3 !important;
    }

    /* ── Body text on dark background ──────────────────────── */
    .stApp, .stApp p, .stApp span, .stApp label, .stApp div {
        color: #C7CCDA;
    }
    h1, h2, h3 {
        font-family: 'Playfair Display', serif !important;
        color: #F4F1EA !important;
        font-weight: 500 !important;
    }

    /* ── Hero banner ────────────────────────────────────────── */
    .hero-banner {
        background: #0B1220;
        border-left: 3px solid #C9A227;
        padding: 44px 40px;
        margin-bottom: 28px;
        position: relative;
    }
    .hero-badge {
        font-size: 11px;
        letter-spacing: 3px;
        color: #C9A227;
        text-transform: uppercase;
        font-family: 'Inter', sans-serif;
        margin-bottom: 18px;
        font-weight: 500;
    }
    .hero-title {
        font-family: 'Playfair Display', serif;
        color: #F4F1EA;
        font-size: 32px;
        font-weight: 500;
        line-height: 1.3;
        margin: 0 0 10px 0;
    }
    .hero-divider {
        width: 48px;
        height: 1px;
        background: #C9A227;
        margin: 18px 0;
    }
    .hero-subtitle {
        font-size: 14px;
        color: #8B93A7;
        font-family: 'Inter', sans-serif;
        line-height: 1.7;
        max-width: 560px;
    }

    /* ── Section headers ────────────────────────────────────── */
    .section-header {
        font-size: 11px;
        font-weight: 500;
        color: #8B93A7;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin: 32px 0 16px 0;
        padding-bottom: 10px;
        border-bottom: 1px solid #1C2333;
    }

    /* ── Stat / metric cards ────────────────────────────────── */
    .stat-card {
        background: #11192B;
        border: 1px solid #1C2333;
        padding: 22px 20px;
        text-align: left;
    }
    .stat-card.accent {
        border-left: 2px solid #C9A227;
    }
    .stat-label {
        font-size: 10px;
        font-weight: 500;
        color: #6E7690;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 8px;
    }
    .stat-number {
        font-family: 'Playfair Display', serif;
        font-size: 30px;
        color: #F4F1EA;
        line-height: 1;
    }
    .stat-icon {
        font-size: 18px;
        color: #C9A227;
        margin-bottom: 10px;
    }

    /* ── Feature / capability cards ─────────────────────────── */
    .feature-card {
        background: #11192B;
        border: 1px solid #1C2333;
        border-left: 2px solid #2B3A5C;
        padding: 22px 20px;
        height: 100%;
        transition: border-left-color 0.2s;
    }
    .feature-card:hover {
        border-left-color: #C9A227;
    }
    .feature-icon {
        font-size: 20px;
        color: #C9A227;
        margin-bottom: 12px;
    }
    .feature-title {
        font-family: 'Playfair Display', serif;
        font-size: 16px;
        font-weight: 500;
        color: #F4F1EA;
        margin-bottom: 8px;
    }
    .feature-desc {
        font-size: 13px;
        color: #8B93A7;
        line-height: 1.7;
    }

    /* ── Rank / medal cards ──────────────────────────────────── */
    .rank-card {
        background: #11192B;
        border: 1px solid #1C2333;
        padding: 20px;
        text-align: center;
    }
    .rank-card.gold   { border-top: 2px solid #C9A227; }
    .rank-card.silver { border-top: 2px solid #8B93A7; }
    .rank-card.bronze { border-top: 2px solid #8A5A33; }
    .rank-medal {
        font-size: 11px;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: #6E7690;
        margin-bottom: 10px;
    }
    .rank-name {
        font-family: 'Playfair Display', serif;
        font-size: 17px;
        color: #F4F1EA;
        margin-bottom: 4px;
    }
    .rank-sector {
        font-size: 11px;
        color: #6E7690;
        margin-bottom: 14px;
    }
    .rank-score {
        font-family: 'Playfair Display', serif;
        font-size: 30px;
        color: #C9A227;
    }
    .rank-score span {
        font-size: 13px;
        color: #6E7690;
        font-family: 'Inter', sans-serif;
    }
    .rank-meta {
        font-size: 11px;
        color: #6E7690;
        margin-top: 10px;
    }

    /* ── Streamlit native widgets re-skinned ────────────────── */
    [data-testid="stMetric"] {
        background: #11192B;
        border: 1px solid #1C2333;
        padding: 16px 18px;
    }
    [data-testid="stMetricLabel"] {
        color: #6E7690 !important;
        font-size: 11px !important;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    [data-testid="stMetricValue"] {
        color: #F4F1EA !important;
        font-family: 'Playfair Display', serif !important;
    }
    [data-testid="stMetricDelta"] svg {
        display: inline;
    }

    .stSelectbox label, .stSlider label, .stMultiSelect label, .stTextInput label {
        color: #8B93A7 !important;
        font-size: 12px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    [data-baseweb="select"] > div {
        background-color: #11192B !important;
        border-color: #1C2333 !important;
        color: #F4F1EA !important;
    }

    [data-testid="stDataFrame"] {
        background: #11192B;
        border: 1px solid #1C2333;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        border-bottom: 1px solid #1C2333;
    }
    .stTabs [data-baseweb="tab"] {
        color: #6E7690;
        font-size: 13px;
    }
    .stTabs [aria-selected="true"] {
        color: #C9A227 !important;
        border-bottom-color: #C9A227 !important;
    }

    hr {
        border-color: #1C2333 !important;
    }

    /* ── Footer ─────────────────────────────────────────────── */
    .platform-footer {
        background: #11192B;
        border: 1px solid #1C2333;
        color: #6E7690;
        padding: 16px 24px;
        text-align: center;
        font-size: 11px;
        letter-spacing: 0.5px;
        margin-top: 40px;
    }
    .platform-footer strong {
        color: #C9A227;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)


# ── Shared safe-formatting helpers (used across all pages) ──────────────
def safe_cr(val):
    try:
        return f"₹{float(val):,.0f} Cr" if val is not None else "N/A"
    except (TypeError, ValueError):
        return "N/A"


def safe_pct(val):
    try:
        return f"{float(val):.1f}%" if val is not None else "N/A"
    except (TypeError, ValueError):
        return "N/A"


def safe_x(val):
    try:
        return f"{float(val):.2f}x" if val is not None else "N/A"
    except (TypeError, ValueError):
        return "N/A"


def to_float(val):
    try:
        return float(val) if val is not None else 0.0
    except (TypeError, ValueError):
        return 0.0