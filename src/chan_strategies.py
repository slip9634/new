"""
Strategies from Ernest Chan, "Algorithmic Trading: Winning Strategies and
Their Rationale" (Wiley, 2013), re-implemented as close to the book's rules as
our data allows. Chapter references are to that book.

No-lookahead contract (same as src/backtest.py): every weight/position is
computed from data up to the close of day t and earns day t+1's return.
Intraday strategies (gap trades) decide at the open of day t using only the
open of t and prior closes/highs/lows, and exit at the close of t.

Parameters are the book's published defaults, NOT re-optimised. The one place
we had to pick a number the book doesn't give for our instruments (Kalman
measurement noise Ve) we estimate it on the in-sample window only.

Every function returns a DataFrame with columns:
    gross  -- daily return before costs
    cost   -- daily cost (turnover x one-way cost)
    net    -- gross - cost
    expo   -- gross exposure held that day (0 = flat)
"""
import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import coint_johansen

IS_END = "2012-12-31"  # the book went to press in 2013: everything after is out-of-sample


def _pack(weights: pd.DataFrame, returns: pd.DataFrame, cost_per_side, lag: int = 1) -> pd.DataFrame:
    """Lag weights `lag` days (1 = trade at the next close), apply returns,
    charge turnover costs. lag=2 is the "one extra day of delay" robustness
    check: an edge that vanishes with it was living off price asynchronicity
    or bid/ask bounce rather than genuine mean reversion."""
    w = weights.shift(lag).fillna(0.0)
    r = returns.reindex(w.index).fillna(0.0)
    gross = (w * r).sum(axis=1)
    turnover = w.diff().abs()
    turnover.iloc[0] = w.iloc[0].abs()
    cost_vec = pd.Series(cost_per_side, index=w.columns) if np.isscalar(cost_per_side) else pd.Series(cost_per_side)
    cost = (turnover * cost_vec.reindex(w.columns).fillna(0)).sum(axis=1)
    return pd.DataFrame({"gross": gross, "cost": cost, "net": gross - cost, "expo": w.abs().sum(axis=1)})


# ---------------------------------------------------------------------------
# Ch.2-3: stationarity / cointegration diagnostics
# ---------------------------------------------------------------------------

def half_life(spread: pd.Series) -> float:
    """Ornstein-Uhlenbeck half-life, Chan eq. 2.5: regress dy on y(t-1)."""
    s = spread.dropna()
    lag = s.shift(1).iloc[1:]
    d = s.diff().iloc[1:]
    lam = np.polyfit(lag.values, d.values, 1)[0]
    return float(-np.log(2) / lam) if lam < 0 else np.inf


def johansen_trace(prices: pd.DataFrame) -> dict:
    """Johansen trace test (r=0) with 1 lag, constant term -- as in Ch.2."""
    res = coint_johansen(prices.dropna().values, det_order=0, k_ar_diff=1)
    return {"trace_stat": float(res.lr1[0]), "crit_95": float(res.cvt[0, 1]),
            "cointegrated_95": bool(res.lr1[0] > res.cvt[0, 1]),
            "hedge_vec": res.evec[:, 0] / res.evec[0, 0]}


# ---------------------------------------------------------------------------
# Ch.2/5 Example 5.1-style: pair with rolling Johansen hedge ratio,
# linear (z-score proportional) mean reversion
# ---------------------------------------------------------------------------

def pair_johansen_linear(prices: pd.DataFrame, lookback_hr: int = 250,
                         lookback_z: int = 20, cost: float = 0.0001, lag: int = 1) -> pd.DataFrame:
    """Chan Ex.5.1 (USD.AUD vs USD.CAD): hedge ratio from a trailing 250-day
    Johansen eigenvector, units held = -z of the unit portfolio over 20 days.
    Returns are P&L / gross market value, as in the book."""
    px = prices.dropna()
    n = len(px)
    hedge = np.full((n, 2), np.nan)
    vals = px.values
    for t in range(lookback_hr, n):
        win = vals[t - lookback_hr + 1:t + 1]
        try:
            ev = coint_johansen(win, det_order=0, k_ar_diff=1).evec[:, 0]
        except np.linalg.LinAlgError:
            continue
        if np.iscomplexobj(ev):  # degenerate window (e.g. ffilled flat prices)
            if np.abs(ev.imag).max() > 1e-12:
                continue
            ev = ev.real
        hedge[t] = ev
    hedge = pd.DataFrame(hedge, index=px.index, columns=px.columns)
    unit_port = (hedge * px).sum(axis=1, min_count=2)
    # z-score of the unit portfolio, computed with the CURRENT hedge vector
    # applied to the trailing window -- no future hedge vector is used.
    z = pd.Series(np.nan, index=px.index)
    for t in range(lookback_hr + lookback_z, n):
        h = hedge.values[t]
        if np.isnan(h).any():
            continue
        hist = vals[t - lookback_z + 1:t + 1] @ h
        sd = hist.std(ddof=1)
        if sd > 0:
            z.iloc[t] = (hist[-1] - hist.mean()) / sd
    units = -z
    dollars = hedge.mul(units, axis=0) * px          # dollar position per leg
    gross_mv = dollars.abs().sum(axis=1)
    weights = dollars.div(gross_mv.replace(0, np.nan), axis=0).fillna(0.0)
    out = _pack(weights, px.pct_change(), cost, lag)
    out.attrs["unit_port"] = unit_port
    return out


