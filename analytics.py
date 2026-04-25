
"""
numpy for math,
pandas for tables,
yfinance to import stock prices (yahoo finance)
"""
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

"""
Description:
function to fetch relevant data.

Expectes:
- A list of ticker strings
- A period of time
Returns:
- A pandas table
"""
def fetch_data(tickers: list[str], period: str = "2y") -> pd.DataFrame:
    #fetch raw data of all given tickers over [period] amount of time
    #need S&P500's ticker because it measures Beta
    all_tickers = list(set(tickers + ["^GSPC"]))
    raw = yf.download(all_tickers, period=period, auto_adjust=True, progress=False)

    #if yfinance returned multiticker format
    if isinstance(raw.columns, pd.MultiIndex):
        #extract all prices from close column hierarchy
        prices = raw["Close"]
    
    #if yfinance returned single flat table
    else:
        #extract all prices in 1 single prices column, rename header to single ticker name
        prices = raw[["Close"]]
        prices.columns = all_tickers
    
    #clean empty rows
    prices = prices.dropna(how="all")
    #fill empty prices with most recent value, them remove rows with missing values in any column
    prices = prices.ffill().dropna(how="any")
    return prices

#take table of daily price changes and calculate the percentage change
def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change().dropna()


def annualized_return(returns: pd.Series) -> float:
    #calculate total returns by converting daily changes from decimal -> percentage. Then multiply all together
    total = (1 + returns).prod()
    #calculate length of years
    n_years = len(returns) / 252
    #calculate per year growth by square rooting by inverse the number of years the ticker grew
    return float(total ** (1 / n_years) - 1)

#return the standard deviation of daily changes in a year
def annualized_volatility(returns: pd.Series) -> float:
    return float(returns.std() * np.sqrt(252))

#return sharpe ratio calculated from annual volatility and return
def sharpe_ratio(returns: pd.Series, risk_free: float = 0.05) -> float:
    ann_ret = annualized_return(returns)
    ann_vol = annualized_volatility(returns)
    #return undefined if dividing by 0
    if ann_vol == 0:
        return np.nan
    return (ann_ret - risk_free) / ann_vol

#Measures how a stock performs relative volatility to the S&p500, recieves both of their daily returns
def beta(stock_returns: pd.Series, market_returns: pd.Series) -> float:
    #concatenate both columns and drop blank values
    aligned = pd.concat([stock_returns, market_returns], axis=1).dropna()
    #compute the 2x2 covariance
    cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
    #return covariance between the stock and market dividedby the variance of the market
    return float(cov[0, 1] / cov[1, 1])

#compute percentage drop from each rolling peak to current price, then find the worst drop
def max_drawdown(prices: pd.Series) -> float:
    roll_max = prices.cummax()
    drawdown = (prices - roll_max) / roll_max
    return float(drawdown.min())


def compute_metrics(prices: pd.DataFrame, tickers: list[str], risk_free: float = 0.05) -> pd.DataFrame:
    
    #calculate daily returns
    rets = daily_returns(prices)

    #determine the market representative
    if "^GSPC" in rets.columns:
        market = rets["^GSPC"]
    else:
        market = None

    rows = []
    #iterate through all user's tickers
    for t in tickers:
        if t not in rets.columns:
            continue
        r = rets[t]
        p = prices[t].dropna()
        row = {
            "Ticker": t,
            "Ann. Return": annualized_return(r),
            "Volatility": annualized_volatility(r),
            "Sharpe Ratio": sharpe_ratio(r, risk_free),
            "Beta": beta(r, market) if market is not None else np.nan,
            "Max Drawdown": max_drawdown(p),
        }
        rows.append(row)
    #create a dataframe from the rows and make tickers the rows
    return pd.DataFrame(rows).set_index("Ticker")

#calculates the correlation between every pair of stocks
def correlation_matrix(prices: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    rets = daily_returns(prices[tickers].dropna())
    return rets.corr()

#recieves dataframe and the user's optional filters
def screen(metrics: pd.DataFrame, sharpe_min: float = None, beta_max: float = None, vol_max: float = None, return_min: float = None) -> pd.DataFrame:
    #initialize all masks as true, tests will prove them wrong
    mask = pd.Series(True, index=metrics.index)
    
    #compare all tickers against the users specified thresholds if not None, assign false if ticker fails test
    if sharpe_min is not None:
        mask &= metrics["Sharpe Ratio"] >= sharpe_min
    if beta_max is not None:
        mask &= metrics["Beta"] <= beta_max
    if vol_max is not None:
        mask &= metrics["Volatility"] <= vol_max
    if return_min is not None:
        mask &= metrics["Ann. Return"] >= return_min
        
    #return results
    return metrics[mask]