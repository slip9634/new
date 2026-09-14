"""
Pure computation, no MCP/network calls -- this is the part that's actually
testable. The orchestrating Claude turn (triggered on a schedule) calls
IBKR's get_price_history itself, dumps the raw response to a JSON file, and
runs this script against it.

Usage: python3 compute_signal.py <ohlcv_json_path>
  ohlcv_json_path: the raw dict IBKR's get_price_history returns
                   ({"time": [...], "open": [...], "high": [...], "low": [...], "close": [...], "volume": [...]})

Prints one JSON line to stdout: target_position, diagnostics, and whether
there was enough history. Never trades on a bar that hasn't closed yet --
drops any bar whose interval end is after "now" before computing anything.
"""
import sys
import json
import datetime as dt
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import strategies as st  # noqa: E402

ENTRY_N = 672   # 7 days of 15-minute bars
EXIT_N = 336    # 3.5 days
TIMEFRAME_SECONDS = 900
MIN_BARS = ENTRY_N + 10


def load_ibkr_ohlcv(path: str) -> pd.DataFrame:
    raw = json.loads(Path(path).read_text())
    df = pd.DataFrame({
        "ts": pd.to_datetime(raw["time"], utc=True),
        "open": raw["open"], "high": raw["high"], "low": raw["low"],
        "close": raw["close"], "volume": raw["volume"],
    }).set_index("ts").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def drop_still_forming_bar(df: pd.DataFrame) -> pd.DataFrame:
    now = pd.Timestamp.now(tz="UTC")
    return df[df.index + pd.Timedelta(seconds=TIMEFRAME_SECONDS) <= now]


def compute(path: str) -> dict:
    df = load_ibkr_ohlcv(path)
    df = drop_still_forming_bar(df)

    if len(df) < MIN_BARS:
        return {"ok": False, "reason": f"only {len(df)} closed bars, need >= {MIN_BARS}", "n_bars": len(df)}

    sig = st.donchian_breakout(df, entry_n=ENTRY_N, exit_n=EXIT_N, long_short=False)
    target_position = int(sig.iloc[-1])

    upper_entry = df["high"].rolling(ENTRY_N).max().shift(1).iloc[-1]
    lower_entry = df["low"].rolling(ENTRY_N).min().shift(1).iloc[-1]
    upper_exit = df["high"].rolling(EXIT_N).max().shift(1).iloc[-1]
    lower_exit = df["low"].rolling(EXIT_N).min().shift(1).iloc[-1]

    return {
        "ok": True,
        "computed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "bar_time": df.index[-1].isoformat(),
        "close": float(df["close"].iloc[-1]),
        "upper_entry": float(upper_entry),
        "lower_entry": float(lower_entry),
        "upper_exit": float(upper_exit),
        "lower_exit": float(lower_exit),
        "target_position": target_position,
        "n_bars_used": len(df),
    }


if __name__ == "__main__":
    result = compute(sys.argv[1])
    print(json.dumps(result, indent=2))
