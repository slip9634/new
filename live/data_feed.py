"""
Live OHLCV feed with a local rolling store, kept in the exact shape the
backtest strategy functions expect: a DataFrame indexed by UTC bar-open
timestamp with columns open/high/low/close/volume.

fetch_ohlcv is a PUBLIC exchange endpoint -- no API key needed, whether you're
in paper or live mode. Only order placement (broker.py) needs credentials.

Critical no-lookahead rule enforced here: the most recent bar an exchange
returns is usually still forming (not yet closed). We drop it unconditionally.
Trading on a bar before it closes is exactly the kind of leakage the backtest
was built to rule out; the live system must hold itself to the same bar.
"""
import time
import pandas as pd
import config as cfg


def _timeframe_seconds(tf: str) -> int:
    unit = tf[-1]
    n = int(tf[:-1])
    return {"m": 60, "h": 3600, "d": 86400}[unit] * n


def make_exchange():
    import ccxt
    klass = getattr(ccxt, cfg.EXCHANGE_ID)
    # Public data never needs credentials; pass them through anyway so the
    # same client object can be reused by broker.py in live mode.
    return klass({"apiKey": cfg.API_KEY, "secret": cfg.API_SECRET, "enableRateLimit": True})


def _load_store() -> pd.DataFrame:
    if cfg.OHLCV_STORE_PATH.exists():
        return pd.read_parquet(cfg.OHLCV_STORE_PATH)
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"]).set_index(
        pd.DatetimeIndex([], tz="UTC", name="ts")
    )


def _save_store(df: pd.DataFrame) -> None:
    df.to_parquet(cfg.OHLCV_STORE_PATH)


def update_and_load(exchange=None) -> pd.DataFrame:
    """Fetch new bars, merge into the local store, drop the still-forming
    last bar, and return the full closed-bar history needed for the strategy's
    rolling windows."""
    exchange = exchange or make_exchange()
    store = _load_store()
    tf_seconds = _timeframe_seconds(cfg.TIMEFRAME)

    if store.empty:
        # Bootstrap: need at least MIN_HISTORY_BARS closed bars.
        since_ms = int((time.time() - cfg.MIN_HISTORY_BARS * tf_seconds) * 1000)
    else:
        # Re-fetch from a little before the last stored bar, in case that bar
        # was still forming last run and has since closed with a final value.
        since_ms = int((store.index[-1].timestamp() - 3 * tf_seconds) * 1000)

    all_rows = []
    limit = 1000
    while True:
        batch = exchange.fetch_ohlcv(cfg.SYMBOL, timeframe=cfg.TIMEFRAME, since=since_ms, limit=limit)
        if not batch:
            break
        all_rows.extend(batch)
        if len(batch) < limit:
            break
        since_ms = batch[-1][0] + 1

    if all_rows:
        new_df = pd.DataFrame(all_rows, columns=["ts_ms", "open", "high", "low", "close", "volume"])
        new_df["ts"] = pd.to_datetime(new_df["ts_ms"], unit="ms", utc=True)
        new_df = new_df.set_index("ts")[["open", "high", "low", "close", "volume"]]
        store = pd.concat([store, new_df])
        store = store[~store.index.duplicated(keep="last")].sort_index()

    # Never trust the most recent bar returned by the exchange -- it may still
    # be forming. Only a bar whose full interval has elapsed is "closed".
    now = pd.Timestamp.now(tz="UTC")
    closed = store[store.index + pd.Timedelta(seconds=tf_seconds) <= now]

    _save_store(closed)
    return closed
