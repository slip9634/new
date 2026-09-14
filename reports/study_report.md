# Crypto strategy study — results

Universe: BTC/USD (Bitstamp spot, 2014-01-01 to 2025-01-06, cleaned & gap-filled). Fee: 0.06% per one-way trade (round-trip 0.12%). Target: >10% p.a. net CAGR. Parameters selected on 2014-2019 IN-SAMPLE data only (max in-sample Sharpe, min. 20 trades); frozen and evaluated once on 2020-2025 OUT-OF-SAMPLE data.


## Timeframe: 5m

Buy & hold benchmark — IS CAGR 46.2%, IS Sharpe 0.88, OOS CAGR 68.5%, OOS Sharpe 1.10, OOS MaxDD -77.3%

| strategy | params | IS Sharpe | IS CAGR | OOS Sharpe | OOS CAGR | OOS MaxDD | OOS Calmar | OOS trades/yr | 2020-22 CAGR | 2023-25 CAGR | >10%pa OOS | robust both halves |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| donchian_breakout_L | `{"entry_n": 2016, "exit_n": 1008, "long_short": false}` | 1.54 | 97.7% | 1.41 | 62.9% | -40.4% | 1.56 | 39 | 57.1% | 72.0% | YES | YES |
| volatility_breakout_L | `{"atr_period": 288, "k": 3.0, "ema_span": 864, "long_short": false}` | 1.05 | 57.6% | 1.28 | 60.9% | -59.0% | 1.03 | 248 | 57.9% | 66.0% | YES | YES |
| tsmom_L | `{"lookback": 51840, "long_short": false}` | 1.15 | 75.9% | 0.86 | 37.6% | -73.1% | 0.51 | 171 | 17.2% | 75.0% | YES | YES |
| ema_crossover_L | `{"fast": 864, "slow": 2016, "long_short": false}` | 1.42 | 100.6% | 0.84 | 33.2% | -66.0% | 0.50 | 51 | 12.0% | 72.4% | YES | YES |
| volatility_breakout_LS | `{"atr_period": 288, "k": 3.0, "ema_span": 864, "long_short": true}` | 0.48 | 0.3% | 0.56 | 15.5% | -62.7% | 0.25 | 248 | 25.6% | 2.1% | YES | YES |
| ema_crossover_adx_L | `{"fast": 144, "slow": 2016, "adx_period": 288, "adx_min": 15, "long_short": false}` | 0.69 | 14.2% | 0.51 | 4.7% | -14.2% | 0.33 | 14 | 3.8% | 5.9% |  |  |
| tsmom_LS | `{"lookback": 51840, "long_short": true}` | 0.86 | 43.9% | 0.24 | -7.3% | -90.1% | -0.08 | 171 | -23.4% | 22.6% |  |  |
| ema_crossover_LS | `{"fast": 864, "slow": 2016, "long_short": true}` | 1.01 | 65.9% | 0.05 | -19.1% | -87.9% | -0.22 | 51 | -34.8% | 11.4% |  |  |
| donchian_breakout_LS | `{"entry_n": 864, "exit_n": 216, "long_short": true}` | 0.99 | 58.8% | -0.23 | -24.0% | -88.2% | -0.27 | 250 | -35.1% | -4.1% |  |  |
| bollinger_mr_L | `{"period": 72, "n_std": 2.5, "exit_z": 0.5, "long_short": false}` | 1.09 | 54.8% | -0.75 | -30.7% | -84.9% | -0.36 | 1168 | -19.9% | -44.1% |  |  |
| bollinger_mr_LS | `{"period": 72, "n_std": 2.0, "exit_z": 0.5, "long_short": true}` | 0.18 | -11.7% | -3.20 | -84.4% | -100.0% | -0.84 | 3284 | -78.9% | -90.1% |  |  |
| ema_crossover_adx_LS | `{"fast": 144, "slow": 2016, "adx_period": 576, "adx_min": 20, "long_short": true}` | 0.65 | 16.5% | nan | nan% | nan% | nan | 0 | nan% | nan% |  |  |

## Timeframe: 15m

Buy & hold benchmark — IS CAGR 46.3%, IS Sharpe 0.87, OOS CAGR 68.5%, OOS Sharpe 1.11, OOS MaxDD -77.3%

