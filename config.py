"""
Configuration for Trading Signal Bot
"""
import json
import os
from dotenv import load_dotenv

load_dotenv()

WATCHLIST_FILE = "watchlist.json"


class Config:
    # ── Telegram ─────────────────────────────────────────
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # ── Binance API (read-only, for market data) ──────────
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET: str = os.getenv("BINANCE_SECRET", "")

    # ── Signal Settings ───────────────────────────────────
    MIN_SCORE: int = 6
    MIN_VOLUME_USDT: float = 50_000_000
    LEVERAGE: int = 10
    MAX_PAIRS: int = 50

    # ── Timeframes ────────────────────────────────────────
    TF_SIGNAL: str = "15m"
    TF_CONFIRM: str = "1h"
    TF_BIAS: str = "4h"
    TF_ZONE: str = "4h"

    # ── Indicators ────────────────────────────────────────
    EMA_FAST: int = 8
    EMA_MID: int = 21
    EMA_SLOW: int = 50
    EMA_TREND: int = 200
    RSI_PERIOD: int = 14
    RSI_OB: float = 70.0
    RSI_OS: float = 30.0
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9
    BB_PERIOD: int = 20
    BB_STD: float = 2.0
    ATR_PERIOD: int = 14
    STOCH_K: int = 14
    STOCH_D: int = 3
    STOCH_SMOOTH: int = 3
    SUPERTREND_PERIOD: int = 10
    SUPERTREND_MULT: float = 3.0
    VOLUME_AVG_PERIOD: int = 20

    # ── S&D Zone Settings ────────────────────────────────
    SD_BASE_MAX_BODY_RATIO: float = 0.4
    SD_IMPULSE_MIN_BODY_RATIO: float = 1.5
    SD_LOOKBACK: int = 100

    # ── Risk Management ───────────────────────────────────
    SL_ATR_MULT: float = 1.5
    TP1_RR: float = 1.5
    TP2_RR: float = 2.5
    TP3_RR: float = 4.0

    # ── Watchlist (persisted to JSON) ────────────────────

    def get_watchlist(self) -> list[str]:
        if os.path.exists(WATCHLIST_FILE):
            try:
                with open(WATCHLIST_FILE) as f:
                    return json.load(f).get("symbols", [])
            except Exception:
                pass
        return []

    def _save_watchlist(self, symbols: list[str]):
        with open(WATCHLIST_FILE, "w") as f:
            json.dump({"symbols": symbols}, f, indent=2)

    def add_to_watchlist(self, symbol: str) -> bool:
        """Returns True if added, False if already exists."""
        wl = self.get_watchlist()
        if symbol in wl:
            return False
        wl.append(symbol)
        self._save_watchlist(wl)
        return True

    def remove_from_watchlist(self, symbol: str) -> bool:
        """Returns True if removed, False if not found."""
        wl = self.get_watchlist()
        if symbol not in wl:
            return False
        wl.remove(symbol)
        self._save_watchlist(wl)
        return True