# ---------------------------------------------------------------------------
# Ch.3 Example 3.3: Kalman-filter dynamic hedge ratio, Bollinger-style entries
# ---------------------------------------------------------------------------

def kalman_hedge(y: pd.Series, x: pd.Series, delta: float = 1e-4, ve: float = 1e-3):
    """Chan's Kalman regression y = beta0*x + beta1 (Ex.3.3). Returns the
    one-step-ahead forecast error e(t), its variance Q(t) and beta(t)."""
    n = len(y)
    X = np.column_stack([x.values, np.ones(n)])
    Y = y.values
    vw = delta / (1 - delta) * np.eye(2)
    beta = np.zeros((n, 2))
    P = np.zeros((2, 2))
    e = np.full(n, np.nan)
    Q = np.full(n, np.nan)
    b = np.zeros(2)
    for t in range(n):
        R = P + vw
        yhat = X[t] @ b
        Q[t] = X[t] @ R @ X[t] + ve
        e[t] = Y[t] - yhat
        K = R @ X[t] / Q[t]
        b = b + K * e[t]
        P = R - np.outer(K, X[t]) @ R
        beta[t] = b
    idx = y.index
    return (pd.Series(e, idx), pd.Series(Q, idx),
            pd.DataFrame(beta, idx, ["slope", "intercept"]))


_MLE_CACHE = {}


def kalman_mle(y: pd.Series, x: pd.Series) -> tuple:
    """(delta, Ve) maximising the Gaussian log-likelihood of the innovations
    e ~ N(0, Q), over a log grid. Chan's delta=1e-4 / Ve=1e-3 were tuned for
    EWA/EWC at ~$20 prices and don't transfer to FX quoted near 1.0."""
    key = (y.name, x.name, y.index[0], y.index[-1], len(y))
    if key in _MLE_CACHE:
        return _MLE_CACHE[key]
    best, best_ll = None, -np.inf
    for delta in 10.0 ** np.arange(-8, -1.99, 0.5):
        for ve in 10.0 ** np.arange(-10, -0.99, 0.5):
            e, Q, _ = kalman_hedge(y, x, delta=delta, ve=ve)
            e, Q = e.values[50:], Q.values[50:]
            ll = -0.5 * np.sum(np.log(Q) + e ** 2 / Q)
            if ll > best_ll:
                best, best_ll = (float(delta), float(ve)), ll
    _MLE_CACHE[key] = best
    return best


def pair_kalman(y: pd.Series, x: pd.Series, cost: float = 0.0001,
                warmup: int = 250, lag: int = 1) -> pd.DataFrame:
    """Ex.3.3 trading rules: long the spread when e < -sqrt(Q), exit when
    e > -sqrt(Q); mirror for shorts. Position in y = +units, in x = -slope*units.

    The filter's noise parameters (delta, Ve) are fitted by maximum
    likelihood on the IN-SAMPLE window only (see kalman_mle)."""
    df = pd.concat([y, x], axis=1, keys=["y", "x"]).dropna()
    ins = df.loc[:IS_END]
    delta, ve = kalman_mle(ins["y"].rename(y.name), ins["x"].rename(x.name))
    e, Q, beta = kalman_hedge(df["y"], df["x"], delta=delta, ve=ve)
    sq = np.sqrt(Q)
    units = pd.Series(0.0, index=df.index)
    pos = 0.0
    for t in range(warmup, len(df)):
        if pos == 0:
            if e.iloc[t] < -sq.iloc[t]:
                pos = 1.0
            elif e.iloc[t] > sq.iloc[t]:
                pos = -1.0
        elif pos > 0 and e.iloc[t] > -sq.iloc[t]:
            pos = 0.0
        elif pos < 0 and e.iloc[t] < sq.iloc[t]:
            pos = 0.0
        units.iloc[t] = pos
    dollars = pd.DataFrame({"y": units * df["y"], "x": -units * beta["slope"] * df["x"]})
    gmv = dollars.abs().sum(axis=1).replace(0, np.nan)
    weights = dollars.div(gmv, axis=0).fillna(0.0)
    weights.columns = [y.name, x.name]
    rets = df.pct_change()
    rets.columns = [y.name, x.name]
    return _pack(weights, rets, cost, lag)


# ---------------------------------------------------------------------------
# Ch.4 / Khandani-Lo: cross-sectional short-term mean reversion
# ---------------------------------------------------------------------------