| strategy | params | IS Sharpe | IS CAGR | OOS Sharpe | OOS CAGR | OOS MaxDD | OOS Calmar | OOS trades/yr | 2020-22 CAGR | 2023-25 CAGR | >10%pa OOS | robust both halves |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| volatility_breakout_L | `{"atr_period": 96, "k": 2.0, "ema_span": 288, "long_short": false}` | 1.39 | 84.5% | 1.37 | 66.0% | -61.2% | 1.08 | 191 | 52.3% | 89.3% | YES | YES |
| donchian_breakout_L | `{"entry_n": 672, "exit_n": 336, "long_short": false}` | 1.60 | 95.6% | 1.39 | 59.9% | -40.2% | 1.49 | 38 | 53.4% | 70.0% | YES | YES |
| tsmom_L | `{"lookback": 17280, "long_short": false}` | 1.17 | 75.3% | 0.95 | 43.8% | -69.4% | 0.63 | 98 | 22.6% | 82.4% | YES | YES |
| ema_crossover_L | `{"fast": 288, "slow": 672, "long_short": false}` | 1.50 | 101.1% | 0.86 | 33.7% | -65.4% | 0.52 | 51 | 12.8% | 72.2% | YES | YES |
| volatility_breakout_LS | `{"atr_period": 96, "k": 2.0, "ema_span": 288, "long_short": true}` | 0.89 | 48.7% | 0.66 | 24.3% | -60.8% | 0.40 | 191 | 18.8% | 33.3% | YES | YES |
| donchian_breakout_LS | `{"entry_n": 2880, "exit_n": 720, "long_short": true}` | 1.04 | 60.8% | 0.60 | 19.3% | -62.2% | 0.31 | 25 | 19.4% | 19.2% | YES | YES |
| ema_crossover_adx_L | `{"fast": 192, "slow": 672, "adx_period": 96, "adx_min": 15, "long_short": false}` | 0.55 | 12.6% | 0.83 | 18.8% | -41.6% | 0.45 | 88 | 0.2% | 53.1% | YES | YES |
| ema_crossover_adx_LS | `{"fast": 192, "slow": 672, "adx_period": 96, "adx_min": 15, "long_short": true}` | 0.45 | 9.6% | 0.48 | 12.1% | -76.4% | 0.16 | 140 | -4.7% | 42.9% | YES |  |
| rsi2_mr | `{"rsi_period": 24, "buy_th": 20, "sell_th": 70, "trend_span": 9600}` | 0.33 | 4.4% | 0.36 | 4.1% | -19.1% | 0.21 | 6 | 5.6% | 1.9% |  |  |
| tsmom_LS | `{"lookback": 17280, "long_short": true}` | 0.94 | 54.4% | 0.37 | 2.2% | -87.2% | 0.03 | 98 | -14.6% | 33.3% |  |  |
| bollinger_mr_L | `{"period": 24, "n_std": 2.5, "exit_z": 0.5, "long_short": false}` | 0.56 | 15.9% | -0.35 | -16.9% | -77.8% | -0.22 | 785 | 1.8% | -38.7% |  |  |
| ema_crossover_LS | `{"fast": 288, "slow": 672, "long_short": true}` | 1.11 | 80.5% | 0.05 | -17.9% | -87.1% | -0.21 | 51 | -33.2% | 11.4% |  |  |
| bollinger_mr_LS | `{"period": 48, "n_std": 2.0, "exit_z": 0.5, "long_short": true}` | -0.49 | -42.0% | -1.75 | -64.9% | -99.5% | -0.65 | 1523 | -56.9% | -74.2% |  |  |

## Timeframe: 1h

Buy & hold benchmark — IS CAGR 46.3%, IS Sharpe 0.88, OOS CAGR 68.4%, OOS Sharpe 1.12, OOS MaxDD -77.2%

