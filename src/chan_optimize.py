"""
Tune / tweak the Chan (2013) strategies -- without fooling ourselves.

Three ways of "optimising", reported side by side:

  1. IS-frozen    pick the best parameter set on <=2012 (what you could have
                  done the day the book came out), freeze it, run 2013->now.
  2. Walk-forward every 1 January, re-pick the top-3 parameter sets by
                  Sharpe on ALL data before that date (expanding window),
                  trade their equal-weight average for the year. Every
                  return in the OOS series was earned with parameters chosen
                  without seeing it. This is the honest "tuned" number.
  3. Hindsight    the best parameter set on 2013->now itself. This is what
                  naive optimisation reports; it is shown only to measure the
                  overfit, with its Deflated Sharpe Ratio (Bailey & Lopez de
                  Prado 2014) given the number of trials.

Finally the walk-forward sleeves are combined into one risk-parity portfolio.

Outputs in reports/chan2013/: optimize_results.csv, walkforward_choices.csv,
optimize_curves.png, optimize_report.md (hand-written from these).

Run from src/:  python3 chan_optimize.py
"""
from itertools import combinations, product
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm

import chan_data as cd
import chan_strategies as cs
from chan_study import COSTS, FX, FX_COST, START

OUT = Path("/home/user/new/reports/chan2013")
OOS_START = "2013-01-01"
WF_FIRST_YEAR = 1996  # walk-forward runs from here; needs >=3y of history
TOP_K = 3


def ann_sharpe(r: pd.Series) -> float:
    r = r.dropna()
    return float(r.mean() / r.std() * np.sqrt(252)) if len(r) > 60 and r.std() > 0 else np.nan


# ---------------------------------------------------------------------------
# Parameter grids: family -> {label: net daily return series}
# ---------------------------------------------------------------------------

def grid_tsmom(panel):
    uni = panel[FX + ["SPY", "WTI", "NATGAS"]]
    costs = {**{c: FX_COST for c in FX}, **COSTS}
    out = {}
    lbs = [21, 63, 126, 252, (63, 126, 252), (21, 63, 126, 252)]
    for lb, sig, reb, vlb in product(lbs, ["sign", "cont"], ["M", "W"], [21, 63]):
        out[f"lb={lb} sig={sig} reb={reb} vol={vlb}"] = cs.tsmom(
            uni, lookback=lb, signal=sig, rebalance=reb, vol_lb=vlb, costs=costs)["net"]
    return out


def grid_xs_rev(fx_obs):
    out = {}
    for h, hl in product([1, 2, 3, 5, 10, 21, 63, 126], [0, 1, 2, 5, 10]):
        out[f"horizon={h} smooth={hl}"] = cs.xs_reversal(fx_obs, cost=FX_COST, horizon=h, smooth_hl=hl)["net"]
    return out


def grid_xs_mom(fx):
    out = {}
    for lb, n, skip in product([21, 63, 126, 252], [2, 3], [0, 5, 21]):
        if skip >= lb:
            continue
        out[f"lb={lb} n={n} skip={skip}"] = cs.xs_momentum(fx, lookback=lb, n_side=n, skip=skip, cost=FX_COST)["net"]
    return out


def grid_kalman_book(fx_obs):
    """Equal-weight book of Kalman pair trades over ALL 36 G10 FX pairs."""
    bands = [(1.0, 1.0), (1.0, 0.0), (1.5, 0.5), (1.5, 0.0), (2.0, 1.0), (2.0, 0.0), (2.5, 0.5)]
    per_band = {b: [] for b in bands}
    for a, b in combinations(FX, 2):
        px = fx_obs[[a, b]].dropna()
        for band in bands:
            per_band[band].append(cs.pair_kalman(px[a], px[b], cost=FX_COST, entry=band[0], exit_=band[1])["net"])
    return {f"entry={e} exit={x}": pd.concat(v, axis=1).mean(axis=1) for (e, x), v in per_band.items()}


def grid_audcad(fx_obs):
    px = fx_obs[["AUD", "CAD"]].dropna()
    out = {}
    for band in [(1.0, 1.0), (1.0, 0.0), (1.5, 0.5), (2.0, 0.0), (2.5, 0.5)]:
        out[f"kalman entry={band[0]} exit={band[1]}"] = cs.pair_kalman(
            px["AUD"], px["CAD"], cost=FX_COST, entry=band[0], exit_=band[1])["net"]
    for zl in [5, 10, 20, 60]:
        out[f"johansen z_lb={zl}"] = cs.pair_johansen_linear(px, lookback_z=zl, cost=FX_COST)["net"]
    return out


