"""
Combine the strategies that cleared Sharpe > 0.5 on their most credible
sample into a single $1,000,000 portfolio.

Selection discipline (why only 4 sleeves, not every Sharpe>0.5 row in the
reports/ CSVs):
  - Many qualifying rows are the SAME signal on the SAME market with a
    slightly different filter (e.g. SPY filters A/B/C/D/E/F are all the
    Monday-weakness rule with a tighter IBS/SMA cut) -- counting all of them
    as separate "strategies" would double-count one signal, not diversify.
    Only the single best-validated variant per distinct market is kept.
  - Rows whose Sharpe>0.5 came ONLY from the short IBKR window (~4yr) and is
    CONTRADICTED by the long github history on the same market are dropped
    as noise, not edge: GBPUSD and EURUSD showed negative Sharpe across
    every filter over 2007-2023 (16yr) in turnaround_matrix.csv, so their
    short-window IBKR-only Sharpe>0.5 cells are excluded here even though
    they technically clear the bar.
  - Cells with too few trades to mean anything (n<40) are excluded even if
    Sharpe>0.5 (e.g. GBPUSD F, n=11, Sharpe 2.28 -- pure noise, already
    flagged as such in the turnaround-matrix artifact).
  - DAX30's day-of-week-optimizer OOS Sharpe rounds to exactly 0.50, not
    "above" 0.5 -- excluded as a boundary case, not rounded in its favor.

Final basket:
  1. BTC/USD, 15m Donchian breakout (entry_n=672/exit_n=336) -- OOS Sharpe
     1.39, 2020-2025. The only trend/momentum sleeve; also the strategy
     currently forward-tested live on the connected IBKR paper account.
  2. SPY, Monday close < prior Friday close (IBS<0.2) -> Wednesday exit --
     Sharpe 0.73, 26yr (2000-2026), n=197. US large-cap mean reversion.
  3. Nasdaq100, same rule -- Sharpe 1.01, 10yr (2013-2023), n=56. Same
     signal family as SPY -- correlation is measured, not assumed away.
  4. HSI, Monday close < prior Friday close (IBS<0.3) -> Wednesday exit --
     Sharpe 0.90, IBKR real data, ~4yr (2022-2026), n=42. Asia sleeve --
     shortest history of the four, flagged accordingly.

Weighting: inverse annualized volatility (each sleeve's own full-history
return series), normalized to 100%, capped at [10%, 50%] per sleeve so no
single sleeve's vol estimate dominates or gets zeroed out.

Combined-portfolio simulation window: Sep 2022 - Sep 2026, the actual
overlap of all four sleeves (HSI's IBKR history is the binding constraint).
Trades outside that window are used only to estimate each sleeve's
volatility (for weighting), not folded into the combined $ curve.
"""
import json
import numpy as np
import pandas as pd

import strategies as st
from backtest import run_backtest
from turnaround_strategy import prep, find_trades
from turnaround_matrix import load_spy, MARKETS as GITHUB_MARKETS
from turnaround_ibkr import load_ibkr

TOTAL_CAPITAL = 1_000_000
FEE_CRYPTO = 0.0006
FEE_EQUITY = 0.0004
COMMON_START = "2022-09-21"  # SPY IBKR start, the latest of the four sleeve starts
COMMON_END = "2026-09-16"


def btc_daily_returns(full: bool = True) -> pd.Series:
    df = pd.read_parquet("/home/user/new/data/btcusd_15m.parquet")
    df.index = pd.to_datetime(df.index, utc=True).tz_localize(None)
    df = df.sort_index()
    sig = st.donchian_breakout(df, entry_n=672, exit_n=336, long_short=False)
    bt = run_backtest(df, sig, fee=FEE_CRYPTO)
    r = bt["returns"].fillna(0)
    daily = (1 + r).resample("D").prod() - 1
    return daily if full else daily.loc[COMMON_START:COMMON_END]


def turnaround_daily_returns(df_loader, ibs_threshold: float, is_ibkr: bool = False) -> pd.Series:
    raw = df_loader()
    df = prep(raw)
    mask = df["ibs"] < ibs_threshold
    fee = FEE_EQUITY
    trades = find_trades(df, mask, None, fee)
    if len(trades) == 0:
        return pd.Series(dtype=float)
    daily_idx = pd.date_range(df.index.min(), df.index.max(), freq="D")
    s = pd.Series(0.0, index=daily_idx)
    for _, t in trades.iterrows():
        s.loc[t["exit_date"]] += t["return"]
    return s


def _obs_per_year(daily_returns: pd.Series, r: pd.Series) -> float:
    """Annualization basis = actual number of non-zero return observations
    per year, NOT calendar days -- these are sparse trade-event series
    (BTC's is genuinely daily; the equity sleeves only carry a nonzero
    return on each trade's exit day), so sqrt(365) would overstate Sharpe
    for anything traded less than daily. Same convention trade_metrics()
    uses elsewhere in this repo (trades_per_year = n_trades/years)."""
    years = (daily_returns.index.max() - daily_returns.index.min()).days / 365.25
    return len(r) / years if years > 0 else np.nan


def ann_vol(daily_returns: pd.Series) -> float:
    r = daily_returns[daily_returns != 0]
    if len(r) < 5:
        return np.nan
    return r.std() * np.sqrt(_obs_per_year(daily_returns, r))


def sharpe_of(daily_returns: pd.Series) -> float:
    r = daily_returns[daily_returns != 0]
    if len(r) < 5:
        return np.nan
    n_per_year = _obs_per_year(daily_returns, r)
    return (r.mean() / r.std()) * np.sqrt(n_per_year) if r.std() > 0 else np.nan


