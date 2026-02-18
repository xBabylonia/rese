"""
Price Monitor
Cek harga real-time setiap 30 detik untuk semua open signals.
Kirim alert Telegram saat TP1/TP2/TP3/SL tersentuh.
"""

import asyncio
import logging
from datetime import datetime, timezone

import ccxt

from config import Config
from tracker import WinRateTracker

logger = logging.getLogger("PriceMonitor")


class PriceMonitor:
    def __init__(self, cfg: Config, tracker: WinRateTracker, bot, chat_id: str):
        self.cfg = cfg
        self.tracker = tracker
        self.bot = bot
        self.chat_id = chat_id
        self.exchange = ccxt.binanceusdm({
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
        })

    async def fetch_prices(self, symbols: list[str]) -> dict[str, float]:
        """Fetch current prices for multiple symbols."""
        prices = {}
        try:
            # batch fetch tickers
            raw_symbols = [s.replace("/USDT", "/USDT:USDT") for s in symbols]
            tickers = await asyncio.to_thread(self.exchange.fetch_tickers, raw_symbols)
            for sym, ticker in tickers.items():
                clean = sym.replace(":USDT", "")
                prices[clean] = ticker.get("last") or ticker.get("close") or 0.0
        except Exception as e:
            logger.debug(f"fetch_prices error: {e}")
            # fallback: fetch one by one
            for sym in symbols:
                try:
                    raw = sym.replace("/USDT", "/USDT:USDT")
                    t = await asyncio.to_thread(self.exchange.fetch_ticker, raw)
                    prices[sym] = t.get("last") or 0.0
                except Exception:
                    pass
        return prices

    def _check_hit(self, signal: dict, price: float) -> tuple[str, float] | None:
        """Check if price hits any TP or SL. Returns (status, price) or None."""
        direction = signal["direction"]
        entry = signal["entry"]
        sl = signal["stop_loss"]
        tps = signal["take_profits"]

        # Check highest TP first
        if direction == "LONG":
            if price >= tps[2]:
                return ("TP3", price)
            elif price >= tps[1]:
                return ("TP2", price)
            elif price >= tps[0]:
                return ("TP1", price)
            elif price <= sl:
                return ("SL", price)
        else:  # SHORT
            if price <= tps[2]:
                return ("TP3", price)
            elif price <= tps[1]:
                return ("TP2", price)
            elif price <= tps[0]:
                return ("TP1", price)
            elif price >= sl:
                return ("SL", price)
        return None

    async def _send_alert(self, signal: dict, status: str, price: float):
        """Send TP/SL hit alert to Telegram."""
        from telegram.constants import ParseMode

        is_win = status.startswith("TP")
        icon = "🎯" if is_win else "🛑"
        result_icon = "✅ WIN" if is_win else "❌ LOSS"
        dir_icon = "🟢" if signal["direction"] == "LONG" else "🔴"
        entry = signal["entry"]
        pnl_pct = abs((price - entry) / entry * 100 * self.cfg.LEVERAGE)
        pnl_str = f"+{pnl_pct:.1f}%" if is_win else f"-{pnl_pct:.1f}%"

        msg = (
            f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"┃  {icon} <b>{status} HIT</b>  ·  {result_icon}\n"
            f"┃  {dir_icon} <b>{signal['symbol']}</b>  ·  {signal['direction']}\n"
            f"┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"┃  📥 <b>Entry:</b>  <code>{entry:.4f}</code>\n"
            f"┃  🏁 <b>Close:</b>  <code>{price:.4f}</code>\n"
            f"┃  💰 <b>PnL:</b>    <b>{pnl_str}</b>  ({self.cfg.LEVERAGE}x)\n"
            f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>🕐 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</i>"
        )

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=msg,
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            logger.error(f"Alert send error: {e}")

    async def check_loop(self):
        """Main monitoring loop — runs every 30 seconds."""
        logger.info("Price monitor started.")
        while True:
            try:
                open_signals = self.tracker.get_open_signals()
                if open_signals:
                    symbols = list({s["symbol"] for s in open_signals})
                    prices = await self.fetch_prices(symbols)

                    for signal in open_signals:
                        price = prices.get(signal["symbol"], 0.0)
                        if price <= 0:
                            continue

                        hit = self._check_hit(signal, price)
                        if hit:
                            status, hit_price = hit
                            self.tracker.update_status(signal["id"], status, hit_price)
                            await self._send_alert(signal, status, hit_price)

            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

            await asyncio.sleep(30)
