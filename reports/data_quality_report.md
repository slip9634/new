# Data quality report — Bitstamp BTC/USD 1-minute

## Raw file, full history

- **n_rows**: 6847200
- **start**: 2012-01-01 00:01:00+00:00
- **end**: 2025-01-07 00:00:00+00:00
- **n_duplicate_ts**: 0
- **median_step_seconds**: 60.0
- **n_steps_not_60s**: 0
- **expected_minutes**: 6847200
- **missing_minutes**: 0
- **pct_missing_minutes**: 0.0
- **n_nan_any**: 0
- **n_negative_or_zero_price**: 0
- **n_ohlc_consistency_violations**: 0

## Liquidity check (why we drop data before 2014-01-01)

- Median daily volume BEFORE cutoff: 3349.62 BTC
- Median daily volume AFTER cutoff: 5201.69 BTC
- Median share of flat (zero-return) minutes BEFORE cutoff: 93.3%
- Median share of flat (zero-return) minutes AFTER cutoff: 8.8%

## Final analysis dataset

- Range: 2014-01-01 00:00:00+00:00 -> 2025-01-07 00:00:00+00:00
- Rows (1-minute bars): 5794561

### 5m bars
- Rows: 1158913
- Range: 2014-01-01 00:00:00+00:00 -> 2025-01-07 00:00:00+00:00
- Saved: /home/user/new/data/btcusd_5m.parquet

### 15m bars
- Rows: 386305
- Range: 2014-01-01 00:00:00+00:00 -> 2025-01-07 00:00:00+00:00
- Saved: /home/user/new/data/btcusd_15m.parquet

### 1h bars
- Rows: 96577
- Range: 2014-01-01 00:00:00+00:00 -> 2025-01-07 00:00:00+00:00
- Saved: /home/user/new/data/btcusd_1h.parquet

### 5h bars
- Rows: 19316
- Range: 2014-01-01 00:00:00+00:00 -> 2025-01-06 23:00:00+00:00
- Saved: /home/user/new/data/btcusd_5h.parquet

### 1d bars
- Rows: 4025
- Range: 2014-01-01 00:00:00+00:00 -> 2025-01-07 00:00:00+00:00
- Saved: /home/user/new/data/btcusd_1d.parquet
