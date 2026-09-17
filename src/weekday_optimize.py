"""Runs the day-of-week optimizer across every daily market in the repo,
including the newly-added Hang Seng Index (HSI, via IBKR -- ~4yr window,
same 1000-daily-bar cap as the other IBKR-only markets)."""
import json
import pandas as pd

from weekday_search import optimize_market
from turnaround_matrix import MARKETS as GITHUB_MARKETS

DATA_DIR = "/home/user/new/data/turnaround_ibkr"


def load_hsi() -> pd.DataFrame:
    raw = json.loads(open(f"{DATA_DIR}/hsi_ibkr.json").read())
    df = pd.DataFrame({
        "date": pd.to_datetime(raw["time"], utc=True).tz_localize(None),
        "open": raw["open"], "high": raw["high"], "low": raw["low"], "close": raw["close"],
    }).set_index("date").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


if __name__ == "__main__":
    results = []
    for name, loader in GITHUB_MARKETS.items():
        df = loader()
        print(f"Optimizing {name} (github, {df.index.min().date()}..{df.index.max().date()}, {len(df)} bars)...")
        results.append(optimize_market(name, df))

    hsi_df = load_hsi()
    print(f"Optimizing HSI (IBKR, {hsi_df.index.min().date()}..{hsi_df.index.max().date()}, {len(hsi_df)} bars)...")
    results.append(optimize_market("HSI", hsi_df))

    print(f"\n{'Market':<10}{'Best pair':<12}{'IS Sharpe':<11}{'IS trades':<11}{'OOS Sharpe':<12}{'OOS trades':<11}{'Baseline OOS (Mon->Wed)':<24}")
    for r in results:
        if not r["ok"]:
            print(f"{r['market']:<10} no pair cleared the min-trade filter")
            continue
        pair = f"{r['best_entry']}->{r['best_exit']}"
        print(f"{r['market']:<10}{pair:<12}{r['is_sharpe']:<11}{r['is_trades']:<11}"
              f"{str(r['oos_sharpe_best']):<12}{r['oos_trades_best']:<11}{str(r['oos_sharpe_baseline_mon_wed']):<24}")

    out = [{k: v for k, v in r.items() if k != "full_grid"} for r in results]
    with open("/home/user/new/reports/weekday_optimize.json", "w") as f:
        json.dump(out, f, indent=2)

    full_out = {r["market"]: r.get("full_grid", []) for r in results}
    with open("/home/user/new/reports/weekday_optimize_full_grid.json", "w") as f:
        json.dump(full_out, f, indent=2)
    print("\nWrote reports/weekday_optimize.json and reports/weekday_optimize_full_grid.json")
