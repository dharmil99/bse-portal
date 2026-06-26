import streamlit as st
import pandas as pd
import sys
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')

from sqlalchemy import text
from scripts.db_connect import get_engine

st.set_page_config(page_title="Excellence Model", page_icon="🏆", layout="wide")

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Page background */
[data-testid="stAppViewContainer"] { background: #0D1117; }
[data-testid="stSidebar"] { background: #161B22; }

/* Hide default streamlit header */
header[data-testid="stHeader"] { background: transparent; }

/* Main title */
.em-title {
    font-family: 'Arial', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: #E6EDF3;
    letter-spacing: -0.5px;
    margin-bottom: 0;
}
.em-subtitle {
    font-size: 0.95rem;
    color: #8B949E;
    margin-top: 4px;
    margin-bottom: 28px;
}

/* Score card */
.score-card {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 10px;
    position: relative;
    transition: border-color 0.2s;
}
.score-card:hover { border-color: #58A6FF; }
.rank-badge {
    font-size: 0.72rem;
    font-weight: 700;
    color: #8B949E;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.company-name {
    font-size: 1.05rem;
    font-weight: 600;
    color: #E6EDF3;
    margin: 3px 0;
}
.score-num {
    font-size: 1.6rem;
    font-weight: 700;
    font-family: monospace;
}
.tier-pill {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    margin-top: 4px;
}

/* Progress bar container */
.prog-wrap {
    background: #21262D;
    border-radius: 4px;
    height: 6px;
    margin-top: 10px;
    overflow: hidden;
}
.prog-fill {
    height: 6px;
    border-radius: 4px;
    transition: width 0.4s ease;
}

/* Category mini-scores */
.cat-row {
    display: flex;
    gap: 8px;
    margin-top: 10px;
    flex-wrap: wrap;
}
.cat-chip {
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 4px;
    border: 1px solid #30363D;
    color: #8B949E;
}

/* Heatmap cell */
.hm-cell-green  { background: #1A3E2A; color: #56D364; border-radius: 4px; padding: 4px 6px; text-align: center; font-size: 0.75rem; font-weight: 600; }
.hm-cell-yellow { background: #3D2F00; color: #E3B341; border-radius: 4px; padding: 4px 6px; text-align: center; font-size: 0.75rem; font-weight: 600; }
.hm-cell-red    { background: #3D1515; color: #F85149; border-radius: 4px; padding: 4px 6px; text-align: center; font-size: 0.75rem; font-weight: 600; }
.hm-cell-gray   { background: #21262D; color: #8B949E; border-radius: 4px; padding: 4px 6px; text-align: center; font-size: 0.75rem; }

/* Section header */
.section-hdr {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #58A6FF;
    margin: 28px 0 14px;
    padding-bottom: 6px;
    border-bottom: 1px solid #21262D;
}

/* Metric legend */
.legend-box {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 0.8rem;
    color: #8B949E;
    margin-bottom: 16px;
}
.legend-box b { color: #E6EDF3; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
AUTO_COMPANIES = [
    "Tata Motors Limited", "Maruti Suzuki India", "Mahindra and Mahindra",
    "Bajaj Auto Limited", "Hero MotoCorp Limited", "TVS Motor Company",
    "Eicher Motors Limited", "Ashok Leyland Limited", "Bosch Limited",
    "MRF Limited", "Apollo Tyres Limited", "CEAT Limited",
    "Balkrishna Industries", "Samvardhana Motherson", "Minda Industries Limited",
    "Sona BLW Precision", "Endurance Technologies", "Escorts Kubota Limited",
    "Force Motors Limited", "Atul Auto Limited"
]

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
    "Net Profit Margin": True, "EBITDA Margin": True, "ROE": True,
    "ROCE": True, "Operating Profit Margin": True, "Revenue Growth YoY": True,
    "3Y Revenue CAGR": True, "NP Growth YoY": True, "Asset Turnover": True,
    "Debtor Days": False, "Inventory Turnover": True, "Debt to Equity": False,
    "Interest Coverage": True, "EPS Growth YoY": True, "Current Ratio": True,
}

CATEGORIES = {
    "Profitability": ["Net Profit Margin", "EBITDA Margin", "ROE", "ROCE", "Operating Profit Margin"],
    "Growth":        ["Revenue Growth YoY", "3Y Revenue CAGR", "NP Growth YoY", "EPS Growth YoY"],
    "Efficiency":    ["Asset Turnover", "Debtor Days", "Inventory Turnover"],
    "Safety":        ["Debt to Equity", "Interest Coverage", "Current Ratio"],
}

CAT_COLORS = {
    "Profitability": "#1F6FEB",
    "Growth":        "#3FB950",
    "Efficiency":    "#A371F7",
    "Safety":        "#F0883E",
}

def tier_info(score):
    if score >= 85:   return ("Excellence Leader", "#1F6FEB", "#0D2F5E")
    elif score >= 70: return ("High Performer",    "#3FB950", "#0D2A15")
    elif score >= 55: return ("Above Average",     "#56D364", "#0D2A15")
    elif score >= 40: return ("Average",           "#E3B341", "#2D1F00")
    elif score >= 25: return ("Below Average",     "#F0883E", "#2D1500")
    else:             return ("Needs Improvement", "#F85149", "#2D0D0D")

def score_color(score):
    if score >= 70: return "#3FB950"
    elif score >= 50: return "#E3B341"
    else: return "#F85149"

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_all_data():
    engine = get_engine()

    def safe_div(a, b, mult=1):
        try:
            if b and float(b) != 0:
                return round(float(a) / float(b) * mult, 2)
        except:
            pass
        return None

    all_ratios = {}
    for company in AUTO_COMPANIES:
        try:
            with engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT company_id FROM companies WHERE company_name = :name"
                ), {"name": company}).fetchone()
                if not result:
                    all_ratios[company] = {}
                    continue
                cid = result[0]

                pl = pd.read_sql(text("""
                    SELECT fiscal_year, sales, net_profit, depreciation, interest
                    FROM profit_loss WHERE company_id = :cid ORDER BY fiscal_year
                """), conn, params={"cid": cid})

                bs = pd.read_sql(text("""
                    SELECT fiscal_year, equity_capital, reserves, borrowings,
                           total_assets, net_block, receivables, inventory,
                           cash_and_bank, other_liabilities
                    FROM balance_sheet WHERE company_id = :cid ORDER BY fiscal_year
                """), conn, params={"cid": cid})

            if pl.empty:
                all_ratios[company] = {}
                continue

            merged = pd.merge(pl, bs, on="fiscal_year", how="inner")
            if merged.empty:
                all_ratios[company] = {}
                continue

            latest = merged.iloc[-1]
            prev   = merged.iloc[-2] if len(merged) > 1 else latest
            old3   = merged.iloc[-4] if len(merged) > 3 else merged.iloc[0]

            r = {}
            ebitda = (latest["net_profit"] or 0) + (latest["interest"] or 0) + (latest["depreciation"] or 0)
            equity = (latest.get("equity_capital") or 0) + (latest.get("reserves") or 0)
            cap_emp = equity + (latest.get("borrowings") or 0)
            ebit   = (latest["net_profit"] or 0) + (latest["interest"] or 0)

            r["Net Profit Margin"]       = safe_div(latest["net_profit"], latest["sales"], 100)
            r["EBITDA Margin"]           = safe_div(ebitda, latest["sales"], 100)
            r["ROE"]                     = safe_div(latest["net_profit"], equity, 100)
            r["ROCE"]                    = safe_div(ebit, cap_emp, 100)
            r["Operating Profit Margin"] = safe_div(ebitda, latest["sales"], 100)
            r["Revenue Growth YoY"]      = safe_div(latest["sales"] - prev["sales"], prev["sales"], 100)

            try:
                if old3["sales"] and float(old3["sales"]) != 0:
                    r["3Y Revenue CAGR"] = round(((float(latest["sales"]) / float(old3["sales"])) ** (1/3) - 1) * 100, 2)
                else:
                    r["3Y Revenue CAGR"] = None
            except:
                r["3Y Revenue CAGR"] = None

            try:
                prev_np = float(prev["net_profit"]); curr_np = float(latest["net_profit"])
                r["NP Growth YoY"] = round((curr_np - prev_np) / abs(prev_np) * 100, 2) if prev_np != 0 else None
            except:
                r["NP Growth YoY"] = None

            r["EPS Growth YoY"] = r["NP Growth YoY"]

            total_assets = float(latest.get("total_assets") or 0)
            if total_assets == 0:
                total_assets = sum(float(latest.get(k) or 0) for k in ["net_block","receivables","inventory","cash_and_bank"])
            r["Asset Turnover"]     = safe_div(latest["sales"], total_assets) if total_assets else None
            r["Debtor Days"]        = safe_div(latest.get("receivables") or 0, latest["sales"], 365)
            r["Inventory Turnover"] = safe_div(latest["sales"], latest.get("inventory")) if latest.get("inventory") else None
            r["Debt to Equity"]     = safe_div(latest.get("borrowings"), equity)

            interest = float(latest.get("interest") or 0)
            r["Interest Coverage"]  = safe_div(ebit, interest) if interest > 0 else None

            curr_assets = sum(float(latest.get(k) or 0) for k in ["receivables","inventory","cash_and_bank"])
            curr_liab   = float(latest.get("other_liabilities") or 0)
            r["Current Ratio"] = safe_div(curr_assets, curr_liab) if curr_liab > 0 else None

            all_ratios[company] = r

        except Exception as e:
            all_ratios[company] = {}

    # Percentile scores
    ratio_names = list(RATIO_WEIGHTS.keys())
    pct_scores = {}
    for company in AUTO_COMPANIES:
        pct_scores[company] = {}

    for rn in ratio_names:
        all_vals = [all_ratios[c].get(rn) for c in AUTO_COMPANIES]
        valid = [v for v in all_vals if v is not None]
        for company in AUTO_COMPANIES:
            val = all_ratios[company].get(rn)
            if val is None or not valid:
                pct_scores[company][rn] = 50
            else:
                if HIGHER_BETTER[rn]:
                    pct_scores[company][rn] = round(sum(1 for v in valid if v <= val) / len(valid) * 100, 1)
                else:
                    pct_scores[company][rn] = round(sum(1 for v in valid if v >= val) / len(valid) * 100, 1)

    # Total scores
    total_scores = {}
    for company in AUTO_COMPANIES:
        total_scores[company] = round(sum(
            pct_scores[company].get(r, 50) * w for r, w in RATIO_WEIGHTS.items()
        ), 1)

    ranked = sorted(total_scores.items(), key=lambda x: x[1], reverse=True)

    # Category scores
    cat_scores = {}
    for company in AUTO_COMPANIES:
        cat_scores[company] = {}
        for cat, ratios in CATEGORIES.items():
            vals = [pct_scores[company].get(r, 50) for r in ratios]
            cat_scores[company][cat] = round(sum(vals) / len(vals), 1)

    return ranked, all_ratios, pct_scores, cat_scores


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown('<p class="em-title">🏆 Excellence Model</p>', unsafe_allow_html=True)
st.markdown('<p class="em-subtitle">Automobile sector · 20 companies · 15 ratios · Peer-relative scoring</p>', unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Calculating excellence scores…"):
    ranked, all_ratios, pct_scores, cat_scores = load_all_data()

# ── Top summary metrics ───────────────────────────────────────────────────────
top_company, top_score = ranked[0]
avg_score = round(sum(s for _, s in ranked) / len(ranked), 1)
leaders = sum(1 for _, s in ranked if s >= 70)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Top Ranked", top_company.replace(" Limited","").replace(" India",""), f"Score: {top_score}")
with m2:
    st.metric("Sector Average", f"{avg_score} / 100")
with m3:
    st.metric("High Performers", f"{leaders} companies", "Score ≥ 70")
with m4:
    st.metric("Companies Ranked", "20", "Automobile sector")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📊 Rankings", "🌡️ Ratio Heatmap", "🔍 Company Deep Dive", "ℹ️ Methodology"])


# ════════════════════════════════════════════════════════
# TAB 1 — RANKINGS
# ════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-hdr">Excellence Rankings — All Companies</div>', unsafe_allow_html=True)

    col_filter, col_sort = st.columns([2, 2])
    with col_filter:
        min_score = st.slider("Minimum score filter", 0, 90, 0, 5)
    with col_sort:
        sort_by = st.selectbox("Sort by", ["Excellence Score", "Profitability", "Growth", "Efficiency", "Safety"])

    # Apply sort
    if sort_by == "Excellence Score":
        display_ranked = sorted(ranked, key=lambda x: x[1], reverse=True)
    else:
        display_ranked = sorted(ranked, key=lambda x: cat_scores[x[0]].get(sort_by, 0), reverse=True)

    display_ranked = [(c, s) for c, s in display_ranked if s >= min_score]

    # Render cards in 2 columns
    c1, c2 = st.columns(2)
    for i, (company, score) in enumerate(display_ranked):
        tier_label, tier_color, tier_bg = tier_info(score)
        short = company.replace(" Limited","").replace(" India","")
        actual_rank = next(j+1 for j,(c,_) in enumerate(ranked) if c == company)

        medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(actual_rank, f"#{actual_rank}")

        cat_chips = "".join([
            f'<span class="cat-chip">{cat[:4]}: <b style="color:#E6EDF3">{cat_scores[company][cat]:.0f}</b></span>'
            for cat in ["Profitability","Growth","Efficiency","Safety"]
        ])

        card_html = f"""
        <div class="score-card">
            <div class="rank-badge">{medal} Rank {actual_rank}</div>
            <div class="company-name">{short}</div>
            <div style="display:flex; align-items:baseline; gap:8px; margin:6px 0">
                <span class="score-num" style="color:{score_color(score)}">{score}</span>
                <span class="tier-pill" style="background:{tier_bg}; color:{tier_color}">{tier_label}</span>
            </div>
            <div class="prog-wrap">
                <div class="prog-fill" style="width:{score}%; background:{score_color(score)}"></div>
            </div>
            <div class="cat-row">{cat_chips}</div>
        </div>
        """
        if i % 2 == 0:
            c1.markdown(card_html, unsafe_allow_html=True)
        else:
            c2.markdown(card_html, unsafe_allow_html=True)

    # Summary table below
    st.markdown('<div class="section-hdr">Summary Table</div>', unsafe_allow_html=True)
    table_rows = []
    for i, (company, score) in enumerate(ranked):
        tier_label, _, _ = tier_info(score)
        table_rows.append({
            "Rank": i+1,
            "Company": company.replace(" Limited","").replace(" India",""),
            "Score": score,
            "Tier": tier_label,
            "Profitability": cat_scores[company]["Profitability"],
            "Growth": cat_scores[company]["Growth"],
            "Efficiency": cat_scores[company]["Efficiency"],
            "Safety": cat_scores[company]["Safety"],
        })
    df_table = pd.DataFrame(table_rows)
    st.dataframe(
        df_table.style.background_gradient(subset=["Score","Profitability","Growth","Efficiency","Safety"],
                                            cmap="RdYlGn", vmin=20, vmax=90),
        use_container_width=True, hide_index=True
    )
# ── Visual Category Comparison ─────────────────────────
st.markdown('<div class="section-hdr">Category Score Breakdown — Top 5 vs Bottom 5</div>', 
            unsafe_allow_html=True)

import plotly.graph_objects as go

top5    = [c for c,_ in ranked[:5]]
bottom5 = [c for c,_ in ranked[-5:]]
compare_companies = top5 + bottom5

categories = ["Profitability", "Growth", "Efficiency", "Safety"]
colors = ["#1F6FEB", "#3FB950", "#A371F7", "#F0883E"]

fig = go.Figure()

for cat, color in zip(categories, colors):
    fig.add_trace(go.Bar(
        name=cat,
        x=[c.replace(" Limited","").replace(" India","")
           for c in compare_companies],
        y=[cat_scores[c][cat] for c in compare_companies],
        marker_color=color,
        opacity=0.85
    ))

fig.add_vline(
    x=4.5,
    line_dash="dash",
    line_color="#8B949E",
    annotation_text="Top 5 | Bottom 5",
    annotation_font_color="#8B949E"
)

fig.update_layout(
    barmode="group",
    height=420,
    paper_bgcolor="#0D1117",
    plot_bgcolor="#0D1117",
    font=dict(color="#E6EDF3", size=11),
    legend=dict(
        orientation="h",
        yanchor="bottom", y=1.02,
        xanchor="right", x=1,
        bgcolor="rgba(0,0,0,0)"
    ),
    xaxis=dict(gridcolor="#21262D", tickangle=-20),
    yaxis=dict(gridcolor="#21262D", title="Percentile Score"),
    margin=dict(t=40, b=60)
)

st.plotly_chart(fig, use_container_width=True)

# ── Why Eicher wins — auto-generated insight ──────────
st.markdown('<div class="section-hdr">Why the Top Company Leads</div>', 
            unsafe_allow_html=True)

top_co   = ranked[0][0]
top_s    = ranked[0][1]
top_short = top_co.replace(" Limited","").replace(" India","")
sector_avg_score = round(sum(s for _,s in ranked) / len(ranked), 1)

# Find their strongest and weakest category
best_cat  = max(CATEGORIES.keys(), 
                key=lambda c: cat_scores[top_co][c])
worst_cat = min(CATEGORIES.keys(), 
                key=lambda c: cat_scores[top_co][c])

# Find top 3 strongest ratios
top_ratios = sorted(
    [(r, pct_scores[top_co][r]) for r in RATIO_WEIGHTS],
    key=lambda x: x[1], reverse=True
)[:3]

insight_col1, insight_col2 = st.columns([1, 1])

with insight_col1:
    st.markdown(f"""
    <div class="score-card" style="border-color:#1F6FEB">
        <div class="rank-badge">🏆 Why {top_short} ranks #1</div>
        <div style="margin-top:12px; color:#E6EDF3; font-size:0.9rem; line-height:1.7">
            <b>{top_short}</b> scores <b style="color:#3FB950">{top_s}/100</b> vs 
            sector average of <b style="color:#E3B341">{sector_avg_score}/100</b> — 
            outperforming peers by <b style="color:#3FB950">
            +{round(top_s - sector_avg_score, 1)} points</b>.<br><br>
            Strongest pillar: <b style="color:#1F6FEB">{best_cat} 
            ({cat_scores[top_co][best_cat]:.0f}/100)</b><br>
            Area to watch: <b style="color:#F0883E">{worst_cat} 
            ({cat_scores[top_co][worst_cat]:.0f}/100)</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

with insight_col2:
    st.markdown(f"""
    <div class="score-card" style="border-color:#3FB950">
        <div class="rank-badge">📊 Top 3 Strongest Ratios</div>
        <div style="margin-top:12px">
    """, unsafe_allow_html=True)

    for ratio_name, pct in top_ratios:
        actual_val = all_ratios[top_co].get(ratio_name)
        val_str = f"{actual_val:.1f}" if actual_val is not None else "N/A"
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; 
                    align-items:center; padding:6px 0; 
                    border-bottom:1px solid #21262D">
            <span style="color:#E6EDF3; font-size:0.85rem">
                {ratio_name}
            </span>
            <span style="color:#3FB950; font-weight:700; font-size:0.9rem">
                {pct:.0f}th pct &nbsp;
                <span style="color:#8B949E; font-weight:400">
                    ({val_str})
                </span>
            </span>
        </div>
        """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# TAB 2 — RATIO HEATMAP
# ════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-hdr">Ratio Heatmap — Percentile Scores per Company</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="legend-box">
        <b>How to read this:</b> Each cell shows the company's <b>percentile score</b> for that ratio against all 20 peers.
        &nbsp; <span style="color:#56D364">■ Green ≥ 75</span> &nbsp;
        <span style="color:#E3B341">■ Yellow 50–74</span> &nbsp;
        <span style="color:#F85149">■ Red &lt; 50</span>
    </div>
    """, unsafe_allow_html=True)

    cat_filter = st.multiselect("Filter categories", list(CATEGORIES.keys()), default=list(CATEGORIES.keys()))

    selected_ratios = []
    for cat in cat_filter:
        selected_ratios.extend(CATEGORIES[cat])

    if selected_ratios:
        heatmap_data = {}
        for company, score in ranked:
            short = company.replace(" Limited","").replace(" India","")
            heatmap_data[short] = {r: pct_scores[company].get(r, 50) for r in selected_ratios}

        df_hm = pd.DataFrame(heatmap_data).T
        df_hm.index.name = "Company"

        # Style: color cells by value
        def color_cell(val):
            if val >= 75:   return "background-color: #1A3E2A; color: #56D364; font-weight: 600"
            elif val >= 50: return "background-color: #3D2F00; color: #E3B341; font-weight: 600"
            else:           return "background-color: #3D1515; color: #F85149; font-weight: 600"

        try:
            styled = df_hm.style.map(color_cell).format("{:.0f}")
        except AttributeError:
            styled = df_hm.style.applymap(color_cell).format("{:.0f}")
        st.dataframe(styled, use_container_width=True, height=600)


# ════════════════════════════════════════════════════════
# TAB 3 — COMPANY DEEP DIVE
# ════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-hdr">Company Deep Dive</div>', unsafe_allow_html=True)

    company_options = [c.replace(" Limited","").replace(" India","") for c, _ in ranked]
    full_names = {c.replace(" Limited","").replace(" India",""): c for c, _ in ranked}

    selected_short = st.selectbox("Select company", company_options)
    selected_company = full_names[selected_short]
    selected_score = dict(ranked)[selected_company]
    selected_rank = next(i+1 for i,(c,_) in enumerate(ranked) if c == selected_company)

    tier_label, tier_color_val, tier_bg_val = tier_info(selected_score)

    # Header
    st.markdown(f"""
    <div class="score-card" style="border-color:{tier_color_val}; margin-bottom:20px">
        <div class="rank-badge">Rank #{selected_rank} of 20</div>
        <div class="company-name" style="font-size:1.4rem">{selected_short}</div>
        <div style="display:flex; align-items:baseline; gap:12px; margin:8px 0">
            <span class="score-num" style="color:{tier_color_val}; font-size:2.2rem">{selected_score}</span>
            <span class="tier-pill" style="background:{tier_bg_val}; color:{tier_color_val}; font-size:0.85rem; padding:5px 14px">{tier_label}</span>
        </div>
        <div class="prog-wrap" style="height:8px">
            <div class="prog-fill" style="width:{selected_score}%; background:{tier_color_val}"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Category scores
    st.markdown("**Category Breakdown**")
    cat_cols = st.columns(4)
    for i, (cat, ratios) in enumerate(CATEGORIES.items()):
        cat_s = cat_scores[selected_company][cat]
        cat_cols[i].metric(cat, f"{cat_s:.0f} / 100",
                           delta="Strong" if cat_s >= 65 else ("Average" if cat_s >= 45 else "Weak"),
                           delta_color="normal" if cat_s >= 65 else ("off" if cat_s >= 45 else "inverse"))

    st.divider()

    # Ratio breakdown table
    st.markdown("**All 15 Ratios — Value vs Percentile**")

    ratio_rows = []
    for cat, ratios in CATEGORIES.items():
        for rn in ratios:
            val = all_ratios[selected_company].get(rn)
            pct = pct_scores[selected_company].get(rn, 50)
            wt  = RATIO_WEIGHTS[rn]

            if pct >= 75:   status = "🟢 Strong"
            elif pct >= 50: status = "🟡 Average"
            else:           status = "🔴 Weak"

            ratio_rows.append({
                "Category": cat,
                "Ratio": rn,
                "Value": round(val, 2) if val is not None else "N/A",
                "Percentile": pct,
                "Weight": f"{int(wt*100)}%",
                "Status": status,
            })

    df_ratios = pd.DataFrame(ratio_rows)
    st.dataframe(
        df_ratios.style.background_gradient(subset=["Percentile"], cmap="RdYlGn", vmin=10, vmax=90),
        use_container_width=True, hide_index=True
    )

    # Strengths & weaknesses
    sorted_ratios = sorted(ratio_rows, key=lambda x: x["Percentile"] if isinstance(x["Percentile"], (int,float)) else 50)
    strengths = [r for r in sorted_ratios if isinstance(r["Percentile"], (int,float)) and r["Percentile"] >= 70][-3:]
    weaknesses = [r for r in sorted_ratios if isinstance(r["Percentile"], (int,float)) and r["Percentile"] < 50][:3]

    if strengths or weaknesses:
        col_s, col_w = st.columns(2)
        with col_s:
            st.markdown("**Top Strengths**")
            for r in reversed(strengths):
                st.success(f"**{r['Ratio']}** — {r['Value']} ({r['Percentile']:.0f}th percentile)")
        with col_w:
            st.markdown("**Areas to Watch**")
            for r in weaknesses:
                st.warning(f"**{r['Ratio']}** — {r['Value']} ({r['Percentile']:.0f}th percentile)")

    # vs Sector average comparison
    st.divider()
    st.markdown("**How does this company compare to sector averages?**")

    compare_rows = []
    for rn in list(RATIO_WEIGHTS.keys()):
        all_vals = [all_ratios[c].get(rn) for c in AUTO_COMPANIES if all_ratios[c].get(rn) is not None]
        company_val = all_ratios[selected_company].get(rn)
        if all_vals and company_val is not None:
            sector_avg = round(sum(all_vals)/len(all_vals), 2)
            diff = round(float(company_val) - sector_avg, 2)
            compare_rows.append({
                "Ratio": rn,
                f"{selected_short}": round(float(company_val), 2),
                "Sector Avg": sector_avg,
                "Difference": diff,
            })

    if compare_rows:
        df_compare = pd.DataFrame(compare_rows)
        st.dataframe(
            df_compare.style.background_gradient(subset=["Difference"], cmap="RdYlGn"),
            use_container_width=True, hide_index=True
        )


# ════════════════════════════════════════════════════════
# TAB 4 — METHODOLOGY
# ════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-hdr">How the Excellence Score Is Calculated</div>', unsafe_allow_html=True)

    st.markdown("""
    **Step 1 — Data Collection**
    Raw financial data is pulled from PostgreSQL for each company: P&L (sales, net profit, EBITDA, interest, depreciation)
    and Balance Sheet (equity, borrowings, assets, receivables, inventory).

    **Step 2 — 15 Ratios Calculated**
    Each ratio is computed from scratch from raw data (not pre-stored ratios) to ensure accuracy and consistency across companies.

    **Step 3 — Percentile Ranking**
    Each company is ranked against all 20 peers on each ratio. A percentile of 80 means the company outperforms 80% of its peers on that metric.
    This approach normalises for sector differences — a tyre manufacturer and a 2-wheeler OEM have very different absolute margins,
    but percentile scoring puts them on the same playing field.

    **Step 4 — Weighted Score**
    Each percentile score is multiplied by its category weight. The sum is the Excellence Score (0–100).
    """)

    st.divider()
    st.markdown("**Category Weights**")

    cat_rows = []
    for cat, ratios in CATEGORIES.items():
        total_w = sum(RATIO_WEIGHTS[r] for r in ratios)
        cat_rows.append({
            "Category": cat,
            "Ratios": ", ".join(ratios),
            "Total Weight": f"{int(total_w*100)}%",
            "Rationale": {
                "Profitability": "Core earnings quality — the most critical measure of business health",
                "Growth":        "Revenue and profit momentum — rewards compounding businesses",
                "Efficiency":    "Asset utilisation — companies squeezing more from their base",
                "Safety":        "Balance sheet strength — floor for financial risk",
            }[cat]
        })
    st.dataframe(pd.DataFrame(cat_rows), use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("**Ratio Weights**")

    wt_rows = [{"Ratio": r, "Category": cat, "Weight": f"{int(w*100)}%", "Higher is Better": "✅" if HIGHER_BETTER[r] else "❌ (lower is better)"}
               for cat, ratios in CATEGORIES.items() for r in ratios
               for w in [RATIO_WEIGHTS[r]]]
    st.dataframe(pd.DataFrame(wt_rows), use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("**Score Tiers**")
    tier_data = [
        {"Range": "85–100", "Tier": "Excellence Leader",  "Meaning": "Top-tier performance across most metrics — sector benchmark"},
        {"Range": "70–84",  "Tier": "High Performer",     "Meaning": "Consistently strong, outperforms majority of peers"},
        {"Range": "55–69",  "Tier": "Above Average",      "Meaning": "Solid business with identifiable strengths"},
        {"Range": "40–54",  "Tier": "Average",            "Meaning": "Mixed performance, in line with sector middle"},
        {"Range": "25–39",  "Tier": "Below Average",      "Meaning": "Notable weaknesses dragging overall score"},
        {"Range": "0–24",   "Tier": "Needs Improvement",  "Meaning": "Multiple areas of concern across categories"},
    ]
    st.dataframe(pd.DataFrame(tier_data), use_container_width=True, hide_index=True)

    st.caption("Data source: BSE/NSE filings via Screener.in · Stored in PostgreSQL · FY ending March 2025")