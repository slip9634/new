"""
Data for the "Ernest Chan (2013) -- does it still work?" study.

Everything here is fetched from raw.githubusercontent.com, the only market-data
path reachable from this sandbox (Yahoo/stooq/FRED/IBKR APIs are blocked).
All series are real, publicly maintained datasets:

  - FX: datasets/exchange-rates  (Federal Reserve H.10 noon buying rates,
        daily, quoted as FOREIGN CURRENCY PER USD). We invert to USD per unit
        of foreign currency so "long AUD" = long the series.
  - WTI / Brent spot: datasets/oil-prices (EIA daily spot prices)
  - Henry Hub natural gas spot: datasets/natural-gas (EIA daily spot)
  - VIX index: datasets/finance-vix (CBOE daily) -- diagnostic only, the index
        itself is not tradable and we have no VX futures history.
  - SPY OHLC: already in this repo, data/turnaround/spy_raw.csv (2000-2025).

Raw downloads are cached under data/chan2013/ so the study is reproducible
offline once fetched.

Known limitations (reported again in the study write-up):
  - Oil and gas are SPOT prices, not futures. Spot returns are not what a
    futures trader earns (no roll yield, and spot gas has delivery-point
    spikes that can't be captured). Commodity results are indicative only.
  - FX spot returns exclude the interest-rate carry a forwards trader would
    earn or pay.
"""
from pathlib import Path
import urllib.request

import pandas as pd

RAW = "https://raw.githubusercontent.com"
DATA_DIR = Path("/home/user/new/data/chan2013")
SPY_PATH = Path("/home/user/new/data/turnaround/spy_raw.csv")

SOURCES = {
    "fx.csv": f"{RAW}/datasets/exchange-rates/main/data/daily.csv",
    "wti.csv": f"{RAW}/datasets/oil-prices/main/data/wti-daily.csv",
    "brent.csv": f"{RAW}/datasets/oil-prices/main/data/brent-daily.csv",
    "natgas.csv": f"{RAW}/datasets/natural-gas/main/data/daily.csv",
    "vix.csv": f"{RAW}/datasets/finance-vix/main/data/vix-daily.csv",
}

# G10 ex-USD (DKK left out: it is pegged to EUR and would just duplicate it).
FX_COUNTRIES = {
    "Australia": "AUD", "Canada": "CAD", "Euro": "EUR", "Japan": "JPY",
    "Switzerland": "CHF", "United Kingdom": "GBP", "New Zealand": "NZD",
    "Sweden": "SEK", "Norway": "NOK",
}


def fetch(force: bool = False) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        out = DATA_DIR / name
        if out.exists() and not force:
            continue
        with urllib.request.urlopen(url, timeout=120) as resp:
            out.write_bytes(resp.read())


def _price_series(name: str) -> pd.Series:
    df = pd.read_csv(DATA_DIR / name, parse_dates=["Date"]).set_index("Date").sort_index()
    s = pd.to_numeric(df["Price"], errors="coerce")
    s = s[s > 0]  # WTI printed a negative spot on 2020-04-20; not a usable price level
    return s[~s.index.duplicated()].dropna()


def load_fx() -> pd.DataFrame:
    """USD value of one unit of each G10 currency, wide by date."""
    df = pd.read_csv(DATA_DIR / "fx.csv", parse_dates=["Date"])
    df = df[df["Country"].isin(FX_COUNTRIES)]
    wide = df.pivot_table(index="Date", columns="Country", values="Exchange rate")
    wide = wide.rename(columns=FX_COUNTRIES).sort_index()
    wide = wide.where(wide > 0)
    return 1.0 / wide


def load_commodities() -> pd.DataFrame:
    return pd.DataFrame({
        "WTI": _price_series("wti.csv"),
        "BRENT": _price_series("brent.csv"),
        "NATGAS": _price_series("natgas.csv"),
    }).sort_index()


def load_vix() -> pd.Series:
    df = pd.read_csv(DATA_DIR / "vix.csv", parse_dates=["DATE"]).set_index("DATE").sort_index()
    return df["CLOSE"]


def load_spy() -> pd.DataFrame:
    df = pd.read_csv(SPY_PATH)
    df.columns = [c.strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["datetime"], format="%m/%d/%Y")
    df = df.set_index("date").sort_index()
    df = df[~df.index.duplicated()]
    return df[["open", "high", "low", "close", "volume"]]


def daily_panel() -> pd.DataFrame:
    """All tradable close series on one US-business-day calendar.

    Gaps of up to 3 days (local holidays) are forward-filled -- only ever
    carrying the last known price forward, never backward.
    """
    panel = pd.concat([load_fx(), load_commodities(), load_spy()["close"].rename("SPY")], axis=1, sort=True)
    panel = panel[panel.index.dayofweek < 5]
    return panel.ffill(limit=3)


if __name__ == "__main__":
    fetch()
    p = daily_panel()
    for c in p.columns:
        s = p[c].dropna()
        print(f"{c:7s} {s.index[0].date()} -> {s.index[-1].date()}  n={len(s)}")
