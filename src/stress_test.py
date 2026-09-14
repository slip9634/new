"""
Robustness checks on the strategies that (a) cleared the 10% p.a. net-of-fee bar
out-of-sample AND (b) were profitable in BOTH out-of-sample sub-periods
(2020-2022 and 2023-2025), i.e. not a strategy that only worked in one regime.

For each such strategy, re-run the OOS backtest at 1x, 2x and 3x the base fee
(0.06% -> 0.12% -> 0.18% one-way) to see how sensitive net returns are to a
higher-fee venue or realistic slippage on top of the quoted taker fee.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

import strategies as st
from backtest import run_backtest
from metrics import compute_performance

DATA_DIR = Path("/home/user/new/data")
REPORT_DIR = Path("/home/user/new/reports")
OOS_START, OOS_END = "2020-01-01", "2025-01-06"
OOSA_START, OOSA_END = "2020-01-01", "2022-12-31"
OOSB_START, OOSB_END = "2023-01-01", "2025-01-06"

FN_MAP = {
    "donchian_breakout": st.donchian_breakout,
    "volatility_breakout": st.volatility_breakout,
    "tsmom": st.time_series_momentum,
    "ema_crossover": st.ema_crossover,
    "ema_crossover_adx": st.ema_crossover_adx,
    "rsi2_mr": st.rsi2_mean_reversion,
    "bollinger_mr": st.bollinger_mean_reversion,
}


def base_name(tag):
    for suffix in ("_LS", "_L"):
        if tag.endswith(suffix):
            return tag[: -len(suffix)]
    return tag


def main():
    res = pd.read_csv(REPORT_DIR / "study_results.csv")
    res["meets"] = res["oos_cagr"] >= 0.10
    res["robust"] = res["meets"] & (res["oosA_cagr"] > 0) & (res["oosB_cagr"] > 0)
    robust = res[res["robust"]].copy()

    rows = []
    for _, r in robust.iterrows():
        tf, tag, params_s = r["timeframe"], r["strategy"], r["params"]
        params = json.loads(params_s)
        fn = FN_MAP[base_name(tag)]
        df = pd.read_parquet(DATA_DIR / f"btcusd_{tf}.parquet")
        sig = fn(df, **params)
        for mult in (1, 2, 3):
            fee = 0.0006 * mult
            sub = (df.index >= OOS_START) & (df.index <= OOS_END)
            bt = run_backtest(df.loc[sub], sig.loc[sub], fee=fee)
            perf = compute_performance(bt["returns"], tf, n_trades=bt["n_trades"])
            rows.append({
                "timeframe": tf, "strategy": tag, "params": params_s,
                "fee_bps_oneway": round(fee * 10000, 2), "oos_cagr": perf["cagr"],
                "oos_sharpe": perf["sharpe"], "oos_maxdd": perf["max_dd"],
                "n_trades_5y": perf["n_trades"], "trades_per_year": perf["n_trades"] / 5.0,
            })

    out = pd.DataFrame(rows)
    out.to_csv(REPORT_DIR / "fee_stress_test.csv", index=False)

    pivot = out.pivot_table(index=["timeframe", "strategy"], columns="fee_bps_oneway", values="oos_cagr")
    pivot.columns = [f"cagr_at_{c:g}bps" for c in pivot.columns]
    base_col = f"cagr_at_{6.0:g}bps"
    trades = out[out["fee_bps_oneway"] == 6.0].set_index(["timeframe", "strategy"])["trades_per_year"]
    pivot["trades_per_year"] = trades
    pivot = pivot.sort_values(base_col, ascending=False)
    pivot.to_csv(REPORT_DIR / "fee_stress_summary.csv")
    print(pivot.to_string())
    high_col = f"cagr_at_{18.0:g}bps"
    print(f"\n{(pivot[high_col] >= 0.10).sum()} / {len(pivot)} of the robust strategies still clear 10% p.a. even at 3x the fee (0.18% one-way)")


if __name__ == "__main__":
    main()
