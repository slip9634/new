"""
Wraps the EXACT strategy function used in the backtest (src/strategies.py),
so the live signal and the backtested signal are provably the same code, not
a re-implementation that could silently drift from what was validated.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import strategies as st  # noqa: E402

import config as cfg


def compute_signal(closed_bars_df):
    """closed_bars_df: DataFrame of fully-closed bars only (see data_feed.py).
    Returns (target_position, diagnostics) using only information available
    at the close of the last closed bar -- identical contract to the backtest:
    the caller executes this decision on the NEXT bar, never the one it was
    computed from."""
    if len(closed_bars_df) < cfg.MIN_HISTORY_BARS:
        raise ValueError(
            f"Only {len(closed_bars_df)} closed bars available, need >= {cfg.MIN_HISTORY_BARS} "
            f"for a {cfg.ENTRY_N}-bar entry window. Let data_feed accumulate more history first."
        )

    sig = st.donchian_breakout(closed_bars_df, entry_n=cfg.ENTRY_N, exit_n=cfg.EXIT_N, long_short=False)
    target_position = int(sig.iloc[-1])

    last = closed_bars_df.iloc[-1]
    upper_entry = closed_bars_df["high"].rolling(cfg.ENTRY_N).max().shift(1).iloc[-1]
    lower_entry = closed_bars_df["low"].rolling(cfg.ENTRY_N).min().shift(1).iloc[-1]
    upper_exit = closed_bars_df["high"].rolling(cfg.EXIT_N).max().shift(1).iloc[-1]
    lower_exit = closed_bars_df["low"].rolling(cfg.EXIT_N).min().shift(1).iloc[-1]

    diagnostics = {
        "bar_time": closed_bars_df.index[-1].isoformat(),
        "close": float(last["close"]),
        "upper_entry": float(upper_entry),
        "lower_entry": float(lower_entry),
        "upper_exit": float(upper_exit),
        "lower_exit": float(lower_exit),
        "target_position": target_position,
    }
    return target_position, diagnostics
