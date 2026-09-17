"""
Re-run the Monday-weakness/Wednesday-exit robustness matrix on real IBKR data
instead of the GitHub broker-feed CSVs. IBKR's get_price_history caps daily
bars at step_count=1000, so this window is short (~2022-2026, ~4 years) --
not a replacement for the longer GitHub-sourced history, but a genuine
out-of-sample check on fresher, exchange-quality (non-CFD-proxy) data for
the same 6 markets, fetched live through the connected IBKR paper account.
"""
import json
import pandas as pd

from turnaround_strategy import prep, find_trades, FILTERS, STOP_LEVELS
from turnaround_matrix import trade_metrics, FEE_1X, FEE_2X

DATA_DIR = "/home/user/new/data/turnaround_ibkr"

INSTRUMENTS = {
    "SPY": ("spy_ibkr.json", False),
    "FTSE100": ("ftse_ibkr.json", False),
    "DAX30": ("dax_ibkr.json", False),
    "Nasdaq100": ("ndx_ibkr.json", False),
    "EURUSD": ("eurusd_ibkr.json", True),
    "GBPUSD": ("gbpusd_ibkr.json", True),
}


def load_ibkr(fname: str, is_fx: bool = False) -> pd.DataFrame:
    """IDEALPRO FX daily bars come back timestamped at the session's START
    (22:15 UTC the evening before, e.g. a bar labeled "Sunday 22:15" is what
    every retail platform calls "Monday's bar"). Equity/index bars are
    timestamped within their own trading day and need no correction --
    verified empirically: shifting FX dates +1 day turns a lopsided weekday
    histogram (194 Sundays, 2 Fridays) into a clean Mon-Fri spread."""
    raw = json.loads(open(f"{DATA_DIR}/{fname}").read())
    dates = pd.to_datetime(raw["time"], utc=True).tz_localize(None)
    if is_fx:
        dates = dates + pd.Timedelta(days=1)
    df = pd.DataFrame({
        "date": dates,
        "open": raw["open"], "high": raw["high"], "low": raw["low"], "close": raw["close"],
    }).set_index("date").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def run_market(name: str, fname: str, is_fx: bool = False) -> pd.DataFrame:
    raw = load_ibkr(fname, is_fx)
    df = prep(raw)
    cal_start, cal_end = df.index.min(), df.index.max()

    rows = []
    for fkey, ffunc in FILTERS.items():
        mask = ffunc(df)
        for skey, spct in STOP_LEVELS.items():
            for cost_label, fee in (("1x", FEE_1X), ("2x", FEE_2X)):
                trades = find_trades(df, mask, spct, fee)
                m = trade_metrics(trades, cal_start, cal_end)
                m.update({
                    "market": name, "filter": fkey, "stop": skey, "cost": cost_label,
                    "data_start": cal_start.date().isoformat(), "data_end": cal_end.date().isoformat(),
                })
                rows.append(m)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    all_rows = []
    for name, (fname, is_fx) in INSTRUMENTS.items():
        print(f"Running {name} (IBKR)...")
        all_rows.append(run_market(name, fname, is_fx))
    full = pd.concat(all_rows, ignore_index=True)
    full.to_csv("/home/user/new/reports/turnaround_matrix_ibkr.csv", index=False)
    print(f"\nWrote {len(full)} rows to reports/turnaround_matrix_ibkr.csv")
