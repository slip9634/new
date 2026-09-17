"""
Weekend effect: buy Friday's open, sell the following Monday's open.

Two implementations here, because they need different bar granularity:

1. `find_weekend_trades()` -- the LITERAL rule, needs daily bars (Friday's own
   open and the next Monday's own open aren't recoverable from a weekly bar).
   Same no-lookahead discipline as turnaround_strategy.py: any filter must be
   computed from data available at or before the PRIOR close (Thursday),
   never from Friday's own high/low/close, since those aren't known yet at
   Friday's open when the entry actually happens.

2. `weekly_gap_returns()` -- a weekly-bar PROXY for the same idea (Friday
   close -> Monday open, not Friday open -> Monday open), used only to reach
   further back in history than IBKR's 1000-daily-bar cap allows. It is a
   different, related measure (skips Friday's own session), not the same
   number -- kept separate and labeled as such rather than blended in.
"""
import numpy as np
import pandas as pd


def find_weekend_trades(df: pd.DataFrame, filter_mask: pd.Series, stop_pct: float | None, fee_round_trip: float) -> pd.DataFrame:
    """df must have 'weekday' (Monday=0) and 'open'/'low' columns, sorted ascending.
    filter_mask must be computed from data no later than the bar BEFORE each Friday."""
    idx = df.index
    weekday = df["weekday"].values
    open_ = df["open"].values
    low = df["low"].values
    n = len(df)
    mask = filter_mask.values

    trades = []
    i = 0
    while i < n:
        if weekday[i] != 4 or not mask[i] or np.isnan(open_[i]):
            i += 1
            continue
        entry_i = i
        entry_price = open_[entry_i]
        j = entry_i + 1
        while j < n and weekday[j] != 0:
            j += 1
        if j >= n:
            break  # no following Monday in the data to exit on
        exit_i = j
        exit_price = open_[exit_i]
        exit_reason = "monday_open"

        if stop_pct:
            stop_price = entry_price * (1 - stop_pct)
            if low[entry_i] <= stop_price:  # only Friday's own remaining session can breach
                exit_price = stop_price
                exit_reason = "stop"

        gross_ret = exit_price / entry_price - 1
        net_ret = gross_ret - fee_round_trip
        trades.append({
            "entry_date": idx[entry_i], "exit_date": idx[exit_i],
            "entry_price": entry_price, "exit_price": exit_price,
            "return": net_ret, "exit_reason": exit_reason,
            "hold_days": (idx[exit_i] - idx[entry_i]).days,
        })
        i = exit_i + 1

    return pd.DataFrame(trades)


def prep_weekend(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["weekday"] = df.index.weekday
    df["sma180"] = df["close"].rolling(180).mean()
    # filters may only see data through the PRIOR bar (Thursday, for a Friday entry)
    df["prior_close"] = df["close"].shift(1)
    df["prior_sma180"] = df["sma180"].shift(1)
    return df


WEEKEND_FILTERS = {
    "A_none": lambda df: pd.Series(True, index=df.index),
    "E_prior_close_lt_sma180": lambda df: df["prior_close"] < df["prior_sma180"],
    "G_prior_close_gt_sma180_control": lambda df: df["prior_close"] > df["prior_sma180"],
}


def weekly_gap_returns(df: pd.DataFrame, fee_round_trip: float) -> pd.DataFrame:
    """Weekly-bar proxy: this week's close -> next week's open. df must have
    'close' and 'open' from consecutive IBKR weekly bars, sorted ascending."""
    close = df["close"]
    next_open = df["open"].shift(-1)
    next_date = pd.Series(df.index, index=df.index).shift(-1)
    gross = next_open / close - 1
    net = gross - fee_round_trip
    out = pd.DataFrame({
        "entry_date": df.index, "exit_date": next_date,
        "entry_price": close, "exit_price": next_open, "return": net,
        "hold_days": 0,  # weekend/holiday gap only -- no trading-day exposure
    }).dropna(subset=["return"])
    return out.reset_index(drop=True)
