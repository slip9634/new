# Ernest Chan, *Algorithmic Trading* (2013): does anything still work?

Re-implementation of the book's main strategy families, with the book's
published rules, run over the era Chan could see (in-sample, start to 2012)
and the 13+ years after publication (out-of-sample, 2013 to Oct 2026).

Code: `src/chan_data.py`, `src/chan_strategies.py`, `src/chan_study.py`
(`cd src && python3 chan_study.py` reproduces everything below).
Raw numbers: `results.csv`, `diagnostics.csv`. Chart: `equity_curves.png`.

## Headline

**Nothing in this set survives as a tradable edge out-of-sample.** The pieces
that look alive turn out, on inspection, to be data artifacts, gross-only
edges that costs remove, or regime luck. Meanwhile buy-and-hold SPY had a
Sharpe of 0.76 over 2013-2026.

## Results: net Sharpe ratio (after costs)

| Strategy (book ref.) | IS ≤2012 | OOS 2013-19 | OOS 2020-26 | **OOS 2013-26** | Verdict |
|---|---:|---:|---:|---:|---|
| AUD/CAD pair, rolling Johansen + linear MR (Ex 5.1) | -0.08 | 0.06 | -0.64 | **-0.29** | ❌ dead (never really worked on this data) |
| AUD/CAD pair, Kalman hedge ratio (Ex 3.3 rules) | 0.03 | 0.10 | -0.13 | **-0.01** | ❌ gross Sharpe ~0.4, eaten by costs |
| Brent/WTI spot pair, Johansen + linear MR | 2.68 | 2.02 | 1.49 | **1.67** | ⚠️ artifact, see below |
| Brent/WTI spot pair, Kalman | 2.16 | 1.89 | 0.89 | **1.03** | ⚠️ artifact, see below |
| ↳ same, **with 1 extra day of execution delay** | 0.40 / -0.04 | | | **0.21 / -0.20** | edge disappears |
| Cross-sectional reversal, G10 FX (Khandani-Lo, Ex 4.3) | -1.15 | -0.18 | 0.29 | **0.04** | ❌ gross 1.03 OOS but costs kill it; with 1d delay -0.84 |
| Cross-sectional momentum, G10 FX (3m) | 0.04 | -0.54 | -0.40 | **-0.47** | ❌ |
| Time-series momentum 12m, G10 FX + SPY (Ch 6) | 0.29 | 0.19 | -0.04 | **0.06** | ⚠️ weak; narrow universe |
| Time-series momentum 12m, FX + SPY + spot oil/gas | 0.28 | 0.36 | 0.04 | **0.19** | ⚠️ weak positive |
| SPY buy-on-gap (Ex 4.1) | -1.01 | -0.72 | 0.58 | **0.14** | n/a: only 6 trades in 26 years on an index |
| SPY opening-gap momentum (Ex 7.1) | -0.35 | 0.44 | -0.42 | **-0.05** | ❌ |
| *Benchmark: SPY buy & hold (price only)* | 0.10 | 0.97 | 0.65 | **0.76** | |

Costs per side: 1bp for G10 FX and SPY, 3bp for oil, 10bp for natural gas.

## What the numbers say

### Mean reversion / pairs (Ch 2-5)
- **AUD/CAD**, Chan's flagship FX pair: the Johansen trace test does **not**
  find cointegration over 1990-2012 (8.97 vs 15.49 critical value; half-life
  about 210 days). It passes over 2013-2026 (23.8), yet the strategy still
  lost money there. A full-sample cointegration test tells you little about
  whether a 20-day-lookback trade will pay. The Kalman version has a real
  but tiny gross edge (Sharpe about 0.3-0.4) that disappears at 1bp per side.
- **Brent/WTI looks great and isn't real.** A net Sharpe of 1.7-2.7
  sustained for 35 years is too good to be true, and the robustness check
  shows why. Delaying execution by one day drops it to 0.2 (Johansen) and
  -0.2 (Kalman). EIA spot Brent is assessed in London and WTI in Cushing at
  different times of day, so the *measured* spread mean-reverts from one day
  to the next even though nobody can trade it. On front-month futures closes
  the result would be very different. This is the kind of trap Chan's
  Ch 1 (backtesting pitfalls) warns about: non-synchronous data.

### Cross-sectional mean reversion (Ch 4)
- The Khandani-Lo rule applied to G10 FX lost heavily in-sample (-1.15) and
  turned gross-positive after 2013 (gross Sharpe 1.03). The edge exists only
  at a 1-day horizon (delay it one day and it goes to -0.84), and turnover
  is so high that 1bp per side leaves a net Sharpe of about 0. That is
  consistent with Chan's own remark that this family needs very cheap
  execution. The stock version from the book wasn't testable (see
  limitations).

### Momentum (Ch 6-7)
- **Time-series momentum** is the only family with a positive net Sharpe in
  most periods, but at 0.06-0.19 out-of-sample it is weak and suffered
  -46% drawdowns at this sizing. That is consistent with the CTA industry's
  weak 2012-2019 and 2023-2025 periods. The universe here is limited to FX,
  SPY and spot energy, with no bond, rate or equity-index futures, which are
  historically the best trend sectors. A full futures universe would very
  likely do better, so read this as a lower bound.
- **FX cross-sectional momentum** has been negative since 2013.
- **Opening-gap momentum on SPY** was negative in-sample, briefly positive
  2013-19, and negative again since 2020: no stable edge.

## Robustness checks applied
- One-bar execution lag everywhere. Weights decided at the close of t earn
  t+1. Gap trades decide at the open using only the open and prior bars, and
  exit at the close.
- **+1 day execution delay** variant for every mean-reversion strategy. This
  is the test that exposed the Brent/WTI artifact.
- Pairs use only days where **both legs actually printed**. No
  forward-filled holiday prices, which would manufacture mean reversion.
- Book parameters were not re-optimized. The one exception is the Kalman
  filter's noise parameters (δ, Ve). Chan's values were tuned for ~$20 ETFs
  and give a degenerate filter on FX near 1.0, so they were fitted by
  maximum likelihood **on in-sample data only**. The calibrated innovations
  have a standard deviation of 0.96 and fall outside ±1σ on 23% of days, as
  a well-specified filter should.
- Results are reported over 2013-19 and 2020-26 separately as well as
  together, so one lucky regime can't carry the out-of-sample number.

## Limitations (data access from this sandbox)
Only raw.githubusercontent.com was reachable. Yahoo, stooq, FRED and broker
APIs were blocked. As a result:
- **No futures data.** Oil and gas are EIA *spot* prices, and FX is Fed H.10
  noon spot rates without carry. The VX/ES roll-yield trade (Ch 5) and
  calendar spreads could not be tested at all. The VIX index alone isn't
  tradable.
- **No stock universe**, so cross-sectional stock reversal and buy-on-gap
  could only be run on SPY, where the 1σ-gap rule fires 6 times in 26 years.
  Leveraged-ETF rebalancing and PEAD likewise need data we don't have.
- SPY is price-only (no dividends), which understates buy-and-hold by about
  2% a year.
- Costs are modeled assumptions (listed above), not measured fills.

## Bottom line
Applied as printed, the book's specific trades don't hold up after
publication on the data available here. The parts that do hold up are the
methods: stationarity and cointegration tests, half-lives, Kalman hedge
ratios, and above all the backtesting-pitfall discipline, which is exactly
what caught the Brent/WTI mirage. Trend following is the one family still
alive, at a modest Sharpe. To take this further, the most informative next
step is to re-run TSMOM and Brent/WTI on real futures closes and the
reversal strategies on a survivorship-free stock universe.
