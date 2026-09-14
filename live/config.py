"""
Forward-test / live-trading configuration.

Everything here is overridable via environment variables so the same code
runs unchanged in paper mode (default, safe) and live mode. Nothing in this
repo ever hardcodes API credentials.

IMPORTANT: this module (and everything under live/) must run OUTSIDE the
sandboxed environment the backtest was built in -- that environment's network
egress policy blocks every exchange host outright (tested: Binance, Coinbase,
Kraken, Bitstamp, Bybit, OKX, CoinGecko all returned 403 from the proxy,
regardless of credentials). Run this on your own machine, a VPS, or wherever
you actually have unrestricted internet access.
"""
import os
from pathlib import Path

# --- Strategy spec, frozen from the backtest. Do not tune these live. ---
# Source: reports/study_results.csv, row timeframe=15m strategy=donchian_breakout_L
# OOS (2020-2025): Sharpe 1.39, CAGR 59.9%, MaxDD -40.2%, Calmar 1.49, ~37.8 trades/yr.
EXCHANGE_ID = os.environ.get("LIVE_EXCHANGE_ID", "bitstamp")  # matches the backtest venue
SYMBOL = os.environ.get("LIVE_SYMBOL", "BTC/USD")
TIMEFRAME = os.environ.get("LIVE_TIMEFRAME", "15m")
ENTRY_N = int(os.environ.get("LIVE_ENTRY_N", 672))   # 672 * 15min = 7 days
EXIT_N = int(os.environ.get("LIVE_EXIT_N", 336))     # 336 * 15min = 3.5 days
FEE_ONE_WAY = float(os.environ.get("LIVE_FEE_ONE_WAY", 0.0006))
MIN_HISTORY_BARS = ENTRY_N + 50  # buffer beyond the longest rolling window

# --- Execution ---
# "paper": simulate fills locally, never touches the exchange's trading endpoints.
# "live":  places real orders. Only switch this once verify_connectivity() has
#          passed AND you've read live/README.md's safety checklist.
EXECUTION_MODE = os.environ.get("EXECUTION_MODE", "paper").lower()
assert EXECUTION_MODE in ("paper", "live"), "EXECUTION_MODE must be 'paper' or 'live'"

API_KEY = os.environ.get("BITSTAMP_API_KEY", "")
API_SECRET = os.environ.get("BITSTAMP_API_SECRET", "")

# Fraction of available quote (USD) balance to deploy on an entry. Kept < 1.0
# so fees/slippage never cause an order to be rejected for insufficient funds.
ALLOCATION_FRACTION = float(os.environ.get("LIVE_ALLOCATION_FRACTION", 0.95))

# Paper-mode only: the notional (USD) the paper account starts with, so its
# equity curve and order sizes are human-readable. Irrelevant in live mode,
# where order sizing reads your REAL account balance via the broker.
PAPER_STARTING_USD = float(os.environ.get("LIVE_PAPER_STARTING_USD", 1000.0))

# --- Safety rails ---
# Normal cadence is ~1 trade / 9 days. If the signal fires more than this many
# times in a day, something is almost certainly broken (bad data, a bug in the
# rolling store) -- halt rather than trade on it.
MAX_DAILY_TRADES = int(os.environ.get("LIVE_MAX_DAILY_TRADES", 3))
# If tracked equity (paper or live) draws down more than this from its peak,
# halt and require a human to clear live/STOP before resuming. The worst OOS
# backtest drawdown for this strategy was -40.2%; this is set tighter than
# that so a live blowup well past the backtest's worst case stops trading.
DRAWDOWN_KILL_SWITCH = float(os.environ.get("LIVE_DRAWDOWN_KILL_SWITCH", 0.45))

# --- Paths ---
LIVE_DIR = Path(__file__).parent
STATE_DIR = Path(os.environ.get("LIVE_STATE_DIR", LIVE_DIR / "state"))
STATE_DIR.mkdir(parents=True, exist_ok=True)
OHLCV_STORE_PATH = STATE_DIR / f"{EXCHANGE_ID}_{SYMBOL.replace('/', '')}_{TIMEFRAME}.parquet"
STATE_JSON_PATH = STATE_DIR / "state.json"
SIGNAL_LOG_PATH = STATE_DIR / "signal_log.jsonl"
ORDERS_LOG_PATH = STATE_DIR / "orders_log.jsonl"
STOP_FILE = STATE_DIR / "STOP"
