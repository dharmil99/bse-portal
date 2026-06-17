import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
import sys
sys.path.insert(0, r'C:\Users\Jignesh\Desktop\bse_portal')
from scripts.db_connect import get_engine

st.set_page_config(page_title="Company Search", page_icon="🔍", layout="wide")
st.title("🔍 Company Search & Deep Dive")

engine = get_engine()

# ── Helpers ───────────────────────────────────────────
def safe_cr(val):
    try:
        return f"₹{float(val):,.0f} Cr" if val is not None else "N/A"
    except:
        return "N/A"

def safe_pct(val):
    try:
        return f"{float(val):.1f}%" if val is not None else "N/A"
    except:
        return "N/A"

def safe_x(val):
    try:
        return f"{float(val):.2f}x" if val is not None else "N/A"
    except:
        return "N/A"

def to_float(val):
    try:
        return float(val) if val is not None else 0
    except:
        return 0

# ── Load company list ─────────────────────────────────
@st.cache_data
def get_companies():
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT c.company_name, c.bse_code, c.nse_symbol,
                   s.sector_name, c.market_cap
            FROM companies c
            JOIN sectors s ON c.sector_id = s.sector_id
            ORDER BY c.company_name
        """), conn)
    return df

companies_df = get_companies()

selected = st.selectbox(
    "Search for a company",
    options=[""] + companies_df["company_name"].tolist(),
    placeholder="Type company name..."
)

if not selected:
    st.info("Select a company above to see its complete financial profile.")
    st.stop()

# ── Load all data for selected company ────────────────
@st.cache_data
def load_company_data(name):
    with engine.connect() as conn:
        ratios = pd.read_sql(text("""
            SELECT r.* FROM financial_ratios r
            JOIN companies c ON r.company_id = c.company_id
            WHERE c.company_name = :n ORDER BY r.quarter
        """), conn, params={"n": name})

        results = pd.read_sql(text("""
            SELECT q.* FROM quarterly_results q
            JOIN companies c ON q.company_id = c.company_id
            WHERE c.company_name = :n ORDER BY q.period_end
        """), conn, params={"n": name})

        pl = pd.read_sql(text("""
            SELECT pl.* FROM profit_loss pl
            JOIN companies c ON pl.company_id = c.company_id
            WHERE c.company_name = :n ORDER BY pl.fiscal_year
        """), conn, params={"n": name})

        bs = pd.read_sql(text("""
            SELECT bs.* FROM balance_sheet bs
            JOIN companies c ON bs.company_id = c.company_id
            WHERE c.company_name = :n ORDER BY bs.fiscal_year
        """), conn, params={"n": name})

        cf = pd.read_sql(text("""
            SELECT cf.* FROM cash_flow cf
            JOIN companies c ON cf.company_id = c.company_id
            WHERE c.company_name = :n ORDER BY cf.fiscal_year
        """), conn, params={"n": name})

        score = conn.execute(text("""
            SELECT b.total_score, b.industry_rank, b.industry_percentile
            FROM benchmark_scores b
            JOIN companies c ON b.company_id = c.company_id
            WHERE c.company_name = :n
            ORDER BY b.computed_at DESC LIMIT 1
        """), {"n": name}).fetchone()

    return ratios, results, pl, bs, cf, score

ratios_df, results_df, pl_df, bs_df, cf_df, score_row = load_company_data(selected)
info = companies_df[companies_df["company_name"] == selected].iloc[0]

# ── Company Header ────────────────────────────────────
st.markdown("---")
h1, h2, h3, h4, h5 = st.columns(5)
h1.markdown(f"### {selected}")
h2.metric("BSE Code",    info['bse_code'])
h3.metric("NSE Symbol",  info['nse_symbol'])
h4.metric("Sector",      info['sector_name'])
h5.metric("Market Cap",  safe_cr(info['market_cap']))

# ── Benchmark Score ───────────────────────────────────
if score_row:
    score = to_float(score_row[0])
    rank  = score_row[1]
    if score >= 80:   label, color = "🏆 Industry Leader", "green"
    elif score >= 60: label, color = "✅ Above Average",   "green"
    elif score >= 40: label, color = "➡️ Average",         "orange"
    elif score >= 20: label, color = "⚠️ Below Average",   "orange"
    else:             label, color = "🔴 Needs Attention",  "red"

    st.markdown("---")
    st.subheader("🏆 Benchmark Score")
    s1, s2, s3 = st.columns(3)
    s1.metric("Score",       f"{score:.1f} / 100")
    s2.metric("Sector Rank", f"#{rank}")
    s3.metric("Rating",      label)

# ── TABS ──────────────────────────────────────────────
st.markdown("---")
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Key Ratios",
    "📈 Revenue & Profit",
    "⚙️ Efficiency",
    "🏦 Balance Sheet",
    "📅 Quarterly View"
])

# ─────────────────────────────────────────────────────
# TAB 1: Key Ratios
# ─────────────────────────────────────────────────────
with tab1:
    if ratios_df.empty:
        st.warning("No ratio data found.")
    else:
        latest_r = ratios_df[ratios_df['quarter'] == 'Q4FY25']
        if latest_r.empty:
            latest_r = ratios_df.iloc[[-1]]
        r = latest_r.iloc[0]

        st.subheader("Latest Financial Ratios (Q4FY25)")

        st.markdown("**Profitability**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("ROE %",          safe_pct(r['roe']))
        c2.metric("ROCE %",         safe_pct(r['roce']))
        c3.metric("Net Margin %",   safe_pct(r['net_margin']))
        c4.metric("EBITDA Margin %",safe_pct(r['ebitda_margin']))

        st.markdown("**Growth**")
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Revenue Growth %", safe_pct(r['revenue_growth']))
        g2.metric("3Y CAGR %",        safe_pct(r['cagr_3y']))
        g3.metric("5Y CAGR %",        safe_pct(r['cagr_5y']))
        g4.metric("PE Ratio",         safe_x(r['pe_ratio']))

        st.markdown("**Leverage**")
        l1, l2 = st.columns(4)[:2]
        l1.metric("Debt / Equity",  safe_x(r['debt_to_equity']))
        l2.metric("Benchmark Score",f"{to_float(score_row[0]):.1f}/100" if score_row else "N/A")

        st.divider()

        # ROE and ROCE trend
        st.subheader("ROE & ROCE Trend Over Years")
        ratio_trend = ratios_df[['quarter','roe','roce','net_margin']].copy()
        for col in ['roe','roce','net_margin']:
            ratio_trend[col] = pd.to_numeric(ratio_trend[col], errors='coerce')

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ratio_trend['quarter'], y=ratio_trend['roe'],
            name='ROE %', mode='lines+markers', line=dict(color='#3498db', width=2)))
        fig.add_trace(go.Scatter(
            x=ratio_trend['quarter'], y=ratio_trend['roce'],
            name='ROCE %', mode='lines+markers', line=dict(color='#2ecc71', width=2)))
        fig.add_trace(go.Scatter(
            x=ratio_trend['quarter'], y=ratio_trend['net_margin'],
            name='Net Margin %', mode='lines+markers', line=dict(color='#e74c3c', width=2)))
        fig.update_layout(height=400, plot_bgcolor='white',
                          xaxis_title='Quarter', yaxis_title='%')
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────
# TAB 2: Revenue & Profit
# ─────────────────────────────────────────────────────
with tab2:
    if pl_df.empty:
        st.warning("No P&L data found.")
    else:
        latest_pl = pl_df.iloc[-1]
        prev_pl   = pl_df.iloc[-2] if len(pl_df) > 1 else latest_pl

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Revenue",    safe_cr(latest_pl['sales']),
                  f"{((to_float(latest_pl['sales'])-to_float(prev_pl['sales']))/max(to_float(prev_pl['sales']),1)*100):.1f}%")
        c2.metric("Net Profit", safe_cr(latest_pl['net_profit']),
                  f"{((to_float(latest_pl['net_profit'])-to_float(prev_pl['net_profit']))/max(to_float(prev_pl['net_profit']),1)*100):.1f}%")
        c3.metric("Interest",     safe_cr(latest_pl['interest']))
        c4.metric("Depreciation", safe_cr(latest_pl['depreciation']))

        st.divider()

        # Revenue vs Net Profit bar
        st.subheader("Revenue vs Net Profit (10 Years)")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=pl_df['fiscal_year'],
            y=pd.to_numeric(pl_df['sales'], errors='coerce'),
            name='Revenue', marker_color='#3498db'))
        fig2.add_trace(go.Bar(
            x=pl_df['fiscal_year'],
            y=pd.to_numeric(pl_df['net_profit'], errors='coerce'),
            name='Net Profit', marker_color='#2ecc71'))
        fig2.update_layout(barmode='group', height=400, plot_bgcolor='white')
        st.plotly_chart(fig2, use_container_width=True)

        # Expense breakdown pie
        st.subheader("Cost Structure (Latest Year)")
        exp = {
            "Raw Material":  to_float(latest_pl.get('raw_material')),
            "Employee Cost": to_float(latest_pl.get('employee_cost')),
            "Depreciation":  to_float(latest_pl.get('depreciation')),
            "Interest":      to_float(latest_pl.get('interest')),
            "Tax":           to_float(latest_pl.get('tax')),
        }
        exp_df = pd.DataFrame(list(exp.items()), columns=['Item','Amount'])
        exp_df = exp_df[exp_df['Amount'] > 0]
        if not exp_df.empty:
            fig3 = px.pie(exp_df, values='Amount', names='Item',
                          hole=0.4, title=f"Cost Breakdown — {latest_pl['fiscal_year']}")
            st.plotly_chart(fig3, use_container_width=True)

# ─────────────────────────────────────────────────────
# TAB 3: Efficiency Ratios
# ─────────────────────────────────────────────────────
with tab3:
    st.subheader("Efficiency & Working Capital Analysis")

    if bs_df.empty or pl_df.empty:
        st.warning("Insufficient data for efficiency analysis.")
    else:
        # Merge P&L and BS for efficiency calculations
        merged = pd.merge(
            pl_df[['fiscal_year','sales','net_profit']],
            bs_df[['fiscal_year','receivables','inventory',
                   'borrowings','reserves','equity_capital',
                   'total_assets','cash_and_bank']],
            on='fiscal_year', how='inner'
        )

        for col in merged.columns:
            if col != 'fiscal_year':
                merged[col] = pd.to_numeric(merged[col], errors='coerce')

        # Calculate efficiency metrics
        merged['debtor_days'] = (
            merged['receivables'] / merged['sales'] * 365
        ).round(1)
        merged['inventory_days'] = (
            merged['inventory'] / merged['sales'] * 365
        ).round(1)
        merged['asset_turnover'] = (
            merged['sales'] / merged['total_assets']
        ).round(2)
        merged['working_capital'] = (
            merged['receivables'].fillna(0) +
            merged['inventory'].fillna(0) -
            merged['cash_and_bank'].fillna(0)
        ).round(0)

        # Latest values
        lm = merged.iloc[-1]
        pm = merged.iloc[-2] if len(merged) > 1 else lm

        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Debtor Days",
                  f"{lm['debtor_days']:.0f} days" if pd.notna(lm['debtor_days']) else "N/A",
                  f"{lm['debtor_days']-pm['debtor_days']:.0f} days" if pd.notna(lm['debtor_days']) else None)
        e2.metric("Inventory Days",
                  f"{lm['inventory_days']:.0f} days" if pd.notna(lm['inventory_days']) else "N/A")
        e3.metric("Asset Turnover",
                  safe_x(lm['asset_turnover']))
        e4.metric("Working Capital",
                  safe_cr(lm['working_capital']))

        st.divider()

        # Debtor Days trend
        st.subheader("Debtor Days Trend")
        st.caption("Lower is better — fewer days to collect payment from customers")
        fig4 = px.line(
            merged.dropna(subset=['debtor_days']),
            x='fiscal_year', y='debtor_days',
            markers=True,
            title='Debtor Days Over Years',
            labels={'debtor_days': 'Days', 'fiscal_year': 'Year'}
        )
        fig4.update_traces(line_color='#e74c3c', line_width=2)
        fig4.update_layout(height=350, plot_bgcolor='white')
        st.plotly_chart(fig4, use_container_width=True)

        # Asset Turnover trend
        st.subheader("Asset Turnover Trend")
        st.caption("Higher is better — more revenue generated per rupee of assets")
        fig5 = px.bar(
            merged.dropna(subset=['asset_turnover']),
            x='fiscal_year', y='asset_turnover',
            color='asset_turnover',
            color_continuous_scale='Blues',
            title='Asset Turnover Ratio',
            labels={'asset_turnover': 'Turnover (x)', 'fiscal_year': 'Year'}
        )
        fig5.update_layout(height=350, plot_bgcolor='white')
        st.plotly_chart(fig5, use_container_width=True)

        # Full efficiency table
        st.subheader("Efficiency Metrics Table")
        eff_display = merged[['fiscal_year','debtor_days',
                               'inventory_days','asset_turnover',
                               'working_capital']].copy()
        eff_display.columns = ['Year','Debtor Days',
                                'Inventory Days','Asset Turnover (x)',
                                'Working Capital (Cr)']
        st.dataframe(eff_display.set_index('Year').T,
                     use_container_width=True)

# ─────────────────────────────────────────────────────
# TAB 4: Balance Sheet Strength
# ─────────────────────────────────────────────────────
with tab4:
    if bs_df.empty:
        st.warning("No Balance Sheet data found.")
    else:
        for col in bs_df.columns:
            if col != 'fiscal_year':
                bs_df[col] = pd.to_numeric(bs_df[col], errors='coerce')

        latest_bs = bs_df.iloc[-1]
        prev_bs   = bs_df.iloc[-2] if len(bs_df) > 1 else latest_bs

        # Key BS metrics
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Total Assets",  safe_cr(latest_bs['total_assets']))
        b2.metric("Borrowings",    safe_cr(latest_bs['borrowings']),
                  f"{((to_float(latest_bs['borrowings'])-to_float(prev_bs['borrowings']))/max(to_float(prev_bs['borrowings']),1)*100):.1f}%")
        b3.metric("Reserves",      safe_cr(latest_bs['reserves']))
        b4.metric("Cash & Bank",   safe_cr(latest_bs['cash_and_bank']))

        st.divider()

        # Debt vs Equity vs Cash
        st.subheader("Debt vs Equity vs Cash Trend")
        fig6 = go.Figure()
        fig6.add_trace(go.Bar(
            x=bs_df['fiscal_year'],
            y=bs_df['reserves'],
            name='Reserves (Equity)', marker_color='#2ecc71'))
        fig6.add_trace(go.Bar(
            x=bs_df['fiscal_year'],
            y=bs_df['borrowings'],
            name='Borrowings (Debt)', marker_color='#e74c3c'))
        fig6.add_trace(go.Scatter(
            x=bs_df['fiscal_year'],
            y=bs_df['cash_and_bank'],
            name='Cash & Bank', mode='lines+markers',
            line=dict(color='#f39c12', width=3),
            yaxis='y2'))
        fig6.update_layout(
            barmode='group', height=420,
            plot_bgcolor='white',
            yaxis=dict(title='₹ Crores'),
            yaxis2=dict(title='Cash (₹ Cr)',
                        overlaying='y', side='right')
        )
        st.plotly_chart(fig6, use_container_width=True)

        # Cash flow if available
        if not cf_df.empty:
            st.divider()
            st.subheader("Cash Flow Summary")
            for col in ['operating_cf','investing_cf','financing_cf']:
                cf_df[col] = pd.to_numeric(cf_df[col], errors='coerce')

            latest_cf = cf_df.iloc[-1]
            cf1, cf2, cf3 = st.columns(3)
            ocf = to_float(latest_cf['operating_cf'])
            icf = to_float(latest_cf['investing_cf'])
            fcf = to_float(latest_cf['financing_cf'])

            cf1.metric("Operating CF",
                       "✅ Positive" if ocf > 0 else "❌ Negative",
                       f"₹{ocf:,.0f} Cr")
            cf2.metric("Investing CF",
                       "✅ Growing" if icf < 0 else "⚠️ Divesting",
                       f"₹{icf:,.0f} Cr")
            cf3.metric("Financing CF",
                       "⚠️ Borrowing" if fcf > 0 else "✅ Repaying",
                       f"₹{fcf:,.0f} Cr")

        # Full BS table
        st.divider()
        st.subheader("Full Balance Sheet (₹ Crores)")
        bs_show = ['fiscal_year','equity_capital','reserves','borrowings',
                   'total_assets','net_block','investments',
                   'receivables','inventory','cash_and_bank']
        bs_show = [c for c in bs_show if c in bs_df.columns]
        st.dataframe(bs_df[bs_show].set_index('fiscal_year').T,
                     use_container_width=True)

# ─────────────────────────────────────────────────────
# TAB 5: Quarterly View
# ─────────────────────────────────────────────────────
with tab5:
    st.subheader("Last 8 Quarters — Detailed View")

    if results_df.empty:
        st.warning("No quarterly data found.")
    else:
        for col in ['revenue','net_profit','ebitda','eps']:
            if col in results_df.columns:
                results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

        last8 = results_df.tail(8).copy()

        # Quarter-by-quarter metrics
        q1, q2, q3, q4 = st.columns(4)
        latest_q = last8.iloc[-1]
        prev_q   = last8.iloc[-2] if len(last8) > 1 else latest_q

        q1.metric("Revenue (Latest)",
                  safe_cr(latest_q['revenue']),
                  f"{((to_float(latest_q['revenue'])-to_float(prev_q['revenue']))/max(to_float(prev_q['revenue']),1)*100):.1f}% QoQ")
        q2.metric("Net Profit",
                  safe_cr(latest_q['net_profit']),
                  f"{((to_float(latest_q['net_profit'])-to_float(prev_q['net_profit']))/max(to_float(prev_q['net_profit']),1)*100):.1f}% QoQ")
        q3.metric("EBITDA",  safe_cr(latest_q['ebitda']))
        q4.metric("EPS",     f"₹{to_float(latest_q['eps']):.2f}")

        st.divider()

        # Quarterly Revenue trend
        st.subheader("Quarterly Revenue & Profit Trend")
        fig7 = go.Figure()
        fig7.add_trace(go.Bar(
            x=last8['quarter'], y=last8['revenue'],
            name='Revenue', marker_color='#3498db'))
        fig7.add_trace(go.Bar(
            x=last8['quarter'], y=last8['net_profit'],
            name='Net Profit', marker_color='#2ecc71'))
        fig7.update_layout(barmode='group', height=380,
                           plot_bgcolor='white')
        st.plotly_chart(fig7, use_container_width=True)

        # EPS trend
        st.subheader("EPS Trend (Last 8 Quarters)")
        fig8 = px.line(
            last8.dropna(subset=['eps']),
            x='quarter', y='eps',
            markers=True,
            title='Earnings Per Share (EPS) Trend',
            labels={'eps': '₹ per share', 'quarter': 'Quarter'}
        )
        fig8.update_traces(line_color='#9b59b6', line_width=2)
        fig8.update_layout(height=350, plot_bgcolor='white')
        st.plotly_chart(fig8, use_container_width=True)

        # Full quarterly table
        st.subheader("Quarterly Data Table (₹ Crores)")
        q_display = last8[['quarter','revenue','net_profit',
                            'ebitda','eps']].copy()
        q_display.columns = ['Quarter','Revenue','Net Profit','EBITDA','EPS']
        st.dataframe(
            q_display.set_index('Quarter').T,
            use_container_width=True
        )