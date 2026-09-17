"""
Strategy signal generators.

Convention: every function returns a `signal` Series aligned to the bar index,
where signal[t] is the position the strategy WANTS to hold based on information
available at the close of bar t (i.e. it may use df.loc[:t] but nothing later).
The backtest engine (see backtest.py) is responsible for lagging this by one bar
before applying it to bar t+1's return, so no strategy here needs to shift
anything itself -- that lag is centralized and enforced in one place.

signal values: +1 long, -1 short, 0 flat.
"""
import numpy as np
import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.fillna(50)


def atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def adx(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = atr(df, period)
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / period, adjust=False).mean() / tr
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / period, adjust=False).mean() / tr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / period, adjust=False).mean().fillna(0)


def ema_crossover(df: pd.DataFrame, fast: int, slow: int, long_short: bool) -> pd.Series:
    f, s = ema(df["close"], fast), ema(df["close"], slow)
    sig = np.where(f > s, 1, -1 if long_short else 0)
    return pd.Series(sig, index=df.index)


def ma_crossover(df: pd.DataFrame, fast: int, slow: int, ma_type: str, long_short: bool) -> pd.Series:
    """Generalized MA crossover: ma_type 'sma' or 'ema'. Long-only or long/short."""
    if ma_type == "sma":
        f, s = df["close"].rolling(fast).mean(), df["close"].rolling(slow).mean()
    else:
        f, s = ema(df["close"], fast), ema(df["close"], slow)
    sig = np.where(f > s, 1, -1 if long_short else 0)
    sig = np.where(f.isna() | s.isna(), 0, sig)
    return pd.Series(sig, index=df.index)


def ema_crossover_adx(df: pd.DataFrame, fast: int, slow: int, adx_period: int, adx_min: float, long_short: bool) -> pd.Series:
    f, s = ema(df["close"], fast), ema(df["close"], slow)
    trend_ok = adx(df, adx_period) > adx_min
    long_sig = f > s
    short_sig = f < s
    sig = np.where(long_sig & trend_ok, 1, np.where(short_sig & trend_ok, (-1 if long_short else 0), 0))
    return pd.Series(sig, index=df.index)


def donchian_breakout(df: pd.DataFrame, entry_n: int, exit_n: int, long_short: bool) -> pd.Series:
    upper_entry = df["high"].rolling(entry_n).max().shift(1)
    lower_entry = df["low"].rolling(entry_n).min().shift(1)
    upper_exit = df["high"].rolling(exit_n).max().shift(1)
    lower_exit = df["low"].rolling(exit_n).min().shift(1)
    close = df["close"]

    sig = np.zeros(len(df))
    pos = 0
    c = close.values
    ue, le, ux, lx = upper_entry.values, lower_entry.values, upper_exit.values, lower_exit.values
    for i in range(len(df)):
        if np.isnan(ue[i]) or np.isnan(le[i]):
            sig[i] = pos
            continue
        if pos <= 0 and c[i] > ue[i]:
            pos = 1
        elif pos >= 0 and long_short and c[i] < le[i]:
            pos = -1
        elif pos == 1 and c[i] < lx[i]:
            pos = 0
        elif pos == -1 and c[i] > ux[i]:
            pos = 0
        sig[i] = pos
    return pd.Series(sig, index=df.index)


def time_series_momentum(df: pd.DataFrame, lookback: int, long_short: bool) -> pd.Series:
    past_ret = df["close"].pct_change(lookback)
    sig = np.where(past_ret > 0, 1, -1 if long_short else 0)
    return pd.Series(sig, index=df.index)


def bollinger_mean_reversion(df: pd.DataFrame, period: int, n_std: float, exit_z: float, long_short: bool) -> pd.Series:
    mid = df["close"].rolling(period).mean()
    std = df["close"].rolling(period).std()
    z = (df["close"] - mid) / std.replace(0, np.nan)

    sig = np.zeros(len(df))
    pos = 0
    zv = z.values
    for i in range(len(df)):
        if np.isnan(zv[i]):
            sig[i] = pos
            continue
        if pos == 0 and zv[i] < -n_std:
            pos = 1
        elif pos == 0 and long_short and zv[i] > n_std:
            pos = -1
        elif pos == 1 and zv[i] > -exit_z:
            pos = 0
        elif pos == -1 and zv[i] < exit_z:
            pos = 0
        sig[i] = pos
    return pd.Series(sig, index=df.index)


def rsi2_mean_reversion(df: pd.DataFrame, rsi_period: int, buy_th: float, sell_th: float, trend_span: int) -> pd.Series:
    """Long-only RSI mean reversion, only takes longs while price above a long trend EMA
    (classic Connors-style filter: buy oversold dips within an uptrend only)."""
    r = rsi(df["close"], rsi_period)
    trend = ema(df["close"], trend_span)
    uptrend = df["close"] > trend

    sig = np.zeros(len(df))
    pos = 0
    rv, up = r.values, uptrend.values
    for i in range(len(df)):
        if pos == 0 and up[i] and rv[i] < buy_th:
            pos = 1
        elif pos == 1 and rv[i] > sell_th:
            pos = 0
        sig[i] = pos
    return pd.Series(sig, index=df.index)


def volatility_breakout(df: pd.DataFrame, atr_period: int, k: float, ema_span: int, long_short: bool) -> pd.Series:
    """Keltner-style: long when close breaks above EMA + k*ATR, short/flat when it breaks below EMA - k*ATR."""
    mid = ema(df["close"], ema_span)
    band = atr(df, atr_period) * k
    upper = (mid + band).shift(1)
    lower = (mid - band).shift(1)
    close = df["close"]

    sig = np.zeros(len(df))
    pos = 0
    c, u, l = close.values, upper.values, lower.values
    for i in range(len(df)):
        if np.isnan(u[i]) or np.isnan(l[i]):
            sig[i] = pos
            continue
        if c[i] > u[i]:
            pos = 1
        elif c[i] < l[i]:
            pos = -1 if long_short else 0
        sig[i] = pos
    return pd.Series(sig, index=df.index)
