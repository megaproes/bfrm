#!/usr/bin/env python3
"""
Monitors all USDT-M futures positions on Binance.
If |positionAmt| * entryPrice > MAX_NOTIONAL, submits a reduce-only market order
to trim the excess (rounded down to symbol LOT_SIZE).
"""

import os
import sys
import time
import logging
from decimal import Decimal, ROUND_DOWN, getcontext
from typing import Dict, Tuple
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException

# ---------- CONFIG ----------
# Option 1: hard-code keys here (leave empty to use environment variables).
BINANCE_API_KEY_HARDCODE = ""
BINANCE_API_SECRET_HARDCODE = ""
MAX_NOTIONAL_HARDCODE = 100      # USD
SLEEP_INTERVAL_HARDCODE = 5

# Limits / timings (env overrides are supported)
MAX_NOTIONAL = Decimal(os.getenv("MAX_NOTIONAL", MAX_NOTIONAL_HARDCODE))  # USD cap per position
SLEEP_INTERVAL = int(os.getenv("SLEEP_INTERVAL", SLEEP_INTERVAL_HARDCODE))     # seconds

# Log file in script directory
LOG_PATH = os.path.join(os.path.dirname(__file__), "risk_manager.log")

# High precision for Decimal operations
getcontext().prec = 28

# ---------- LOGGING ----------
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("risk_manager")


def load_api_keys() -> Tuple[str, str]:
    """Use hard-coded keys if set; otherwise read from environment."""
    key = BINANCE_API_KEY_HARDCODE or os.getenv("BINANCE_API_KEY")
    sec = BINANCE_API_SECRET_HARDCODE or os.getenv("BINANCE_API_SECRET")
    if not key or not sec:
        log.error("API keys not found. Set BINANCE_API_KEY / BINANCE_API_SECRET or hard-code them.")
        raise SystemExit(1)
    return key, sec


def load_step_sizes(client: Client) -> Dict[str, Decimal]:
    """Map symbol -> LOT_SIZE step (Decimal)."""
    info = client.futures_exchange_info()
    steps: Dict[str, Decimal] = {}
    for s in info["symbols"]:
        sym = s["symbol"]
        for f in s["filters"]:
            if f["filterType"] == "LOT_SIZE":
                steps[sym] = Decimal(f["stepSize"])
                break
    log.info(f"Loaded step sizes for {len(steps)} symbols. MAX_NOTIONAL=${MAX_NOTIONAL}")
    return steps


def format_qty(d: Decimal) -> str:
    """Normalize Decimal to string Binance accepts (no scientific notation)."""
    return format(d.normalize(), "f")


def monitor(client: Client) -> None:
    steps = load_step_sizes(client)

    while True:
        try:
            # Each item has strings: symbol, positionAmt, entryPrice, etc.
            positions = client.futures_position_information()

            for p in positions:
                sym = p["symbol"]
                qty = Decimal(p["positionAmt"])
                if qty == 0:
                    continue

                entry = Decimal(p["entryPrice"])  # assumed > 0 if qty != 0
                notional = abs(qty * entry)
                log.info(f"{sym:10s} | qty={qty:+.6f} @ {entry:.8f} -> ${notional:.2f}")

                if notional <= MAX_NOTIONAL:
                    continue

                # Direction: long -> SELL to reduce; short -> BUY to reduce.
                side = Client.SIDE_SELL if qty > 0 else Client.SIDE_BUY
                sign = Decimal(1) if qty > 0 else Decimal(-1)

                # Target qty at the notional cap (same sign as current position).
                target_qty = (MAX_NOTIONAL / entry) * sign
                excess = qty - target_qty  # signed
                step = steps.get(sym)

                if step is None:
                    log.warning(f"{sym}: step size not found, skipping.")
                    continue

                # Order size: absolute excess, rounded down to LOT_SIZE.
                close_qty = abs(excess).quantize(step, rounding=ROUND_DOWN)
                if close_qty < step:
                    log.info(f"{sym}: excess < step size ({step}), skipping.")
                    continue

                qty_str = format_qty(close_qty)
                try:
                    order = client.futures_create_order(
                        symbol=sym,
                        side=side,
                        type="MARKET",
                        quantity=qty_str,
                        reduceOnly=True,
                    )
                    log.info(f"{sym}: closed excess {qty_str} (orderId={order['orderId']})")
                except (BinanceAPIException, BinanceOrderException) as e:
                    log.error(f"{sym}: order rejected: {e}")

            time.sleep(SLEEP_INTERVAL)

        except (BinanceAPIException, BinanceOrderException) as e:
            log.error(f"Binance API error: {e}")
            time.sleep(SLEEP_INTERVAL)
        except Exception as e:
            log.error(f"Unexpected error: {e}", exc_info=True)
            time.sleep(SLEEP_INTERVAL)


def main() -> None:
    api_key, api_secret = load_api_keys()
    client = Client(api_key, api_secret)
    monitor(client)


if __name__ == "__main__":
    main()
