"""
Full study: for each timeframe, grid-search each strategy family on the
IN-SAMPLE window only (selecting by in-sample Sharpe, with a minimum trade
count so we don't pick a "strategy" that made 3 lucky trades), then evaluate
the SAME frozen parameters on the OUT-OF-SAMPLE window -- no re-fitting, no
peeking. Also reports full-period stats and two OOS sub-periods for
consistency checking.

IS:  2014-01-01 -> 2019-12-31  (parameter selection)
OOS: 2020-01-01 -> 2025-01-06  (validation only, used exactly once)
  OOS-A: 2020-01-01 -> 2022-12-31 (covid crash/recovery, 2021 bull, 2022 bear)
  OOS-B: 2023-01-01 -> 2025-01-06 (post-FTX recovery/bull)
"""
import time
import json
import numpy as np
import pandas as pd
from pathlib import Path

import strategies as st
import grids as gr
from backtest import run_backtest
from metrics import compute_performance

DATA_DIR = Path("/home/user/new/data")
REPORT_DIR = Path("/home/user/new/reports")
FEE = 0.0006
MIN_TRADES_IS = 20

IS_START, IS_END = "2014-01-01", "2019-12-31"
OOS_START, OOS_END = "2020-01-01", "2025-01-06"
OOSA_START, OOSA_END = "2020-01-01", "2022-12-31"
OOSB_START, OOSB_END = "2023-01-01", "2025-01-06"

TIMEFRAMES = ["5m", "15m", "1h", "5h", "1d"]

STRATEGY_SPECS = [
    ("ema_crossover", st.ema_crossover, gr.ema_crossover_grid, True),
    ("ema_crossover", st.ema_crossover, gr.ema_crossover_grid, False),
    ("ema_crossover_adx", st.ema_crossover_adx, gr.ema_crossover_adx_grid, True),
    ("ema_crossover_adx", st.ema_crossover_adx, gr.ema_crossover_adx_grid, False),
    ("donchian_breakout", st.donchian_breakout, gr.donchian_grid, True),
    ("donchian_breakout", st.donchian_breakout, gr.donchian_grid, False),
    ("tsmom", st.time_series_momentum, gr.tsmom_grid, True),
    ("tsmom", st.time_series_momentum, gr.tsmom_grid, False),
    ("bollinger_mr", st.bollinger_mean_reversion, gr.bollinger_grid, True),
    ("bollinger_mr", st.bollinger_mean_reversion, gr.bollinger_grid, False),
    ("volatility_breakout", st.volatility_breakout, gr.volbreakout_grid, True),
    ("volatility_breakout", st.volatility_breakout, gr.volbreakout_grid, False),
    ("rsi2_mr", st.rsi2_mean_reversion, gr.rsi2_grid, None),
]


def get_signal(fn, df, params):
    return fn(df, **params)


def eval_window(df, signal, timeframe, start, end):
    sub_idx = (df.index >= start) & (df.index <= end)
    d = df.loc[sub_idx]
    s = signal.loc[sub_idx]
    if len(d) < 10:
        return None
    bt = run_backtest(d, s, fee=FEE)
    perf = compute_performance(bt["returns"], timeframe, n_trades=bt["n_trades"])
    return perf, bt


def run_family(timeframe, df, name, fn, grid_fn, long_short, results, curves):
    grid = grid_fn(timeframe) if long_short is None else grid_fn(timeframe, long_short)
    best = None
    t0 = time.time()
    for params in grid:
        sig = get_signal(fn, df, params)
        is_eval = eval_window(df, sig, timeframe, IS_START, IS_END)
        if is_eval is None:
            continue
        is_perf, _ = is_eval
        if is_perf["n_trades"] < MIN_TRADES_IS or not np.isfinite(is_perf["sharpe"]):
            continue
        if best is None or is_perf["sharpe"] > best["is_perf"]["sharpe"]:
            best = {"params": params, "is_perf": is_perf}
    elapsed = time.time() - t0
    tag = f"{name}{'_LS' if long_short else ('_L' if long_short is not None else '')}"
    if best is None:
        print(f"[{timeframe}] {tag}: no candidate cleared min-trades filter ({len(grid)} combos, {elapsed:.1f}s)")
        return
    # Freeze params, now compute on full history + all sub-windows, no re-selection
    sig = get_signal(fn, df, best["params"])
    full_eval = eval_window(df, sig, timeframe, df.index.min(), df.index.max())
    oos_eval = eval_window(df, sig, timeframe, OOS_START, OOS_END)
    oosa_eval = eval_window(df, sig, timeframe, OOSA_START, OOSA_END)
    oosb_eval = eval_window(df, sig, timeframe, OOSB_START, OOSB_END)

    row = {
        "timeframe": timeframe,
        "strategy": tag,
        "params": json.dumps(best["params"]),
        "is_sharpe": best["is_perf"]["sharpe"],
        "is_cagr": best["is_perf"]["cagr"],
        "is_maxdd": best["is_perf"]["max_dd"],
        "is_trades": best["is_perf"]["n_trades"],
        "oos_sharpe": oos_eval[0]["sharpe"] if oos_eval else np.nan,
        "oos_cagr": oos_eval[0]["cagr"] if oos_eval else np.nan,
        "oos_maxdd": oos_eval[0]["max_dd"] if oos_eval else np.nan,
        "oos_calmar": oos_eval[0]["calmar"] if oos_eval else np.nan,
        "oos_trades": oos_eval[0]["n_trades"] if oos_eval else np.nan,
        "oosA_cagr": oosa_eval[0]["cagr"] if oosa_eval else np.nan,
        "oosB_cagr": oosb_eval[0]["cagr"] if oosb_eval else np.nan,
        "full_sharpe": full_eval[0]["sharpe"] if full_eval else np.nan,
        "full_cagr": full_eval[0]["cagr"] if full_eval else np.nan,
        "full_maxdd": full_eval[0]["max_dd"] if full_eval else np.nan,
        "n_combos_tested": len(grid),
        "search_seconds": round(elapsed, 1),
    }
    results.append(row)
    if full_eval is not None:
        curves[f"{timeframe}__{tag}"] = full_eval[1]["equity"]
    print(f"[{timeframe}] {tag}: best={best['params']} IS_sharpe={best['is_perf']['sharpe']:.2f} "
          f"OOS_cagr={row['oos_cagr']*100 if pd.notna(row['oos_cagr']) else float('nan'):.1f}% "
          f"({len(grid)} combos, {elapsed:.1f}s)")


def main():
    results = []
    curves = {}
    for timeframe in TIMEFRAMES:
        df = pd.read_parquet(DATA_DIR / f"btcusd_{timeframe}.parquet")
        for name, fn, grid_fn, long_short in STRATEGY_SPECS:
            run_family(timeframe, df, name, fn, grid_fn, long_short, results, curves)

    res_df = pd.DataFrame(results).sort_values(["timeframe", "oos_cagr"], ascending=[True, False])
    res_df.to_csv(REPORT_DIR / "study_results.csv", index=False)

    curves_df = pd.DataFrame(curves)
    curves_df.to_parquet(REPORT_DIR / "equity_curves.parquet")

    print("\n=== SAVED ===")
    print(REPORT_DIR / "study_results.csv")
    print(REPORT_DIR / "equity_curves.parquet")


if __name__ == "__main__":
    main()
