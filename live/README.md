# Forward-testing the 15m Donchian breakout on Bitstamp BTC/USD

Frozen strategy spec (do not tune these live — that defeats the point of a
forward test): 15-minute bars, long/cash, enter on a close above the highest
high of the prior 672 bars (7 days), exit on a close below the lowest low of
the prior 336 bars (3.5 days). Backtested OOS (2020–2025): Sharpe 1.39, CAGR
59.9%, max drawdown -40.2%, ~37.8 trades/year (about one trade every 9–10
days). Full backtest: `../reports/study_report.md`.

## This must run outside the sandbox it was built in

The environment this was developed in blocks every exchange host at the
network level (Binance, Coinbase, Kraken, Bitstamp, Bybit, OKX, CoinGecko all
returned 403 from the proxy — an organization network policy, not a
credentials problem). None of the code in `live/` has been run against a real
network. Run it on your own machine, a VPS, or wherever you have normal
internet access.

## Setup

```bash
pip install ccxt pandas pyarrow
cd live
python3 test_offline.py          # sanity check: no network needed, should print "All offline checks passed."
```

Environment variables (all optional except the two API keys, needed only for
live mode):

| Variable | Default | Purpose |
|---|---|---|
| `EXECUTION_MODE` | `paper` | `paper` or `live`. Stay on `paper` until you've completed the checklist below. |
| `BITSTAMP_API_KEY` / `BITSTAMP_API_SECRET` | — | Only needed for `live`. Create these in Bitstamp's account settings with **trading** permission only — not withdrawal. |
| `LIVE_ALLOCATION_FRACTION` | `0.95` | Fraction of available USD deployed on an entry. |
| `LIVE_PAPER_STARTING_USD` | `1000` | Paper-mode starting capital, for readable order sizes and an equity curve. |
| `LIVE_MAX_DAILY_TRADES` | `3` | Safety cap. Normal cadence is ~1 trade/9 days; hitting this means something is broken. |
| `LIVE_DRAWDOWN_KILL_SWITCH` | `0.45` | Halts trading (writes `live/state/STOP`) if tracked equity draws down more than this from its peak. Set tighter than the backtest's worst OOS drawdown (-40.2%) on purpose. |

## Running it

```bash
cd live
python3 run_once.py
```

Set up a cron entry to run it every 15 minutes:

```cron
*/15 * * * * cd /path/to/live && /usr/bin/python3 run_once.py >> run.log 2>&1
```

State lives in `live/state/` (created automatically):
- `<exchange>_<symbol>_<timeframe>.parquet` — the rolling closed-bar OHLCV store.
- `state.json` — current position, paper equity, trade-cap tracking.
- `signal_log.jsonl` — every bar's channel bounds and the resulting decision. Append-only, one line per run.
- `orders_log.jsonl` — every order (paper or live), with fill details.
- `STOP` — if this file exists, `run_once.py` refuses to do anything. Delete it manually to resume after investigating why it was written.

## Safety checklist before ever setting `EXECUTION_MODE=live`

1. **Run in paper mode for at least 8–12 weeks.** At ~1 trade/9 days that's the
   minimum to see several real signal events, not just the data pipeline
   working.
2. **Cross-check `signal_log.jsonl` against an independent recompute.** Pull
   the same window from your rolling parquet store and run
   `src/strategies.donchian_breakout` on it standalone (outside `run_once.py`)
   to confirm the numbers match. This catches implementation drift, not edge
   decay.
3. **Verify connectivity read-only first:**
   ```python
   from broker import LiveBroker
   LiveBroker().verify_connectivity()   # fetches balance only, places no orders
   ```
   Confirm it prints your actual balances before proceeding.
4. **Create API keys with trading permission only, never withdrawal.** If the
   key/secret ever leak, the blast radius is capped at what's in the trading
   account.
5. **Start with a small `LIVE_ALLOCATION_FRACTION` or a small sub-account**,
   not your full intended size. Scale up only once live fills track the
   0.06%-fee assumption reasonably closely (check `orders_log.jsonl`'s actual
   fee vs. notional).
6. **Check `run.log` and `state/STOP` daily** for at least the first month.
   The kill switch and daily-trade cap are there to fail loud, not silent —
   don't let a cron job run unattended for months without anyone reading it.

## What this does NOT do

- No position sizing beyond "all-in / all-out" on the frozen allocation
  fraction — no scaling in/out, no leverage.
- No slippage modeling beyond the exchange's own fill price — market orders
  on a breakout can fill worse than the last closed bar's price, especially
  in fast moves. Compare `orders_log.jsonl` fills to `signal_log.jsonl`
  closes over time to see how much this costs in practice.
- No multi-asset or multi-venue logic. This is BTC/USD on Bitstamp, matching
  the backtest exactly, on purpose.
