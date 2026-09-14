# Forward-testing via IBKR (Paxos crypto desk), paper account

This is the IBKR-connected version of the forward test — a different execution
model than `live/` (which targets Bitstamp directly via `ccxt` and needs to
run on your own machine, since exchange APIs are blocked from this sandbox).
IBKR's data and account tools are reachable *from inside a Claude Code
session* via the "Interactive Brokers (IBKR)" connector, so this version runs
as a recurring **Routine**: a scheduled trigger that spawns a fresh Claude
session, which calls the IBKR tools directly, computes the signal, and stages
an order instruction when the position should change.

Same frozen spec as `live/`: 15-minute bars, Donchian breakout long/cash,
entry_n=672 (7 days), exit_n=336 (3.5 days). Contract: BTC on PAXOS,
`contract_id=479624278`.

## Critical difference from `live/`: IBKR never auto-executes

`create_order_instruction` does not place a live order. It stages a draft and
returns a deep-link URL for a human to review and submit inside the IBKR
platform. This is true even on the paper account — it's how the tool works,
not a safety choice layered on top. So "fully automated" here means: **Claude
watches the signal and prepares the order; you still click approve.**

## How it runs

A Routine (`mcp__Claude_Code_Remote__create_trigger`) fires on a schedule,
spawning a fresh Claude session each time (no memory of prior firings — all
state is read from files in `live_ibkr/state/`, which persists in this same
environment across firings). Each firing:

1. Calls `get_price_history` (contract_id 479624278, CRYPTO, 15-minute bars,
   ~1000 bars back — large results get saved to a file automatically, per
   the harness's own token-limit handling).
2. Runs `compute_signal.py` against that file — pure computation, drops any
   bar that hasn't closed yet, returns the target position (0/1) and the
   channel bounds it was computed from. This part is unit-testable and
   network-free; see `test_offline.py`... (not yet written for this variant —
   `compute_signal.py`'s logic is a thin wrapper around the same
   `src/strategies.donchian_breakout` already covered by the main study).
3. Calls `get_account_positions` to read the ACTUAL current BTC holding —
   this is the source of truth for "current position," not a locally
   persisted guess.
4. If target != current: stages a `create_order_instruction` (BUY to enter
   with a fixed ~$2,000 notional, SELL to exit the full position) and
   messages you the review link. If unchanged: logs a heartbeat, no message.
5. Safety: if it sees more than 2 position changes in the trailing 24 hours
   (this strategy trades ~once/9 days), it stops and flags a likely bug
   instead of staging another order.

State lives in `live_ibkr/state/`:
- `signal_log.jsonl` — every check, heartbeat or not.
- `orders_log.jsonl` — every staged instruction and its review URL.

## Setting the cadence

Created at hourly by default (`13 * * * *`, UTC, off-tick). The channel is a
multi-day signal, so hourly checking loses at most ~1 hour of reaction time
against the 15-minute bars it's computed from — immaterial at this holding
period. Change it any time:

```
mcp__Claude_Code_Remote__update_trigger(trigger_id=<id>, cron_expression="...")
```

List/inspect with `list_triggers`, disable with `update_trigger(..., enabled=false)`,
or fire it on demand with `fire_trigger` to check right now without waiting.

## What's NOT handled yet

- Order sizing is a flat ~$2,000 notional per entry, not tied to account
  equity or the backtest's position-sizing (which was 100% notional in/out).
  Adjust in the Routine's prompt if you want different sizing.
- No reconciliation if you manually trade BTC in this account outside the
  strategy — `get_account_positions` is trusted as ground truth every time,
  so a manual trade would look like the strategy's own position to the next
  check.