| strategy | params | IS Sharpe | IS CAGR | OOS Sharpe | OOS CAGR | OOS MaxDD | OOS Calmar | OOS trades/yr | 2020-22 CAGR | 2023-25 CAGR | >10%pa OOS | robust both halves |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tsmom_L | `{"lookback": 1440, "long_short": false}` | 1.24 | 75.0% | 1.35 | 69.5% | -51.1% | 1.36 | 59 | 54.3% | 95.1% | YES | YES |
| volatility_breakout_L | `{"atr_period": 12, "k": 1.0, "ema_span": 72, "long_short": false}` | 1.49 | 90.0% | 1.33 | 62.6% | -64.6% | 0.97 | 158 | 56.0% | 73.0% | YES | YES |
| donchian_breakout_L | `{"entry_n": 720, "exit_n": 180, "long_short": false}` | 1.56 | 78.6% | 1.01 | 36.0% | -54.6% | 0.66 | 14 | 23.5% | 57.0% | YES | YES |
| ema_crossover_L | `{"fast": 72, "slow": 168, "long_short": false}` | 1.59 | 102.3% | 0.85 | 32.1% | -68.3% | 0.47 | 51 | 9.7% | 74.4% | YES | YES |
| ema_crossover_adx_L | `{"fast": 48, "slow": 168, "adx_period": 48, "adx_min": 15, "long_short": false}` | 1.13 | 43.7% | 0.91 | 25.8% | -46.9% | 0.55 | 71 | -1.6% | 81.4% | YES |  |
| ema_crossover_adx_LS | `{"fast": 24, "slow": 336, "adx_period": 24, "adx_min": 15, "long_short": true}` | 0.92 | 50.0% | 0.63 | 22.2% | -67.3% | 0.33 | 194 | -2.0% | 69.8% | YES |  |
| volatility_breakout_LS | `{"atr_period": 12, "k": 1.0, "ema_span": 72, "long_short": true}` | 1.06 | 70.0% | 0.63 | 21.5% | -70.2% | 0.31 | 158 | 28.5% | 11.6% | YES | YES |
| tsmom_LS | `{"lookback": 4320, "long_short": true}` | 1.02 | 64.6% | 0.53 | 13.9% | -85.1% | 0.16 | 48 | -2.0% | 42.3% | YES |  |
| rsi2_mr | `{"rsi_period": 12, "buy_th": 20, "sell_th": 70, "trend_span": 2400}` | 0.35 | 5.9% | 0.41 | 6.6% | -25.0% | 0.26 | 16 | 4.0% | 10.6% |  |  |
| donchian_breakout_LS | `{"entry_n": 720, "exit_n": 180, "long_short": true}` | 1.18 | 71.8% | 0.36 | 5.0% | -72.7% | 0.07 | 25 | 6.2% | 3.1% |  |  |
| bollinger_mr_L | `{"period": 6, "n_std": 2.0, "exit_z": 0.5, "long_short": false}` | 0.25 | 2.3% | -0.96 | -7.5% | -34.6% | -0.22 | 44 | -11.9% | -0.4% |  |  |
| bollinger_mr_LS | `{"period": 6, "n_std": 2.0, "exit_z": 0.5, "long_short": true}` | -0.58 | -10.7% | -1.05 | -12.3% | -56.8% | -0.22 | 88 | -15.4% | -7.3% |  |  |
| ema_crossover_LS | `{"fast": 72, "slow": 168, "long_short": true}` | 1.22 | 93.8% | 0.01 | -19.3% | -88.0% | -0.22 | 51 | -36.1% | 13.7% |  |  |

## Timeframe: 5h

Buy & hold benchmark — IS CAGR 45.9%, IS Sharpe 0.88, OOS CAGR 68.7%, OOS Sharpe 1.13, OOS MaxDD -77.1%

