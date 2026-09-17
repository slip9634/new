"""
Systematic MA-crossover parameter search for the slow-trend sleeve (BTC/USD spot,
Bitstamp data via data_prep.py -- the only clean data available in this environment;
no ETH, funding-rate, options/DVOL, or equity data exists here, so this covers only
the trend-sleeve fit, not the funding-rate or equity-pairs ideas).

Same IS/OOS discipline as run_study.py: IS 2014-2019 for parameter selection (max IS
Sharpe, min 20 trades), OOS 2020-2025 evaluated once on frozen params. No lookahead:
backtest.py lags every signal by one bar before applying it to that bar's return.
"""
import itertools
import pandas as pd

import strategies as st
from backtest import run_backtest
from metrics import compute_performance

IS_START, IS_END = "2014-01-01", "2019-12-31"
OOS_START, OOS_END = "2020-01-01", "2025-12-31"
FEE = 0.0006

FAST_PERIODS = [10, 20, 30, 50, 75, 100]
SLOW_PERIODS = [50, 75, 100, 150, 200, 250, 300]
MA_TYPES = ["sma", "ema"]
TIMEFRAMES = ["1h", "1d"]

MIN_IS_TRADES = 20


def load(tf: str) -> pd.DataFrame:
    df = pd.read_parquet(f"/home/user/new/data/btcusd_{tf}.parquet")
    df.index = pd.to_datetime(df.index, utc=True)
    return df.sort_index()


def buy_hold_benchmark(df: pd.DataFrame, tf: str, start: str, end: str) -> dict:
    window = df.loc[start:end]
    ret = window["close"].pct_change().fillna(0)
    return compute_performance(ret, tf, n_trades=1)


def search(tf: str) -> list[dict]:
    df = load(tf)
    is_df = df.loc[IS_START:IS_END]
    oos_df = df.loc[OOS_START:OOS_END]

    results = []
    for ma_type, fast, slow in itertools.product(MA_TYPES, FAST_PERIODS, SLOW_PERIODS):
        if fast >= slow:
            continue
        for long_short in (False, True):
            sig_is = st.ma_crossover(is_df, fast, slow, ma_type, long_short)
            bt_is = run_backtest(is_df, sig_is, fee=FEE)
            perf_is = compute_performance(bt_is["returns"], tf, n_trades=bt_is["n_trades"])
            if perf_is["n_trades"] < MIN_IS_TRADES or pd.isna(perf_is["sharpe"]):
                continue
            results.append({
                "tf": tf, "ma_type": ma_type, "fast": fast, "slow": slow,
                "long_short": long_short, "is_sharpe": perf_is["sharpe"],
                "is_cagr": perf_is["cagr"], "is_trades": perf_is["n_trades"],
            })

    results.sort(key=lambda r: r["is_sharpe"], reverse=True)
    top5 = results[:5]

    for r in top5:
        sig_oos = st.ma_crossover(oos_df, r["fast"], r["slow"], r["ma_type"], r["long_short"])
        bt_oos = run_backtest(oos_df, sig_oos, fee=FEE)
        perf_oos = compute_performance(bt_oos["returns"], tf, n_trades=bt_oos["n_trades"])
        r.update({
            "oos_sharpe": perf_oos["sharpe"], "oos_cagr": perf_oos["cagr"],
            "oos_max_dd": perf_oos["max_dd"], "oos_trades": perf_oos["n_trades"],
            "oos_calmar": perf_oos["calmar"],
        })

    bh = buy_hold_benchmark(df, tf, OOS_START, OOS_END)
    print(f"\n=== {tf} MA-crossover search: {len(results)} candidates passed IS filter (min {MIN_IS_TRADES} trades) ===")
    print(f"Buy & hold OOS benchmark: Sharpe={bh['sharpe']:.2f}, CAGR={bh['cagr']*100:.1f}%, MaxDD={bh['max_dd']*100:.1f}%")
    print(f"{'ma_type':<6}{'fast':<6}{'slow':<6}{'L/S':<6}{'IS Sharpe':<11}{'OOS Sharpe':<11}{'OOS CAGR%':<11}{'OOS MaxDD%':<11}{'OOS trades':<11}")
    for r in top5:
        print(f"{r['ma_type']:<6}{r['fast']:<6}{r['slow']:<6}{str(r['long_short']):<6}"
              f"{r['is_sharpe']:<11.2f}{r['oos_sharpe']:<11.2f}{r['oos_cagr']*100:<11.1f}"
              f"{r['oos_max_dd']*100:<11.1f}{r['oos_trades']:<11}")
    return top5


if __name__ == "__main__":
    all_results = {}
    for tf in TIMEFRAMES:
        all_results[tf] = search(tf)
