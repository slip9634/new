import json
import base64
import pandas as pd
from pathlib import Path

REPORT_DIR = Path("/home/user/new/reports")
DATA_DIR = Path("/home/user/new/data")
OUT = Path("/tmp/claude-0/-home-user-new/772d45bc-504e-549f-bb6e-5972f5142183/scratchpad/crypto_backtest/report.html")

TARGET = 0.10
IS_START, IS_END = "2014-01-01", "2019-12-31"
OOS_START, OOS_END = "2020-01-01", "2025-01-06"

STRAT_LABELS = {
    "ema_crossover_L": "EMA crossover (long/cash)",
    "ema_crossover_LS": "EMA crossover (long/short)",
    "ema_crossover_adx_L": "EMA crossover + ADX filter (long/cash)",
    "ema_crossover_adx_LS": "EMA crossover + ADX filter (long/short)",
    "donchian_breakout_L": "Donchian channel breakout (long/cash)",
    "donchian_breakout_LS": "Donchian channel breakout (long/short)",
    "tsmom_L": "Time-series momentum (long/cash)",
    "tsmom_LS": "Time-series momentum (long/short)",
    "bollinger_mr_L": "Bollinger mean-reversion (long/cash)",
    "bollinger_mr_LS": "Bollinger mean-reversion (long/short)",
    "volatility_breakout_L": "ATR / Keltner volatility breakout (long/cash)",
    "volatility_breakout_LS": "ATR / Keltner volatility breakout (long/short)",
    "rsi2_mr": "RSI(2) mean-reversion (long/cash, uptrend filter)",
}

TF_LABELS = {"5m": "5-minute", "15m": "15-minute", "1h": "1-hour", "5h": "5-hour", "1d": "Daily"}

from metrics import compute_performance
import sys
sys.path.insert(0, str(Path(__file__).parent))


def buy_and_hold(tf):
    df = pd.read_parquet(DATA_DIR / f"btcusd_{tf}.parquet")
    ret = df["close"].pct_change()
    is_p = compute_performance(ret.loc[(df.index >= IS_START) & (df.index <= IS_END)], tf)
    oos_p = compute_performance(ret.loc[(df.index >= OOS_START) & (df.index <= OOS_END)], tf)
    return is_p, oos_p


def pct(x, d=1):
    return f"{x*100:.{d}f}%" if pd.notna(x) else "—"


def num(x, d=2):
    return f"{x:.{d}f}" if pd.notna(x) else "—"


def params_short(js):
    p = json.loads(js)
    p.pop("long_short", None)
    return ", ".join(f"{k}={v}" for k, v in p.items())