| strategy | params | IS Sharpe | IS CAGR | OOS Sharpe | OOS CAGR | OOS MaxDD | OOS Calmar | OOS trades/yr | 2020-22 CAGR | 2023-25 CAGR | >10%pa OOS | robust both halves |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| volatility_breakout_L | `{"atr_period": 5, "k": 1.0, "ema_span": 14, "long_short": false}` | 1.59 | 92.6% | 1.40 | 68.1% | -59.0% | 1.15 | 66 | 52.4% | 94.7% | YES | YES |
| tsmom_L | `{"lookback": 14, "long_short": false}` | 1.53 | 90.1% | 1.35 | 65.2% | -57.2% | 1.14 | 219 | 49.7% | 91.5% | YES | YES |
| ema_crossover_adx_L | `{"fast": 2, "slow": 67, "adx_period": 5, "adx_min": 15, "long_short": false}` | 1.70 | 106.1% | 1.25 | 58.3% | -54.4% | 1.07 | 83 | 33.9% | 103.3% | YES | YES |
| ema_crossover_L | `{"fast": 2, "slow": 67, "long_short": false}` | 1.69 | 105.3% | 1.19 | 54.5% | -54.7% | 0.99 | 79 | 30.1% | 99.6% | YES | YES |
| donchian_breakout_L | `{"entry_n": 34, "exit_n": 8, "long_short": false}` | 1.90 | 99.6% | 1.20 | 42.6% | -33.1% | 1.29 | 41 | 30.4% | 63.0% | YES | YES |
| tsmom_LS | `{"lookback": 14, "long_short": true}` | 1.16 | 80.0% | 0.72 | 29.7% | -53.9% | 0.55 | 219 | 25.0% | 37.1% | YES | YES |
| volatility_breakout_LS | `{"atr_period": 5, "k": 2.0, "ema_span": 10, "long_short": true}` | 1.22 | 89.3% | 0.66 | 24.4% | -54.8% | 0.45 | 29 | 15.0% | 39.8% | YES | YES |
| donchian_breakout_LS | `{"entry_n": 67, "exit_n": 34, "long_short": true}` | 1.24 | 83.3% | 0.57 | 17.5% | -72.0% | 0.24 | 29 | 12.4% | 25.5% | YES | YES |
| ema_crossover_adx_LS | `{"fast": 2, "slow": 67, "adx_period": 5, "adx_min": 15, "long_short": true}` | 1.36 | 109.9% | 0.56 | 16.6% | -76.8% | 0.22 | 89 | -0.8% | 48.2% | YES |  |
| ema_crossover_LS | `{"fast": 2, "slow": 67, "long_short": true}` | 1.36 | 109.9% | 0.52 | 13.9% | -76.8% | 0.18 | 79 | -6.1% | 51.5% | YES |  |
| rsi2_mr | `{"rsi_period": 2, "buy_th": 10, "sell_th": 60, "trend_span": 144}` | -0.00 | -2.8% | 0.39 | 6.0% | -36.9% | 0.16 | 71 | 5.5% | 6.7% |  |  |
| bollinger_mr_L | `{"period": 34, "n_std": 3.0, "exit_z": 0.5, "long_short": false}` | -0.03 | -7.1% | -0.22 | -8.7% | -52.7% | -0.16 | 14 | -18.3% | 7.9% |  |  |
| bollinger_mr_LS | `{"period": 34, "n_std": 3.0, "exit_z": 0.0, "long_short": true}` | -0.51 | -29.6% | -0.73 | -30.0% | -89.2% | -0.34 | 32 | -40.9% | -9.9% |  |  |

## Timeframe: 1d

Buy & hold benchmark — IS CAGR 45.5%, IS Sharpe 0.87, OOS CAGR 69.8%, OOS Sharpe 1.15, OOS MaxDD -76.7%

| strategy | params | IS Sharpe | IS CAGR | OOS Sharpe | OOS CAGR | OOS MaxDD | OOS Calmar | OOS trades/yr | 2020-22 CAGR | 2023-25 CAGR | >10%pa OOS | robust both halves |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tsmom_L | `{"lookback": 14, "long_short": false}` | 1.36 | 75.1% | 1.43 | 72.0% | -51.1% | 1.41 | 44 | 59.2% | 92.9% | YES | YES |
| ema_crossover_adx_L | `{"fast": 2, "slow": 14, "adx_period": 2, "adx_min": 20, "long_short": false}` | 1.59 | 93.5% | 1.18 | 52.9% | -61.7% | 0.86 | 37 | 35.9% | 82.4% | YES | YES |
| volatility_breakout_L | `{"atr_period": 2, "k": 1.0, "ema_span": 2, "long_short": false}` | 1.29 | 70.7% | 1.01 | 42.0% | -60.4% | 0.70 | 24 | 27.2% | 67.4% | YES | YES |
| ema_crossover_L | `{"fast": 3, "slow": 7, "long_short": false}` | 1.58 | 96.1% | 0.97 | 38.8% | -63.8% | 0.61 | 49 | 28.7% | 55.4% | YES | YES |
| donchian_breakout_L | `{"entry_n": 7, "exit_n": 2, "long_short": false}` | 1.54 | 76.6% | 1.00 | 36.1% | -56.0% | 0.64 | 28 | 17.3% | 69.9% | YES | YES |
| donchian_breakout_LS | `{"entry_n": 14, "exit_n": 7, "long_short": true}` | 0.92 | 48.0% | 0.64 | 22.7% | -62.3% | 0.36 | 20 | 23.0% | 22.5% | YES | YES |
| rsi2_mr | `{"rsi_period": 2, "buy_th": 10, "sell_th": 70, "trend_span": 100}` | 0.48 | 10.0% | 0.68 | 12.9% | -23.5% | 0.55 | 15 | 15.7% | 8.8% | YES | YES |
| ema_crossover_adx_LS | `{"fast": 2, "slow": 14, "adx_period": 2, "adx_min": 20, "long_short": true}` | 1.21 | 86.4% | 0.42 | 6.9% | -76.0% | 0.09 | 42 | -1.6% | 21.2% |  |  |
| bollinger_mr_L | `{"period": 7, "n_std": 2.0, "exit_z": 0.0, "long_short": false}` | 0.20 | 1.3% | 0.10 | -1.6% | -40.6% | -0.04 | 11 | -7.4% | 7.6% |  |  |
| volatility_breakout_LS | `{"atr_period": 2, "k": 1.0, "ema_span": 2, "long_short": true}` | 0.91 | 49.2% | 0.23 | -6.0% | -72.2% | -0.08 | 24 | -11.2% | 2.6% |  |  |
| tsmom_LS | `{"lookback": 90, "long_short": true}` | 1.17 | 81.6% | 0.22 | -7.0% | -87.9% | -0.08 | 15 | -26.6% | 32.4% |  |  |
| ema_crossover_LS | `{"fast": 3, "slow": 7, "long_short": true}` | 1.25 | 93.6% | 0.15 | -10.5% | -82.0% | -0.13 | 50 | -9.3% | -12.0% |  |  |
| bollinger_mr_LS | `{"period": 7, "n_std": 2.0, "exit_z": 0.5, "long_short": true}` | -0.52 | -23.3% | -0.56 | -21.3% | -70.7% | -0.30 | 23 | -22.1% | -20.1% |  |  |