def xs_reversal(prices: pd.DataFrame, cost: float = 0.0001, lag: int = 1) -> pd.DataFrame:
    """Chan Ex.4.3 (Khandani & Lo 2007): w_i = -(r_i - mean(r)) / sum|r_i - mean(r)|,
    rebalanced daily, held one day. Dollar-neutral, gross exposure 1."""
    r = prices.pct_change()
    dev = r.sub(r.mean(axis=1), axis=0)
    w = -dev.div(dev.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    w = w.where(r.notna(), 0.0)
    return _pack(w, r, cost, lag)


def _hold_monthly(raw: pd.DataFrame) -> pd.DataFrame:
    """Keep only month-end weights and hold them until the next month end."""
    is_me = pd.Series(raw.index.to_period("M"), index=raw.index)
    is_me = is_me.ne(is_me.shift(-1))
    held = raw.copy()
    held.loc[~is_me.values] = np.nan
    return held.ffill().fillna(0.0)


# ---------------------------------------------------------------------------
# Ch.6: interday momentum
# ---------------------------------------------------------------------------

def tsmom(prices: pd.DataFrame, lookback: int = 252, vol_lb: int = 63,
          target_vol: float = 0.40, costs=0.0001, rebalance: str = "ME") -> pd.DataFrame:
    """Time-series momentum (Ch.6, after Moskowitz-Ooi-Pedersen 2012): long if
    trailing 12m return > 0 else short; each asset scaled to target_vol / N
    using 63-day realised vol; weights refreshed at month end only."""
    r = prices.pct_change()
    sig = np.sign(prices / prices.shift(lookback) - 1)
    vol = r.rolling(vol_lb).std() * np.sqrt(252)
    n_live = sig.notna().sum(axis=1).replace(0, np.nan)
    raw = sig * (target_vol / vol)
    raw = raw.clip(-3, 3).div(n_live, axis=0)
    w = _hold_monthly(raw).where(prices.notna(), 0.0)
    return _pack(w, r, costs)


def xs_momentum(prices: pd.DataFrame, lookback: int = 63, n_side: int = 3,
                cost: float = 0.0001) -> pd.DataFrame:
    """Cross-sectional momentum (Ch.6): rank trailing 3m returns monthly,
    long the top n, short the bottom n, equal weight, gross 1."""
    ret_lb = prices / prices.shift(lookback) - 1
    rank = ret_lb.rank(axis=1)
    cnt = ret_lb.notna().sum(axis=1)
    long_ = rank.gt(cnt - n_side, axis=0)
    short = rank.le(n_side, axis=0) & ret_lb.notna()
    raw = (long_.astype(float) - short.astype(float)) / (2 * n_side)
    raw = raw.where(cnt >= 2 * n_side, 0.0)
    w = _hold_monthly(raw)
    return _pack(w, prices.pct_change(), cost)


# ---------------------------------------------------------------------------
# Ch.4 / Ch.7: opening-gap strategies (intraday, open -> close)
# ---------------------------------------------------------------------------

def _gap_frame(ohlc: pd.DataFrame, vol_lb: int = 90):
    c = ohlc["close"]
    sd = c.pct_change().rolling(vol_lb).std().shift(1)  # known before today's open
    prev_low, prev_high = ohlc["low"].shift(1), ohlc["high"].shift(1)
    intraday = ohlc["close"] / ohlc["open"] - 1
    return sd, prev_low, prev_high, intraday


def buy_on_gap(ohlc: pd.DataFrame, entry_z: float = 1.0, ma_lb: int = 20,
               cost: float = 0.0001) -> pd.DataFrame:
    """Chan Ex.4.1 'buy-on-gap', applied to SPY: buy at the open if
    open < prev_low * (1 - entry_z * sd90) AND open > 20d MA of closes
    (the MA uses closes up to yesterday); sell at today's close."""
    sd, prev_low, _, intraday = _gap_frame(ohlc)
    ma = ohlc["close"].rolling(ma_lb).mean().shift(1)
    o = ohlc["open"]
    long_ = (o < prev_low * (1 - entry_z * sd)) & (o > ma)
    pos = long_.astype(float)
    gross = pos * intraday
    cost_s = pos * 2 * cost  # in at open, out at close
    return pd.DataFrame({"gross": gross, "cost": cost_s, "net": gross - cost_s, "expo": pos})


def gap_momentum(ohlc: pd.DataFrame, entry_z: float = 0.1, cost: float = 0.0001) -> pd.DataFrame:
    """Chan Ex.7.1 (FSTX opening-gap momentum), applied to SPY: long at the open
    if open > prev_high * (1 + 0.1 sd), short if open < prev_low * (1 - 0.1 sd);
    exit at the close."""
    sd, prev_low, prev_high, intraday = _gap_frame(ohlc)
    o = ohlc["open"]
    pos = (o > prev_high * (1 + entry_z * sd)).astype(float) - (o < prev_low * (1 - entry_z * sd)).astype(float)
    gross = pos * intraday
    cost_s = pos.abs() * 2 * cost
    return pd.DataFrame({"gross": gross, "cost": cost_s, "net": gross - cost_s, "expo": pos.abs()})