def max_dd_of(equity: pd.Series) -> float:
    running_max = equity.cummax()
    return (equity / running_max - 1).min()


if __name__ == "__main__":
    sleeves = {}

    print("Building BTC 15m Donchian sleeve...")
    sleeves["BTC (15m Donchian)"] = btc_daily_returns()

    print("Building SPY Monday IBS<0.2 sleeve...")
    sleeves["SPY (Monday->Wed)"] = turnaround_daily_returns(load_spy, 0.2)

    print("Building Nasdaq100 Monday IBS<0.2 sleeve...")
    sleeves["Nasdaq100 (Monday->Wed)"] = turnaround_daily_returns(GITHUB_MARKETS["Nasdaq100"], 0.2)

    print("Building HSI Monday IBS<0.3 sleeve...")
    sleeves["HSI (Monday->Wed)"] = turnaround_daily_returns(lambda: load_ibkr("hsi_ibkr.json", False), 0.3)

    # --- weighting: inverse full-history annualized vol, capped [10%,50%] ---
    vols = {name: ann_vol(s) for name, s in sleeves.items()}
    inv_vol = {name: 1 / v for name, v in vols.items()}
    total_inv = sum(inv_vol.values())
    raw_weights = {name: iv / total_inv for name, iv in inv_vol.items()}
    capped = {name: min(max(w, 0.10), 0.50) for name, w in raw_weights.items()}
    norm = sum(capped.values())
    weights = {name: w / norm for name, w in capped.items()}

    print("\nFull-history stats and weights:")
    for name in sleeves:
        print(f"  {name}: ann_vol={vols[name]*100:.1f}%  raw_weight={raw_weights[name]*100:.1f}%  final_weight={weights[name]*100:.1f}%")

    # --- pairwise correlation over the common window ---
    common = pd.DataFrame({name: s.loc[COMMON_START:COMMON_END] for name, s in sleeves.items()}).fillna(0)
    corr = common.corr()
    print("\nPairwise correlation (common window, daily returns incl. zero days):")
    print(corr.round(2).to_string())

    # --- combined portfolio simulation over the common window ---
    dollar_alloc = {name: TOTAL_CAPITAL * weights[name] for name in sleeves}
    sleeve_equity = {}
    for name in sleeves:
        r = common[name]
        equity = dollar_alloc[name] * (1 + r).cumprod()
        sleeve_equity[name] = equity

    portfolio_equity = sum(sleeve_equity.values())
    portfolio_returns = portfolio_equity.pct_change().fillna(0)

    port_sharpe = sharpe_of(portfolio_returns.replace(0, np.nan).dropna().reindex(portfolio_returns.index, fill_value=0))
    years = (common.index.max() - common.index.min()).days / 365.25
    total_return = portfolio_equity.iloc[-1] / TOTAL_CAPITAL - 1
    cagr = (1 + total_return) ** (1 / years) - 1
    max_dd = max_dd_of(portfolio_equity)

    print(f"\n=== Combined portfolio, {COMMON_START} -> {COMMON_END} ({years:.1f}yr), ${TOTAL_CAPITAL:,} ===")
    print(f"Final value: ${portfolio_equity.iloc[-1]:,.0f}  (total return {total_return*100:.1f}%, CAGR {cagr*100:.1f}%)")
    print(f"Max drawdown: {max_dd*100:.1f}%")
    print(f"Portfolio Sharpe (trade-day basis): {port_sharpe:.2f}" if not np.isnan(port_sharpe) else "Portfolio Sharpe: n/a")

    for name in sleeves:
        final = sleeve_equity[name].iloc[-1]
        print(f"  {name}: ${dollar_alloc[name]:,.0f} -> ${final:,.0f} ({(final/dollar_alloc[name]-1)*100:+.1f}%)")

    out = {
        "total_capital": TOTAL_CAPITAL,
        "common_window": {"start": COMMON_START, "end": COMMON_END},
        "sleeves": {
            name: {
                "ann_vol_full_history": round(float(vols[name]), 4),
                "weight": round(float(weights[name]), 4),
                "dollar_alloc": round(float(dollar_alloc[name]), 2),
                "common_window_final_value": round(float(sleeve_equity[name].iloc[-1]), 2),
                "common_window_return_pct": round(float(sleeve_equity[name].iloc[-1] / dollar_alloc[name] - 1) * 100, 2),
                "actual_data_start": sleeves[name][sleeves[name] != 0].index.min().date().isoformat() if (sleeves[name] != 0).any() else None,
                "actual_data_end": sleeves[name].dropna().index.max().date().isoformat(),
            } for name in sleeves
        },
        "correlation_matrix": corr.round(3).to_dict(),
        "portfolio": {
            "final_value": round(float(portfolio_equity.iloc[-1]), 2),
            "total_return_pct": round(float(total_return) * 100, 2),
            "cagr_pct": round(float(cagr) * 100, 2),
            "max_dd_pct": round(float(max_dd) * 100, 2),
            "sharpe": round(float(port_sharpe), 2) if not np.isnan(port_sharpe) else None,
        },
        "equity_curve": {
            "dates": [d.date().isoformat() for d in portfolio_equity.index],
            "portfolio": [round(float(v), 2) for v in portfolio_equity.values],
            "sleeves": {name: [round(float(v), 2) for v in eq.values] for name, eq in sleeve_equity.items()},
        },
    }
    with open("/home/user/new/reports/portfolio/portfolio_result.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nWrote reports/portfolio/portfolio_result.json")
