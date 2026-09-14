"""Append-only journal + small persisted state. Deliberately simple (JSON/JSONL
files, not a database) so every record is human-readable and diffable."""
import json
import datetime as dt
import config as cfg

DEFAULT_STATE = {
    "position": 0,               # 0 = flat/cash, 1 = long BTC -- must mirror the exchange's actual state
    "paper_equity": 1.0,         # only meaningful in paper mode
    "peak_equity": 1.0,
    "trade_count_today": 0,
    "last_trade_date": None,     # ISO date string
    "last_processed_bar": None,  # ISO timestamp of the last bar a decision was made from
}


def load_state() -> dict:
    if cfg.STATE_JSON_PATH.exists():
        return {**DEFAULT_STATE, **json.loads(cfg.STATE_JSON_PATH.read_text())}
    return dict(DEFAULT_STATE)


def save_state(state: dict) -> None:
    cfg.STATE_JSON_PATH.write_text(json.dumps(state, indent=2, default=str))


def _append_jsonl(path, record: dict) -> None:
    record = {"logged_at": dt.datetime.now(dt.timezone.utc).isoformat(), **record}
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def log_signal(diagnostics: dict, prev_position: int) -> None:
    _append_jsonl(cfg.SIGNAL_LOG_PATH, {**diagnostics, "prev_position": prev_position})


def log_order(record: dict) -> None:
    _append_jsonl(cfg.ORDERS_LOG_PATH, record)


def bump_daily_trade_count(state: dict) -> dict:
    today = dt.date.today().isoformat()
    if state.get("last_trade_date") != today:
        state["trade_count_today"] = 0
        state["last_trade_date"] = today
    state["trade_count_today"] += 1
    return state


def update_equity_and_check_kill_switch(state: dict, bar_return: float) -> bool:
    """Only tracks paper-mode equity as a proxy for 'is this behaving like the
    backtest said it would'. In live mode, wire this to real account equity
    before trusting it. Returns True if the kill switch should trip."""
    state["paper_equity"] *= (1 + bar_return)
    state["peak_equity"] = max(state["peak_equity"], state["paper_equity"])
    drawdown = state["paper_equity"] / state["peak_equity"] - 1
    return drawdown <= -cfg.DRAWDOWN_KILL_SWITCH
