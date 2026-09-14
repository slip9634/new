"""Parameter grids, expressed in real-world days/hours and converted to bar
counts per timeframe, so e.g. "1-day EMA" means the same wall-clock window
whether we're on 5m or 1h bars. Grids are intentionally modest in size
(a few dozen combinations per family) to limit overfitting risk from
data-mining a huge parameter space.
"""
import numpy as np

BARS_PER_DAY = {"5m": 288, "15m": 96, "1h": 24, "5h": 4.8, "1d": 1}


def days_to_bars(days_list, timeframe, min_bars=2):
    bpd = BARS_PER_DAY[timeframe]
    bars = sorted({max(min_bars, int(round(d * bpd))) for d in days_list})
    return bars


def ema_crossover_grid(timeframe, long_short):
    fast_days = [0.25, 0.5, 1, 2, 3]
    slow_days = [3, 7, 14, 30, 60]
    fasts = days_to_bars(fast_days, timeframe)
    slows = days_to_bars(slow_days, timeframe)
    combos = []
    for f in fasts:
        for s in slows:
            if f < s:
                combos.append({"fast": f, "slow": s, "long_short": long_short})
    return combos


def ema_crossover_adx_grid(timeframe, long_short):
    fast_days = [0.5, 1, 2]
    slow_days = [7, 14, 30]
    adx_days = [1, 2]
    fasts = days_to_bars(fast_days, timeframe)
    slows = days_to_bars(slow_days, timeframe)
    adx_p = days_to_bars(adx_days, timeframe)
    combos = []
    for f in fasts:
        for s in slows:
            if f >= s:
                continue
            for ap in adx_p:
                for amin in (15, 20, 25):
                    combos.append({"fast": f, "slow": s, "adx_period": ap, "adx_min": amin, "long_short": long_short})
    return combos


def donchian_grid(timeframe, long_short):
    entry_days = [1, 3, 7, 14, 30, 60]
    entries = days_to_bars(entry_days, timeframe)
    combos = []
    for e in entries:
        for exit_frac in (0.25, 0.5):
            x = max(2, int(round(e * exit_frac)))
            if x < e:
                combos.append({"entry_n": e, "exit_n": x, "long_short": long_short})
    return combos


def tsmom_grid(timeframe, long_short):
    lookback_days = [1, 3, 7,14, 30, 60, 90, 180, 365]
    lookbacks = days_to_bars(lookback_days, timeframe)
    return [{"lookback": lb, "long_short": long_short} for lb in lookbacks]


def bollinger_grid(timeframe, long_short):
    period_days = [0.25, 0.5, 1, 2, 3, 7]
    periods = days_to_bars(period_days, timeframe)
    combos = []
    for p in periods:
        for n_std in (2.0, 2.5, 3.0):
            for exit_z in (0.0, 0.5):
                combos.append({"period": p, "n_std": n_std, "exit_z": exit_z, "long_short": long_short})
    return combos


def rsi2_grid(timeframe):
    rsi_period_days = [0.25, 0.5]
    trend_days = [30, 60, 100]
    rsi_periods = days_to_bars(rsi_period_days, timeframe, min_bars=2)
    trend_spans = days_to_bars(trend_days, timeframe)
    combos = []
    for rp in rsi_periods:
        for bt in (10, 20):
            for st in (60, 70):
                for ts in trend_spans:
                    combos.append({"rsi_period": rp, "buy_th": bt, "sell_th": st, "trend_span": ts})
    return combos


def volbreakout_grid(timeframe, long_short):
    atr_days = [0.5, 1, 2]
    ema_days = [0.5, 1, 2, 3]
    atr_periods = days_to_bars(atr_days, timeframe)
    ema_spans = days_to_bars(ema_days, timeframe)
    combos = []
    for ap in atr_periods:
        for es in ema_spans:
            for k in (1.0, 2.0, 3.0):
                combos.append({"atr_period": ap, "k": k, "ema_span": es, "long_short": long_short})
    return combos