## All strategies clearing the >10% p.a. net-of-fee bar OUT-OF-SAMPLE

| timeframe | strategy | OOS CAGR | OOS Sharpe | OOS MaxDD | buy&hold OOS CAGR | buy&hold OOS Sharpe |
|---|---|---|---|---|---|---|
| 15m | donchian_breakout_L | 59.9% | 1.39 | -40.2% | 68.5% | 1.11 |
| 15m | volatility_breakout_L | 66.0% | 1.37 | -61.2% | 68.5% | 1.11 |
| 15m | tsmom_L | 43.8% | 0.95 | -69.4% | 68.5% | 1.11 |
| 15m | ema_crossover_L | 33.7% | 0.86 | -65.4% | 68.5% | 1.11 |
| 15m | ema_crossover_adx_L | 18.8% | 0.83 | -41.6% | 68.5% | 1.11 |
| 15m | volatility_breakout_LS | 24.3% | 0.66 | -60.8% | 68.5% | 1.11 |
| 15m | donchian_breakout_LS | 19.3% | 0.60 | -62.2% | 68.5% | 1.11 |
| 15m | ema_crossover_adx_LS | 12.1% | 0.48 | -76.4% | 68.5% | 1.11 |
| 1d | tsmom_L | 72.0% | 1.43 | -51.1% | 69.8% | 1.15 |
| 1d | ema_crossover_adx_L | 52.9% | 1.18 | -61.7% | 69.8% | 1.15 |
| 1d | volatility_breakout_L | 42.0% | 1.01 | -60.4% | 69.8% | 1.15 |
| 1d | donchian_breakout_L | 36.1% | 1.00 | -56.0% | 69.8% | 1.15 |
| 1d | ema_crossover_L | 38.8% | 0.97 | -63.8% | 69.8% | 1.15 |
| 1d | rsi2_mr | 12.9% | 0.68 | -23.5% | 69.8% | 1.15 |
| 1d | donchian_breakout_LS | 22.7% | 0.64 | -62.3% | 69.8% | 1.15 |
| 1h | tsmom_L | 69.5% | 1.35 | -51.1% | 68.4% | 1.12 |
| 1h | volatility_breakout_L | 62.6% | 1.33 | -64.6% | 68.4% | 1.12 |
| 1h | donchian_breakout_L | 36.0% | 1.01 | -54.6% | 68.4% | 1.12 |
| 1h | ema_crossover_adx_L | 25.8% | 0.91 | -46.9% | 68.4% | 1.12 |
| 1h | ema_crossover_L | 32.1% | 0.85 | -68.3% | 68.4% | 1.12 |
| 1h | ema_crossover_adx_LS | 22.2% | 0.63 | -67.3% | 68.4% | 1.12 |
| 1h | volatility_breakout_LS | 21.5% | 0.63 | -70.2% | 68.4% | 1.12 |
| 1h | tsmom_LS | 13.9% | 0.53 | -85.1% | 68.4% | 1.12 |
| 5h | volatility_breakout_L | 68.1% | 1.40 | -59.0% | 68.7% | 1.13 |
| 5h | tsmom_L | 65.2% | 1.35 | -57.2% | 68.7% | 1.13 |
| 5h | ema_crossover_adx_L | 58.3% | 1.25 | -54.4% | 68.7% | 1.13 |
| 5h | donchian_breakout_L | 42.6% | 1.20 | -33.1% | 68.7% | 1.13 |
| 5h | ema_crossover_L | 54.5% | 1.19 | -54.7% | 68.7% | 1.13 |
| 5h | tsmom_LS | 29.7% | 0.72 | -53.9% | 68.7% | 1.13 |
| 5h | volatility_breakout_LS | 24.4% | 0.66 | -54.8% | 68.7% | 1.13 |
| 5h | donchian_breakout_LS | 17.5% | 0.57 | -72.0% | 68.7% | 1.13 |
| 5h | ema_crossover_adx_LS | 16.6% | 0.56 | -76.8% | 68.7% | 1.13 |
| 5h | ema_crossover_LS | 13.9% | 0.52 | -76.8% | 68.7% | 1.13 |
| 5m | donchian_breakout_L | 62.9% | 1.41 | -40.4% | 68.5% | 1.10 |
| 5m | volatility_breakout_L | 60.9% | 1.28 | -59.0% | 68.5% | 1.10 |
| 5m | tsmom_L | 37.6% | 0.86 | -73.1% | 68.5% | 1.10 |
| 5m | ema_crossover_L | 33.2% | 0.84 | -66.0% | 68.5% | 1.10 |
| 5m | volatility_breakout_LS | 15.5% | 0.56 | -62.7% | 68.5% | 1.10 |


