import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
import sys
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')
from scripts.db_connect import get_engine

st.set_page_config(page_title="Company Financials", page_icon="📊", layout="wide")
st.title("📊 Deep Financial Analysis")
st.caption("P&L, Balance Sheet and Cash Flow — 10 years of data")

engine = get_engine()

# ── Helper functions ──────────────────────────────────────────────────────────
def safe_cr(val):
    """Format value as crores safely — returns N/A if None"""
    try:
        return f"₹{float(val):,.0f} Cr" if val is not None else "N/A"
    except:
        return "N/A"

def safe_delta(curr, prev):
    """Calculate percentage change safely"""
    try:
        if curr is not None and prev is not None and float(prev) != 0:
            return f"{((float(curr) - float(prev)) / float(prev) * 100):.1f}%"
    except:
        pass
    return None

def to_float(val):
    """Convert to float safely — returns 0 if None"""
    try:
        return float(val) if val is not None else 0
    except:
        return 0

def to_numeric_series(series):
    """Convert pandas series to numeric safely"""
    return pd.to_numeric(series, errors='coerce')

# ── Company selector ──────────────────────────────────────────────────────────
with engine.connect() as conn:
    companies = pd.read_sql(text("""
        SELECT c.company_name, s.sector_name
        FROM companies c
        JOIN sectors s ON c.sector_id = s.sector_id
        ORDER BY c.company_name
    """), conn)

selected = st.selectbox("Select Company", companies["company_name"].tolist())
sector = companies[companies["company_name"] == selected]["sector_name"].values[0]
st.caption(f"Sector: {sector}")

