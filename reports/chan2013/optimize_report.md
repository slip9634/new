# Tuning the Chan (2013) strategies: what optimisation actually buys

Code: `src/chan_optimize.py` (run from `src/`). Raw output:
`optimize_results.csv`, `walkforward_choices.csv`, `optimize_portfolio.csv`,
`optimize_curves.png`.

## Method: three ways to "optimise", side by side
1. **IS-frozen**: pick the best parameters on ≤2012, freeze them, trade
   2013→2026. This is what you could have done the day the book came out.
2. **Walk-forward** (the honest tuned number): every 1 January, re-pick the
   top-3 parameter sets by Sharpe on all prior data and trade their average
   for the year. No OOS return is ever earned with parameters that saw it.
3. **Hindsight**: the best parameter set on 2013→2026 itself. This is what a
   naive optimiser reports. It is shown only to measure overfitting, with
   the **Deflated Sharpe Ratio** p-value (Bailey & López de Prado), which
   corrects for the number of trials.

About 150 parameter sets across 6 families; the Kalman pairs book trades all
36 G10 FX pairs. Costs are the same as the base study (1bp per side for FX
and SPY). Search knobs added: TSMOM lookback blends, continuous signal,
weekly/monthly rebalancing and volatility windows; reversal horizon and
weight smoothing; momentum lookback, skip window and number of names per
side; Kalman entry/exit bands; gap follow vs fade and gap size.

## Results: net Sharpe ratio, 2013 → Oct 2026

| Family | Book default | IS-frozen | **Walk-forward** | Hindsight best | DSR p | % of trials > 0 OOS |
|---|---:|---:|---:|---:|---:|---:|
| **XS reversal, G10 FX** | 0.04 | 0.20 | **0.39** | 0.65 | 0.75 | **93% (37/40)** |
| AUD/CAD pair (Kalman/Johansen) | -0.01 | 0.03 | **0.29** | 0.44 | 0.52 | 44% |
| TSMOM (FX + SPY + energy) | 0.19 | -0.17 | -0.10 | 0.24 | 0.35 | 31% |
| Kalman pairs book, 36 FX pairs | -0.05 | -0.25 | -0.06 | 0.22 | 0.54 | 29% |
| SPY opening gap | -0.05 | 0.04 | -0.39 | 0.14 | 0.30 | 40% |
| XS momentum, G10 FX | -0.47 | -0.46 | -0.55 | 0.16 | 0.17 | 14% |

How to read it: a "hindsight best" with a DSR p-value well under 0.95 is
indistinguishable from the best of N random strategies. **None of the
hindsight winners clears that bar.** The only meaningful numbers are in the
walk-forward column.

## The one survivor: cross-sectional FX reversal at a weekly horizon

The book's rule (Ex 4.3, Khandani-Lo, reversing 1-day returns, rebalanced
daily) nets about 0 because costs eat it. **Reverse 3- to 10-day relative
moves and smooth the weights** (EWMA half-life of 2–10 days, which cuts
turnover) and it works:

- **Robust across parameters:** 37 of 40 settings are positive OOS. The OOS
  grid is a smooth plateau (0.35–0.65), not an isolated spike.
- **Positive in both eras:** about 0.12–0.19 net in-sample (1990–2012) for
  horizons of 2–5 days with smoothing, and 0.35–0.6 since 2013.
- **Not driven by one currency:** dropping any single currency leaves OOS
  Sharpe between 0.33 and 0.45.
- **Not an execution artifact:** with one extra day of delay, Sharpe goes
  from 0.42 to 0.36. Both halves of the OOS period are similar (0.41 / 0.43).
- **But it lives or dies on costs.** At about 29× annual turnover:

  | Cost per side | 1bp | 2bp | 3bp | 5bp |
  |---|---:|---:|---:|---:|
  | OOS Sharpe (horizon 5, smoothing 5) | 0.42 | 0.26 | 0.10 | -0.22 |

  Its raw volatility is only 1.8% a year, so useful returns need about 5×
  leverage. That is only viable with institutional FX execution (sub-1bp in
  majors, plus tight Scandinavian crosses) or by trading it as a
  netting overlay on flows you already have. At retail spreads it doesn't
  pay.

Runner-up: **AUD/CAD Kalman with wider bands** (enter at 2σ, exit at 0).
The walk-forward process picked it consistently from 2011 onward, and it
scores 0.29 OOS. But fewer than half the variants are positive, so treat it
as weak evidence.

## What optimisation did not fix
- **Trend following** got *worse* when tuned. The parameters that looked
  best through 2012 (63-day continuous signal) underperformed the plain
  12-month rule after 2013. That is classic overfitting to a regime. The
  limiting factor is the universe (no bond, rate or equity-index futures),
  not the parameters.
- **FX cross-sectional momentum:** 86% of variants are negative OOS. It's dead.
- **The SPY gap trade** flips between "fade" and "follow" depending on the
  window. Walk-forward picked "fade big gaps" (trailing Sharpe 0.75 in 2011)
  and lost: -0.39 OOS.
- **Combining everything into a risk-parity book** (walk-forward, 10% vol
  target) gives -0.24 OOS, and -0.17 when sleeves are only included while
  their trailing 3-year Sharpe is > 0. Diversifying across things with no
  edge doesn't create one. Even the hindsight pick of just the two survivors
  scored 0.32 for 2013–19 and -0.09 for 2020+ once leveraged to 10% vol.

## Bottom line
Tuning turned one family (FX reversal) from break-even into a robust but
thin, cost-sensitive edge (walk-forward OOS Sharpe about 0.4 at 1bp). It
did nothing for the rest. Most of the apparent gains from optimisation are
the overfitting the DSR column flags. The next gains would come from better
data and more assets: futures for trend and carry, interest rates for FX
carry, and a stock universe for equity reversal. More parameter search on
the same data won't help.
