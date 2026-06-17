import streamlit as st
import pandas as pd
from sqlalchemy import text
import sys, os

sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal\app')
from scripts.db_connect import get_engine
from components.pdf_generator import generate_pdf_report

st.set_page_config(page_title="PDF Report", page_icon="📄", layout="wide")
st.title("📄 Download Company Report")
st.caption("Generate a professional benchmarking PDF for any BSE-listed company")

engine = get_engine()

with engine.connect() as conn:
    companies = pd.read_sql(text("""
        SELECT c.company_name, s.sector_name
        FROM companies c
        JOIN sectors s ON c.sector_id = s.sector_id
        ORDER BY c.company_name
    """), conn)

selected = st.selectbox("Select Company", companies["company_name"].tolist())

if selected:
    sector = companies[companies["company_name"] == selected]["sector_name"].values[0]

    with engine.connect() as conn:
        ratios_row = pd.read_sql(text("""
            SELECT fr.net_margin, fr.ebitda_margin, fr.roce,
                   fr.debt_to_equity, fr.roe
            FROM financial_ratios fr
            JOIN companies c ON fr.company_id = c.company_id
            WHERE c.company_name = :name
            ORDER BY fr.quarter DESC LIMIT 1
        """), conn, params={"name": selected})

        score_row = pd.read_sql(text("""
            SELECT bs.total_score, bs.industry_rank
            FROM benchmark_scores bs
            JOIN companies c ON bs.company_id = c.company_id
            WHERE c.company_name = :name
            ORDER BY bs.computed_at DESC LIMIT 1
        """), conn, params={"name": selected})

    if ratios_row.empty or score_row.empty:
        st.warning("No data found for this company.")
        st.stop()

    ratios = ratios_row.iloc[0].to_dict()
    score = float(score_row.iloc[0]["total_score"])

    if score >= 80:   label = "Industry Leader"
    elif score >= 60: label = "Above Average"
    elif score >= 40: label = "Average"
    elif score >= 20: label = "Below Average"
    else:             label = "Needs Attention"

    # Preview
    st.subheader(f"📊 Preview — {selected}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Benchmark Score", f"{score}/100")
    c2.metric("Rating", label)
    c3.metric("Net Margin", f"{ratios.get('net_margin', 'N/A')}%")
    c4.metric("ROCE", f"{ratios.get('roce', 'N/A')}%")

    st.divider()

    # Generate + Download
    if st.button("📄 Generate PDF Report"):
        with st.spinner("Generating PDF..."):
            pdf_buffer = generate_pdf_report(selected, sector, ratios, score, label)
        st.success("✅ PDF Ready!")
        st.download_button(
            label="⬇️ Download Report",
            data=pdf_buffer,
            file_name=f"{selected.replace(' ', '_')}_Report.pdf",
            mime="application/pdf"
        )