"""
Order execution, paper and live, behind one interface. Built on ccxt
(pip install ccxt) rather than a hand-rolled Bitstamp auth client -- ccxt's
Bitstamp adapter is widely used and already handles the exchange's HMAC
signing correctly, which is not something to reimplement from memory for
code that will place real orders.
"""
import config as cfg
import journal


class PaperBroker:
    """Simulates a fill at the current close price, minus the same one-way
    fee used in the backtest. No network calls, no credentials needed."""

    mode = "paper"

    def verify_connectivity(self):
        print("Paper mode: no exchange connection to verify.")
        return True

    def get_available_quote_usd(self, state: dict) -> float:
        return cfg.PAPER_STARTING_USD * state["paper_equity"]

    def get_available_base(self, state: dict) -> float:
        return state.get("base_amount", 0.0)

    def execute(self, side: str, price: float, notional_usd: float) -> dict:
        fee = notional_usd * cfg.FEE_ONE_WAY
        fill = {
            "mode": "paper",
            "side": side,
            "symbol": cfg.SYMBOL,
            "price": price,
            "notional_usd": notional_usd,
            "amount_base": notional_usd / price,
            "fee_usd": fee,
            "order_id": None,
            "status": "simulated_filled",
        }
        journal.log_order(fill)
        return fill


class LiveBroker:
    """Places real market orders via ccxt. Nothing here runs unless
    EXECUTION_MODE=live -- see run_once.py's mode gate."""

    mode = "live"

    def __init__(self):
        import ccxt
        if not cfg.API_KEY or not cfg.API_SECRET:
            raise RuntimeError("EXECUTION_MODE=live requires BITSTAMP_API_KEY and BITSTAMP_API_SECRET")
        klass = getattr(ccxt, cfg.EXCHANGE_ID)
        self.exchange = klass({"apiKey": cfg.API_KEY, "secret": cfg.API_SECRET, "enableRateLimit": True})

    def verify_connectivity(self):
        """Read-only balance check. Run this manually and confirm it prints
        sane numbers BEFORE ever setting EXECUTION_MODE=live for real trading."""
        balance = self.exchange.fetch_balance()
        print("Connected. Free balances:", {k: v for k, v in balance.get("free", {}).items() if v})
        return balance

    def get_available_quote_usd(self, state: dict) -> float:
        quote_ccy = cfg.SYMBOL.split("/")[1]
        return self.exchange.fetch_balance().get("free", {}).get(quote_ccy, 0.0)

    def get_available_base(self, state: dict) -> float:
        base_ccy = cfg.SYMBOL.split("/")[0]
        return self.exchange.fetch_balance().get("free", {}).get(base_ccy, 0.0)

    def execute(self, side: str, price_estimate: float, notional_usd: float) -> dict:
        amount_base = notional_usd / price_estimate
        order = self.exchange.create_order(cfg.SYMBOL, type="market", side=side, amount=amount_base)
        fill = {
            "mode": "live",
            "side": side,
            "symbol": cfg.SYMBOL,
            "price_estimate": price_estimate,
            "notional_usd_estimate": notional_usd,
            "amount_base_requested": amount_base,
            "order_id": order.get("id"),
            "status": order.get("status"),
            "raw_order": order,
        }
        journal.log_order(fill)
        return fill


def get_broker():
    return PaperBroker() if cfg.EXECUTION_MODE == "paper" else LiveBroker()
