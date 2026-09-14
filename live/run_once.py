#!/usr/bin/env python3
"""
Entry point: run this once per bar (cron: */15 * * * * for the 15m default).

Each run:
  1. Refuses to do anything if live/state/STOP exists (manual or kill-switch halt).
  2. Pulls new closed bars, recomputes the frozen backtested signal.
  3. If the target position hasn't changed: updates the paper-equity tracker
     for the bar that just closed and exits -- no order, no fee.
  4. If it changed: sizes an order off actual available balance (paper or
     live), executes it through the broker, and journals everything.
  5. Checks the daily trade cap and drawdown kill switch; trips STOP if either
     is breached, rather than trading through a state the backtest never saw.

Safe to run from cron unattended in paper mode. In live mode, only after you
have (a) run in paper for weeks and manually diffed signal_log.jsonl against
an independent recompute from src/strategies.py on the same window, and
(b) called broker.LiveBroker().verify_connectivity() successfully.
"""
import sys
import datetime as dt

import config as cfg
import data_feed
import signal_engine
import journal
import broker as broker_mod


def main():
    if cfg.STOP_FILE.exists():
        print(f"[{dt.datetime.now(dt.timezone.utc).isoformat()}] STOP file present "
              f"({cfg.STOP_FILE}) -- halted, doing nothing.")
        sys.exit(0)

    state = journal.load_state()
    closed_bars = data_feed.update_and_load()
    target_position, diag = signal_engine.compute_signal(closed_bars)
    prev_position = state["position"]
    journal.log_signal(diag, prev_position)
    print(f"[{diag['bar_time']}] close={diag['close']:.2f} "
          f"entry_band=({diag['lower_entry']:.2f},{diag['upper_entry']:.2f}) "
          f"exit_band=({diag['lower_exit']:.2f},{diag['upper_exit']:.2f}) "
          f"prev_pos={prev_position} target_pos={target_position}")

    if state["last_processed_bar"] == diag["bar_time"]:
        print("Already processed this bar -- exiting (cron ran twice for the same bar).")
        sys.exit(0)

    # Book the return of the bar that just closed, under the position that was
    # ACTUALLY held during it (prev_position) -- mirrors backtest.py exactly:
    # strategy_return[t] = position[t] * bar_return[t] - turnover[t] * fee.
    closes = closed_bars["close"]
    bar_return = closes.iloc[-1] / closes.iloc[-2] - 1 if len(closes) >= 2 else 0.0
    turnover = abs(target_position - prev_position)
    net_bar_return = prev_position * bar_return - turnover * cfg.FEE_ONE_WAY
    kill = journal.update_equity_and_check_kill_switch(state, net_bar_return)

    broker = broker_mod.get_broker()

    if target_position != prev_position:
        state = journal.bump_daily_trade_count(state)
        if state["trade_count_today"] > cfg.MAX_DAILY_TRADES:
            cfg.STOP_FILE.write_text(
                f"Halted {dt.datetime.now(dt.timezone.utc).isoformat()}: "
                f"{state['trade_count_today']} trades today > MAX_DAILY_TRADES="
                f"{cfg.MAX_DAILY_TRADES}. This strategy trades ~once/9 days -- "
                f"this many signals in one day means check the data feed for a bug "
                f"before removing this file.\n"
            )
            print("Daily trade cap exceeded -- halted, STOP file written, no order sent.")
            journal.save_state(state)
            sys.exit(1)

        side = "buy" if target_position == 1 else "sell"
        if side == "buy":
            quote_avail = broker.get_available_quote_usd(state)
            notional_usd = quote_avail * cfg.ALLOCATION_FRACTION
            fill = broker.execute(side, diag["close"], notional_usd)
            state["base_amount"] = fill.get("amount_base") or fill.get("amount_base_requested", 0.0)
        else:
            base_avail = broker.get_available_base(state)
            notional_usd = base_avail * diag["close"]
            fill = broker.execute(side, diag["close"], notional_usd)
            state["base_amount"] = 0.0

        print(f"EXECUTED {side.upper()} {cfg.SYMBOL} mode={broker.mode} "
              f"notional~${notional_usd:,.2f} order_id={fill.get('order_id')}")
        state["position"] = target_position
    else:
        print("No position change -- heartbeat only.")

    state["last_processed_bar"] = diag["bar_time"]
    journal.save_state(state)

    if kill:
        cfg.STOP_FILE.write_text(
            f"Halted {dt.datetime.now(dt.timezone.utc).isoformat()}: tracked equity drew down "
            f"more than {cfg.DRAWDOWN_KILL_SWITCH*100:.0f}% from its peak "
            f"(backtest's worst OOS drawdown was -40.2%). Investigate before removing this file.\n"
        )
        print("!!! DRAWDOWN KILL SWITCH TRIPPED. STOP file written. Investigate before resuming. !!!")
        sys.exit(1)


if __name__ == "__main__":
    main()
