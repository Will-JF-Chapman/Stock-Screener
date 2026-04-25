# Stock Screener & Portfolio Analyzer

A stock analysis web app built with Python and Streamlit. Pulls real market data from Yahoo Finance and gives you metrics, charts, screening tools, and a formatted Excel report — all in one place.

---

## Files

| File | Description |
|------|-------------|
| `app.py` | Streamlit web app — main entry point |
| `analytics.py` | Data fetching and financial metrics calculations |
| `export.py` | Excel report generator |

---

## Setup

### 1. Install dependencies

```bash
pip install yfinance pandas numpy matplotlib plotly streamlit openpyxl
```

### 2. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## What It Does

### Sidebar Configuration

Everything is configured from the sidebar before running analysis:

- **Watchlist** — enter any comma-separated list of ticker symbols (e.g. `AAPL, MSFT, TSLA`). Supports US stocks, ETFs, indices, and international tickers like `TASE.TA`. Non-US tickers with different trading calendars are handled via forward-filling.
- **Historical Period** — choose from 6 months up to 5 years of data
- **Portfolio Weights** — toggle between equal-weight (automatic) or custom weights per ticker using sliders. Custom weights are automatically normalized to 100%.
- **Screening Filters** — optionally enable any combination of:
  - Sharpe Ratio ≥ threshold
  - Beta ≤ threshold
  - Volatility ≤ threshold
  - Annualized Return ≥ threshold
- **Risk-Free Rate** — configurable baseline rate used in Sharpe Ratio calculations, defaulting to 5%

Once configured, click **Run Analysis**. Results persist in session state so interacting with charts or exporting to Excel will not reset the analysis.

---

### Metrics Computed

For each ticker in your watchlist:

| Metric | Description |
|--------|-------------|
| **Annualized Return** | Compound annual growth rate over the selected period |
| **Volatility** | Annualized standard deviation of daily returns |
| **Sharpe Ratio** | Excess return above the risk-free rate per unit of volatility |
| **Beta** | Price sensitivity relative to the S&P 500 (`^GSPC`) |
| **Max Drawdown** | Largest peak-to-trough percentage decline over the period |

Portfolio-level metrics (weighted return, volatility, and Sharpe) are displayed at the top of the dashboard and reflect your chosen weights.

---

### Tabs

**Metrics & Screening** — table of all computed metrics with pass/fail badges based on your active screening filters. Passing stocks are highlighted in green, failing in red.

**Price History** — two charts:
- Normalized price history with all tickers indexed to 100 at the start of the period, making relative performance directly comparable across stocks
- 30-day rolling annualized returns showing momentum trends over time

**Risk / Return** — scatter plot with annualized volatility on the x-axis and annualized return on the y-axis. Each point is sized by Sharpe ratio. A dotted line marks the risk-free rate. Stocks that passed screening are shown in blue, failures in red.

**Correlation** — heatmap of pairwise return correlations across all tickers. Useful for assessing diversification — stocks with low or negative correlations reduce overall portfolio risk.

**Allocation** — two portfolio views:
- *Target Allocation* — your intended weights as configured in the sidebar, with dollar values based on a $100,000 portfolio
- *Current Drifted Allocation* — where the portfolio would actually sit today if you invested at the start of the period and never rebalanced, showing each position's current value and gain/loss in dollars

---

### Excel Report

Click **Generate Excel Report** to download a formatted `.xlsx` file. The report contains four sheets:

1. **Summary Metrics** — all tickers with their computed metrics and a Pass/Fail screening column, color-coded green and red
2. **Correlation Matrix** — the full pairwise correlation table, color-coded by strength (green for high positive, red for negative, dark blue on the diagonal)
3. **Portfolio** — two sections: Target Allocation (your intended weights and dollar values) and Current Drifted Allocation (actual current values, drifted weights, and gain/loss per position with totals)
4. **Price History** — full normalized price history for the selected period, one column per ticker

---

## Analytics Module (Standalone Use)

`analytics.py` can be imported and used independently of the Streamlit app:

```python
from analytics import fetch_data, compute_metrics, correlation_matrix, screen

# Fetch 2 years of price data
prices = fetch_data(["AAPL", "MSFT", "NVDA"], period="2y")

# Compute metrics with a 5% risk-free rate
metrics = compute_metrics(prices, ["AAPL", "MSFT", "NVDA"], risk_free=0.05)

# Filter to stocks with Sharpe >= 1.0 and Beta <= 1.2
passed = screen(metrics, sharpe_min=1.0, beta_max=1.2)
print(passed)
```

---

## Notes

- The S&P 500 (`^GSPC`) is always fetched internally as the market benchmark for Beta calculations. It can also be added to your watchlist as a regular ticker if you want to include it in your analysis.
- Normalized price history is indexed to 100 at the start of the selected period. The values shown are not actual stock prices — they represent percentage growth relative to the starting date.
- The drifted allocation assumes a lump-sum investment at the start of the period with no rebalancing, based purely on price returns.
