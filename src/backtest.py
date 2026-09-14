"""
Core backtest engine.

No-lookahead contract:
  - `signal[t]` (produced by a strategy function) may only use information
    available up to and including the close of bar t.
  - This engine ALWAYS lags the signal by one full bar (`shift(1)`) before
    multiplying it by that bar's return. In practice this means: a decision
    made using bar t's close is executed at bar t+1's open/close, and the
    P&L booked for bar t+1 uses bar t's decision, never bar t+1's own data.
  - Transaction costs are charged on every unit of position CHANGE (turnover),
    at the bar where the change takes effect, priced at the one-way fee.

This mirrors how a live bar-close strategy actually trades: you can't react to
a candle until it closes, and the earliest you can be filled is on the next one.
"""
import numpy as np
import pandas as pd


def run_backtest(df: pd.DataFrame, signal: pd.Series, fee: float = 0.0006) -> dict:
    close = df["close"]
    bar_return = close.pct_change()

    position = signal.shift(1).fillna(0)  # <-- the no-lookahead lag
    turnover = position.diff().abs().fillna(position.abs())  # first bar: entering from flat

    strategy_return = position * bar_return - turnover * fee

    n_trades = int((position.diff().fillna(position) != 0).sum())

    return {
        "returns": strategy_return,
        "position": position,
        "turnover": turnover,
        "n_trades": n_trades,
        "equity": (1 + strategy_return.fillna(0)).cumprod(),
    }
