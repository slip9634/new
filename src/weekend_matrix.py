"""
Runs the weekend-effect strategy (Friday open -> Monday open) across every
daily dataset already in this repo (long-history GitHub CSVs + short-window
IBKR pull), plus a weekly-bar Friday-close -> Monday-open proxy on IBKR's
weekly bars for markets where that reaches much further back than the
1000-daily-bar cap allows.
"""
import json
import pandas as pd

from weekend_effect import prep_weekend, find_weekend_trades, weekly_gap_returns, WEEKEND_FILTERS
from turnaround_matrix import trade_metrics, FEE_1X, FEE_2X, MARKETS as DAILY_MARKETS
from turnaround_ibkr import load_ibkr, INSTRUMENTS as IBKR_DAILY_INSTRUMENTS

STOP_LEVELS = {"no_stop": None, "stop_2pct": 0.02, "stop_5pct": 0.05, "stop_10pct": 0.10}
WEEKLY_DIR = "/home/user/new/data/turnaround_ibkr_weekly"
WEEKLY_FILES = {
    "SPY": "spy_weekly.json", "FTSE100": "ftse_weekly.json", "DAX30": "dax_weekly.json",
    "Nasdaq100": "ndx_weekly.json", "EURUSD": "eurusd_weekly.json", "GBPUSD": "gbpusd_weekly.json",
}


def run_daily_source(name: str, loader, source_label: str) -> pd.DataFrame:
    raw = loader()
    df = prep_weekend(raw)
    cal_start, cal_end = df.index.min(), df.index.max()
    rows = []
    for fkey, ffunc in WEEKEND_FILTERS.items():
        mask = ffunc(df)
        for skey, spct in STOP_LEVELS.items():
            for clabel, fee in (("1x", FEE_1X), ("2x", FEE_2X)):
                trades = find_weekend_trades(df, mask, spct, fee)
                m = trade_metrics(trades, cal_start, cal_end)
                m.update({"market": name, "source": source_label, "filter": fkey, "stop": skey, "cost": clabel,
                           "data_start": cal_start.date().isoformat(), "data_end": cal_end.date().isoformat()})
                rows.append(m)
    return pd.DataFrame(rows)


def load_weekly(fname: str) -> pd.DataFrame:
    raw = json.loads(open(f"{WEEKLY_DIR}/{fname}").read())
    df = pd.DataFrame({
        "date": pd.to_datetime(raw["time"], utc=True).tz_localize(None),
        "open": raw["open"], "high": raw["high"], "low": raw["low"], "close": raw["close"],
    }).set_index("date").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def run_weekly(name: str, fname: str) -> pd.DataFrame:
    df = load_weekly(fname)
    cal_start, cal_end = df.index.min(), df.index.max()
    rows = []
    for clabel, fee in (("1x", FEE_1X), ("2x", FEE_2X)):
        trades = weekly_gap_returns(df, fee)
        m = trade_metrics(trades, cal_start, cal_end)
        m.update({"market": name, "source": "ibkr_weekly_gap", "filter": "A_none", "stop": "no_stop", "cost": clabel,
                   "data_start": cal_start.date().isoformat(), "data_end": cal_end.date().isoformat()})
        rows.append(m)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    all_rows = []

    for name, loader in DAILY_MARKETS.items():
        print(f"Weekend effect, github daily: {name}")
        all_rows.append(run_daily_source(name, loader, "github_daily"))

    for name, (fname, is_fx) in IBKR_DAILY_INSTRUMENTS.items():
        print(f"Weekend effect, IBKR daily: {name}")
        all_rows.append(run_daily_source(name, lambda fname=fname, is_fx=is_fx: load_ibkr(fname, is_fx), "ibkr_daily"))

    for name, fname in WEEKLY_FILES.items():
        print(f"Weekend gap, IBKR weekly: {name}")
        all_rows.append(run_weekly(name, fname))

    full = pd.concat(all_rows, ignore_index=True)
    full.to_csv("/home/user/new/reports/weekend_effect_matrix.csv", index=False)
    print(f"\nWrote {len(full)} rows to reports/weekend_effect_matrix.csv")
