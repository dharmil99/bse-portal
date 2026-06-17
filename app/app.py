import streamlit as st

st.set_page_config(
    page_title="BSE Benchmarking Portal",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Business Benchmarking & Intelligence Platform")
st.subheader("Powered by Eelanos Analytics")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Companies Tracked", "21")
col2.metric("Sectors Covered", "5")
col3.metric("Years of Data", "10")
col4.metric("Ratios Calculated", "8")

st.markdown("---")
st.markdown("### 🚀 What would you like to do?")

c1, c2, c3 = st.columns(3)
with c1:
    st.info("🔍 **Search Company**\n\nFind any BSE company and see full financial profile with benchmark score")
with c2:
    st.info("📊 **Benchmark Chart**\n\nInteractive bubble chart comparing all companies in a sector")
with c3:
    st.info("⚖️ **Compare Peers**\n\nSide-by-side comparison of 2-5 companies")

st.markdown("---")
st.caption("Data sourced from BSE | Screener.in | Updated quarterly")