def grid_gap(spy):
    out = {}
    for z, d in product([0.1, 0.25, 0.5, 0.75, 1.0], [1.0, -1.0]):
        out[f"entry_z={z} {'follow' if d > 0 else 'fade'}"] = cs.gap_momentum(spy, entry_z=z, direction=d, cost=COSTS["SPY"])["net"]
    return out


# ---------------------------------------------------------------------------
# Selection methods
# ---------------------------------------------------------------------------

def walk_forward(grid: dict, k: int = TOP_K):
    df = pd.concat(grid, axis=1).sort_index()
    first = df.apply(lambda c: c.ne(0).idxmax())  # first active day per param
    pieces, choices = [], []
    for year in range(WF_FIRST_YEAR, df.index[-1].year + 1):
        start = pd.Timestamp(f"{year}-01-01")
        hist = df.loc[:start - pd.Timedelta(days=1)]
        scores = {}
        for c in df.columns:
            h = hist[c].loc[first[c]:]
            if len(h) >= 3 * 252:
                scores[c] = ann_sharpe(h)
        if not scores:
            continue
        top = pd.Series(scores).dropna().sort_values(ascending=False).head(k)
        yr = df.loc[f"{year}", top.index].mean(axis=1)
        pieces.append(yr)
        choices.append({"year": year, "picked": " | ".join(top.index), "trailing_sharpe": " | ".join(f"{v:.2f}" for v in top)})
    return pd.concat(pieces), pd.DataFrame(choices)


def deflated_sharpe(r: pd.Series, trial_srs: np.ndarray) -> float:
    """Probability that the best-of-N Sharpe is > 0 after correcting for the
    number of trials (Bailey & Lopez de Prado 2014). Inputs are daily."""
    r = r.dropna()
    n = len(trial_srs)
    sr = r.mean() / r.std()
    var_sr = np.nanvar(trial_srs)
    g = 0.5772156649
    sr0 = np.sqrt(var_sr) * ((1 - g) * norm.ppf(1 - 1 / n) + g * norm.ppf(1 - 1 / (n * np.e)))
    skew, kurt = r.skew(), r.kurt() + 3
    denom = np.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr ** 2)
    return float(norm.cdf((sr - sr0) * np.sqrt(len(r) - 1) / denom))


def evaluate(name: str, grid: dict, baseline_label: str):
    df = pd.concat(grid, axis=1).sort_index()
    is_ = df.loc[:"2012"]
    oos = df.loc[OOS_START:]
    is_sr = is_.apply(lambda c: ann_sharpe(c.loc[c.ne(0).idxmax():]))
    oos_sr = oos.apply(ann_sharpe)
    is_best = is_sr.idxmax()
    hind_best = oos_sr.idxmax()
    wf, choices = walk_forward(grid)
    wf_oos = wf.loc[OOS_START:]
    daily_trials = oos.apply(lambda c: c.mean() / c.std()).values
    row = {
        "family": name,
        "n_trials": df.shape[1],
        "book_default": baseline_label,
        "book_default_oos_sharpe": oos_sr.get(baseline_label, np.nan),
        "is_best_params": is_best,
        "is_best_is_sharpe": is_sr[is_best],
        "is_best_oos_sharpe": oos_sr[is_best],
        "walkforward_oos_sharpe": ann_sharpe(wf_oos),
        "wf_2013_19": ann_sharpe(wf.loc["2013":"2019"]),
        "wf_2020_now": ann_sharpe(wf.loc["2020":]),
        "hindsight_best_params": hind_best,
        "hindsight_best_oos_sharpe": oos_sr[hind_best],
        "hindsight_deflated_sr_prob": deflated_sharpe(oos[hind_best], daily_trials),
        "median_trial_oos_sharpe": float(np.nanmedian(oos_sr)),
        "frac_trials_oos_positive": float((oos_sr > 0).mean()),
    }
    choices.insert(0, "family", name)
    return row, wf, choices


