"""
Data preparation for the crypto strategy backtest.

Source: Bitstamp BTC/USD 1-minute OHLCV, 2012-01-01 -> 2025-01-06
        https://github.com/ff137/bitstamp-btcusd-minute-data
        (aggregated by the repo maintainer from Bitstamp's public trade history;
         a widely used, freely licensed dataset for BTC/USD retail-venue backtests)

This script:
 1. Loads the raw 1-minute CSV.
 2. Validates it (monotonic timestamps, no duplicate timestamps, regular 60s grid).
 3. Reindexes to a complete 1-minute grid so every higher timeframe bar is built
    from a fixed number of minutes (missing minutes = no trade -> flat candle,
    volume 0, OHLC = previous close). This is standard for illiquid early-history
    crypto data and never uses information from the future.
 4. Drops the pre-liquidity era (see LIQUIDITY_START) where the venue traded at a
    handful of static prices with near-zero volume -- backtesting there would be
    fitting to noise, not a strategy edge.
 5. Resamples to 5min, 15min, 1H and 1D bars with proper OHLCV aggregation.
 6. Writes Parquet files to data/ and a data-quality report to reports/.

No forward-looking transforms happen here: resampling only ever aggregates bars
that are fully closed, and reindex/ffill only ever carries the LAST known price
forward in time, never backward.
"""
import pandas as pd
import numpy as np
from pathlib import Path

RAW_PATH = Path("/tmp/claude-0/-home-user-new/772d45bc-504e-549f-bb6e-5972f5142183/scratchpad/crypto_backtest/data/btcusd_bitstamp_1min.csv")
DATA_DIR = Path("/home/user/new/data")
REPORT_DIR = Path("/home/user/new/reports")
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Bitstamp BTC/USD was extremely thin (near-zero volume, flat prices for hours)
# before this date. Confirmed below via the volume/zero-return diagnostics.
LIQUIDITY_START = "2014-01-01"


def load_raw() -> pd.DataFrame:
    df = pd.read_csv(RAW_PATH)
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    df["ts"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df = df.drop(columns=["timestamp"]).set_index("ts").sort_index()
    return df


def validate_raw(df: pd.DataFrame) -> dict:
    report = {}
    report["n_rows"] = len(df)
    report["start"] = str(df.index.min())
    report["end"] = str(df.index.max())
    report["n_duplicate_ts"] = int(df.index.duplicated().sum())
    diffs = df.index.to_series().diff().dropna()
    report["median_step_seconds"] = diffs.median().total_seconds()
    report["n_steps_not_60s"] = int((diffs != pd.Timedelta(seconds=60)).sum())
    full_range = pd.date_range(df.index.min(), df.index.max(), freq="1min", tz="UTC")
    report["expected_minutes"] = len(full_range)
    report["missing_minutes"] = len(full_range) - len(df)
    report["pct_missing_minutes"] = 100 * report["missing_minutes"] / len(full_range)
    report["n_nan_any"] = int(df.isna().any(axis=1).sum())
    report["n_negative_or_zero_price"] = int((df[["open", "high", "low", "close"]] <= 0).any(axis=1).sum())
    bad_ohlc = (df["high"] < df[["open", "close", "low"]].max(axis=1)) | (df["low"] > df[["open", "close", "high"]].min(axis=1))
    report["n_ohlc_consistency_violations"] = int(bad_ohlc.sum())
    return report, full_range


def clean(df: pd.DataFrame, full_range: pd.DatetimeIndex) -> pd.DataFrame:
    df = df[~df.index.duplicated(keep="first")]
    df = df.reindex(full_range)
    # Missing minute -> no trade: flat candle at previous close, zero volume.
    df["close"] = df["close"].ffill()
    for col in ["open", "high", "low"]:
        df[col] = df[col].fillna(df["close"])
    df["volume"] = df["volume"].fillna(0.0)
    df = df.dropna()  # only possible remaining NaNs are a leading close with no prior data
    return df


def liquidity_diagnostics(df: pd.DataFrame) -> pd.DataFrame:
    daily_vol = df["volume"].resample("1D").sum()
    zero_ret_share = (df["close"].pct_change() == 0).resample("1D").mean()
    diag = pd.DataFrame({"daily_volume_btc": daily_vol, "zero_return_minute_share": zero_ret_share})
    return diag


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    out = df.resample(rule, label="left", closed="left").agg(agg)
    out = out.dropna(subset=["open", "high", "low", "close"])
    return out


def main():
    lines = []
    raw = load_raw()
    report, full_range = validate_raw(raw)
    lines.append("# Data quality report — Bitstamp BTC/USD 1-minute\n")
    lines.append("## Raw file, full history\n")
    for k, v in report.items():
        lines.append(f"- **{k}**: {v}")

    cleaned = clean(raw, full_range)

    diag = liquidity_diagnostics(cleaned)
    diag.to_csv(REPORT_DIR / "liquidity_diagnostics_daily.csv")

    pre = diag.loc[:LIQUIDITY_START]
    post = diag.loc[LIQUIDITY_START:]
    lines.append("\n## Liquidity check (why we drop data before {})\n".format(LIQUIDITY_START))
    lines.append(f"- Median daily volume BEFORE cutoff: {pre['daily_volume_btc'].median():.2f} BTC")
    lines.append(f"- Median daily volume AFTER cutoff: {post['daily_volume_btc'].median():.2f} BTC")
    lines.append(f"- Median share of flat (zero-return) minutes BEFORE cutoff: {pre['zero_return_minute_share'].median()*100:.1f}%")
    lines.append(f"- Median share of flat (zero-return) minutes AFTER cutoff: {post['zero_return_minute_share'].median()*100:.1f}%")

    final = cleaned.loc[LIQUIDITY_START:].copy()
    lines.append(f"\n## Final analysis dataset\n")
    lines.append(f"- Range: {final.index.min()} -> {final.index.max()}")
    lines.append(f"- Rows (1-minute bars): {len(final)}")

    # Persist the cleaned 1-minute series only as parquet in the scratchpad
    # (too large to commit); commit the resampled timeframes used for the study.
    scratch_dir = RAW_PATH.parent
    final.to_parquet(scratch_dir / "btcusd_1min_clean.parquet")

    for rule, name in [("5min", "5m"), ("15min", "15m"), ("1h", "1h"), ("5h", "5h"), ("1D", "1d")]:
        res = resample_ohlcv(final, rule)
        out_path = DATA_DIR / f"btcusd_{name}.parquet"
        res.to_parquet(out_path)
        lines.append(f"\n### {name} bars")
        lines.append(f"- Rows: {len(res)}")
        lines.append(f"- Range: {res.index.min()} -> {res.index.max()}")
        lines.append(f"- Saved: {out_path}")

    (REPORT_DIR / "data_quality_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
