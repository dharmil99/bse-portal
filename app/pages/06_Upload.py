import streamlit as st
import pandas as pd
from sqlalchemy import text
import sys, os

# Fix import path
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')

from scripts.db_connect import get_engine
from etl.upload_handler import parse_upload, compute_benchmark_score

st.set_page_config(page_title="Upload & Benchmark", page_icon="📤", layout="wide")
st.title("📤 Upload Your Company Financials")
st.caption("Benchmark your company against BSE-listed sector peers instantly")

# --- Template download hint ---
with st.expander("📋 What format should my file be in?"):
    st.markdown("""
    Upload an **Excel (.xlsx) or CSV** file with these columns (amounts in ₹ Crores):

    | Revenue | EBITDA | Net Profit | Total Debt | Equity | Capital Employed |
    |---------|--------|------------|------------|--------|-----------------|
    | 5000    | 900    | 450        | 200        | 2000   | 2800            |

    - One row of data is enough
    - Column names must match exactly (case-insensitive)
    """)

    # Provide sample CSV for download
    sample = pd.DataFrame([{
        "Revenue": 5000, "EBITDA": 900, "Net Profit": 450,
        "Total Debt": 200, "Equity": 2000, "Capital Employed": 2800
    }])
    st.download_button("⬇️ Download Sample Template", sample.to_csv(index=False),
                       "sample_template.csv", "text/csv")

st.divider()

# --- Company info ---
col1, col2 = st.columns(2)
with col1:
    company_name = st.text_input("Your Company Name", placeholder="e.g. ABC Industries Ltd")
with col2:
    engine = get_engine()
    with engine.connect() as conn:
        sectors = pd.read_sql(text("SELECT sector_id, sector_name FROM sectors"), conn)
    sector_choice = st.selectbox("Select Your Sector", sectors["sector_name"].tolist())

uploaded_file = st.file_uploader("Upload Financials (Excel or CSV)", type=["xlsx", "csv"])

if uploaded_file and company_name:
    st.divider()
    data = parse_upload(uploaded_file)

    if "error" in data:
        st.error(f"❌ {data['error']}")
        st.stop()

    # --- Show computed ratios ---
    st.subheader(f"📊 Ratios for {company_name}")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Net Margin", f"{data['net_margin']}%")
    r2.metric("EBITDA Margin", f"{data['ebitda_margin']}%")
    r3.metric("ROCE", f"{data['roce']}%")
    r4.metric("Debt / Equity", f"{data['debt_to_equity']}x")

    # --- Fetch sector peers ---
    sector_id = sectors[sectors["sector_name"] == sector_choice]["sector_id"].values[0]
    with engine.connect() as conn:
        peer_df = pd.read_sql(text("""
            SELECT fr.net_margin, fr.roce, fr.debt_to_equity, fr.ebitda_margin
            FROM financial_ratios fr
            JOIN companies c ON fr.company_id = c.company_id
            WHERE c.sector_id = :sid
              AND fr.quarter = (SELECT quarter FROM benchmark_scores ORDER BY computed_at DESC LIMIT 1)
        """), conn, params={"sid": int(sector_id)})

    if peer_df.empty:
        st.warning("No peer data found for this sector.")
        st.stop()

    # --- Benchmark score ---
    scores = compute_benchmark_score(data, peer_df)

    st.divider()
    st.subheader("🏆 Your Benchmark Result")
    sc1, sc2 = st.columns(2)
    sc1.metric("Overall Score", f"{scores['total_score']} / 100")
    sc2.metric("Rating", scores["label"])

    # --- Peer comparison bar chart ---
    st.subheader(f"📈 You vs {sector_choice} Peers")
    compare_metrics = ["net_margin", "roce", "ebitda_margin"]
    rows = []
    for m in compare_metrics:
        if m in peer_df.columns:
            rows.append({"Metric": m.replace("_", " ").title(),
                         "Your Company": data[m],
                         "Sector Avg": round(peer_df[m].mean(), 2)})

    compare_df = pd.DataFrame(rows).set_index("Metric")
    st.bar_chart(compare_df)

    # --- Save to DB ---
    if st.button("💾 Save to Database"):
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO uploaded_companies
                  (company_name, sector_id, revenue, ebitda, net_profit,
                   total_debt, equity, capital_employed, fiscal_year)
                VALUES
                  (:name, :sid, :rev, :ebitda, :np, :td, :eq, :ce, '2025')
            """), {
                "name": company_name, "sid": int(sector_id),
                "rev": data["revenue"], "ebitda": data["ebitda"],
                "np": data["net_profit"], "td": data["total_debt"],
                "eq": data["equity"], "ce": data["capital_employed"]
            })
            conn.commit()
        st.success("✅ Saved successfully!")

elif uploaded_file and not company_name:
    st.warning("Please enter your company name above.")