def risk_parity(sleeves: dict, vol_lb: int = 252, target: float = 0.10,
                select: bool = False) -> pd.Series:
    """Inverse-vol weights from trailing data, refreshed monthly, then the
    whole book scaled to `target` vol using trailing realised vol (lagged).
    select=True: a sleeve only gets weight while its own trailing 3-year
    walk-forward Sharpe is > 0 (the selection is walk-forward too)."""
    df = pd.concat(sleeves, axis=1).sort_index().fillna(0.0)
    vol = df.rolling(vol_lb, min_periods=126).std()
    inv = 1 / vol.replace(0, np.nan)
    if select:
        trail = df.rolling(3 * 252, min_periods=252).mean() / df.rolling(3 * 252, min_periods=252).std()
        inv = inv.where(trail > 0)
    w = inv.div(inv.sum(axis=1), axis=0)
    w = cs._hold_monthly(w).shift(1)
    port = (w * df).sum(axis=1)
    pvol = port.rolling(vol_lb, min_periods=126).std().shift(1) * np.sqrt(252)
    scale = (target / pvol).clip(upper=20).fillna(0)
    return port * scale


def main():
    panel = cd.daily_panel().loc[START:]
    fx_obs = cd.load_fx().loc[START:]
    spy = cd.load_spy()

    families = {
        "TSMOM (FX+SPY+energy)": (grid_tsmom(panel), "lb=252 sig=sign reb=M vol=63"),
        "XS reversal G10 FX": (grid_xs_rev(fx_obs), "horizon=1 smooth=0"),
        "XS momentum G10 FX": (grid_xs_mom(panel[FX]), "lb=63 n=3 skip=0"),
        "Kalman pairs book, all 36 G10 FX pairs": (grid_kalman_book(fx_obs), "entry=1.0 exit=1.0"),
        "AUD/CAD pair (Kalman + Johansen variants)": (grid_audcad(fx_obs), "kalman entry=1.0 exit=1.0"),
        "SPY opening gap (follow / fade)": (grid_gap(spy), "entry_z=0.1 follow"),
    }

    rows, wfs, choices = [], {}, []
    for name, (grid, base) in families.items():
        row, wf, ch = evaluate(name, grid, base)
        rows.append(row)
        wfs[name] = wf
        choices.append(ch)
        print(f"{name:45s} book={row['book_default_oos_sharpe']:+.2f}  IS-frozen={row['is_best_oos_sharpe']:+.2f}  "
              f"walk-fwd={row['walkforward_oos_sharpe']:+.2f}  hindsight={row['hindsight_best_oos_sharpe']:+.2f} "
              f"(DSR p={row['hindsight_deflated_sr_prob']:.2f}, {row['n_trials']} trials)")

    ports = {"all sleeves": risk_parity(wfs), "selective (trailing 3y SR>0)": risk_parity(wfs, select=True)}
    port = ports["selective (trailing 3y SR>0)"]
    port_rows = []
    for (pname, pr), (label, (lo, hi)) in product(ports.items(), {
            "1996-2012": ("1996", "2012"), "2013-2019": ("2013", "2019"),
            "2020-now": ("2020", None), "2013-now": ("2013", None)}.items()):
        r = pr.loc[lo:hi]
        eq = (1 + r).cumprod()
        port_rows.append({"portfolio": pname, "period": label, "sharpe": ann_sharpe(r),
                          "cagr": eq.iloc[-1] ** (252 / len(r)) - 1, "vol": r.std() * np.sqrt(252),
                          "max_dd": (eq / eq.cummax() - 1).min()})
    port_df = pd.DataFrame(port_rows)
    print("\nWalk-forward risk-parity portfolios (10% vol target, leverage cap 20x):")
    print(port_df.round(3).to_string(index=False))
    yearly = port.groupby(port.index.year).apply(lambda r: (1 + r).prod() - 1)
    print("\nSelective portfolio calendar-year returns:", yearly.loc[2013:].round(3).to_dict())

    pd.DataFrame(rows).to_csv(OUT / "optimize_results.csv", index=False, float_format="%.4f")
    pd.concat(choices).to_csv(OUT / "walkforward_choices.csv", index=False)
    port_df.to_csv(OUT / "optimize_portfolio.csv", index=False, float_format="%.4f")

    fig, axes = plt.subplots(4, 2, figsize=(13, 14))
    for ax, (name, wf) in zip(axes.flat, list(wfs.items()) + [("Selective risk-parity portfolio of walk-forward sleeves (10% vol)", port.loc["1996":])]):
        eq = (1 + wf.loc["1996":]).cumprod()
        ax.plot(eq.index, eq.values, lw=1, color="#2563eb")
        ax.axvline(pd.Timestamp(OOS_START), color="#dc2626", ls="--", lw=1)
        ax.set_yscale("log")
        ax.set_title(f"{name}  [walk-forward]", fontsize=9)
        ax.grid(alpha=0.3)
    axes.flat[-1].axis("off")
    fig.suptitle("Walk-forward tuned strategies, net of costs (params re-picked each Jan from past data only)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(OUT / "optimize_curves.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
