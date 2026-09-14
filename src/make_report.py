"""Turn reports/study_results.csv + equity_curves.parquet into a readable
summary: per-timeframe leaderboard, buy-and-hold comparison, and equity charts."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

from metrics import compute_performance, BARS_PER_YEAR

DATA_DIR = Path("/home/user/new/data")
REPORT_DIR = Path("/home/user/new/reports")
TARGET_CAGR = 0.10

IS_START, IS_END = "2014-01-01", "2019-12-31"
OOS_START, OOS_END = "2020-01-01", "2025-01-06"


def buy_and_hold_stats(timeframe):
    df = pd.read_parquet(DATA_DIR / f"btcusd_{timeframe}.parquet")
    ret = df["close"].pct_change()
    full = compute_performance(ret, timeframe)
    is_ret = ret.loc[(df.index >= IS_START) & (df.index <= IS_END)]
    oos_ret = ret.loc[(df.index >= OOS_START) & (df.index <= OOS_END)]
    is_perf = compute_performance(is_ret, timeframe)
    oos_perf = compute_performance(oos_ret, timeframe)
    return full, is_perf, oos_perf


def main():
    res = pd.read_csv(REPORT_DIR / "study_results.csv")
    curves = pd.read_parquet(REPORT_DIR / "equity_curves.parquet")

    lines = ["# Crypto strategy study — results\n"]
    lines.append(f"Universe: BTC/USD (Bitstamp spot), 2014-01-01 to 2025-01-06. "
                 f"Fee: 0.06% per one-way trade. Target: >{TARGET_CAGR*100:.0f}% p.a. net CAGR, "
                 f"selected in-sample (2014-2019), validated strictly out-of-sample (2020-2025).\n")

    qualifiers = []
    for tf in ["5m", "15m", "1h", "5h", "1d"]:
        sub = res[res["timeframe"] == tf].copy()
        if sub.empty:
            continue
        bh_full, bh_is, bh_oos = buy_and_hold_stats(tf)
        sub = sub.sort_values("oos_cagr", ascending=False)
        lines.append(f"\n## Timeframe: {tf}\n")
        lines.append(f"Buy & hold benchmark — IS CAGR {bh_is['cagr']*100:.1f}%, IS Sharpe {bh_is['sharpe']:.2f}, "
                     f"OOS CAGR {bh_oos['cagr']*100:.1f}%, OOS Sharpe {bh_oos['sharpe']:.2f}, "
                     f"OOS MaxDD {bh_oos['max_dd']*100:.1f}%\n")
        lines.append("| strategy | params | IS Sharpe | IS CAGR | OOS Sharpe | OOS CAGR | OOS MaxDD | OOS Calmar | OOS trades/yr | meets 10%pa OOS |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for _, r in sub.iterrows():
            meets = "YES" if pd.notna(r["oos_cagr"]) and r["oos_cagr"] >= TARGET_CAGR else ""
            trades_yr = r["oos_trades"] / 5.0
            lines.append(f"| {r['strategy']} | `{r['params']}` | {r['is_sharpe']:.2f} | {r['is_cagr']*100:.1f}% | "
                         f"{r['oos_sharpe']:.2f} | {r['oos_cagr']*100:.1f}% | {r['oos_maxdd']*100:.1f}% | "
                         f"{r['oos_calmar']:.2f} | {trades_yr:.0f} | {meets} |")
            if meets == "YES":
                qualifiers.append({**r.to_dict(), "bh_oos_cagr": bh_oos["cagr"]})

    lines.append("\n\n## Strategies clearing the >10% p.a. net-of-fee bar OUT-OF-SAMPLE\n")
    if qualifiers:
        q = pd.DataFrame(qualifiers).sort_values(["timeframe", "oos_sharpe"], ascending=[True, False])
        lines.append("| timeframe | strategy | params | OOS CAGR | OOS Sharpe | OOS MaxDD | vs buy&hold OOS CAGR |")
        lines.append("|---|---|---|---|---|---|---|")
        for _, r in q.iterrows():
            lines.append(f"| {r['timeframe']} | {r['strategy']} | `{r['params']}` | {r['oos_cagr']*100:.1f}% | "
                         f"{r['oos_sharpe']:.2f} | {r['oos_maxdd']*100:.1f}% | {r['bh_oos_cagr']*100:.1f}% |")
    else:
        lines.append("None.")

    (REPORT_DIR / "study_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    # Equity chart: best OOS-CAGR strategy per timeframe vs buy&hold, OOS window only
    fig, axes = plt.subplots(len(curves.columns and ["5m","15m","1h","5h","1d"]), 1, figsize=(10, 14))
    tfs = ["5m", "15m", "1h", "5h", "1d"]
    for ax, tf in zip(axes, tfs):
        sub = res[res["timeframe"] == tf].sort_values("oos_cagr", ascending=False)
        if sub.empty:
            continue
        best_tag = sub.iloc[0]["strategy"]
        col = f"{tf}__{best_tag}"
        if col not in curves.columns:
            continue
        eq = curves[col].dropna()
        eq_oos = eq.loc[(eq.index >= OOS_START)]
        eq_oos = eq_oos / eq_oos.iloc[0]
        df = pd.read_parquet(DATA_DIR / f"btcusd_{tf}.parquet")
        bh = (1 + df["close"].pct_change().fillna(0)).cumprod()
        bh_oos = bh.loc[bh.index >= OOS_START]
        bh_oos = bh_oos / bh_oos.iloc[0]
        ax.plot(eq_oos.index, eq_oos.values, label=f"{best_tag} (strategy)")
        ax.plot(bh_oos.index, bh_oos.values, label="buy & hold", alpha=0.6)
        ax.set_yscale("log")
        ax.set_title(f"{tf}: best OOS strategy vs buy&hold (out-of-sample, 2020-2025)")
        ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(REPORT_DIR / "oos_equity_curves.png", dpi=130)
    print("Saved chart to", REPORT_DIR / "oos_equity_curves.png")


if __name__ == "__main__":
    main()
