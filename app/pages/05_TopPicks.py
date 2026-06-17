import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from scripts.db_connect import get_engine

st.set_page_config(page_title="Top Picks", page_icon="🏆", layout="wide")
st.title("🏆 Top Picks — Industry Leaders")
st.caption("Ranked by benchmark score across all sectors")

engine = get_engine()

# --- Controls ---
col1, col2 = st.columns([2, 1])
with col1:
    metric = st.selectbox("Rank by", [
        "total_score", "roe", "roce", "net_margin",
        "revenue_growth", "cagr_3y", "cagr_5y"
    ], format_func=lambda x: {
        "total_score":     "Overall Benchmark Score",
        "roe":             "ROE (Return on Equity)",
        "roce":            "ROCE (Return on Capital Employed)",
        "net_margin":      "Net Profit Margin",
        "revenue_growth":  "Revenue Growth (YoY)",
        "cagr_3y":         "3-Year Revenue CAGR",
        "cagr_5y":         "5-Year Revenue CAGR"
    }[x])
with col2:
    top_n = st.slider("Show top", 5, 20, 10)

# --- Query ---
with engine.connect() as conn:
    df = pd.read_sql(text("""
        SELECT
            c.company_name,
            s.sector_name,
            bs.total_score,
            bs.industry_rank,
            fr.roe,
            fr.roce,
            fr.net_margin,
            fr.revenue_growth,
            fr.cagr_3y,
            fr.cagr_5y,
            fr.debt_to_equity
        FROM benchmark_scores bs
        JOIN companies c ON bs.company_id = c.company_id
        JOIN sectors s ON c.sector_id = s.sector_id
        JOIN financial_ratios fr ON fr.company_id = bs.company_id
            AND fr.quarter = bs.quarter
        WHERE bs.quarter = (
            SELECT quarter FROM benchmark_scores ORDER BY computed_at DESC LIMIT 1
        )
        ORDER BY bs.total_score DESC
    """), conn)

if df.empty:
    st.warning("No benchmark data found. Run engine/benchmark_engine.py first.")
    st.stop()

# --- Sort + slice ---
df_sorted = df.sort_values(metric, ascending=False).head(top_n).reset_index(drop=True)
df_sorted.index += 1  # rank starts at 1

# --- Score label helper ---
def score_label(score):
    if score >= 80: return "🥇 Industry Leader"
    elif score >= 60: return "🟢 Above Average"
    elif score >= 40: return "🟡 Average"
    elif score >= 20: return "🟠 Below Average"
    else: return "🔴 Needs Attention"

# --- Leaderboard table ---
st.subheader(f"Top {top_n} Companies")
display_df = df_sorted[["company_name", "sector_name", "total_score",
                         "roe", "roce", "net_margin", "revenue_growth"]].copy()
display_df.columns = ["Company", "Sector", "Score", "ROE%", "ROCE%", "Net Margin%", "Rev Growth%"]
display_df["Rating"] = display_df["Score"].apply(score_label)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=False,
    column_config={
        "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"),
    }
)

# --- Bar chart ---
st.subheader("📊 Visual Ranking")
metric_label = {
    "total_score": "Benchmark Score",
    "roe": "ROE (%)", "roce": "ROCE (%)",
    "net_margin": "Net Margin (%)", "revenue_growth": "Revenue Growth (%)",
    "cagr_3y": "3Y CAGR (%)", "cagr_5y": "5Y CAGR (%)"
}[metric]

fig = px.bar(
    df_sorted,
    x=metric,
    y="company_name",
    color="sector_name",
    orientation="h",
    labels={metric: metric_label, "company_name": "", "sector_name": "Sector"},
    title=f"Top {top_n} by {metric_label}",
    height=450
)
fig.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig, use_container_width=True)

# --- Sector breakdown ---
st.subheader("🗂️ By Sector")
sector_cols = st.columns(len(df_sorted["sector_name"].unique()))
for i, (sector, group) in enumerate(df_sorted.groupby("sector_name")):
    with sector_cols[i % len(sector_cols)]:
        st.markdown(f"**{sector}**")
        for _, row in group.iterrows():
            st.markdown(f"- {row['company_name']} ({row['total_score']:.0f})")