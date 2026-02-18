"""
Win Rate Tracker
Menyimpan semua signal ke JSON lokal dan update status TP/SL hit.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("Tracker")

TRACKER_FILE = "signals_tracker.json"


class WinRateTracker:
    def __init__(self):
        self.data = self._load()

    def _load(self) -> dict:
        if os.path.exists(TRACKER_FILE):
            try:
                with open(TRACKER_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"signals": {}, "stats": {"total": 0, "tp1": 0, "tp2": 0, "tp3": 0, "sl": 0, "open": 0}}

    def _save(self):
        try:
            with open(TRACKER_FILE, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Tracker save error: {e}")

    def add_signal(self, signal: dict) -> str:
        """Add new signal, return signal_id."""
        sig_id = f"{signal['symbol'].replace('/', '')}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        self.data["signals"][sig_id] = {
            "id": sig_id,
            "symbol": signal["symbol"],
            "direction": signal["direction"],
            "entry": signal["entry"],
            "stop_loss": signal["stop_loss"],
            "take_profits": signal["take_profits"],
            "score": signal["score"],
            "timestamp": signal["timestamp"],
            "status": "OPEN",       # OPEN | TP1 | TP2 | TP3 | SL
            "closed_at": None,
            "closed_price": None,
        }
        self.data["stats"]["total"] += 1
        self.data["stats"]["open"] += 1
        self._save()
        return sig_id

    def update_status(self, sig_id: str, status: str, price: float):
        """Update signal status (TP1/TP2/TP3/SL)."""
        if sig_id not in self.data["signals"]:
            return
        sig = self.data["signals"][sig_id]
        if sig["status"] != "OPEN":
            return

        sig["status"] = status
        sig["closed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        sig["closed_price"] = price
        self.data["stats"]["open"] = max(0, self.data["stats"]["open"] - 1)

        key = status.lower()
        if key in self.data["stats"]:
            self.data["stats"][key] += 1

        self._save()
        logger.info(f"Signal {sig_id} → {status} @ {price}")

    def get_open_signals(self) -> list[dict]:
        return [s for s in self.data["signals"].values() if s["status"] == "OPEN"]

    def get_stats(self) -> dict:
        stats = self.data["stats"]
        closed = stats["tp1"] + stats["tp2"] + stats["tp3"] + stats["sl"]
        wins = stats["tp1"] + stats["tp2"] + stats["tp3"]
        win_rate = (wins / closed * 100) if closed > 0 else 0.0
        return {**stats, "closed": closed, "wins": wins, "win_rate": win_rate}

    def get_recent_signals(self, limit: int = 10) -> list[dict]:
        all_sigs = list(self.data["signals"].values())
        all_sigs.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_sigs[:limit]

    def is_duplicate(self, symbol: str, direction: str, window_minutes: int = 60) -> bool:
        """Check if same signal sent in last N minutes."""
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        for s in self.data["signals"].values():
            if s["symbol"] == symbol and s["direction"] == direction and s["status"] == "OPEN":
                try:
                    ts = datetime.strptime(s["timestamp"], "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
                    if (now - ts).total_seconds() < window_minutes * 60:
                        return True
                except Exception:
                    pass
        return False
