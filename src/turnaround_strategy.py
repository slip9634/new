"""
Monday-weakness -> Wednesday-exit mean reversion ("Turnaround Tuesday"-style),
plus IBS and SMA180 filter variants, plus stop-loss variants.

Rule (fixed core, per the brief):
  Monday close < previous Friday close  ->  buy at Monday close
  Exit at Wednesday close (or the next available bar if Wednesday is a
  holiday, capped at the bar before the next Monday so trades never overlap).

This is a same-day EOD-decision strategy (a well-known simplification in this
literature, distinct from the bar-lagged crypto engine in backtest.py): the
entry uses Monday's own fully-realized close, which is standard for this
class of strategy but still a modeling assumption, not free-money certainty
-- a live version would need to trade very near the close.

IBS = (Close - Low) / (High - Low) for the Monday bar itself (how the entry
bar closed relative to its own range -- the classic definition).

All filters and stop levels are applied identically across markets so the
robustness matrix is apples-to-apples.
"""
import numpy as np
import pandas as pd


def add_ibs(df: pd.DataFrame) -> pd.Series:
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    return ((df["close"] - df["low"]) / rng).fillna(0.5)


def add_sma(df: pd.DataFrame, period: int) -> pd.Series:
    return df["close"].rolling(period).mean()


FILTERS = {
    "A_none": lambda df: pd.Series(True, index=df.index),
    "B_ibs_lt_0.5": lambda df: df["ibs"] < 0.5,
    "C_ibs_lt_0.3": lambda df: df["ibs"] < 0.3,
    "D_ibs_lt_0.2": lambda df: df["ibs"] < 0.2,
    "E_close_lt_sma180": lambda df: df["close"] < df["sma180"],
    "F_ibs_lt_0.2_and_close_lt_sma180": lambda df: (df["ibs"] < 0.2) & (df["close"] < df["sma180"]),
    "G_close_gt_sma180_control": lambda df: df["close"] > df["sma180"],
}

STOP_LEVELS = {"no_stop": None, "stop_2pct": 0.02, "stop_5pct": 0.05, "stop_10pct": 0.10}


def find_trades(df: pd.DataFrame, filter_mask: pd.Series, stop_pct: float | None, fee_round_trip: float) -> pd.DataFrame:
    """df must be a daily OHLC frame, UTC/naive datetime index, sorted ascending,
    with a 'weekday' column (Monday=0). Returns one row per trade."""
    idx = df.index
    weekday = df["weekday"].values
    close = df["close"].values
    low = df["low"].values
    n = len(df)

    monday_prev_friday_down = df["prev_friday_down"].values
    mask = filter_mask.values

    trades = []
    i = 0
    while i < n:
        is_entry = (weekday[i] == 0) and monday_prev_friday_down[i] and mask[i] and not np.isnan(close[i])
        if not is_entry:
            i += 1
            continue

        entry_i = i
        entry_price = close[entry_i]
        entry_date = idx[entry_i]

        # find exit: first Wednesday after entry, else last bar before next Monday
        j = entry_i + 1
        exit_i = None
        while j < n and weekday[j] != 0:  # stop scanning once we hit the next Monday
            if weekday[j] == 2:
                exit_i = j
                break
            j += 1
        if exit_i is None:
            # Wednesday missing (holiday) -> exit at last bar before next Monday
            exit_i = j - 1 if j > entry_i + 1 else entry_i + 1
            if exit_i >= n:
                break  # no data left to exit on, drop this dangling trade

        # check stop breach on any bar strictly after entry, up to exit_i
        stop_price = entry_price * (1 - stop_pct) if stop_pct else None
        actual_exit_i = exit_i
        exit_price = close[exit_i]
        exit_reason = "wednesday"
        if stop_price is not None:
            for k in range(entry_i + 1, exit_i + 1):
                if low[k] <= stop_price:
                    actual_exit_i = k
                    exit_price = stop_price
                    exit_reason = "stop"
                    break

        gross_ret = exit_price / entry_price - 1
        net_ret = gross_ret - fee_round_trip
        trades.append({
            "entry_date": entry_date, "exit_date": idx[actual_exit_i],
            "entry_price": entry_price, "exit_price": exit_price,
            "hold_days": actual_exit_i - entry_i, "return": net_ret,
            "exit_reason": exit_reason,
        })
        i = actual_exit_i + 1  # never overlap trades

    return pd.DataFrame(trades)


def prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["weekday"] = df.index.weekday
    df["ibs"] = add_ibs(df)
    df["sma180"] = add_sma(df, 180)
    # ffilled Friday close: on any row, the most recent Friday's close on or
    # before that row. On a Monday row this is exactly "the previous Friday
    # close" (skipping back further if that Friday itself was a holiday).
    friday_close = df["close"].where(df["weekday"] == 4).ffill()
    df["prev_friday_down"] = False
    monday_mask = df["weekday"] == 0
    df.loc[monday_mask, "prev_friday_down"] = (
        df.loc[monday_mask, "close"] < friday_close.loc[monday_mask]
    )
    df["prev_friday_down"] = df["prev_friday_down"].fillna(False)
    return df
