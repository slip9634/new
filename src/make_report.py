"""Turn reports/study_results.csv + fee_stress_test.csv + equity_curves.parquet
into a readable summary: per-timeframe leaderboard, buy-and-hold comparison,
robustness-screened recommendations, and equity charts."""
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
    is_ret = ret.loc[(df.index >= IS_START) & (df.index <= IS_END)]
    oos_ret = ret.loc[(df.index >= OOS_START) & (df.index <= OOS_END)]
    return compute_performance(is_ret, timeframe), compute_performance(oos_ret, timeframe)


def main():
    res = pd.read_csv(REPORT_DIR / "study_results.csv")
    curves = pd.read_parquet(REPORT_DIR / "equity_curves.parquet")
    fee_stress = pd.read_csv(REPORT_DIR / "fee_stress_test.csv")

    res["meets_10pa"] = res["oos_cagr"] >= TARGET_CAGR
    res["robust_both_halves"] = res["meets_10pa"] & (res["oosA_cagr"] > 0) & (res["oosB_cagr"] > 0)

    lines = ["# Crypto strategy study — results\n"]
    lines.append(f"Universe: BTC/USD (Bitstamp spot, 2014-01-01 to 2025-01-06, cleaned & gap-filled). "
                 f"Fee: 0.06% per one-way trade (round-trip 0.12%). "
                 f"Target: >{TARGET_CAGR*100:.0f}% p.a. net CAGR. "
                 f"Parameters selected on 2014-2019 IN-SAMPLE data only (max in-sample Sharpe, "
                 f"min. 20 trades); frozen and evaluated once on 2020-2025 OUT-OF-SAMPLE data.\n")

    qualifiers, robust_rows = [], []
    for tf in ["5m", "15m", "1h", "5h", "1d"]:
        sub = res[res["timeframe"] == tf].copy()
        if sub.empty:
            continue
        bh_is, bh_oos = buy_and_hold_stats(tf)
        sub = sub.sort_values("oos_cagr", ascending=False)
        lines.append(f"\n## Timeframe: {tf}\n")
        lines.append(f"Buy & hold benchmark — IS CAGR {bh_is['cagr']*100:.1f}%, IS Sharpe {bh_is['sharpe']:.2f}, "
                     f"OOS CAGR {bh_oos['cagr']*100:.1f}%, OOS Sharpe {bh_oos['sharpe']:.2f}, "
                     f"OOS MaxDD {bh_oos['max_dd']*100:.1f}%\n")
        lines.append("| strategy | params | IS Sharpe | IS CAGR | OOS Sharpe | OOS CAGR | OOS MaxDD | OOS Calmar | OOS trades/yr | 2020-22 CAGR | 2023-25 CAGR | >10%pa OOS | robust both halves |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for _, r in sub.iterrows():
            meets = "YES" if r["meets_10pa"] else ""
            robust = "YES" if r["robust_both_halves"] else ""
            trades_yr = r["oos_trades"] / 5.0
            lines.append(f"| {r['strategy']} | `{r['params']}` | {r['is_sharpe']:.2f} | {r['is_cagr']*100:.1f}% | "
                         f"{r['oos_sharpe']:.2f} | {r['oos_cagr']*100:.1f}% | {r['oos_maxdd']*100:.1f}% | "
                         f"{r['oos_calmar']:.2f} | {trades_yr:.0f} | {r['oosA_cagr']*100:.1f}% | {r['oosB_cagr']*100:.1f}% | {meets} | {robust} |")
            if r["meets_10pa"]:
                qualifiers.append({**r.to_dict(), "bh_oos_cagr": bh_oos["cagr"], "bh_oos_sharpe": bh_oos["sharpe"]})
            if r["robust_both_halves"]:
                robust_rows.append(r.to_dict())

    lines.append("\n\n## All strategies clearing the >10% p.a. net-of-fee bar OUT-OF-SAMPLE\n")
    if qualifiers:
        q = pd.DataFrame(qualifiers).sort_values(["timeframe", "oos_sharpe"], ascending=[True, False])
        lines.append("| timeframe | strategy | OOS CAGR | OOS Sharpe | OOS MaxDD | buy&hold OOS CAGR | buy&hold OOS Sharpe |")
        lines.append("|---|---|---|---|---|---|---|")
        for _, r in q.iterrows():
            lines.append(f"| {r['timeframe']} | {r['strategy']} | {r['oos_cagr']*100:.1f}% | "
                         f"{r['oos_sharpe']:.2f} | {r['oos_maxdd']*100:.1f}% | {r['bh_oos_cagr']*100:.1f}% | {r['bh_oos_sharpe']:.2f} |")
    else:
        lines.append("None.")

    lines.append("\n\n## Robustness screen: positive in BOTH out-of-sample sub-periods "
                 "(2020-2022 crash/bull/bear AND 2023-2025 recovery) -- these are the credible candidates, "
                 "not strategies that got lucky in one regime\n")
    robust_df = pd.DataFrame(robust_rows).sort_values(["timeframe", "oos_sharpe"], ascending=[True, False]) if robust_rows else pd.DataFrame()
    if not robust_df.empty:
        lines.append("| timeframe | strategy | OOS Sharpe | OOS CAGR | OOS MaxDD | OOS Calmar |")
        lines.append("|---|---|---|---|---|---|")
        for _, r in robust_df.iterrows():
            lines.append(f"| {r['timeframe']} | {r['strategy']} | {r['oos_sharpe']:.2f} | {r['oos_cagr']*100:.1f}% | "
                         f"{r['oos_maxdd']*100:.1f}% | {r['oos_calmar']:.2f} |")

    lines.append("\n\n## Fee sensitivity: same robust strategies at 1x / 2x / 3x the quoted fee (0.06% -> 0.18% one-way)\n")
    pivot = fee_stress.pivot_table(index=["timeframe", "strategy"], columns="fee_bps_oneway", values="oos_cagr")
    pivot.columns = [f"{c:g}bps" for c in pivot.columns]
    trades = fee_stress[fee_stress["fee_bps_oneway"] == 6.0].set_index(["timeframe", "strategy"])["trades_per_year"]
    pivot["trades/yr"] = trades
    pivot = pivot.sort_values("6bps", ascending=False)
    lines.append("| timeframe | strategy | CAGR@6bps | CAGR@12bps | CAGR@18bps | trades/yr |")
    lines.append("|---|---|---|---|---|---|")
    for (tf, strat), r in pivot.iterrows():
        lines.append(f"| {tf} | {strat} | {r['6bps']*100:.1f}% | {r['12bps']*100:.1f}% | {r['18bps']*100:.1f}% | {r['trades/yr']:.0f} |")
    n_hold = (pivot["18bps"] >= TARGET_CAGR).sum()
    lines.append(f"\n{n_hold}/{len(pivot)} robust strategies still clear 10% p.a. even at 3x the quoted fee.\n")

    (REPORT_DIR / "study_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-40:]))

    # Equity chart: pick, per timeframe, the ROBUST (both-halves-positive) strategy
    # with the highest OOS Sharpe -- not just the highest raw CAGR, which rewards luck.
    tfs = ["5m", "15m", "1h", "5h", "1d"]
    fig, axes = plt.subplots(len(tfs), 1, figsize=(10, 16))
    for ax, tf in zip(axes, tfs):
        sub = res[(res["timeframe"] == tf) & (res["robust_both_halves"])].sort_values("oos_sharpe", ascending=False)
        if sub.empty:
            sub = res[res["timeframe"] == tf].sort_values("oos_sharpe", ascending=False)
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
        ax.plot(eq_oos.index, eq_oos.values, label=f"{best_tag} (strategy)", linewidth=1.2)
        ax.plot(bh_oos.index, bh_oos.values, label="buy & hold", alpha=0.6, linewidth=1.0)
        ax.set_yscale("log")
        ax.set_title(f"{tf}: recommended (robust, highest OOS Sharpe) vs buy&hold — OOS 2020-2025")
        ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(REPORT_DIR / "oos_equity_curves.png", dpi=130)
    print("\nSaved chart to", REPORT_DIR / "oos_equity_curves.png")


if __name__ == "__main__":
    main()