# ── Load all data ─────────────────────────────────────────────────────────────
with engine.connect() as conn:
    pl = pd.read_sql(text("""
        SELECT pl.* FROM profit_loss pl
        JOIN companies c ON pl.company_id = c.company_id
        WHERE c.company_name = :name
        ORDER BY pl.fiscal_year
    """), conn, params={"name": selected})

    bs = pd.read_sql(text("""
        SELECT bs.* FROM balance_sheet bs
        JOIN companies c ON bs.company_id = c.company_id
        WHERE c.company_name = :name
        ORDER BY bs.fiscal_year
    """), conn, params={"name": selected})

    cf = pd.read_sql(text("""
        SELECT cf.* FROM cash_flow cf
        JOIN companies c ON cf.company_id = c.company_id
        WHERE c.company_name = :name
        ORDER BY cf.fiscal_year
    """), conn, params={"name": selected})

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📈 P&L Statement", "🏦 Balance Sheet", "💵 Cash Flow"])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: P&L Statement
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    if pl.empty:
        st.warning("No P&L data found for this company.")
    else:
        latest = pl.iloc[-1]
        prev   = pl.iloc[-2] if len(pl) > 1 else latest

        # Key metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Revenue",
                  safe_cr(latest['sales']),
                  safe_delta(latest['sales'], prev['sales']))
        c2.metric("Net Profit",
                  safe_cr(latest['net_profit']),
                  safe_delta(latest['net_profit'], prev['net_profit']))
        c3.metric("Interest",     safe_cr(latest['interest']))
        c4.metric("Depreciation", safe_cr(latest['depreciation']))

        st.divider()

        # Revenue vs Net Profit trend
        st.subheader("Revenue vs Net Profit Trend")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=pl["fiscal_year"],
            y=to_numeric_series(pl["sales"]),
            name="Revenue",
            marker_color="#3498db"
        ))
        fig.add_trace(go.Bar(
            x=pl["fiscal_year"],
            y=to_numeric_series(pl["net_profit"]),
            name="Net Profit",
            marker_color="#2ecc71"
        ))
        fig.update_layout(barmode="group", height=400, plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

        # Expense breakdown pie chart
        st.subheader("Expense Breakdown (Latest Year)")
        exp_data = {
            "Raw Material":  to_float(latest.get("raw_material")),
            "Employee Cost": to_float(latest.get("employee_cost")),
            "Depreciation":  to_float(latest.get("depreciation")),
            "Interest":      to_float(latest.get("interest")),
            "Tax":           to_float(latest.get("tax")),
        }
        exp_df = pd.DataFrame(list(exp_data.items()), columns=["Expense", "Amount"])
        exp_df = exp_df[exp_df["Amount"] > 0]

        if not exp_df.empty:
            fig2 = px.pie(
                exp_df,
                values="Amount",
                names="Expense",
                title=f"Cost Structure — {latest['fiscal_year']}",
                hole=0.4
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No expense breakdown data available.")

        # Full P&L table
        st.subheader("Full P&L Table (₹ Crores)")
        display_cols = ["fiscal_year", "sales", "raw_material", "employee_cost",
                        "depreciation", "interest", "profit_before_tax",
                        "tax", "net_profit"]
        display_cols = [c for c in display_cols if c in pl.columns]
        st.dataframe(
            pl[display_cols].set_index("fiscal_year").T,
            use_container_width=True
        )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: Balance Sheet
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    if bs.empty:
        st.warning("No Balance Sheet data found for this company.")
    else:
        latest_bs = bs.iloc[-1]
        prev_bs   = bs.iloc[-2] if len(bs) > 1 else latest_bs

        # Key metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Assets",
                  safe_cr(latest_bs['total_assets']))
        c2.metric("Borrowings",
                  safe_cr(latest_bs['borrowings']),
                  safe_delta(latest_bs['borrowings'], prev_bs['borrowings']))
        c3.metric("Reserves",
                  safe_cr(latest_bs['reserves']))
        c4.metric("Cash & Bank",
                  safe_cr(latest_bs['cash_and_bank']))

        st.divider()

        # Assets composition over time
        st.subheader("Assets Composition Over Time")
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=bs["fiscal_year"],
            y=to_numeric_series(bs["net_block"]),
            name="Net Block",
            fill="tonexty",
            line=dict(color="#3498db")
        ))
        fig3.add_trace(go.Scatter(
            x=bs["fiscal_year"],
            y=to_numeric_series(bs["investments"]),
            name="Investments",
            fill="tonexty",
            line=dict(color="#2ecc71")
        ))
        fig3.add_trace(go.Scatter(
            x=bs["fiscal_year"],
            y=to_numeric_series(bs["cash_and_bank"]),
            name="Cash & Bank",
            fill="tonexty",
            line=dict(color="#f39c12")
        ))
        fig3.update_layout(height=400, plot_bgcolor="white")
        st.plotly_chart(fig3, use_container_width=True)

        # Debt vs Equity trend
        st.subheader("Debt vs Equity Trend")
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(
            x=bs["fiscal_year"],
            y=to_numeric_series(bs["reserves"]),
            name="Reserves",
            marker_color="#2ecc71"
        ))
        fig4.add_trace(go.Bar(
            x=bs["fiscal_year"],
            y=to_numeric_series(bs["borrowings"]),
            name="Borrowings",
            marker_color="#e74c3c"
        ))
        fig4.update_layout(barmode="group", height=350, plot_bgcolor="white")
        st.plotly_chart(fig4, use_container_width=True)

        # Full Balance Sheet table
        st.subheader("Full Balance Sheet (₹ Crores)")
        display_bs = ["fiscal_year", "equity_capital", "reserves", "borrowings",
                      "other_liabilities", "total_assets", "net_block",
                      "investments", "receivables", "inventory", "cash_and_bank"]
        display_bs = [c for c in display_bs if c in bs.columns]
        st.dataframe(
            bs[display_bs].set_index("fiscal_year").T,
            use_container_width=True
        )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: Cash Flow
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    if cf.empty:
        st.warning("No Cash Flow data found for this company.")
    else:
        latest_cf = cf.iloc[-1]

        # Key metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Operating CF",  safe_cr(latest_cf['operating_cf']))
        c2.metric("Investing CF",  safe_cr(latest_cf['investing_cf']))
        c3.metric("Financing CF",  safe_cr(latest_cf['financing_cf']))
        c4.metric("Net Cash Flow", safe_cr(latest_cf['net_cash_flow']))

        st.divider()

        # Cash Flow trend chart
        st.subheader("Cash Flow Trend")
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(
            x=cf["fiscal_year"],
            y=to_numeric_series(cf["operating_cf"]),
            name="Operating",
            marker_color="#3498db"
        ))
        fig5.add_trace(go.Bar(
            x=cf["fiscal_year"],
            y=to_numeric_series(cf["investing_cf"]),
            name="Investing",
            marker_color="#e74c3c"
        ))
        fig5.add_trace(go.Bar(
            x=cf["fiscal_year"],
            y=to_numeric_series(cf["financing_cf"]),
            name="Financing",
            marker_color="#f39c12"
        ))
        fig5.update_layout(barmode="group", height=400, plot_bgcolor="white")
        st.plotly_chart(fig5, use_container_width=True)

        # Cash Flow health check
        st.subheader("Cash Flow Health Check")
        h1, h2, h3 = st.columns(3)

        ocf = to_float(latest_cf['operating_cf'])
        icf = to_float(latest_cf['investing_cf'])
        fcf = to_float(latest_cf['financing_cf'])

        h1.metric(
            "Operating CF",
            "✅ Positive" if ocf > 0 else "❌ Negative",
            f"₹{ocf:,.0f} Cr"
        )
        h2.metric(
            "Investing CF",
            "✅ Investing in growth" if icf < 0 else "⚠️ Divesting assets",
            f"₹{icf:,.0f} Cr"
        )
        h3.metric(
            "Financing CF",
            "⚠️ Taking on debt" if fcf > 0 else "✅ Repaying debt",
            f"₹{fcf:,.0f} Cr"
        )

        # Full Cash Flow table
        st.divider()
        st.subheader("Full Cash Flow Table (₹ Crores)")
        cf_display = ["fiscal_year", "operating_cf", "investing_cf",
                      "financing_cf", "net_cash_flow"]
        cf_display = [c for c in cf_display if c in cf.columns]
        st.dataframe(
            cf[cf_display].set_index("fiscal_year").T,
            use_container_width=True
        )