## Robustness screen: positive in BOTH out-of-sample sub-periods (2020-2022 crash/bull/bear AND 2023-2025 recovery) -- these are the credible candidates, not strategies that got lucky in one regime

| timeframe | strategy | OOS Sharpe | OOS CAGR | OOS MaxDD | OOS Calmar |
|---|---|---|---|---|---|
| 15m | donchian_breakout_L | 1.39 | 59.9% | -40.2% | 1.49 |
| 15m | volatility_breakout_L | 1.37 | 66.0% | -61.2% | 1.08 |
| 15m | tsmom_L | 0.95 | 43.8% | -69.4% | 0.63 |
| 15m | ema_crossover_L | 0.86 | 33.7% | -65.4% | 0.52 |
| 15m | ema_crossover_adx_L | 0.83 | 18.8% | -41.6% | 0.45 |
| 15m | volatility_breakout_LS | 0.66 | 24.3% | -60.8% | 0.40 |
| 15m | donchian_breakout_LS | 0.60 | 19.3% | -62.2% | 0.31 |
| 1d | tsmom_L | 1.43 | 72.0% | -51.1% | 1.41 |
| 1d | ema_crossover_adx_L | 1.18 | 52.9% | -61.7% | 0.86 |
| 1d | volatility_breakout_L | 1.01 | 42.0% | -60.4% | 0.70 |
| 1d | donchian_breakout_L | 1.00 | 36.1% | -56.0% | 0.64 |
| 1d | ema_crossover_L | 0.97 | 38.8% | -63.8% | 0.61 |
| 1d | rsi2_mr | 0.68 | 12.9% | -23.5% | 0.55 |
| 1d | donchian_breakout_LS | 0.64 | 22.7% | -62.3% | 0.36 |
| 1h | tsmom_L | 1.35 | 69.5% | -51.1% | 1.36 |
| 1h | volatility_breakout_L | 1.33 | 62.6% | -64.6% | 0.97 |
| 1h | donchian_breakout_L | 1.01 | 36.0% | -54.6% | 0.66 |
| 1h | ema_crossover_L | 0.85 | 32.1% | -68.3% | 0.47 |
| 1h | volatility_breakout_LS | 0.63 | 21.5% | -70.2% | 0.31 |
| 5h | volatility_breakout_L | 1.40 | 68.1% | -59.0% | 1.15 |
| 5h | tsmom_L | 1.35 | 65.2% | -57.2% | 1.14 |
| 5h | ema_crossover_adx_L | 1.25 | 58.3% | -54.4% | 1.07 |
| 5h | donchian_breakout_L | 1.20 | 42.6% | -33.1% | 1.29 |
| 5h | ema_crossover_L | 1.19 | 54.5% | -54.7% | 0.99 |
| 5h | tsmom_LS | 0.72 | 29.7% | -53.9% | 0.55 |
| 5h | volatility_breakout_LS | 0.66 | 24.4% | -54.8% | 0.45 |
| 5h | donchian_breakout_LS | 0.57 | 17.5% | -72.0% | 0.24 |
| 5m | donchian_breakout_L | 1.41 | 62.9% | -40.4% | 1.56 |
| 5m | volatility_breakout_L | 1.28 | 60.9% | -59.0% | 1.03 |
| 5m | tsmom_L | 0.86 | 37.6% | -73.1% | 0.51 |
| 5m | ema_crossover_L | 0.84 | 33.2% | -66.0% | 0.50 |
| 5m | volatility_breakout_LS | 0.56 | 15.5% | -62.7% | 0.25 |


