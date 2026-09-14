"""Performance metrics for backtest return series. Crypto trades 24/7/365."""
import numpy as np
import pandas as pd

BARS_PER_YEAR = {
    "5m": 365 * 24 * 60 / 5,
    "15m": 365 * 24 * 60 / 15,
    "1h": 365 * 24,
    "5h": 365 * 24 / 5,
    "1d": 365,
}


def compute_performance(strategy_returns: pd.Series, timeframe: str, n_trades: int = None) -> dict:
    r = strategy_returns.dropna()
    if len(r) == 0 or r.std() == 0:
        out = {"n_bars": len(r), "cagr": np.nan, "sharpe": np.nan, "max_dd": np.nan,
               "calmar": np.nan, "vol_ann": np.nan, "total_return": np.nan}
        if n_trades is not None:
            out["n_trades"] = n_trades
            out["trades_per_year"] = np.nan
        return out
    freq = BARS_PER_YEAR[timeframe]
    equity = (1 + r).cumprod()
    years = len(r) / freq
    total_return = equity.iloc[-1] - 1
    cagr = equity.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan
    vol_ann = r.std() * np.sqrt(freq)
    sharpe = (r.mean() * freq) / vol_ann if vol_ann > 0 else np.nan
    running_max = equity.cummax()
    dd = equity / running_max - 1
    max_dd = dd.min()
    calmar = cagr / abs(max_dd) if max_dd < 0 else np.nan
    out = {
        "n_bars": len(r),
        "years": years,
        "total_return": total_return,
        "cagr": cagr,
        "vol_ann": vol_ann,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "calmar": calmar,
    }
    if n_trades is not None:
        out["n_trades"] = n_trades
        out["trades_per_year"] = n_trades / years if years > 0 else np.nan
    return out
