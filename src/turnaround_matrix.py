"""
Robustness matrix for the Monday-weakness -> Wednesday-exit strategy across
markets, filters and stop levels.

Data sources (all verified real, fetched via raw.githubusercontent.com --
the only network path reachable from this sandbox; direct exchange/broker/
Yahoo/stooq/FRED APIs are all blocked here):
  - SPY: willhjw/big_movers "SPY Historical Data.csv" (2000-06-08 to 2025-09-23)
  - FTSE100, DAX30, Nasdaq100, EURUSD, GBPUSD:
    TheSnowGuru/Stocks-Futures-Financial-Time-series-Tick-Bar-Data (broker/CFD
    daily feed). Coverage is shorter than SPY's: index CFDs from 2013-05 to
    2023-09, FX from 2007-09 to 2023-09. This is NOT the full 2000-2026 window
    requested -- reported honestly per-market below, not stretched or faked.
  - BTC/USD: already in this repo (data/btcusd_1d.parquet), 2014-2025, added
    as a bonus real market (crypto trades every weekday too).

Cost assumption (not specified in the brief for equities/index/FX -- flagged
explicitly): 4bps round-trip as the "1x" cost proxy (spread + commission),
8bps as "2x". This is a modeling assumption, not observed data.
"""
import numpy as np
import pandas as pd

from turnaround_strategy import prep, find_trades, FILTERS, STOP_LEVELS

FEE_1X = 0.0004
FEE_2X = 0.0008

DATA_DIR = "/home/user/new/data/turnaround"


def load_spy() -> pd.DataFrame:
    df = pd.read_csv(f"{DATA_DIR}/spy_raw.csv")
    df.columns = [c.strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["datetime"], format="%m/%d/%Y")
    df = df.set_index("date").sort_index()
    return df[["open", "high", "low", "close", "volume"]]


def load_snowguru(name: str) -> pd.DataFrame:
    df = pd.read_csv(f"{DATA_DIR}/{name}_raw.csv", sep="\t")
    df.columns = [c.strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["time"])
    df = df.set_index("date").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df[["open", "high", "low", "close", "volume"]]


def load_btc() -> pd.DataFrame:
    df = pd.read_parquet("/home/user/new/data/btcusd_1d.parquet")
    df.index = pd.to_datetime(df.index, utc=True).tz_localize(None)
    return df.sort_index()[["open", "high", "low", "close", "volume"]]


MARKETS = {
    "SPY": load_spy,
    "FTSE100": lambda: load_snowguru("ftse100"),
    "DAX30": lambda: load_snowguru("dax30"),
    "Nasdaq100": lambda: load_snowguru("nasdaq100"),
    "EURUSD": lambda: load_snowguru("eurusd"),
    "GBPUSD": lambda: load_snowguru("gbpusd"),
    "BTCUSD": load_btc,
}


def trade_metrics(trades: pd.DataFrame, calendar_start: pd.Timestamp, calendar_end: pd.Timestamp) -> dict:
    if len(trades) == 0:
        return {"n_trades": 0}
    r = trades["return"].values
    n = len(r)
    win_rate = float((r > 0).mean())
    avg_trade = float(r.mean())
    gains = r[r > 0].sum()
    losses = -r[r < 0].sum()
    profit_factor = float(gains / losses) if losses > 0 else np.inf

    equity = np.cumprod(1 + r)
    running_max = np.maximum.accumulate(equity)
    dd = equity / running_max - 1
    max_dd = float(dd.min())

    years = (calendar_end - calendar_start).days / 365.25
    trades_per_year = n / years if years > 0 else np.nan
    cagr = float(equity[-1] ** (1 / years) - 1) if years > 0 and equity[-1] > 0 else np.nan

    std = r.std()
    sharpe = float((avg_trade / std) * np.sqrt(trades_per_year)) if std > 0 else np.nan
    downside = r[r < 0]
    down_std = downside.std() if len(downside) > 1 else np.nan
    sortino = float((avg_trade / down_std) * np.sqrt(trades_per_year)) if down_std and down_std > 0 else np.nan

    hold_days_total = trades["hold_days"].sum()
    exposure = float(hold_days_total / (calendar_end - calendar_start).days) if (calendar_end - calendar_start).days > 0 else np.nan

    worst_trade = float(r.min())
    years_series = trades["exit_date"].dt.year
    yearly = trades.groupby(years_series)["return"].apply(lambda x: np.prod(1 + x) - 1)
    worst_year = float(yearly.min()) if len(yearly) else np.nan

    return {
        "n_trades": n, "win_rate": win_rate, "avg_trade": avg_trade,
        "profit_factor": profit_factor, "cagr": cagr, "sharpe": sharpe,
        "sortino": sortino, "max_dd": max_dd, "exposure": exposure,
        "worst_trade": worst_trade, "worst_year": worst_year,
        "trades_per_year": trades_per_year,
    }


def sub_period_cagr(trades: pd.DataFrame, start: str, end: str) -> float:
    sub = trades[(trades["exit_date"] >= start) & (trades["exit_date"] <= end)]
    if len(sub) == 0:
        return np.nan
    r = sub["return"].values
    equity = np.prod(1 + r)
    years = (pd.Timestamp(end) - pd.Timestamp(start)).days / 365.25
    return float(equity ** (1 / years) - 1) if years > 0 else np.nan


def run_market(name: str, loader) -> pd.DataFrame:
    raw = loader()
    df = prep(raw)
    cal_start, cal_end = df.index.min(), df.index.max()

    rows = []
    for fname, ffunc in FILTERS.items():
        mask = ffunc(df)
        for sname, spct in STOP_LEVELS.items():
            for cost_label, fee in (("1x", FEE_1X), ("2x", FEE_2X)):
                trades = find_trades(df, mask, spct, fee)
                m = trade_metrics(trades, cal_start, cal_end)
                m.update({
                    "market": name, "filter": fname, "stop": sname, "cost": cost_label,
                    "data_start": cal_start.date().isoformat(), "data_end": cal_end.date().isoformat(),
                })
                if len(trades):
                    m["cagr_2000_09"] = sub_period_cagr(trades, "2000-01-01", "2009-12-31")
                    m["cagr_2010_19"] = sub_period_cagr(trades, "2010-01-01", "2019-12-31")
                    m["cagr_2020_26"] = sub_period_cagr(trades, "2020-01-01", "2026-12-31")
                rows.append(m)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    all_rows = []
    for name, loader in MARKETS.items():
        print(f"Running {name}...")
        res = run_market(name, loader)
        all_rows.append(res)
    full = pd.concat(all_rows, ignore_index=True)
    full.to_csv("/home/user/new/reports/turnaround_matrix.csv", index=False)
    print(f"\nWrote {len(full)} rows to reports/turnaround_matrix.csv")
