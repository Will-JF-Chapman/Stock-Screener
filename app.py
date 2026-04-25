import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
#used to save excel file temporarily
import tempfile, os
from analytics import fetch_data, compute_metrics, correlation_matrix, screen
from export import export_report

#set browser page title, icon, and to use the whole screen
st.set_page_config(
    page_title="Stock Screener & Portfolio Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
  [data-testid="stSidebar"] { background: #0d1b2a; }
  [data-testid="stSidebar"] * { color: #e0e8f0 !important; }
  .metric-card {
    background: linear-gradient(135deg, #1e3a5f, #0d1b2a);
    border: 1px solid #2d5a8e;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
    color: white;
  }
  .metric-card .val { font-size: 1.8rem; font-weight: 700; color: #4fc3f7; }
  .metric-card .lbl { font-size: 0.78rem; color: #90caf9; letter-spacing: .05em; text-transform: uppercase; }
  h1 { color: #1565c0 !important; }
  h2, h3 { color: #1565c0 !important; }
  [data-testid="stToolbar"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

#track the state of analysis
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
#initialize data if not fetched yet
if "prices" not in st.session_state:
    st.session_state.prices = None
if "metrics" not in st.session_state:
    st.session_state.metrics = None
if "corr" not in st.session_state:
    st.session_state.corr = None
if "screened" not in st.session_state:
    st.session_state.screened = None
if "valid_tickers" not in st.session_state:
    st.session_state.valid_tickers = []
if "weights" not in st.session_state:
    st.session_state.weights = {}
if "risk_free" not in st.session_state:
    st.session_state.risk_free = 0.05

#sidebar creations
with st.sidebar:
    #title and divider
    st.markdown("## 📈")
    st.title("⚙️ Configuration")
    st.markdown("---")

    #tickers with defaults
    st.subheader("📋 Watchlist")
    default_tickers = "AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, JPM, JNJ, BRK-B"
    ticker_input = st.text_area("Tickers (comma-separated)", value=default_tickers, height=100)
    tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

    st.subheader("📅 Time Period")
    period = st.selectbox("Historical Period", ["6mo", "1y", "2y", "3y", "5y"], index=2)

    st.subheader("💼 Portfolio Weights")
    #if the user has selected to weigh all stocks equally
    equal_weight = st.checkbox("Equal-weight portfolio", value=True)
    if equal_weight:
        weights = {t: 1 / len(tickers) for t in tickers}
        st.caption(f"Each stock weighted at {1/len(tickers):.1%}")
    else:
        st.caption("Set custom weights below. They will be normalized to sum to 100%.")
        raw_weights = {}
        for t in tickers:
            raw_weights[t] = st.slider(t, 0, 100, 10, 1)

        #if the user's total weights is above or below 100, normalize them
        total_raw = sum(raw_weights.values()) or 1
        weights = {t: v / total_raw for t, v in raw_weights.items()}

        st.caption(f"Total input: {sum(raw_weights.values())}% → normalized to 100%")

    #user's selected filters
    ########################################################################
    st.subheader("🔍 Screening Filters")

    use_sharpe = st.checkbox("Sharpe Ratio ≥", value=True)
    if use_sharpe:
        sharpe_min = st.slider("Min Sharpe", 0.0, 3.0, 1.0, 0.1)
    else:
        sharpe_min = None

    use_beta = st.checkbox("Beta ≤", value=False)
    if use_beta:
        beta_max = st.slider("Max Beta", 0.1, 2.5, 1.2, 0.1)
    else:
        beta_max = None

    use_vol = st.checkbox("Volatility ≤", value=False)
    if use_vol:
        vol_max = st.slider("Max Volatility", 0.05, 0.80, 0.35, 0.01)
    else:
        vol_max = None

    use_ret = st.checkbox("Ann. Return ≥", value=False)
    if use_ret:
        return_min = st.slider("Min Return", -0.20, 0.80, 0.10, 0.01)
    else:
        return_min = None
    
    st.subheader("⚠️ Risk-Free Rate")
    risk_free = st.slider("Risk-Free Rate (%)", 0.0, 8.0, 5.0, 0.25) / 100

    ########################################################################

    run = st.button("🚀 Run Analysis", use_container_width=True, type="primary")

#main area
st.title("📈 Stock Screener & Portfolio Analyzer")
st.caption("Real market data · Key metrics · Screening · Excel export")

#if the user ran analysis
if run:
    with st.spinner("📡 Fetching market data…"):
        try:
            prices = fetch_data(tickers, period=period)
        except Exception as e:
            st.error(f"Data fetch failed: {e}")
            st.stop()

    valid_tickers = [t for t in tickers if t in prices.columns]
    if not valid_tickers:
        st.error("No valid tickers found. Check your symbols.")
        st.stop()
    if len(valid_tickers) < len(tickers):
        missing = set(tickers) - set(valid_tickers)
        st.warning(f"Could not fetch data for: {', '.join(missing)}")

    #only keep valid tickers, discard unvalid tickers then renormalize
    valid_weights = {t: weights[t] for t in valid_tickers if t in weights}
    total_w = sum(valid_weights.values()) or 1
    weights = {t: v / total_w for t, v in valid_weights.items()}

    #compute tickers that passed screening, correlation matrix, and metrics
    with st.spinner("🔢 Computing metrics…"):
        metrics = compute_metrics(prices, valid_tickers, risk_free=risk_free)
        corr = correlation_matrix(prices, valid_tickers)
        screened = screen(metrics, sharpe_min=sharpe_min, beta_max=beta_max, vol_max=vol_max, return_min=return_min)

    #save everything to session state
    st.session_state.analysis_done = True
    st.session_state.prices = prices
    st.session_state.metrics = metrics
    st.session_state.corr = corr
    st.session_state.screened = screened
    st.session_state.valid_tickers = valid_tickers
    st.session_state.weights = weights
    st.session_state.risk_free = risk_free

#explain analysis tool to user if analysis not ran yet
if not st.session_state.analysis_done:
    st.info("👈 Configure your watchlist and filters in the sidebar, then click **Run Analysis**.")
    st.markdown("""
    **What this app does:**
    - Fetches live historical prices via `yfinance`
    - Computes **Sharpe ratio**, **Beta** vs S&P 500, **annualized return**, **volatility**, and **max drawdown**
    - Builds a **correlation matrix** across your stocks
    - Interactive charts: price history, risk/return scatter, correlation heatmap, allocation pie
    - **Screening filter** — surface only stocks meeting your criteria
    - **One-click Excel export** with formatted multi-sheet report
    """)
    st.stop()

#retrieve from session state
prices = st.session_state.prices
metrics = st.session_state.metrics
corr = st.session_state.corr
screened = st.session_state.screened
valid_tickers = st.session_state.valid_tickers
weights = st.session_state.weights
risk_free = st.session_state.risk_free

#Portfolio overview cards
st.markdown("---")
st.subheader("📊 Portfolio Overview")
cols = st.columns(5)

#price changes every single trading day for every ticket
port_rets = prices[valid_tickers].pct_change().dropna()
#daily changes every single day multiplied for corressponding weight then summed
port_ret_series = (port_rets * pd.Series(weights)).sum(axis=1)
#annual return calculated from portfolio gains
port_ann_ret = float((1 + port_ret_series).prod() ** (252 / len(port_ret_series)) - 1)
#portfolio returns volatility
port_vol = float(port_ret_series.std() * np.sqrt(252))
#sharpe value of the portfolio
port_sharpe = (port_ann_ret - risk_free) / port_vol if port_vol else 0
#'best' item with the highest sharp ratio in the portfolio
best = metrics["Sharpe Ratio"].idxmax()
#how many stocks passed the screening process
pass_count = len(screened)

#initial stats on the portfolio
kpis = [
    ("Portfolio Return", f"{port_ann_ret:.1%}"),
    ("Portfolio Volatility", f"{port_vol:.1%}"),
    ("Portfolio Sharpe", f"{port_sharpe:.2f}"),
    ("Best Sharpe", f"{best} ({metrics.loc[best,'Sharpe Ratio']:.2f})"),
    ("Stocks Passing", f"{pass_count} / {len(valid_tickers)}"),
]
#create columns for each of the child graphs/tables
for col, (lbl, val) in zip(cols, kpis):
    col.markdown(
        f"""<div class="metric-card"><div class="val">{val}</div><div class="lbl">{lbl}</div></div>""",
        unsafe_allow_html=True
    )

#tabs for the child graphs/tables
st.markdown("---")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Metrics & Screening", "📈 Price History", "🎯 Risk / Return", "🗺️ Correlation", "🥧 Allocation"])

#Tab 1: Metrics Table
with tab1:
    st.subheader("Stock Metrics & Screening Results")
    #paste the table of stock metrics, but add a column to display if a individual stock passed the screening
    display = metrics.copy()
    display.index.name = "Ticker"
    display["Pass"] = display.index.map(lambda t: "✅ Pass" if t in screened.index else "❌ Fail")

    #format columns in the table to two decimal points
    fmt_cols = {
        "Ann. Return": "{:.2%}",
        "Volatility": "{:.2%}",
        "Sharpe Ratio": "{:.2f}",
        "Beta": "{:.2f}",
        "Max Drawdown": "{:.2%}",
    }
    styled = display.style.format(fmt_cols)

    def color_pass(v):
        if v == "✅ Pass":
            return "color: #2e7d32; font-weight: bold"
        return "color: #c62828; font-weight: bold"

    styled = styled.map(color_pass, subset=["Pass"])
    st.dataframe(styled, use_container_width=True)

    if len(screened) > 0:
        st.success(f"**{len(screened)} stock(s) passed your filters:** {', '.join(screened.index.tolist())}")
    else:
        st.warning("No stocks passed the current screening filters. Try relaxing them.")

#Tab 2: Price History
with tab2:
    st.subheader("Normalized Price History (Base = 100)")
    #Normalize 100*current_price/old_price
    norm = (prices[valid_tickers].dropna() / prices[valid_tickers].dropna().iloc[0]) * 100
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    for i, t in enumerate(valid_tickers):
        #add one line to chart per ticker, y is the normalized value, x is the date
        fig.add_trace(go.Scatter(
            x=norm.index, y=norm[t], name=t,
            line=dict(width=2, color=colors[i % len(colors)]),
            hovertemplate=f"<b>{t}</b>: %{{y:.1f}}<extra></extra>"
        ))
    #apply constant background color on the graph and display all ticket normalized prices once the user hovers over the graph
    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(20,20,20,0.85)",
            bordercolor="rgba(255,255,255,0.2)",
            font=dict(size=11, color="white", family="monospace"),
            namelength=-1,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        xaxis_title="Date", yaxis_title="Indexed Price (Base=100)",
        height=520, margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("30-Day Rolling Returns")
    #calculate 30 day rolling average then annualize
    rolling = prices[valid_tickers].pct_change().rolling(30).mean() * 252
    #now add a new line where the y values are each tickers rolling return over the last 30 days
    fig2 = go.Figure()
    for i, t in enumerate(valid_tickers):
        fig2.add_trace(go.Scatter(
            x=rolling.index, y=rolling[t], name=t,
            line=dict(width=1.5, color=colors[i % len(colors)]),
            hovertemplate=f"<b>{t}</b>: %{{y:.1%}}<extra></extra>"
        ))
    fig2.add_hline(y=0, line_dash="dot", line_color="gray")
    #add hover as in previous graph
    fig2.update_layout(
        template="plotly_white",
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(20,20,20,0.85)",
            bordercolor="rgba(255,255,255,0.2)",
            font=dict(size=11, color="white", family="monospace"),
            namelength=-1,
        ),
        xaxis_title="Date", yaxis_title="Annualized Rolling Return",
        yaxis_tickformat=".0%", height=480,
        legend=dict(orientation="h", y=1.01, x=0)
    )
    st.plotly_chart(fig2, use_container_width=True)

#Tab 3: Risk/Return Scatter
with tab3:
    st.subheader("Risk / Return Scatter Plot")
    scatter_df = metrics.reset_index()
    #create a column of all tickers screening process pass status
    scatter_df["Passed"] = scatter_df["Ticker"].isin(screened.index)
    #compute a column of all tickers size based on the sharp ratio
    scatter_df["size"] = scatter_df["Sharpe Ratio"].clip(lower=0) * 15 + 8

    #create a scatter plot with volatility (risk) on the x axis and annual return on the y axis
    fig3 = go.Figure()
    for passed, grp in scatter_df.groupby("Passed"):
        fig3.add_trace(go.Scatter(
            x=grp["Volatility"], y=grp["Ann. Return"],
            mode="markers+text",
            text=grp["Ticker"], textposition="top center",
            name="Pass" if passed else "Fail",
            marker=dict(
                size=grp["size"], color="#2196F3" if passed else "#EF5350",
                line=dict(width=1.5, color="white"), opacity=0.85
            ),
            hovertemplate="<b>%{text}</b><br>Return: %{y:.2%}<br>Volatility: %{x:.2%}<extra></extra>"
        ))
    fig3.update_layout(
        template="plotly_white",
        xaxis=dict(title="Annualized Volatility", tickformat=".0%"),
        yaxis=dict(title="Annualized Return", tickformat=".0%"),
        height=500, legend_title="Screening",
        shapes=[dict(
            type="line", x0=0, x1=scatter_df["Volatility"].max() * 1.1,
            y0=risk_free, y1=risk_free,
            line=dict(dash="dot", color="gray", width=1)
        )]
    )
    #label the risk free y value on the scatterplot
    fig3.add_annotation(
        x=scatter_df["Volatility"].min(), y=risk_free,
        text=f"Risk-Free Rate ({risk_free:.1%})", showarrow=False,
        yshift=10, font=dict(color="gray", size=10)
    )
    st.plotly_chart(fig3, use_container_width=True)

#Tab 4: Correlation
with tab4:
    st.subheader("Return Correlation Matrix")
    #create heatmap from correlation matrix corr
    fig4 = px.imshow(
        corr, text_auto=".2f", aspect="auto",
        color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
        labels=dict(color="Correlation")
    )
    fig4.update_traces(textfont_size=11)
    fig4.update_layout(height=500, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig4, use_container_width=True)
    st.caption("Values near +1 = highly correlated. Near 0 = uncorrelated. Near -1 = inversely correlated.")

#Tab 5: Allocation
with tab5:
    st.subheader("Portfolio Allocation")

    #retrieve original weights
    pie_labels = list(weights.keys())
    pie_vals = [weights[t] for t in pie_labels]

    #calculate change in prices
    valid_pie = [t for t in pie_labels if t in prices.columns]
    start_prices = prices[valid_pie].dropna().iloc[0]
    end_prices = prices[valid_pie].dropna().iloc[-1]
    growth = end_prices / start_prices

    #dollar value invested in each position at the start, based on a $100,000 portfolio
    start_vals = {t: weights.get(t, 0) * 100_000 for t in valid_pie}
    end_vals = {t: start_vals[t] * growth[t] for t in valid_pie}
    total_end = sum(end_vals.values())
    drifted_weights = {t: end_vals[t] / total_end for t in valid_pie}

    #intial portfolio with original pie values
    st.markdown("#### 🎯 Target Allocation")
    st.caption("Your intended portfolio weights as set in the sidebar.")
    c1, c2 = st.columns([1, 1])
    with c1:
        fig5 = go.Figure(go.Pie(
            labels=pie_labels, values=pie_vals,
            hole=0.45, textinfo="label+percent",
            marker=dict(colors=colors[:len(pie_labels)]),
            hovertemplate="<b>%{label}</b><br>Weight: %{percent}<extra></extra>"
        ))
        fig5.update_layout(
            showlegend=False,
            annotations=[dict(text="Target", x=0.5, y=0.5, font_size=14, showarrow=False)],
            height=400, margin=dict(l=0, r=0, t=20, b=0)
        )
        st.plotly_chart(fig5, use_container_width=True)
    #create a table reprsenting the original portfolios weights with values
    with c2:
        wt_df = pd.DataFrame({
            "Ticker": pie_labels,
            "Weight": [f"{v:.1%}" for v in pie_vals],
            "$ Value ($100k port)": [f"${v * 100_000:,.0f}" for v in pie_vals]
        })
        st.dataframe(wt_df.set_index("Ticker"), use_container_width=True)

    st.markdown("---")

    #drifted pie chart
    drift_labels = list(drifted_weights.keys())
    drift_vals = list(drifted_weights.values())
    st.markdown("#### 📈 Current Drifted Allocation")
    st.caption(f"Where your portfolio sits today if you invested $100,000 at the start and never rebalanced. Total value: ${total_end:,.0f}")
    d1, d2 = st.columns([1, 1])
    #create a pie chart with the drifted portfolio weights
    with d1:
        fig6 = go.Figure(go.Pie(
            labels=drift_labels, values=drift_vals,
            hole=0.45, textinfo="label+percent",
            marker=dict(colors=colors[:len(drift_labels)]),
            hovertemplate="<b>%{label}</b><br>Weight: %{percent}<extra></extra>"
        ))
        fig6.update_layout(
            showlegend=False,
            annotations=[dict(text="Today", x=0.5, y=0.5, font_size=14, showarrow=False)],
            height=400, margin=dict(l=0, r=0, t=20, b=0)
        )
        st.plotly_chart(fig6, use_container_width=True)
    #create a value displaying the drifted portfolios new weights, profit and value
    with d2:
        drift_df = pd.DataFrame({
            "Ticker": drift_labels,
            "Drifted Weight": [f"{v:.1%}" for v in drift_vals],
            "Current Value": [f"${end_vals[t]:,.0f}" for t in drift_labels],
            "Gain / Loss": [f"{'+ ' if end_vals[t] - start_vals[t] >= 0 else '- '}${abs(end_vals[t] - start_vals[t]):,.0f}" for t in drift_labels],
        })
        st.dataframe(drift_df.set_index("Ticker"), use_container_width=True)

#excel spreadsheet
st.markdown("---")
st.subheader("📥 Export Report to Excel")
#if the user wants a excel report
if st.button("Generate Excel Report", type="primary"):
    with st.spinner("Building Excel report…"):
        #compute drifted allocation for export
        valid_pie = [t for t in valid_tickers if t in prices.columns]
        start_prices = prices[valid_pie].dropna().iloc[0]
        end_prices = prices[valid_pie].dropna().iloc[-1]
        growth = end_prices / start_prices
        start_vals_exp = {t: weights.get(t, 0) * 100_000 for t in valid_pie}
        end_vals_exp = {t: start_vals_exp[t] * growth[t] for t in valid_pie}
        total_end_exp = sum(end_vals_exp.values())
        drifted_weights_exp = {t: end_vals_exp[t] / total_end_exp for t in valid_pie}

        #create a temporary microsoft excel spreadsheet
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            #send all relevant data to export.py to generate a report
            path = export_report(
                metrics=metrics, corr=corr, prices=prices,
                tickers=valid_tickers, weights=weights,
                output_path=tmp.name, screened=screened,
                end_vals=end_vals_exp, start_vals=start_vals_exp,
                drifted_weights=drifted_weights_exp, total_end=total_end_exp
            )
        #read from the report
        with open(path, "rb") as f:
            excel_data = f.read()
        os.unlink(path)
    #on click, give the user stock_report.xlsx which has the date from our excel report
    st.download_button(
        label="⬇️ Download stock_report.xlsx",
        data=excel_data,
        file_name="stock_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    st.success("Report ready! Click above to download.")