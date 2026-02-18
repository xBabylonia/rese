"""
╔══════════════════════════════════════════════════════════╗
║         FUTURES SIGNAL BOT - BINANCE CCXT                ║
║         Telegram Bot with Full Technical Analysis        ║
╚══════════════════════════════════════════════════════════╝

Commands:
  /scan [SYMBOL]  — scan semua pair atau pair tertentu
  /watchlist      — lihat watchlist
  /addwatch BTC   — tambah pair ke watchlist
  /delwatch BTC   — hapus pair dari watchlist
  /stats          — win rate & statistik signal
  /open           — semua signal yang masih open
  /help           — daftar perintah
"""

import asyncio
import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

from analyzer import SignalAnalyzer
from config import Config
from monitor import PriceMonitor
from tracker import WinRateTracker

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("TradingBot")


class TradingSignalBot:
    def __init__(self):
        self.config = Config()
        self.analyzer = SignalAnalyzer(self.config)
        self.tracker = WinRateTracker()
        self.signal_count_today = 0
        self.last_reset_date = datetime.now(timezone.utc).date()
        self.app = Application.builder().token(self.config.TELEGRAM_TOKEN).build()
        self.monitor = PriceMonitor(
            self.config,
            self.tracker,
            self.app.bot,
            self.config.TELEGRAM_CHAT_ID,
        )
        self._register_handlers()

    # ── Command Handlers ───────────────────────────────────

    def _register_handlers(self):
        self.app.add_handler(CommandHandler("start",     self._cmd_start))
        self.app.add_handler(CommandHandler("help",      self._cmd_help))
        self.app.add_handler(CommandHandler("scan",      self._cmd_scan))
        self.app.add_handler(CommandHandler("watchlist", self._cmd_watchlist))
        self.app.add_handler(CommandHandler("addwatch",  self._cmd_addwatch))
        self.app.add_handler(CommandHandler("delwatch",  self._cmd_delwatch))
        self.app.add_handler(CommandHandler("stats",     self._cmd_stats))
        self.app.add_handler(CommandHandler("open",      self._cmd_open))

    async def _cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 <b>Trading Signal Bot</b>\n\n"
            "Bot aktif dan sedang berjalan!\n"
            "Ketik /help untuk daftar perintah.",
            parse_mode=ParseMode.HTML,
        )

    async def _cmd_help(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        msg = (
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "┃  📖 <b>DAFTAR PERINTAH</b>\n"
            "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "┃  /scan           — scan semua pair\n"
            "┃  /scan BTC       — scan BTC/USDT saja\n"
            "┃  /scan BTC ETH   — scan beberapa pair\n"
            "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "┃  /watchlist      — lihat watchlist\n"
            "┃  /addwatch BTC   — tambah ke watchlist\n"
            "┃  /delwatch BTC   — hapus dari watchlist\n"
            "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "┃  /stats          — win rate & statistik\n"
            "┃  /open           — signal yang masih open\n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    async def _cmd_scan(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        args = ctx.args

        if args:
            symbols = [f"{a.upper().replace('USDT','').strip('/')}/USDT:USDT" for a in args]
            label = ", ".join(a.upper() for a in args)
            await update.message.reply_text(
                f"🔍 <b>Scanning:</b> {label}\n<i>Mohon tunggu...</i>",
                parse_mode=ParseMode.HTML,
            )
        else:
            symbols = None
            await update.message.reply_text(
                "🔍 <b>Scanning semua pair...</b>\n<i>Mohon tunggu 1-2 menit.</i>",
                parse_mode=ParseMode.HTML,
            )

        signals = await self.analyzer.scan_all_pairs(watchlist=symbols)

        if signals:
            signals.sort(key=lambda x: x["score"], reverse=True)
            sent = 0
            for sig in signals:
                if not self.tracker.is_duplicate(sig["symbol"], sig["direction"]):
                    sig_id = self.tracker.add_signal(sig)
                    sig["id"] = sig_id
                    await self._send_signal_to(update.effective_chat.id, sig)
                    sent += 1
                    await asyncio.sleep(1.2)
            await update.message.reply_text(
                f"✅ Scan selesai · <b>{sent} signal</b> ditemukan.",
                parse_mode=ParseMode.HTML,
            )
        else:
            await update.message.reply_text("😶 Tidak ada signal yang memenuhi syarat saat ini.")

    async def _cmd_watchlist(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        wl = self.config.get_watchlist()
        if not wl:
            await update.message.reply_text(
                "📋 Watchlist kosong.\n\nGunakan <code>/addwatch BTC</code> untuk menambahkan.",
                parse_mode=ParseMode.HTML,
            )
            return
        items = "\n".join(f"┃  • <b>{s}</b>" for s in wl)
        msg = (
            f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"┃  📋 <b>WATCHLIST</b>  ({len(wl)} pair)\n"
            f"┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{items}\n"
            f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>/addwatch SYMBOL · /delwatch SYMBOL</i>"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    async def _cmd_addwatch(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not ctx.args:
            await update.message.reply_text("Usage: <code>/addwatch BTC</code>", parse_mode=ParseMode.HTML)
            return
        added = []
        for a in ctx.args:
            sym = a.upper().replace("USDT", "").strip("/") + "/USDT"
            if self.config.add_to_watchlist(sym):
                added.append(sym)
        if added:
            await update.message.reply_text(
                "✅ Ditambahkan ke watchlist:\n" + "\n".join(f"  • <b>{s}</b>" for s in added),
                parse_mode=ParseMode.HTML,
            )
        else:
            await update.message.reply_text("⚠️ Sudah ada di watchlist.")

    async def _cmd_delwatch(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not ctx.args:
            await update.message.reply_text("Usage: <code>/delwatch BTC</code>", parse_mode=ParseMode.HTML)
            return
        removed = []
        for a in ctx.args:
            sym = a.upper().replace("USDT", "").strip("/") + "/USDT"
            if self.config.remove_from_watchlist(sym):
                removed.append(sym)
        if removed:
            await update.message.reply_text(
                "🗑 Dihapus dari watchlist:\n" + "\n".join(f"  • <b>{s}</b>" for s in removed),
                parse_mode=ParseMode.HTML,
            )
        else:
            await update.message.reply_text("⚠️ Tidak ditemukan di watchlist.")

    async def _cmd_stats(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        s = self.tracker.get_stats()
        wr = s["win_rate"]
        bar = self._score_bar(int(wr), 100)
        recent = self.tracker.get_recent_signals(5)

        recent_lines = ""
        for r in recent:
            status_icon = {"OPEN": "🔵", "TP1": "✅", "TP2": "✅", "TP3": "🏆", "SL": "❌"}.get(r["status"], "❓")
            dir_icon = "📈" if r["direction"] == "LONG" else "📉"
            recent_lines += f"┃  {status_icon} {dir_icon} <b>{r['symbol']}</b>  ·  {r['status']}\n"

        msg = (
            f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"┃  📊 <b>WIN RATE STATISTICS</b>\n"
            f"┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"┃  🎯 <b>Win Rate:</b>  {wr:.1f}%  {bar}\n"
            f"┃  📦 <b>Total Signal:</b>  {s['total']}\n"
            f"┃  🔵 <b>Open:</b>   {s['open']}\n"
            f"┃  ✅ <b>TP1 Hit:</b> {s['tp1']}\n"
            f"┃  ✅ <b>TP2 Hit:</b> {s['tp2']}\n"
            f"┃  🏆 <b>TP3 Hit:</b> {s['tp3']}\n"
            f"┃  ❌ <b>SL Hit:</b>  {s['sl']}\n"
            f"┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"┃  🕐 <b>5 Signal Terakhir:</b>\n"
            f"{recent_lines if recent_lines else '┃  (belum ada data)\n'}"
            f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    async def _cmd_open(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        opens = self.tracker.get_open_signals()
        if not opens:
            await update.message.reply_text("✅ Tidak ada signal open saat ini.")
            return

        lines = ""
        for s in opens[-10:]:
            dir_icon = "🟢" if s["direction"] == "LONG" else "🔴"
            lines += (
                f"┃  {dir_icon} <b>{s['symbol']}</b>  ·  {s['direction']}\n"
                f"┃     Entry: <code>{s['entry']:.4f}</code>  ·  Score: {s['score']}\n"
                f"┃     <i>{s['timestamp']}</i>\n"
            )

        msg = (
            f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"┃  🔵 <b>OPEN SIGNALS</b>  ({len(opens)} total)\n"
            f"┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{lines}"
            f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    # ── Signal Sender ──────────────────────────────────────

    async def _send_signal_to(self, chat_id, signal: dict):
        msg = self._format_signal(signal)
        try:
            await self.app.bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode=ParseMode.HTML,
            )
            self.signal_count_today += 1
            logger.info(f"Signal: {signal['symbol']} {signal['direction']} score={signal['score']}")
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")

    # ── Auto Scan Loop ─────────────────────────────────────

    async def _auto_scan_loop(self):
        await self.app.bot.send_message(
            chat_id=self.config.TELEGRAM_CHAT_ID,
            text=(
                "🤖 <b>Trading Signal Bot Started</b>\n\n"
                "📊 Scanning Binance Futures...\n"
                "⏱ Interval: Every 15 minutes\n"
                "🎯 Min Score: 6/13\n"
                "🔔 TP/SL Monitor: Active\n\n"
                "📖 /help untuk daftar perintah\n"
                "<i>Initializing first scan...</i>"
            ),
            parse_mode=ParseMode.HTML,
        )

        while True:
            try:
                today = datetime.now(timezone.utc).date()
                if today != self.last_reset_date:
                    self.signal_count_today = 0
                    self.last_reset_date = today

                logger.info("Auto scan started...")
                watchlist = self.config.get_watchlist()
                wl_symbols = [f"{s.replace('/USDT','')}/USDT:USDT" for s in watchlist] if watchlist else None
                signals = await self.analyzer.scan_all_pairs(watchlist=wl_symbols)

                if signals:
                    signals.sort(key=lambda x: x["score"], reverse=True)
                    sent = 0
                    for sig in signals:
                        if not self.tracker.is_duplicate(sig["symbol"], sig["direction"]):
                            sig_id = self.tracker.add_signal(sig)
                            sig["id"] = sig_id
                            await self._send_signal_to(self.config.TELEGRAM_CHAT_ID, sig)
                            sent += 1
                            await asyncio.sleep(1.5)
                    if sent > 0:
                        await self._send_scan_summary(signals)
                    logger.info(f"Auto scan done. {sent} new signals.")
                else:
                    logger.info("Auto scan done. No signals.")

            except Exception as e:
                logger.error(f"Auto scan error: {e}", exc_info=True)

            now = datetime.now(timezone.utc)
            seconds_to_next = (15 - now.minute % 15) * 60 - now.second
            logger.info(f"Next scan in {seconds_to_next}s")
            await asyncio.sleep(seconds_to_next)

    # ── Formatters ─────────────────────────────────────────

    def _format_signal(self, s: dict) -> str:
        direction_icon = "🟢" if s["direction"] == "LONG" else "🔴"
        direction_text = "LONG 📈" if s["direction"] == "LONG" else "SHORT 📉"
        score_bar = self._score_bar(s["score"])
        strength = self._strength_label(s["score"])
        zone_info = (
            f"\n┃  📦 <b>S&D Zone:</b> {s['sd_zone_type']} ({s['sd_zone_tf']})"
            if s.get("sd_zone_type") else ""
        )
        tp_lines = ""
        for i, tp in enumerate(s["take_profits"], 1):
            pnl = abs((tp - s["entry"]) / s["entry"] * 100 * s.get("leverage", 10))
            tp_lines += f"\n┃  🎯 <b>TP{i}:</b> <code>{tp:.4f}</code>  <i>(+{pnl:.1f}%)</i>"
        sl_pct = abs((s["stop_loss"] - s["entry"]) / s["entry"] * 100)

        return (
            f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"┃  {direction_icon} <b>{s['symbol']}</b>  ·  {direction_text}\n"
            f"┃  ⚡ <b>Strength:</b> {strength}  {score_bar}\n"
            f"┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"┃  💰 <b>Entry:</b>    <code>{s['entry']:.4f}</code>\n"
            f"┃  🛑 <b>Stop Loss:</b> <code>{s['stop_loss']:.4f}</code>  <i>(-{sl_pct:.1f}%)</i>"
            f"{tp_lines}\n"
            f"┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"┃  📊 <b>Timeframe:</b> {s['timeframe']}\n"
            f"┃  🔧 <b>Leverage:</b>  {s.get('leverage', 10)}x\n"
            f"┃  ⚖️  <b>RR Ratio:</b>  1:{s['rr_ratio']:.1f}"
            f"{zone_info}\n"
            f"┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"┃  🔍 <b>Confluences:</b>\n"
            f"{self._format_confluences(s['confluences'])}"
            f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>🕐 {s['timestamp']}  ·  Score: {s['score']}/{s['max_score']}</i>"
        )

    def _format_confluences(self, confluences: list) -> str:
        icons = {
            "EMA Trend Aligned": "📈", "MACD Crossover": "⚡",
            "RSI Confirmed": "📊", "Volume Spike": "📦",
            "VWAP Confirmed": "💹", "BB Squeeze Break": "💥",
            "Supertrend": "🧭", "Demand Zone": "🟩",
            "Supply Zone": "🟥", "Fresh Zone": "✨",
            "Daily Zone": "🏛️", "Bullish Pattern": "🕯️",
            "Bearish Pattern": "🕯️", "Pivot Support": "📍",
            "Pivot Resistance": "📍", "Stoch RSI": "🔄",
            "OBV Divergence": "📉",
        }
        return "".join(f"┃    {icons.get(c, '✅')} {c}\n" for c in confluences)

    async def _send_scan_summary(self, signals: list):
        long_c  = sum(1 for s in signals if s["direction"] == "LONG")
        short_c = sum(1 for s in signals if s["direction"] == "SHORT")
        hq      = sum(1 for s in signals if s["score"] >= 9)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        msg = (
            f"╔══════════════════════════════╗\n"
            f"║       📊  SCAN REPORT        ║\n"
            f"╚══════════════════════════════╝\n\n"
            f"🕐 <b>{now}</b>\n\n"
            f"📈 <b>LONG:</b>  {long_c} signals\n"
            f"📉 <b>SHORT:</b> {short_c} signals\n"
            f"⭐ <b>High Quality (≥9):</b> {hq}\n"
            f"📦 <b>Total:</b> {len(signals)}\n\n"
            f"<i>/stats · /open · /watchlist</i>"
        )
        try:
            await self.app.bot.send_message(
                chat_id=self.config.TELEGRAM_CHAT_ID,
                text=msg,
                parse_mode=ParseMode.HTML,
            )
        except TelegramError as e:
            logger.error(f"Summary error: {e}")

    def _score_bar(self, score: int, max_score: int = 13) -> str:
        filled = round((score / max_score) * 8)
        return "█" * filled + "░" * (8 - filled)

    def _strength_label(self, score: int) -> str:
        if score >= 11:  return "🔥 VERY STRONG"
        elif score >= 9: return "💪 STRONG"
        elif score >= 7: return "✅ MODERATE"
        else:            return "⚠️ WEAK"

    # ── Entry Point ────────────────────────────────────────

    async def run(self):
        logger.info("🚀 Bot starting...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        await asyncio.gather(
            self._auto_scan_loop(),
            self.monitor.check_loop(),
        )


def main():
    bot = TradingSignalBot()
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