## Fee sensitivity: same robust strategies at 1x / 2x / 3x the quoted fee (0.06% -> 0.18% one-way)

| timeframe | strategy | CAGR@6bps | CAGR@12bps | CAGR@18bps | trades/yr |
|---|---|---|---|---|---|
| 1d | tsmom_L | 72.0% | 67.5% | 63.2% | 44 |
| 1h | tsmom_L | 69.5% | 63.6% | 57.9% | 59 |
| 5h | volatility_breakout_L | 68.1% | 61.6% | 55.3% | 66 |
| 15m | volatility_breakout_L | 66.0% | 48.1% | 32.1% | 191 |
| 5h | tsmom_L | 65.2% | 44.9% | 27.2% | 219 |
| 5m | donchian_breakout_L | 62.9% | 59.1% | 55.4% | 39 |
| 1h | volatility_breakout_L | 62.6% | 48.0% | 34.6% | 158 |
| 5m | volatility_breakout_L | 60.9% | 38.8% | 19.6% | 248 |
| 15m | donchian_breakout_L | 59.9% | 56.3% | 52.8% | 38 |
| 5h | ema_crossover_adx_L | 58.3% | 50.7% | 43.4% | 83 |
| 5h | ema_crossover_L | 54.5% | 47.4% | 40.6% | 79 |
| 1d | ema_crossover_adx_L | 52.9% | 49.5% | 46.2% | 37 |
| 15m | tsmom_L | 43.8% | 35.6% | 27.9% | 98 |
| 5h | donchian_breakout_L | 42.6% | 39.2% | 35.8% | 41 |
| 1d | volatility_breakout_L | 42.0% | 40.0% | 38.0% | 24 |
| 1d | ema_crossover_L | 38.8% | 34.8% | 30.9% | 49 |
| 5m | tsmom_L | 37.6% | 24.3% | 12.2% | 171 |
| 1d | donchian_breakout_L | 36.1% | 33.8% | 31.6% | 28 |
| 1h | donchian_breakout_L | 36.0% | 34.9% | 33.8% | 14 |
| 15m | ema_crossover_L | 33.7% | 29.7% | 25.9% | 51 |
| 5m | ema_crossover_L | 33.2% | 29.2% | 25.3% | 51 |
| 1h | ema_crossover_L | 32.1% | 28.1% | 24.3% | 51 |
| 5h | tsmom_LS | 29.7% | -0.2% | -23.2% | 219 |
| 5h | volatility_breakout_LS | 24.4% | 20.1% | 16.0% | 29 |
| 15m | volatility_breakout_LS | 24.3% | -1.1% | -21.3% | 191 |
| 1d | donchian_breakout_LS | 22.7% | 20.9% | 19.1% | 20 |
| 1h | volatility_breakout_LS | 21.5% | 0.6% | -16.8% | 158 |
| 15m | donchian_breakout_LS | 19.3% | 17.5% | 15.8% | 25 |
| 15m | ema_crossover_adx_L | 18.8% | 12.8% | 7.0% | 88 |
| 5h | donchian_breakout_LS | 17.5% | 15.3% | 13.2% | 29 |
| 5m | volatility_breakout_LS | 15.5% | -14.2% | -36.2% | 248 |
| 1d | rsi2_mr | 12.9% | 11.9% | 10.9% | 15 |

27/32 robust strategies still clear 10% p.a. even at 3x the quoted fee.

