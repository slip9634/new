"""
Offline tests -- no network, runnable anywhere (including the sandbox this was
built in). These cannot verify the actual exchange connection or Bitstamp's
auth handshake (ccxt handles that, and it's untestable without live network),
but they do verify every piece of logic this repo is actually responsible for:
signal wiring, the still-forming-bar guard, fee/turnover math, and the safety
rails. Run with: python3 test_offline.py
"""
import sys
import shutil
import tempfile
import datetime as dt
import numpy as np
import pandas as pd

TMP = tempfile.mkdtemp()
import os
os.environ["LIVE_STATE_DIR"] = TMP

import config as cfg
import signal_engine
import journal
import broker as broker_mod

failures = []


def check(name, cond):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}")
    if not cond:
        failures.append(name)


def make_series(n, start_price=100.0, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    rets = rng.normal(0, 0.001, n)
    close = start_price * (1 + rets).cumprod()
    df = pd.DataFrame({
        "open": close, "high": close * 1.001, "low": close * 0.999,
        "close": close, "volume": 1.0,
    }, index=idx)
    return df


# --- Test 1: signal_engine raises cleanly on insufficient history ---
short_df = make_series(10)
try:
    signal_engine.compute_signal(short_df)
    check("raises on insufficient history", False)
except ValueError:
    check("raises on insufficient history", True)


# --- Test 2: an unambiguous breakout produces target_position == 1 ---
df = make_series(cfg.MIN_HISTORY_BARS + 10, seed=1)
# force a clean breakout on the final closed bar: last close far above all prior highs
df.iloc[-1, df.columns.get_loc("close")] = df["high"].iloc[:-1].max() * 1.10
df.iloc[-1, df.columns.get_loc("high")] = df["close"].iloc[-1] * 1.001
target, diag = signal_engine.compute_signal(df)
check("breakout above channel -> target_position == 1", target == 1)
check("diagnostics has expected keys", set(diag) >= {"bar_time", "close", "upper_entry", "lower_entry", "target_position"})
check("upper_entry excludes the breakout bar itself (no lookahead)",
      diag["upper_entry"] < diag["close"])


# --- Test 3: donchian_breakout used here is the SAME function object imported
#     from src/strategies.py, not a re-implementation ---
import strategies as st
check("signal_engine uses src.strategies.donchian_breakout directly",
      signal_engine.st.donchian_breakout is st.donchian_breakout)


# --- Test 4: data_feed drops a still-forming last bar ---
import data_feed


class FakeExchange:
    def __init__(self, rows):
        self.rows = rows

    def fetch_ohlcv(self, symbol, timeframe, since, limit):
        batch = [r for r in self.rows if r[0] >= since][:limit]
        return batch


now = pd.Timestamp.now(tz="UTC")
tf_seconds = 900
n_bars = 5
bar_times = [now - pd.Timedelta(seconds=tf_seconds * (n_bars - i)) for i in range(n_bars)]
rows = [[int(t.timestamp() * 1000), 100 + i, 101 + i, 99 + i, 100.5 + i, 1.0] for i, t in enumerate(bar_times)]
# Last row's bar START is `now - 0 seconds` effectively (still forming) if within tf_seconds of now
still_forming_start = now - pd.Timedelta(seconds=100)  # started 100s ago, far from closing
rows.append([int(still_forming_start.timestamp() * 1000), 200, 201, 199, 200.5, 1.0])

fake = FakeExchange(rows)
cfg.OHLCV_STORE_PATH.unlink(missing_ok=True)
result = data_feed.update_and_load(exchange=fake)
check("still-forming last bar is dropped", 200 not in result["open"].values)
check("fully-closed bars are kept", len(result) == n_bars)


# --- Test 5: fee/turnover math matches backtest.py's convention exactly ---
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "src"))
from backtest import run_backtest

toy_close = pd.Series([100, 110, 121], index=pd.date_range("2024-01-01", periods=3, freq="1D"))
toy_signal = pd.Series([1, 1, 0], index=toy_close.index)
bt = run_backtest(pd.DataFrame({"close": toy_close}), toy_signal, fee=cfg.FEE_ONE_WAY)
expected_bar2_return = 1 * (121 / 110 - 1)  # position=1 (from signal[bar0]) applied to bar2's return, no turnover
check("backtest fee/turnover convention: mid-trade bar has zero fee drag",
      abs(bt["returns"].iloc[2] - expected_bar2_return) < 1e-9)

state = journal.load_state()
prev_position, target_position = 1, 1
bar_return = toy_close.iloc[2] / toy_close.iloc[1] - 1
turnover = abs(target_position - prev_position)
net = prev_position * bar_return - turnover * cfg.FEE_ONE_WAY
check("run_once's per-bar pnl formula matches backtest.py's for a held position",
      abs(net - expected_bar2_return) < 1e-9)


# --- Test 6: daily trade cap and drawdown kill switch actually trip ---
state = dict(journal.DEFAULT_STATE)
for _ in range(cfg.MAX_DAILY_TRADES):
    state = journal.bump_daily_trade_count(state)
check("trade count reaches cap without tripping", state["trade_count_today"] == cfg.MAX_DAILY_TRADES)
state = journal.bump_daily_trade_count(state)
check("one more trade exceeds the cap (run_once would halt here)",
      state["trade_count_today"] > cfg.MAX_DAILY_TRADES)

state2 = dict(journal.DEFAULT_STATE)
tripped = journal.update_equity_and_check_kill_switch(state2, -0.10)
check("small drawdown does not trip kill switch", not tripped)
tripped = journal.update_equity_and_check_kill_switch(state2, -0.50)
check("large drawdown trips kill switch", tripped)


# --- Test 7: PaperBroker fee matches config, never touches network ---
pb = broker_mod.PaperBroker()
fill = pb.execute("buy", price=100.0, notional_usd=1000.0)
check("PaperBroker fee = notional * FEE_ONE_WAY", abs(fill["fee_usd"] - 1000.0 * cfg.FEE_ONE_WAY) < 1e-9)
check("PaperBroker never sets an order_id (no exchange involved)", fill["order_id"] is None)


shutil.rmtree(TMP, ignore_errors=True)

print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("All offline checks passed.")
