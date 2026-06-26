import streamlit as st
import pandas as pd
import sys
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')

from sqlalchemy import text
from scripts.db_connect import get_engine

st.set_page_config(page_title="Excellence Model", page_icon="🏆", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0D1117; }
[data-testid="stSidebar"] { background: #161B22; }
header[data-testid="stHeader"] { background: transparent; }
.em-title { font-family: Arial; font-size: 2rem; font-weight: 700; color: #E6EDF3; margin-bottom: 0; }
.em-subtitle { font-size: 0.95rem; color: #8B949E; margin-top: 4px; margin-bottom: 28px; }
.score-card { background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px 20px; margin-bottom: 10px; }
.score-card:hover { border-color: #58A6FF; }
.rank-badge { font-size: 0.72rem; font-weight: 700; color: #8B949E; text-transform: uppercase; letter-spacing: 1px; }
.company-name { font-size: 1.05rem; font-weight: 600; color: #E6EDF3; margin: 3px 0; }
.score-num { font-size: 1.6rem; font-weight: 700; font-family: monospace; }
.tier-pill { display: inline-block; font-size: 0.72rem; font-weight: 600; padding: 3px 10px; border-radius: 20px; margin-top: 4px; }
.prog-wrap { background: #21262D; border-radius: 4px; height: 6px; margin-top: 10px; overflow: hidden; }
.prog-fill { height: 6px; border-radius: 4px; }
.cat-row { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.cat-chip { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #30363D; color: #8B949E; }
.section-hdr { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: #58A6FF; margin: 28px 0 14px; padding-bottom: 6px; border-bottom: 1px solid #21262D; }
.sector-hdr { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 10px 16px; margin: 20px 0 10px; font-size: 1rem; font-weight: 700; color: #E6EDF3; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
RATIO_WEIGHTS = {
    "Net Profit Margin": 0.10, "EBITDA Margin": 0.10,
    "ROE": 0.08, "ROCE": 0.07, "Operating Profit Margin": 0.05,
    "Revenue Growth YoY": 0.10, "3Y Revenue CAGR": 0.08,
    "NP Growth YoY": 0.07, "Asset Turnover": 0.07,
    "Debtor Days": 0.05, "Inventory Turnover": 0.08,
    "Debt to Equity": 0.08, "Interest Coverage": 0.07,
    "EPS Growth YoY": 0.05, "Current Ratio": 0.05,
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

def safe_div(a, b, mult=1):
    try:
        if b and float(b) != 0:
            return round(float(a) / float(b) * mult, 2)
    except: pass
    return None

# ── Load all companies from DB ────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_all_data():
    engine = get_engine()

    # Get all companies with their sectors
    with engine.connect() as conn:
        companies_df = pd.read_sql(text("""
            SELECT c.company_id, c.company_name, s.sector_name
            FROM companies c
            JOIN sectors s ON c.sector_id = s.sector_id
            ORDER BY s.sector_name, c.company_name
        """), conn)

    all_companies = companies_df['company_name'].tolist()
    sector_map = dict(zip(companies_df['company_name'], companies_df['sector_name']))

    all_ratios = {}
    for _, row in companies_df.iterrows():
        company = row['company_name']
        cid = row['company_id']
        try:
            with engine.connect() as conn:
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
            ebitda   = (latest["net_profit"] or 0) + (latest["interest"] or 0) + (latest["depreciation"] or 0)
            equity   = (latest.get("equity_capital") or 0) + (latest.get("reserves") or 0)
            cap_emp  = equity + (latest.get("borrowings") or 0)
            ebit     = (latest["net_profit"] or 0) + (latest["interest"] or 0)

            r["Net Profit Margin"]       = safe_div(latest["net_profit"], latest["sales"], 100)
            r["EBITDA Margin"]           = safe_div(ebitda, latest["sales"], 100)
            r["ROE"]                     = safe_div(latest["net_profit"], equity, 100)
            r["ROCE"]                    = safe_div(ebit, cap_emp, 100)
            r["Operating Profit Margin"] = safe_div(ebitda, latest["sales"], 100)
            r["Revenue Growth YoY"]      = safe_div(latest["sales"] - prev["sales"], prev["sales"], 100)
            try:
                if old3["sales"] and float(old3["sales"]) != 0:
                    r["3Y Revenue CAGR"] = round(((float(latest["sales"]) / float(old3["sales"])) ** (1/3) - 1) * 100, 2)
                else: r["3Y Revenue CAGR"] = None
            except: r["3Y Revenue CAGR"] = None
            try:
                prev_np = float(prev["net_profit"]); curr_np = float(latest["net_profit"])
                r["NP Growth YoY"] = round((curr_np - prev_np) / abs(prev_np) * 100, 2) if prev_np != 0 else None
            except: r["NP Growth YoY"] = None
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
            r["Current Ratio"]      = safe_div(curr_assets, curr_liab) if curr_liab > 0 else None
            all_ratios[company] = r
        except Exception as e:
            all_ratios[company] = {}

    # Build sector groups
    sectors = {}
    for company in all_companies:
        sec = sector_map.get(company, "Unknown")
        sectors.setdefault(sec, []).append(company)

    # Calculate percentile scores PER SECTOR
    ratio_names = list(RATIO_WEIGHTS.keys())
    pct_scores  = {c: {} for c in all_companies}
    total_scores = {}
    cat_scores   = {}

    for sec, companies in sectors.items():
        if len(companies) < 2:
            for c in companies:
                for rn in ratio_names: pct_scores[c][rn] = 50
                total_scores[c] = 50.0
                cat_scores[c]   = {cat: 50.0 for cat in CATEGORIES}
            continue

        for rn in ratio_names:
            vals = [all_ratios[c].get(rn) for c in companies]
            valid = [v for v in vals if v is not None]
            for c in companies:
                val = all_ratios[c].get(rn)
                if val is None or not valid:
                    pct_scores[c][rn] = 50
                else:
                    if HIGHER_BETTER[rn]:
                        pct_scores[c][rn] = round(sum(1 for v in valid if v <= val) / len(valid) * 100, 1)
                    else:
                        pct_scores[c][rn] = round(sum(1 for v in valid if v >= val) / len(valid) * 100, 1)

        for c in companies:
            total_scores[c] = round(sum(pct_scores[c].get(r, 50) * w for r, w in RATIO_WEIGHTS.items()), 1)
            cat_scores[c]   = {}
            for cat, ratios in CATEGORIES.items():
                vals = [pct_scores[c].get(r, 50) for r in ratios]
                cat_scores[c][cat] = round(sum(vals) / len(vals), 1)

    # Also compute OVERALL cross-sector rankings
    overall_pct = {c: {} for c in all_companies}
    for rn in ratio_names:
        vals  = [all_ratios[c].get(rn) for c in all_companies]
        valid = [v for v in vals if v is not None]
        for c in all_companies:
            val = all_ratios[c].get(rn)
            if val is None or not valid:
                overall_pct[c][rn] = 50
            else:
                if HIGHER_BETTER[rn]:
                    overall_pct[c][rn] = round(sum(1 for v in valid if v <= val) / len(valid) * 100, 1)
                else:
                    overall_pct[c][rn] = round(sum(1 for v in valid if v >= val) / len(valid) * 100, 1)

    overall_scores = {c: round(sum(overall_pct[c].get(r, 50) * w for r, w in RATIO_WEIGHTS.items()), 1) for c in all_companies}
    overall_ranked = sorted(overall_scores.items(), key=lambda x: x[1], reverse=True)

    return all_companies, sector_map, sectors, all_ratios, pct_scores, total_scores, cat_scores, overall_ranked, overall_scores

# ── Load ──────────────────────────────────────────────────────────────────────
with st.spinner("Loading excellence scores for all sectors…"):
    all_companies, sector_map, sectors, all_ratios, pct_scores, total_scores, cat_scores, overall_ranked, overall_scores = load_all_data()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<p class="em-title">🏆 Excellence Model</p>', unsafe_allow_html=True)
n_sectors = len([s for s, c in sectors.items() if len(c) >= 2])
st.markdown(f'<p class="em-subtitle">All sectors · {len(all_companies)} companies · 15 ratios · Peer-relative scoring within each sector</p>', unsafe_allow_html=True)

# ── Top metrics ───────────────────────────────────────────────────────────────
top_co, top_sc = overall_ranked[0]
avg_sc = round(sum(overall_scores.values()) / len(overall_scores), 1)
leaders = sum(1 for _, s in overall_ranked if s >= 70)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Overall #1", top_co.replace(" Limited","").replace(" India",""), f"Score: {top_sc}")
m2.metric("Overall Average", f"{avg_sc} / 100")
m3.metric("High Performers", f"{leaders} companies", "Score ≥ 70 overall")
m4.metric("Total Companies", len(all_companies), f"{n_sectors} sectors")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📊 Sector Rankings", "🌍 Overall Rankings", "🔍 Company Deep Dive", "ℹ️ Methodology"])

# ════════════════════════════════════════════════════════
# TAB 1 — SECTOR RANKINGS
# ════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-hdr">Rankings within each sector</div>', unsafe_allow_html=True)

    sector_list = sorted([s for s, c in sectors.items() if len(c) >= 2])
    selected_sector = st.selectbox("Select sector", ["All Sectors"] + sector_list)

    sectors_to_show = sector_list if selected_sector == "All Sectors" else [selected_sector]

    for sec in sectors_to_show:
        companies_in_sec = sectors[sec]
        ranked_sec = sorted(companies_in_sec, key=lambda c: total_scores.get(c, 0), reverse=True)

        st.markdown(f'<div class="sector-hdr">🏭 {sec} &nbsp;·&nbsp; {len(companies_in_sec)} companies</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        for i, company in enumerate(ranked_sec):
            score = total_scores.get(company, 0)
            tier_label, tier_color, tier_bg = tier_info(score)
            short = company.replace(" Limited","").replace(" India","")
            medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(i+1, f"#{i+1}")

            cat_chips = "".join([
                f'<span class="cat-chip">{cat[:4]}: <b style="color:#E6EDF3">{cat_scores[company][cat]:.0f}</b></span>'
                for cat in ["Profitability","Growth","Efficiency","Safety"]
            ])

            card = f"""
            <div class="score-card">
                <div class="rank-badge">{medal} Rank {i+1}</div>
                <div class="company-name">{short}</div>
                <div style="display:flex;align-items:baseline;gap:8px;margin:6px 0">
                    <span class="score-num" style="color:{score_color(score)}">{score}</span>
                    <span class="tier-pill" style="background:{tier_bg};color:{tier_color}">{tier_label}</span>
                </div>
                <div class="prog-wrap"><div class="prog-fill" style="width:{score}%;background:{score_color(score)}"></div></div>
                <div class="cat-row">{cat_chips}</div>
            </div>"""

            if i % 2 == 0: c1.markdown(card, unsafe_allow_html=True)
            else:           c2.markdown(card, unsafe_allow_html=True)

        # Sector summary table
        with st.expander(f"📋 {sec} — Full table"):
            rows = []
            for i, c in enumerate(ranked_sec):
                tl, _, _ = tier_info(total_scores.get(c, 0))
                rows.append({
                    "Rank": i+1, "Company": c.replace(" Limited","").replace(" India",""),
                    "Score": total_scores.get(c, 0), "Tier": tl,
                    "Profitability": cat_scores[c]["Profitability"],
                    "Growth": cat_scores[c]["Growth"],
                    "Efficiency": cat_scores[c]["Efficiency"],
                    "Safety": cat_scores[c]["Safety"],
                })
            df = pd.DataFrame(rows)
            st.dataframe(df.style.background_gradient(
                subset=["Score","Profitability","Growth","Efficiency","Safety"],
                cmap="RdYlGn", vmin=20, vmax=90),
                use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════
# TAB 2 — OVERALL CROSS-SECTOR RANKINGS
# ════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-hdr">Overall rankings — all 42 companies, cross-sector comparison</div>', unsafe_allow_html=True)
    st.info("ℹ️ These scores rank all companies against each other regardless of sector. Sector rankings (Tab 1) are more fair for peer comparison.", icon="ℹ️")

    min_score = st.slider("Minimum score", 0, 90, 0, 5, key="overall_slider")
    filtered = [(c, s) for c, s in overall_ranked if s >= min_score]

    c1, c2 = st.columns(2)
    for i, (company, score) in enumerate(filtered):
        tier_label, tier_color, tier_bg = tier_info(score)
        short = company.replace(" Limited","").replace(" India","")
        sec   = sector_map.get(company, "")
        medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(i+1, f"#{i+1}")

        card = f"""
        <div class="score-card">
            <div class="rank-badge">{medal} Rank {i+1} &nbsp;·&nbsp; {sec}</div>
            <div class="company-name">{short}</div>
            <div style="display:flex;align-items:baseline;gap:8px;margin:6px 0">
                <span class="score-num" style="color:{score_color(score)}">{score}</span>
                <span class="tier-pill" style="background:{tier_bg};color:{tier_color}">{tier_label}</span>
            </div>
            <div class="prog-wrap"><div class="prog-fill" style="width:{score}%;background:{score_color(score)}"></div></div>
        </div>"""
        if i % 2 == 0: c1.markdown(card, unsafe_allow_html=True)
        else:           c2.markdown(card, unsafe_allow_html=True)

    # Full table
    st.markdown('<div class="section-hdr">Summary Table</div>', unsafe_allow_html=True)
    table_rows = []
    for i, (c, s) in enumerate(overall_ranked):
        tl, _, _ = tier_info(s)
        table_rows.append({
            "Rank": i+1,
            "Company": c.replace(" Limited","").replace(" India",""),
            "Sector": sector_map.get(c,""),
            "Overall Score": s,
            "Tier": tl,
        })
    st.dataframe(
        pd.DataFrame(table_rows).style.background_gradient(subset=["Overall Score"], cmap="RdYlGn", vmin=20, vmax=90),
        use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════
# TAB 3 — COMPANY DEEP DIVE
# ════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-hdr">Company Deep Dive</div>', unsafe_allow_html=True)

    # Group by sector for selectbox
    company_options = []
    for sec in sorted(sectors.keys()):
        for c in sorted(sectors[sec]):
            company_options.append(c)

    short_to_full = {c.replace(" Limited","").replace(" India",""): c for c in all_companies}
    display_options = [c.replace(" Limited","").replace(" India","") for c in company_options]

    selected_short = st.selectbox("Select company", display_options)
    selected_company = short_to_full.get(selected_short, selected_short)
    selected_sector  = sector_map.get(selected_company, "")
    sector_score     = total_scores.get(selected_company, 0)
    overall_score    = overall_scores.get(selected_company, 0)

    # Rank within sector
    sec_companies = sectors.get(selected_sector, [])
    sec_ranked    = sorted(sec_companies, key=lambda c: total_scores.get(c, 0), reverse=True)
    sec_rank      = next((i+1 for i, c in enumerate(sec_ranked) if c == selected_company), "-")
    overall_rank  = next((i+1 for i, (c,_) in enumerate(overall_ranked) if c == selected_company), "-")

    tier_label, tier_color_val, tier_bg_val = tier_info(sector_score)

    st.markdown(f"""
    <div class="score-card" style="border-color:{tier_color_val}; margin-bottom:20px">
        <div class="rank-badge">#{sec_rank} in {selected_sector} &nbsp;·&nbsp; #{overall_rank} Overall</div>
        <div class="company-name" style="font-size:1.4rem">{selected_short}</div>
        <div style="display:flex;align-items:baseline;gap:16px;margin:8px 0;flex-wrap:wrap">
            <div>
                <div style="font-size:0.7rem;color:#8B949E">SECTOR SCORE</div>
                <span class="score-num" style="color:{tier_color_val};font-size:2rem">{sector_score}</span>
            </div>
            <div>
                <div style="font-size:0.7rem;color:#8B949E">OVERALL SCORE</div>
                <span class="score-num" style="color:{score_color(overall_score)};font-size:2rem">{overall_score}</span>
            </div>
            <span class="tier-pill" style="background:{tier_bg_val};color:{tier_color_val};font-size:0.85rem;padding:5px 14px">{tier_label}</span>
        </div>
        <div class="prog-wrap" style="height:8px">
            <div class="prog-fill" style="width:{sector_score}%;background:{tier_color_val}"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Category scores
    st.markdown("**Category Breakdown (within sector)**")
    cat_cols = st.columns(4)
    for i, cat in enumerate(["Profitability","Growth","Efficiency","Safety"]):
        cs = cat_scores[selected_company][cat]
        delta = "Strong" if cs >= 65 else ("Average" if cs >= 45 else "Weak")
        cat_cols[i].metric(cat, f"{cs:.0f} / 100", delta=delta,
                           delta_color="normal" if cs >= 65 else ("off" if cs >= 45 else "inverse"))

    st.divider()

    # Ratio table
    st.markdown("**All 15 Ratios — Value vs Sector Percentile**")
    ratio_rows = []
    for cat, ratios in CATEGORIES.items():
        for rn in ratios:
            val = all_ratios[selected_company].get(rn)
            pct = pct_scores[selected_company].get(rn, 50)
            status = "🟢 Strong" if pct >= 75 else ("🟡 Average" if pct >= 50 else "🔴 Weak")
            ratio_rows.append({
                "Category": cat, "Ratio": rn,
                "Value": round(float(val), 2) if val is not None else "N/A",
                "Sector Percentile": pct, "Weight": f"{int(RATIO_WEIGHTS[rn]*100)}%",
                "Status": status,
            })
    df_r = pd.DataFrame(ratio_rows)
    st.dataframe(df_r.style.background_gradient(subset=["Sector Percentile"], cmap="RdYlGn", vmin=10, vmax=90),
                 use_container_width=True, hide_index=True)

    # Strengths & weaknesses
    sorted_r = sorted(ratio_rows, key=lambda x: x["Sector Percentile"] if isinstance(x["Sector Percentile"], (int,float)) else 50)
    strengths  = [r for r in sorted_r if isinstance(r["Sector Percentile"],(int,float)) and r["Sector Percentile"] >= 70][-3:]
    weaknesses = [r for r in sorted_r if isinstance(r["Sector Percentile"],(int,float)) and r["Sector Percentile"] < 50][:3]

    col_s, col_w = st.columns(2)
    with col_s:
        st.markdown("**Top Strengths**")
        for r in reversed(strengths):
            st.success(f"**{r['Ratio']}** — {r['Value']} ({r['Sector Percentile']:.0f}th percentile)")
    with col_w:
        st.markdown("**Areas to Watch**")
        for r in weaknesses:
            st.warning(f"**{r['Ratio']}** — {r['Value']} ({r['Sector Percentile']:.0f}th percentile)")

    # Sector peer comparison
    st.divider()
    st.markdown(f"**{selected_short} vs {selected_sector} sector peers**")
    peer_rows = []
    for peer in sec_ranked:
        ps = total_scores.get(peer, 0)
        tl, tc, _ = tier_info(ps)
        peer_rows.append({
            "Company": peer.replace(" Limited","").replace(" India",""),
            "Score": ps, "Tier": tl,
            "Profitability": cat_scores[peer]["Profitability"],
            "Growth": cat_scores[peer]["Growth"],
            "Efficiency": cat_scores[peer]["Efficiency"],
            "Safety": cat_scores[peer]["Safety"],
        })
    df_peer = pd.DataFrame(peer_rows)
    st.dataframe(df_peer.style.background_gradient(
        subset=["Score","Profitability","Growth","Efficiency","Safety"],
        cmap="RdYlGn", vmin=20, vmax=90),
        use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════
# TAB 4 — METHODOLOGY
# ════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-hdr">How the Excellence Score is Calculated</div>', unsafe_allow_html=True)

    st.markdown("""
    **Step 1 — Data Collection**
    Raw P&L and Balance Sheet data pulled from PostgreSQL for each company (latest FY).

    **Step 2 — 15 Ratios Calculated**
    Profitability, Growth, Efficiency and Safety ratios computed from scratch for every company.

    **Step 3 — Percentile Ranking (within sector)**
    Each company is ranked against its sector peers only. A score of 80 means the company beats 80% of peers in its sector on that metric.
    This keeps comparisons fair — an IT company is only ranked against other IT companies, not against a steel manufacturer.

    **Step 4 — Weighted Score**
    Each percentile score × its weight → sum = Excellence Score (0–100).

    **Overall Rankings (Tab 2)** rank all companies cross-sector — useful for spotting standout performers across the market.
    """)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Ratio Weights**")
        wt_rows = [{"Ratio": r, "Weight": f"{int(w*100)}%", "Higher is Better": "✅" if HIGHER_BETTER[r] else "❌"}
                   for r, w in RATIO_WEIGHTS.items()]
        st.dataframe(pd.DataFrame(wt_rows), use_container_width=True, hide_index=True)
    with col2:
        st.markdown("**Score Tiers**")
        tier_data = [
            {"Range": "85–100", "Tier": "Excellence Leader"},
            {"Range": "70–84",  "Tier": "High Performer"},
            {"Range": "55–69",  "Tier": "Above Average"},
            {"Range": "40–54",  "Tier": "Average"},
            {"Range": "25–39",  "Tier": "Below Average"},
            {"Range": "0–24",   "Tier": "Needs Improvement"},
        ]
        st.dataframe(pd.DataFrame(tier_data), use_container_width=True, hide_index=True)

    st.caption("Data: BSE/NSE filings via Screener.in · PostgreSQL · FY ending March 2025")