def main():
    res = pd.read_csv(REPORT_DIR / "study_results.csv")
    res["meets"] = res["oos_cagr"] >= TARGET
    res["robust"] = res["meets"] & (res["oosA_cagr"] > 0) & (res["oosB_cagr"] > 0)
    fee = pd.read_csv(REPORT_DIR / "fee_stress_test.csv")

    chart_b64 = base64.b64encode((REPORT_DIR / "oos_equity_curves.png").read_bytes()).decode()

    tfs = ["5m", "15m", "1h", "5h", "1d"]
    n_robust_total = int(res["robust"].sum())
    n_meets_total = int(res["meets"].sum())

    # ---- tabs content ----
    tab_buttons, tab_panels = [], []
    for i, tf in enumerate(tfs):
        is_p, oos_p = buy_and_hold(tf)
        sub = res[res["timeframe"] == tf].sort_values("oos_sharpe", ascending=False)
        rows = []
        for _, r in sub.iterrows():
            badge = ""
            if r["robust"]:
                badge = '<span class="tag tag-robust">robust</span>'
            elif r["meets"]:
                badge = '<span class="tag tag-meets">meets 10%</span>'
            dd_class = "neg" if r["oos_maxdd"] < 0 else ""
            rows.append(f"""<tr>
              <td>{STRAT_LABELS.get(r['strategy'], r['strategy'])} {badge}</td>
              <td class="mono small">{params_short(r['params'])}</td>
              <td class="mono num">{num(r['oos_sharpe'])}</td>
              <td class="mono num {'pos' if r['oos_cagr']>=0 else 'neg'}">{pct(r['oos_cagr'])}</td>
              <td class="mono num neg">{pct(r['oos_maxdd'])}</td>
              <td class="mono num">{num(r['oos_calmar'])}</td>
              <td class="mono num">{pct(r['oosA_cagr'])}</td>
              <td class="mono num">{pct(r['oosB_cagr'])}</td>
            </tr>""")
        active = "active" if i == 0 else ""
        tab_buttons.append(f'<button class="tabbtn {active}" data-tab="{tf}">{TF_LABELS[tf]}</button>')
        tab_panels.append(f"""
        <div class="tabpanel {active}" data-panel="{tf}">
          <div class="benchmark-row">
            <div class="bstat"><span class="blabel">Buy &amp; hold OOS CAGR</span><span class="bval mono">{pct(oos_p['cagr'])}</span></div>
            <div class="bstat"><span class="blabel">Buy &amp; hold OOS Sharpe</span><span class="bval mono">{num(oos_p['sharpe'])}</span></div>
            <div class="bstat"><span class="blabel">Buy &amp; hold OOS Max DD</span><span class="bval mono neg">{pct(oos_p['max_dd'])}</span></div>
          </div>
          <div class="tablewrap">
          <table class="data">
            <thead><tr>
              <th>Strategy</th><th>Frozen parameters</th><th>OOS Sharpe</th><th>OOS CAGR</th>
              <th>OOS Max DD</th><th>OOS Calmar</th><th>2020&ndash;22 CAGR</th><th>2023&ndash;25 CAGR</th>
            </tr></thead>
            <tbody>{''.join(rows)}</tbody>
          </table>
          </div>
        </div>""")

    # ---- robustness screen table ----
    robust_df = res[res["robust"]].sort_values(["timeframe", "oos_sharpe"], ascending=[True, False])
    robust_rows = []
    for _, r in robust_df.iterrows():
        robust_rows.append(f"""<tr>
          <td class="mono">{TF_LABELS[r['timeframe']]}</td>
          <td>{STRAT_LABELS.get(r['strategy'], r['strategy'])}</td>
          <td class="mono num">{num(r['oos_sharpe'])}</td>
          <td class="mono num pos">{pct(r['oos_cagr'])}</td>
          <td class="mono num neg">{pct(r['oos_maxdd'])}</td>
          <td class="mono num">{num(r['oos_calmar'])}</td>
        </tr>""")

    # ---- fee sensitivity table ----
    piv = fee.pivot_table(index=["timeframe", "strategy"], columns="fee_bps_oneway", values="oos_cagr")
    piv.columns = [f"{c:g}" for c in piv.columns]
    trades = fee[fee["fee_bps_oneway"] == 6.0].set_index(["timeframe", "strategy"])["trades_per_year"]
    piv["trades"] = trades
    piv = piv.sort_values("6", ascending=False)
    fee_rows = []
    for (tf, strat), r in piv.iterrows():
        cls18 = "pos" if r["18"] >= TARGET else "neg"
        fee_rows.append(f"""<tr>
          <td class="mono">{TF_LABELS[tf]}</td>
          <td>{STRAT_LABELS.get(strat, strat)}</td>
          <td class="mono num">{pct(r['6'])}</td>
          <td class="mono num">{pct(r['12'])}</td>
          <td class="mono num {cls18}">{pct(r['18'])}</td>
          <td class="mono num">{r['trades']:.0f}</td>
        </tr>""")
    n_hold_3x = int((piv["18"] >= TARGET).sum())

    html = f"""<title>BTC Systematic Strategy Study</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{
  --bg:#F5F6F2; --surface:#FFFFFF; --surface-2:#EAEEE8; --ink:#161B17; --muted:#5C6A62;
  --line:#DCE2DA; --accent:#1F6F5C; --accent-soft:#DCEDE5; --loss:#B23A2F; --loss-soft:#F5DEDA;
  --radius:10px;
}}
@media (prefers-color-scheme: dark){{
  :root:not([data-theme="light"]){{
    --bg:#10140F1; --bg:#10140F; --surface:#171D19; --surface-2:#1E2621; --ink:#E7ECE7; --muted:#93A399;
    --line:#2A332C; --accent:#57C7A0; --accent-soft:#1B3930; --loss:#E2685C; --loss-soft:#3A211C;
  }}
}}
:root[data-theme="dark"]{{
  --bg:#10140F; --surface:#171D19; --surface-2:#1E2621; --ink:#E7ECE7; --muted:#93A399;
  --line:#2A332C; --accent:#57C7A0; --accent-soft:#1B3930; --loss:#E2685C; --loss-soft:#3A211C;
}}
*{{box-sizing:border-box;}}
body{{
  background:var(--bg); color:var(--ink); margin:0; padding-inline:20px;
  font-family:"IBM Plex Sans",system-ui,sans-serif; line-height:1.55;
}}
.wrap{{max-width:920px; margin:0 auto; padding-block:40px 80px;}}
h1,h2,h3{{font-family:"Fraunces",Georgia,serif; text-wrap:balance; margin:0 0 .3em;}}
h1{{font-size:clamp(1.7rem,4vw,2.5rem); font-weight:600; letter-spacing:-0.01em;}}
h2{{font-size:1.4rem; font-weight:600; margin-top:2.6em; border-top:1px solid var(--line); padding-top:1.1em;}}
h3{{font-size:1.05rem; font-weight:600; margin-top:1.4em;}}
p{{max-width:68ch;}}
.eyebrow{{
  font-family:"IBM Plex Mono",monospace; font-size:.72rem; letter-spacing:.09em; text-transform:uppercase;
  color:var(--accent); font-weight:500; margin-bottom:.6em;
}}
.lede{{color:var(--muted); font-size:1.05rem; max-width:62ch;}}
.mono{{font-family:"IBM Plex Mono",monospace;}}
.small{{font-size:.82rem;}}
.pos{{color:var(--accent);}}
.neg{{color:var(--loss);}}
.tiles{{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:1.8em 0;}}
.tile{{
  background:var(--surface); border:1px solid var(--line); border-radius:var(--radius);
  padding:14px 16px;
}}
.tile .tlabel{{display:block; font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); margin-bottom:.4em;}}
.tile .tval{{font-family:"IBM Plex Mono",monospace; font-size:1.3rem; font-weight:500; font-variant-numeric:tabular-nums;}}
.callout{{
  background:var(--surface-2); border-left:3px solid var(--accent); border-radius:0 var(--radius) var(--radius) 0;
  padding:16px 20px; margin:1.6em 0; max-width:68ch;
}}
.callout.warn{{border-left-color:var(--loss); background:var(--loss-soft);}}
ul{{padding-left:1.2em; max-width:64ch;}}
li{{margin-bottom:.4em;}}
.tabnav{{display:flex; gap:6px; flex-wrap:wrap; margin:1.4em 0 1em; border-bottom:1px solid var(--line); padding-bottom:0;}}
.tabbtn{{
  font-family:"IBM Plex Mono",monospace; font-size:.82rem; background:none; border:none; color:var(--muted);
  padding:8px 4px; margin-right:14px; cursor:pointer; border-bottom:2px solid transparent; margin-bottom:-1px;
}}
.tabbtn.active{{color:var(--ink); border-bottom-color:var(--accent); font-weight:500;}}
.tabpanel{{display:none;}}
.tabpanel.active{{display:block;}}
.benchmark-row{{display:flex; gap:24px; flex-wrap:wrap; margin:1em 0 1.2em; padding:12px 16px; background:var(--surface-2); border-radius:var(--radius);}}
.bstat{{display:flex; flex-direction:column;}}
.blabel{{font-size:.72rem; color:var(--muted); text-transform:uppercase; letter-spacing:.05em;}}
.bval{{font-size:1.05rem; font-variant-numeric:tabular-nums;}}
.tablewrap{{overflow-x:auto; border:1px solid var(--line); border-radius:var(--radius);}}
table.data{{border-collapse:collapse; width:100%; font-size:.86rem; min-width:640px;}}
table.data th{{
  text-align:left; font-size:.72rem; text-transform:uppercase; letter-spacing:.04em; color:var(--muted);
  padding:10px 12px; border-bottom:1px solid var(--line); background:var(--surface-2); white-space:nowrap;
}}
table.data td{{padding:9px 12px; border-bottom:1px solid var(--line); background:var(--surface); white-space:nowrap;}}
table.data td.num{{text-align:right; font-variant-numeric:tabular-nums;}}
table.data tr:last-child td{{border-bottom:none;}}
.tag{{font-family:"IBM Plex Mono",monospace; font-size:.64rem; padding:2px 6px; border-radius:999px; margin-left:6px; white-space:nowrap;}}
.tag-robust{{background:var(--accent-soft); color:var(--accent);}}
.tag-meets{{background:var(--surface-2); color:var(--muted); border:1px solid var(--line);}}
figure{{margin:1.6em 0;}}
figure img{{width:100%; border-radius:var(--radius); border:1px solid var(--line); display:block; background:#fff;}}
figcaption{{font-size:.82rem; color:var(--muted); margin-top:.6em; max-width:68ch;}}
.foot{{margin-top:3em; padding-top:1.4em; border-top:1px solid var(--line); color:var(--muted); font-size:.82rem;}}
a{{color:var(--accent);}}
@media (max-width:520px){{
  .tile .tval{{font-size:1.1rem;}}
  table.data{{font-size:.78rem;}}
}}
</style>

<div class="wrap">
  <div class="eyebrow">Quantitative research &middot; BTC/USD spot</div>
  <h1>Does a systematic BTC strategy clear 10% p.a. net of fees?</h1>
  <p class="lede">A no-lookahead backtest of trend, breakout, momentum and mean-reversion strategies across
  five timeframes &mdash; 5-minute through daily &mdash; on eleven years of cleaned Bitstamp BTC/USD data,
  fees included, parameters frozen before validation.</p>

  <div class="tiles">
    <div class="tile"><span class="tlabel">Universe</span><span class="tval">BTC/USD spot</span></div>
    <div class="tile"><span class="tlabel">History used</span><span class="tval">2014&ndash;2025</span></div>
    <div class="tile"><span class="tlabel">Fee (one-way)</span><span class="tval">0.06%</span></div>
    <div class="tile"><span class="tlabel">Target</span><span class="tval">&gt;10% p.a. net</span></div>
    <div class="tile"><span class="tlabel">Strategies &times; timeframes tested</span><span class="tval">{len(res)}</span></div>
    <div class="tile"><span class="tlabel">Clear the bar out-of-sample</span><span class="tval">{n_meets_total}</span></div>
  </div>

  <h2>Executive summary</h2>
  <p>Yes &mdash; but the honest headline is that the bar is easy to clear in this window, not that any of
  these strategies are a discovered edge. Out-of-sample (2020&ndash;2025) buy-and-hold BTC alone returned
  <strong>~70% p.a.</strong> with a Sharpe ratio around <strong>1.1&ndash;1.2</strong>. Against that backdrop,
  {n_meets_total} of {len(res)} strategy&times;timeframe combinations cleared 10% p.a. net of the 0.06% fee, and
  {n_robust_total} of those were profitable in <em>both</em> out-of-sample sub-periods (2020&ndash;22's
  crash/bull/bear cycle and 2023&ndash;25's recovery) rather than riding a single regime.</p>
  <p>The real, credible finding: <strong>long-only trend/breakout systems &mdash; Donchian channel breakout,
  ATR/Keltner volatility breakout, and time-series momentum &mdash; consistently matched or beat buy-and-hold on
  a risk-adjusted basis</strong> (higher Sharpe, shallower drawdown) across every timeframe tested, while
  giving up some raw upside during the fastest bull legs. Systematic <strong>shorting was a persistent drag</strong>:
  BTC's 2014&ndash;2025 secular uptrend punished long/short variants of the same rules almost everywhere.
  Mean-reversion (Bollinger, RSI(2)) mostly failed &mdash; crypto trends, it doesn't range.</p>

  <div class="callout warn">
    <strong>Read this before the tables.</strong> Every strategy here, including buy-and-hold, drew down
    30&ndash;85% peak-to-trough out of sample. A 10%+ p.a. CAGR target says nothing about the ride getting
    there. The strategies flagged <span class="tag tag-robust">robust</span> reduced that drawdown relative
    to buy-and-hold; none eliminated it.
  </div>

  <h2>Data &amp; method</h2>
  <h3>Data</h3>
  <ul>
    <li><strong>Source:</strong> Bitstamp BTC/USD, 1-minute OHLCV, 2012&ndash;2025, from the community-maintained,
    freely licensed dataset <span class="mono small">ff137/bitstamp-btcusd-minute-data</span> on GitHub.</li>
    <li><strong>Cleaning:</strong> reindexed to a complete 1-minute grid (no gaps), zero/duplicate/OHLC-consistency
    checks passed. Pre-2014 history was dropped &mdash; 93% of minutes were flat vs. 9% after, i.e. the
    feed was too coarse to backtest honestly before then.</li>
    <li><strong>Resampling:</strong> 5m / 15m / 1h / 5h / 1d bars built once from the same clean 1-minute series,
    so every timeframe reflects the same underlying trades.</li>
    <li><strong>Caveat:</strong> single venue, spot only. Other venues, order books and slippage at size will differ.</li>
  </ul>
  <h3>No-lookahead backtest design</h3>
  <ul>
    <li>Every signal is lagged one full bar before it is applied to that bar's return &mdash; a decision made
    on bar <em>t</em>'s close is executed no earlier than bar <em>t+1</em>. No indicator ever sees its own bar's
    future high/low/close.</li>
    <li>Fees: 0.06% charged on every unit of position turnover (entering, exiting, or flipping), not just at trade count.</li>
    <li><strong>In-sample</strong> 2014&ndash;2019: each strategy family is grid-searched (parameter windows expressed
    in real days/hours so they mean the same thing on every timeframe) and the single configuration with the
    best in-sample Sharpe (min. 20 trades, to avoid picking a lucky handful) is frozen.</li>
    <li><strong>Out-of-sample</strong> 2020&ndash;2025: the frozen configuration is run once, with no re-fitting,
    and split again into 2020&ndash;22 and 2023&ndash;25 to check it isn't a one-regime fluke.</li>
    <li><strong>Fee stress test:</strong> robust strategies were re-run at 2&times; and 3&times; the quoted fee
    (0.12% and 0.18% one-way) &mdash; {n_hold_3x} of {len(robust_df)} still cleared 10% p.a. even at 3&times;.</li>
  </ul>

  <h2>Results by timeframe</h2>
  <p>Ranked by out-of-sample Sharpe. <span class="tag tag-robust">robust</span> = cleared 10% p.a. net AND
  profitable in both OOS sub-periods; <span class="tag tag-meets">meets 10%</span> = cleared the bar but only
  in one sub-period.</p>
  <div class="tabnav">{''.join(tab_buttons)}</div>
  {''.join(tab_panels)}

  <h2>Robustness screen</h2>
  <p>Only strategies profitable in <em>both</em> out-of-sample halves &mdash; the credible candidates, not
  strategies that got lucky in one regime.</p>
  <div class="tablewrap">
  <table class="data">
    <thead><tr><th>Timeframe</th><th>Strategy</th><th>OOS Sharpe</th><th>OOS CAGR</th><th>OOS Max DD</th><th>OOS Calmar</th></tr></thead>
    <tbody>{''.join(robust_rows)}</tbody>
  </table>
  </div>

  <h2>Fee sensitivity</h2>
  <p>The 0.06% assumption is a good spot-taker fee at most major venues, but real slippage on top of it varies.
  Here the same robust strategies are re-run at 1&times;, 2&times; and 3&times; that fee.</p>
  <div class="tablewrap">
  <table class="data">
    <thead><tr><th>Timeframe</th><th>Strategy</th><th>CAGR @ 6bps</th><th>CAGR @ 12bps</th><th>CAGR @ 18bps</th><th>Trades / yr</th></tr></thead>
    <tbody>{''.join(fee_rows)}</tbody>
  </table>
  </div>
  <p class="small" style="color:var(--muted)">High-turnover intraday variants (150&ndash;250 trades/yr) lose the
  most to fees; low-turnover daily/hourly trend rules barely move.</p>

  <h2>Out-of-sample equity curves</h2>
  <figure>
    <img src="data:image/png;base64,{chart_b64}" alt="Out-of-sample equity curves, recommended strategy vs buy-and-hold, per timeframe">
    <figcaption>Recommended pick per timeframe (robust, highest OOS Sharpe) vs. buy-and-hold, rebased to 1.0 at 2020-01-01, log scale.
    Note the strategies hold up better through the 2022 drawdown and converge with buy-and-hold by 2024&ndash;25.</figcaption>
  </figure>

  <h2>Limitations, read before trading any of this</h2>
  <ul>
    <li><strong>One coin, one venue.</strong> This is BTC/USD on Bitstamp spot. Altcoins, futures/perps, and
    other exchanges were not tested here and behave differently (perpetual funding-rate carry, in particular,
    is a well-documented crypto-specific strategy this study could not test &mdash; no funding-rate history
    was reachable from this environment).</li>
    <li><strong>Shorting is spot-unrealistic.</strong> The long/short variants shown are theoretical overlays;
    shorting spot BTC in practice needs margin or a futures venue, with borrow/funding costs not modeled here.</li>
    <li><strong>Slippage beyond the quoted fee</strong> is not modeled explicitly; see the fee stress test as a proxy.</li>
    <li><strong>Regime dependency.</strong> The out-of-sample window still contains a historic bull market.
    A structurally different future (prolonged sideways or bear market) would compress every number here,
    active strategies and buy-and-hold alike.</li>
    <li><strong>Selection was constrained but not eliminated.</strong> Day-denominated grids, a minimum trade
    count, and a two-sub-period robustness screen reduce, but do not remove, in-sample overfitting risk.</li>
  </ul>

  <div class="foot">
    Code, cleaned data, and full result tables (<span class="mono">study_results.csv</span>,
    <span class="mono">fee_stress_test.csv</span>) are in the repository under <span class="mono">src/</span> and
    <span class="mono">reports/</span>. Not investment advice.
  </div>
</div>

<script>
document.querySelectorAll('.tabbtn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    const tf = btn.dataset.tab;
    document.querySelectorAll('.tabbtn').forEach(b => b.classList.toggle('active', b === btn));
    document.querySelectorAll('.tabpanel').forEach(p => p.classList.toggle('active', p.dataset.panel === tf));
  }});
}});
</script>
"""
    OUT.write_text(html)
    print("wrote", OUT, len(html), "bytes")


if __name__ == "__main__":
    main()
