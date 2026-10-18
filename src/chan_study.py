"""
"Ernest Chan (2013): is anything still working?" -- run every strategy,
split into the book's in-sample era (start -> 2012) and the post-publication
out-of-sample era (2013 -> latest), and write:

  reports/chan2013/results.csv        per strategy x period metrics
  reports/chan2013/diagnostics.csv    cointegration / half-life of the pairs, IS vs OOS
  reports/chan2013/equity_curves.png  net-of-cost equity, publication date marked
  reports/chan2013/report.md          write-up

Run from src/:  python3 chan_study.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import chan_data as cd
import chan_strategies as cs

OUT = Path("/home/user/new/reports/chan2013")
START = "1990-01-01"  # skip the 1970s-80s pegs/ERM era for FX
PERIODS = {
    "IS (book era)": (None, cs.IS_END),
    "OOS 2013-2019": ("2013-01-01", "2019-12-31"),
    "OOS 2020-now": ("2020-01-01", None),
    "OOS 2013-now": ("2013-01-01", None),
}
COSTS = {"SPY": 0.0001, "WTI": 0.0003, "BRENT": 0.0003, "NATGAS": 0.0010}
FX = list(cd.FX_COUNTRIES.values())
FX_COST = 0.0001


def stats(df: pd.DataFrame) -> dict:
    r = df["net"].dropna()
    active = df["expo"] > 0
    # trim leading days before the strategy ever held a position
    if active.any():
        r = r.loc[active.idxmax():]
    if len(r) < 60 or r.std() == 0:
        return {"years": len(r) / 252, "sharpe": np.nan, "sharpe_gross": np.nan, "cagr": np.nan,
                "vol": np.nan, "max_dd": np.nan, "pct_in_mkt": np.nan}
    g = df["gross"].loc[r.index]
    eq = (1 + r).cumprod()
    yrs = len(r) / 252
    return {
        "years": round(yrs, 1),
        "sharpe": r.mean() / r.std() * np.sqrt(252),
        "sharpe_gross": g.mean() / g.std() * np.sqrt(252) if g.std() > 0 else np.nan,
        "cagr": eq.iloc[-1] ** (1 / yrs) - 1,
        "vol": r.std() * np.sqrt(252),
        "max_dd": (eq / eq.cummax() - 1).min(),
        "pct_in_mkt": float((df["expo"].loc[r.index] > 0).mean()),
    }


def build() -> dict:
    cd.fetch()
    panel = cd.daily_panel().loc[START:]
    spy = cd.load_spy()
    fx = panel[FX]

    # Pairs and cross-sectional reversal use only days where every leg actually
    # printed (no forward-filled holiday prices, which fake mean reversion).
    fx_obs = cd.load_fx().loc[START:]
    aud_cad = fx_obs[["AUD", "CAD"]].dropna()
    oil = cd.load_commodities()[["BRENT", "WTI"]].loc[START:].dropna()

    s = {}
    for lag, tag in [(1, ""), (2, " [+1d delay]")]:
        s[f"Pair AUD/CAD - Johansen + linear MR (Ex 5.1){tag}"] = cs.pair_johansen_linear(aud_cad, cost=FX_COST, lag=lag)
        s[f"Pair AUD/CAD - Kalman (Ex 3.3 rules){tag}"] = cs.pair_kalman(aud_cad["AUD"], aud_cad["CAD"], cost=FX_COST, lag=lag)
        s[f"Pair Brent/WTI spot - Johansen + linear MR{tag}"] = cs.pair_johansen_linear(oil, cost=COSTS["WTI"], lag=lag)
        s[f"Pair Brent/WTI spot - Kalman{tag}"] = cs.pair_kalman(oil["BRENT"], oil["WTI"], cost=COSTS["WTI"], lag=lag)
        s[f"XS reversal, G10 FX (Khandani-Lo, Ex 4.3){tag}"] = cs.xs_reversal(fx_obs, cost=FX_COST, lag=lag)
    s["XS momentum, G10 FX (3m, top/bottom 3)"] = cs.xs_momentum(fx, cost=FX_COST)
    fx_spy = panel[FX + ["SPY"]]
    s["TSMOM 12m, G10 FX + SPY (Ch 6)"] = cs.tsmom(fx_spy, costs={**{c: FX_COST for c in FX}, "SPY": COSTS["SPY"]})
    multi = panel[FX + ["SPY", "WTI", "NATGAS"]]
    s["TSMOM 12m, FX + SPY + spot oil/gas"] = cs.tsmom(multi, costs={**{c: FX_COST for c in FX}, **COSTS})
    s["SPY buy-on-gap (Ex 4.1)"] = cs.buy_on_gap(spy, cost=COSTS["SPY"])
    s["SPY opening-gap momentum (Ex 7.1)"] = cs.gap_momentum(spy, cost=COSTS["SPY"])
    bh = spy["close"].pct_change().fillna(0)
    s["Benchmark: SPY buy & hold (price only)"] = pd.DataFrame({"gross": bh, "cost": 0.0, "net": bh, "expo": 1.0})
    return s, panel


def diagnostics() -> pd.DataFrame:
    rows = []
    obs = pd.concat([cd.load_fx(), cd.load_commodities()], axis=1, sort=True).loc[START:]
    for a, b in [("AUD", "CAD"), ("BRENT", "WTI")]:
        px = obs[[a, b]].dropna()
        for label, (lo, hi) in [("IS (book era)", (None, cs.IS_END)), ("OOS 2013-now", ("2013-01-01", None))]:
            sub = px.loc[lo:hi]
            j = cs.johansen_trace(sub)
            spread = sub[a] + j["hedge_vec"][1] * sub[b]
            rows.append({"pair": f"{a}/{b}", "period": label, "start": sub.index[0].date(),
                         "end": sub.index[-1].date(), "johansen_trace": round(j["trace_stat"], 2),
                         "crit_95": round(j["crit_95"], 2), "cointegrated_95": j["cointegrated_95"],
                         "half_life_days": round(cs.half_life(spread), 1)})
    return pd.DataFrame(rows)


def plot(strats: dict, path: Path) -> None:
    keys = [k for k in strats if not k.startswith("Benchmark") and "delay" not in k]
    fig, axes = plt.subplots(5, 2, figsize=(13, 17))
    for ax, k in zip(axes.flat, keys):
        r = strats[k]["net"]
        active = strats[k]["expo"] > 0
        r = r.loc[active.idxmax():] if active.any() else r
        eq = (1 + r).cumprod()
        ax.plot(eq.index, eq.values, lw=1, color="#2563eb", label="as published")
        delayed = strats.get(f"{k} [+1d delay]")
        if delayed is not None:
            eq_d = (1 + delayed["net"].loc[eq.index[0]:]).cumprod()
            ax.plot(eq_d.index, eq_d.values, lw=1, color="#6b7280", ls=":", label="+1 day execution delay")
            ax.legend(fontsize=7, loc="upper left")
        ax.axvline(pd.Timestamp("2013-01-01"), color="#dc2626", ls="--", lw=1)
        ax.set_yscale("log")
        ax.set_title(k, fontsize=9)
        ax.grid(alpha=0.3)
    fig.suptitle("Chan (2013) strategies, net of costs, log scale. Red line = book published (OOS starts)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    strats, panel = build()
    rows = []
    for name, df in strats.items():
        for plabel, (lo, hi) in PERIODS.items():
            rows.append({"strategy": name, "period": plabel, **stats(df.loc[lo:hi])})
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "results.csv", index=False, float_format="%.4f")
    diag = diagnostics()
    diag.to_csv(OUT / "diagnostics.csv", index=False)
    plot(strats, OUT / "equity_curves.png")

    pivot = res.pivot(index="strategy", columns="period", values="sharpe")[list(PERIODS)]
    pivot = pivot.reindex(list(strats))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 10)
    pivot.index = [i[:55] for i in pivot.index]
    print(pivot.round(2))
    print()
    print(diag.to_string(index=False))
    return res, diag


if __name__ == "__main__":
    main()
