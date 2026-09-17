"""
Generalizes the Monday->Wednesday rule to a full entry-weekday x exit-weekday
grid search (25 pairs, Monday=0..Friday=4), to test whether Wednesday is
actually the best exit day or just the one the literature happened to pick.

Entry condition, generalized from "Monday close < prior Friday close":
close on the chosen entry weekday < close on the immediately preceding
trading day (whatever weekday that is). Same-day EOD decision as the rest of
this project's weekday strategies (close is known before entering at that
same close) -- consistent modeling choice, not a new source of lookahead.

Validation: time-ordered 60/40 split per instrument (first 60% of its
available history = in-sample for picking the best pair by Sharpe with a
minimum trade count; last 40% = out-of-sample, evaluated once, frozen).
A 60/40 split is used (not the fixed-calendar IS/OOS split from the crypto
study) because these markets have wildly different data coverage -- a
split that's relative to each instrument's own history is the only one
that's fair across a 4-year IBKR window and a 26-year GitHub one alike.
"""
import numpy as np
import pandas as pd

WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri"]


def prep_generic(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["weekday"] = df.index.weekday
    df["down_day"] = df["close"] < df["close"].shift(1)
    return df


def find_trades_generic(df: pd.DataFrame, entry_weekday: int, exit_weekday: int,
                         stop_pct: float | None, fee_round_trip: float) -> pd.DataFrame:
    idx = df.index
    weekday = df["weekday"].values
    close = df["close"].values
    low = df["low"].values
    down = df["down_day"].values
    n = len(df)

    trades = []
    i = 0
    while i < n:
        if weekday[i] != entry_weekday or not down[i] or np.isnan(close[i]):
            i += 1
            continue
        entry_i = i
        entry_price = close[entry_i]

        j = entry_i + 1
        exit_i = None
        while j < n:
            if weekday[j] == exit_weekday:
                exit_i = j
                break
            j += 1
        if exit_i is None:
            break  # ran out of data before the exit weekday recurs

        stop_price = entry_price * (1 - stop_pct) if stop_pct else None
        actual_exit_i = exit_i
        exit_price = close[exit_i]
        if stop_price is not None:
            for k in range(entry_i + 1, exit_i + 1):
                if low[k] <= stop_price:
                    actual_exit_i = k
                    exit_price = stop_price
                    break

        net_ret = exit_price / entry_price - 1 - fee_round_trip
        trades.append({
            "entry_date": idx[entry_i], "exit_date": idx[actual_exit_i],
            "return": net_ret, "hold_days": (idx[actual_exit_i] - idx[entry_i]).days,
        })
        i = actual_exit_i + 1

    return pd.DataFrame(trades)


def split_is_oos(df: pd.DataFrame, is_frac: float = 0.6):
    cut = int(len(df) * is_frac)
    return df.iloc[:cut], df.iloc[cut:]


def sharpe_of(trades: pd.DataFrame, calendar_start, calendar_end) -> tuple[float, int]:
    if len(trades) == 0:
        return float("nan"), 0
    r = trades["return"].values
    n = len(r)
    years = (calendar_end - calendar_start).days / 365.25
    trades_per_year = n / years if years > 0 else np.nan
    std = r.std()
    sharpe = (r.mean() / std) * np.sqrt(trades_per_year) if std > 0 and trades_per_year > 0 else np.nan
    return sharpe, n


def optimize_market(name: str, df: pd.DataFrame, fee: float = 0.0004, min_is_trades: int = 15) -> dict:
    df = prep_generic(df)
    is_df, oos_df = split_is_oos(df)

    grid = []
    for entry_wd in range(5):
        for exit_wd in range(5):
            trades_is = find_trades_generic(is_df, entry_wd, exit_wd, None, fee)
            sharpe_is, n_is = sharpe_of(trades_is, is_df.index.min(), is_df.index.max())
            if n_is < min_is_trades or np.isnan(sharpe_is):
                continue
            grid.append({"entry_wd": entry_wd, "exit_wd": exit_wd, "is_sharpe": sharpe_is, "is_trades": n_is})

    if not grid:
        return {"market": name, "ok": False}

    grid.sort(key=lambda g: g["is_sharpe"], reverse=True)
    best = grid[0]

    trades_oos_best = find_trades_generic(oos_df, best["entry_wd"], best["exit_wd"], None, fee)
    oos_sharpe_best, n_oos_best = sharpe_of(trades_oos_best, oos_df.index.min(), oos_df.index.max())

    trades_oos_baseline = find_trades_generic(oos_df, 0, 2, None, fee)  # Monday->Wednesday
    oos_sharpe_baseline, n_oos_baseline = sharpe_of(trades_oos_baseline, oos_df.index.min(), oos_df.index.max())

    return {
        "market": name, "ok": True,
        "best_entry": WEEKDAY_NAMES[best["entry_wd"]], "best_exit": WEEKDAY_NAMES[best["exit_wd"]],
        "is_sharpe": round(best["is_sharpe"], 2), "is_trades": best["is_trades"],
        "oos_sharpe_best": round(oos_sharpe_best, 2) if not np.isnan(oos_sharpe_best) else None,
        "oos_trades_best": n_oos_best,
        "oos_sharpe_baseline_mon_wed": round(oos_sharpe_baseline, 2) if not np.isnan(oos_sharpe_baseline) else None,
        "oos_trades_baseline": n_oos_baseline,
        "is_start": is_df.index.min().date().isoformat(), "is_end": is_df.index.max().date().isoformat(),
        "oos_start": oos_df.index.min().date().isoformat(), "oos_end": oos_df.index.max().date().isoformat(),
        "full_grid": grid,
    }
