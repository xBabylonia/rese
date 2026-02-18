"""
Signal Analyzer — Full Technical Analysis Engine
Includes: EMA, RSI, MACD, BB, ATR, Supertrend, VWAP,
          OBV, Stochastic RSI, Pivot Points, S&D Zones,
          Candlestick Patterns, Multi-Timeframe Scoring
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import ccxt.pro as ccxtpro
import ccxt
import numpy as np
import pandas as pd
import pandas_ta as ta

from config import Config

logger = logging.getLogger("Analyzer")


# ══════════════════════════════════════════════
#  EXCHANGE WRAPPER
# ══════════════════════════════════════════════
class BinanceClient:
    def __init__(self, config: Config):
        self.exchange = ccxt.binanceusdm({
            "apiKey": config.BINANCE_API_KEY,
            "secret": config.BINANCE_SECRET,
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
        })

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 250) -> Optional[pd.DataFrame]:
        try:
            raw = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not raw or len(raw) < 50:
                return None
            df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)
            df = df.astype(float)
            return df
        except Exception as e:
            logger.debug(f"fetch_ohlcv {symbol} {timeframe}: {e}")
            return None

    def get_futures_pairs(self, min_volume: float, max_pairs: int) -> list[str]:
        try:
            self.exchange.load_markets()
            tickers = self.exchange.fetch_tickers()
            pairs = []
            for symbol, ticker in tickers.items():
                if not symbol.endswith("/USDT:USDT"):
                    continue
                vol = ticker.get("quoteVolume") or 0
                if vol >= min_volume:
                    pairs.append((symbol, vol))
            pairs.sort(key=lambda x: x[1], reverse=True)
            return [p[0] for p in pairs[:max_pairs]]
        except Exception as e:
            logger.error(f"get_futures_pairs: {e}")
            return []


# ══════════════════════════════════════════════
#  INDICATOR CALCULATIONS
# ══════════════════════════════════════════════
class Indicators:
    @staticmethod
    def ema(df: pd.DataFrame, periods: list[int]) -> pd.DataFrame:
        for p in periods:
            df[f"ema{p}"] = ta.ema(df["close"], length=p)
        return df

    @staticmethod
    def rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        df["rsi"] = ta.rsi(df["close"], length=period)
        return df

    @staticmethod
    def macd(df: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.DataFrame:
        m = ta.macd(df["close"], fast=fast, slow=slow, signal=signal)
        df["macd"] = m[f"MACD_{fast}_{slow}_{signal}"]
        df["macd_signal"] = m[f"MACDs_{fast}_{slow}_{signal}"]
        df["macd_hist"] = m[f"MACDh_{fast}_{slow}_{signal}"]
        return df

    @staticmethod
    def bollinger(df: pd.DataFrame, period=20, std=2.0) -> pd.DataFrame:
        bb = ta.bbands(df["close"], length=period, std=std)
        df["bb_upper"] = bb[f"BBU_{period}_{std}"]
        df["bb_mid"] = bb[f"BBM_{period}_{std}"]
        df["bb_lower"] = bb[f"BBL_{period}_{std}"]
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]
        return df

    @staticmethod
    def atr(df: pd.DataFrame, period=14) -> pd.DataFrame:
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=period)
        return df

    @staticmethod
    def supertrend(df: pd.DataFrame, period=10, multiplier=3.0) -> pd.DataFrame:
        st = ta.supertrend(df["high"], df["low"], df["close"], length=period, multiplier=multiplier)
        col_dir = f"SUPERTd_{period}_{multiplier}"
        col_val = f"SUPERT_{period}_{multiplier}"
        if col_dir in st.columns:
            df["supertrend_dir"] = st[col_dir]
            df["supertrend"] = st[col_val]
        else:
            df["supertrend_dir"] = 0
            df["supertrend"] = np.nan
        return df

    @staticmethod
    def stoch_rsi(df: pd.DataFrame, k=14, d=3, smooth=3) -> pd.DataFrame:
        sr = ta.stochrsi(df["close"], length=k, rsi_length=k, k=d, d=smooth)
        if sr is not None and not sr.empty:
            cols = sr.columns.tolist()
            df["stoch_k"] = sr[cols[0]]
            df["stoch_d"] = sr[cols[1]]
        else:
            df["stoch_k"] = np.nan
            df["stoch_d"] = np.nan
        return df

    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.DataFrame:
        df["vwap"] = ta.vwap(df["high"], df["low"], df["close"], df["volume"])
        return df

    @staticmethod
    def obv(df: pd.DataFrame) -> pd.DataFrame:
        df["obv"] = ta.obv(df["close"], df["volume"])
        df["obv_ema"] = ta.ema(df["obv"], length=20)
        return df

    @staticmethod
    def volume_avg(df: pd.DataFrame, period=20) -> pd.DataFrame:
        df["vol_avg"] = df["volume"].rolling(period).mean()
        df["vol_ratio"] = df["volume"] / df["vol_avg"]
        return df

    @staticmethod
    def pivot_points(df: pd.DataFrame) -> dict:
        """Classic pivot points from previous daily candle."""
        h = df["high"].iloc[-2]
        l = df["low"].iloc[-2]
        c = df["close"].iloc[-2]
        p = (h + l + c) / 3
        return {
            "pivot": p,
            "r1": 2 * p - l,
            "r2": p + (h - l),
            "s1": 2 * p - h,
            "s2": p - (h - l),
        }

    @staticmethod
    def apply_all(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
        df = Indicators.ema(df, [cfg.EMA_FAST, cfg.EMA_MID, cfg.EMA_SLOW, cfg.EMA_TREND])
        df = Indicators.rsi(df, cfg.RSI_PERIOD)
        df = Indicators.macd(df, cfg.MACD_FAST, cfg.MACD_SLOW, cfg.MACD_SIGNAL)
        df = Indicators.bollinger(df, cfg.BB_PERIOD, cfg.BB_STD)
        df = Indicators.atr(df, cfg.ATR_PERIOD)
        df = Indicators.supertrend(df, cfg.SUPERTREND_PERIOD, cfg.SUPERTREND_MULT)
        df = Indicators.stoch_rsi(df, cfg.STOCH_K, cfg.STOCH_D, cfg.STOCH_SMOOTH)
        df = Indicators.vwap(df)
        df = Indicators.obv(df)
        df = Indicators.volume_avg(df, cfg.VOLUME_AVG_PERIOD)
        return df


# ══════════════════════════════════════════════
#  SUPPLY & DEMAND ZONE DETECTOR
# ══════════════════════════════════════════════
class SDZoneDetector:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def detect_zones(self, df: pd.DataFrame) -> list[dict]:
        """Detect S&D zones: DBD, DBR, RBD, RBR."""
        if len(df) < 10:
            return []
        atr = df["atr"].iloc[-1]
        zones = []
        lookback = min(self.cfg.SD_LOOKBACK, len(df) - 3)

        for i in range(1, lookback - 1):
            idx = -(i + 1)  # base candle index
            base = df.iloc[idx]
            prev = df.iloc[idx - 1]
            next_ = df.iloc[idx + 1]

            base_body = abs(base["close"] - base["open"])
            prev_body = abs(prev["close"] - prev["open"])
            next_body = abs(next_["close"] - next_["open"])

            is_base = base_body < (atr * self.cfg.SD_BASE_MAX_BODY_RATIO)
            is_prev_impulse = prev_body > (atr * self.cfg.SD_IMPULSE_MIN_BODY_RATIO)
            is_next_impulse = next_body > (atr * self.cfg.SD_IMPULSE_MIN_BODY_RATIO)

            if not is_base:
                continue

            # Determine zone type
            zone_type = None
            if prev["close"] < prev["open"] and next_["close"] < next_["open"] and is_prev_impulse and is_next_impulse:
                zone_type = "DBD"  # Supply
            elif prev["close"] < prev["open"] and next_["close"] > next_["open"] and is_next_impulse:
                zone_type = "DBR"  # Demand
            elif prev["close"] > prev["open"] and next_["close"] > next_["open"] and is_prev_impulse and is_next_impulse:
                zone_type = "RBR"  # Demand
            elif prev["close"] > prev["open"] and next_["close"] < next_["open"] and is_next_impulse:
                zone_type = "RBD"  # Supply

            if not zone_type:
                continue

            zone_high = max(base["open"], base["close"], base["high"])
            zone_low = min(base["open"], base["close"], base["low"])
            is_supply = zone_type in ("DBD", "RBD")
            is_demand = zone_type in ("DBR", "RBR")

            # Fresh check: price hasn't re-entered zone after formation
            current_price = df["close"].iloc[-1]
            subsequent = df.iloc[idx + 2:]
            if is_supply:
                touched = any((subsequent["high"] >= zone_low).values)
            else:
                touched = any((subsequent["low"] <= zone_high).values)

            impulse_strength = next_body / atr

            zones.append({
                "type": zone_type,
                "is_supply": is_supply,
                "is_demand": is_demand,
                "high": zone_high,
                "low": zone_low,
                "fresh": not touched,
                "impulse_strength": impulse_strength,
                "candle_index": idx,
            })

        return zones

    def price_in_zone(self, price: float, zones: list[dict], direction: str) -> Optional[dict]:
        """Check if current price is in a relevant S&D zone."""
        buffer = 0.003  # 0.3% buffer
        for z in zones:
            if direction == "LONG" and z["is_demand"]:
                if z["low"] * (1 - buffer) <= price <= z["high"] * (1 + buffer):
                    return z
            elif direction == "SHORT" and z["is_supply"]:
                if z["low"] * (1 - buffer) <= price <= z["high"] * (1 + buffer):
                    return z
        return None


# ══════════════════════════════════════════════
#  CANDLESTICK PATTERN DETECTOR
# ══════════════════════════════════════════════
class PatternDetector:
    @staticmethod
    def detect(df: pd.DataFrame) -> Optional[str]:
        c = df.iloc[-1]
        p = df.iloc[-2]
        atr = df["atr"].iloc[-1]

        body = c["close"] - c["open"]
        body_abs = abs(body)
        upper_wick = c["high"] - max(c["open"], c["close"])
        lower_wick = min(c["open"], c["close"]) - c["low"]

        prev_body = p["close"] - p["open"]
        prev_body_abs = abs(prev_body)

        # Bullish Engulfing
        if (prev_body < 0 and body > 0 and
                c["open"] < p["close"] and c["close"] > p["open"] and
                body_abs > prev_body_abs):
            return "Bullish Pattern"  # Bullish Engulfing

        # Bearish Engulfing
        if (prev_body > 0 and body < 0 and
                c["open"] > p["close"] and c["close"] < p["open"] and
                body_abs > prev_body_abs):
            return "Bearish Pattern"  # Bearish Engulfing

        # Hammer (Bullish)
        if (body_abs < atr * 0.4 and lower_wick > body_abs * 2 and
                upper_wick < body_abs * 0.5 and lower_wick > atr * 0.5):
            return "Bullish Pattern"  # Hammer

        # Shooting Star (Bearish)
        if (body_abs < atr * 0.4 and upper_wick > body_abs * 2 and
                lower_wick < body_abs * 0.5 and upper_wick > atr * 0.5):
            return "Bearish Pattern"  # Shooting Star

        # Pin Bar Bullish
        if lower_wick > body_abs * 3 and upper_wick < lower_wick * 0.3:
            return "Bullish Pattern"

        # Pin Bar Bearish
        if upper_wick > body_abs * 3 and lower_wick < upper_wick * 0.3:
            return "Bearish Pattern"

        return None


# ══════════════════════════════════════════════
#  SIGNAL SCORER
# ══════════════════════════════════════════════
class SignalScorer:
    MAX_SCORE = 13

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def score(
        self,
        df_signal: pd.DataFrame,
        df_confirm: pd.DataFrame,
        df_bias: pd.DataFrame,
        direction: str,
        sd_zone: Optional[dict],
        sd_zone_tf: str = "",
    ) -> tuple[int, list[str]]:
        score = 0
        confluences = []

        c = df_signal.iloc[-1]  # current candle

        # ── 1. EMA Trend Aligned (4H bias) ─ max +2
        bias = df_bias.iloc[-1]
        if direction == "LONG":
            if (bias[f"ema{self.cfg.EMA_FAST}"] > bias[f"ema{self.cfg.EMA_MID}"] and
                    bias[f"ema{self.cfg.EMA_MID}"] > bias[f"ema{self.cfg.EMA_SLOW}"]):
                score += 2
                confluences.append("EMA Trend Aligned")
        else:
            if (bias[f"ema{self.cfg.EMA_FAST}"] < bias[f"ema{self.cfg.EMA_MID}"] and
                    bias[f"ema{self.cfg.EMA_MID}"] < bias[f"ema{self.cfg.EMA_SLOW}"]):
                score += 2
                confluences.append("EMA Trend Aligned")

        # ── 2. Supertrend (1H confirm) ─ max +1
        conf = df_confirm.iloc[-1]
        if direction == "LONG" and conf.get("supertrend_dir", 0) == 1:
            score += 1
            confluences.append("Supertrend")
        elif direction == "SHORT" and conf.get("supertrend_dir", 0) == -1:
            score += 1
            confluences.append("Supertrend")

        # ── 3. MACD Crossover (15m) ─ max +2
        prev = df_signal.iloc[-2]
        if direction == "LONG":
            if (c["macd"] > c["macd_signal"] and
                    prev["macd"] <= prev["macd_signal"] and
                    c["macd_hist"] > 0):
                score += 2
                confluences.append("MACD Crossover")
        else:
            if (c["macd"] < c["macd_signal"] and
                    prev["macd"] >= prev["macd_signal"] and
                    c["macd_hist"] < 0):
                score += 2
                confluences.append("MACD Crossover")

        # ── 4. RSI ─ max +1
        rsi = c["rsi"]
        if not pd.isna(rsi):
            if direction == "LONG" and 20 <= rsi <= 60:
                score += 1
                confluences.append("RSI Confirmed")
            elif direction == "SHORT" and 40 <= rsi <= 80:
                score += 1
                confluences.append("RSI Confirmed")

        # ── 5. Volume Spike ─ max +1
        if not pd.isna(c.get("vol_ratio", np.nan)) and c["vol_ratio"] >= 1.5:
            score += 1
            confluences.append("Volume Spike")

        # ── 6. VWAP ─ max +1
        if not pd.isna(c.get("vwap", np.nan)):
            if direction == "LONG" and c["close"] > c["vwap"]:
                score += 1
                confluences.append("VWAP Confirmed")
            elif direction == "SHORT" and c["close"] < c["vwap"]:
                score += 1
                confluences.append("VWAP Confirmed")

        # ── 7. Stochastic RSI ─ max +1
        if not pd.isna(c.get("stoch_k", np.nan)) and not pd.isna(c.get("stoch_d", np.nan)):
            if direction == "LONG" and c["stoch_k"] < 20 and c["stoch_k"] > c["stoch_d"]:
                score += 1
                confluences.append("Stoch RSI")
            elif direction == "SHORT" and c["stoch_k"] > 80 and c["stoch_k"] < c["stoch_d"]:
                score += 1
                confluences.append("Stoch RSI")

        # ── 8. OBV Divergence ─ max +1
        if not pd.isna(c.get("obv", np.nan)) and not pd.isna(c.get("obv_ema", np.nan)):
            if direction == "LONG" and c["obv"] > c["obv_ema"]:
                score += 1
                confluences.append("OBV Divergence")
            elif direction == "SHORT" and c["obv"] < c["obv_ema"]:
                score += 1
                confluences.append("OBV Divergence")

        # ── 9. Candlestick Pattern ─ max +1
        pattern = PatternDetector.detect(df_signal)
        if pattern:
            if direction == "LONG" and pattern == "Bullish Pattern":
                score += 1
                confluences.append("Bullish Pattern")
            elif direction == "SHORT" and pattern == "Bearish Pattern":
                score += 1
                confluences.append("Bearish Pattern")

        # ── 10. S&D Zone ─ max +3
        if sd_zone:
            if sd_zone["is_demand"] and direction == "LONG":
                score += 3
                confluences.append("Demand Zone")
            elif sd_zone["is_supply"] and direction == "SHORT":
                score += 3
                confluences.append("Supply Zone")

            if sd_zone.get("fresh"):
                score += 1  # bonus (not counted in max_score for fair comparison)
                confluences.append("Fresh Zone")

            if sd_zone.get("impulse_strength", 0) >= 2.0:
                confluences.append("Daily Zone")

        return score, confluences


# ══════════════════════════════════════════════
#  MAIN ANALYZER
# ══════════════════════════════════════════════
class SignalAnalyzer:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.client = BinanceClient(cfg)
        self.sd_detector = SDZoneDetector(cfg)
        self.scorer = SignalScorer(cfg)

    def _determine_direction(self, df_bias: pd.DataFrame, df_confirm: pd.DataFrame) -> Optional[str]:
        """Determine LONG or SHORT from bias and confirmation TF."""
        b = df_bias.iloc[-1]
        c = df_confirm.iloc[-1]

        ema_fast = b[f"ema{self.cfg.EMA_FAST}"]
        ema_mid = b[f"ema{self.cfg.EMA_MID}"]
        ema_slow = b[f"ema{self.cfg.EMA_SLOW}"]
        ema_trend = b[f"ema{self.cfg.EMA_TREND}"]

        if pd.isna(ema_fast) or pd.isna(ema_trend):
            return None

        bias_bullish = ema_fast > ema_mid and b["close"] > ema_slow
        bias_bearish = ema_fast < ema_mid and b["close"] < ema_slow

        st_dir = c.get("supertrend_dir", 0)

        if bias_bullish and st_dir >= 0:
            return "LONG"
        elif bias_bearish and st_dir <= 0:
            return "SHORT"
        # Neutral bias: allow both based on supertrend
        elif st_dir == 1:
            return "LONG"
        elif st_dir == -1:
            return "SHORT"
        return None

    def _calculate_levels(self, df: pd.DataFrame, direction: str) -> dict:
        """Calculate entry, SL, TP levels."""
        c = df.iloc[-1]
        atr = c["atr"]
        entry = c["close"]

        sl_dist = atr * self.cfg.SL_ATR_MULT

        if direction == "LONG":
            stop_loss = entry - sl_dist
            tp1 = entry + sl_dist * self.cfg.TP1_RR
            tp2 = entry + sl_dist * self.cfg.TP2_RR
            tp3 = entry + sl_dist * self.cfg.TP3_RR
        else:
            stop_loss = entry + sl_dist
            tp1 = entry - sl_dist * self.cfg.TP1_RR
            tp2 = entry - sl_dist * self.cfg.TP2_RR
            tp3 = entry - sl_dist * self.cfg.TP3_RR

        rr = self.cfg.TP2_RR
        return {
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profits": [tp1, tp2, tp3],
            "rr_ratio": rr,
        }

    def _analyze_pair(self, symbol: str) -> Optional[dict]:
        """Full analysis pipeline for one symbol."""
        try:
            df_signal = self.client.fetch_ohlcv(symbol, self.cfg.TF_SIGNAL, limit=250)
            df_confirm = self.client.fetch_ohlcv(symbol, self.cfg.TF_CONFIRM, limit=250)
            df_bias = self.client.fetch_ohlcv(symbol, self.cfg.TF_BIAS, limit=250)
            df_zone = self.client.fetch_ohlcv(symbol, self.cfg.TF_ZONE, limit=150)

            if any(df is None for df in [df_signal, df_confirm, df_bias, df_zone]):
                return None

            # Apply indicators
            df_signal = Indicators.apply_all(df_signal, self.cfg)
            df_confirm = Indicators.apply_all(df_confirm, self.cfg)
            df_bias = Indicators.apply_all(df_bias, self.cfg)
            df_zone = Indicators.atr(df_zone, self.cfg.ATR_PERIOD)

            # Determine direction
            direction = self._determine_direction(df_bias, df_confirm)
            if not direction:
                return None

            # S&D Zone detection
            zones = self.sd_detector.detect_zones(df_zone)
            current_price = df_signal["close"].iloc[-1]
            sd_zone = self.sd_detector.price_in_zone(current_price, zones, direction)
            sd_zone_tf = self.cfg.TF_ZONE if sd_zone else ""
            sd_zone_type = sd_zone["type"] if sd_zone else None

            # Score
            score, confluences = self.scorer.score(
                df_signal, df_confirm, df_bias,
                direction, sd_zone, sd_zone_tf
            )

            if score < self.cfg.MIN_SCORE:
                return None

            # Levels
            levels = self._calculate_levels(df_signal, direction)

            # Clean symbol name for display
            display_symbol = symbol.replace("/USDT:USDT", "/USDT")

            return {
                "symbol": display_symbol,
                "direction": direction,
                "timeframe": self.cfg.TF_SIGNAL,
                "score": score,
                "max_score": self.scorer.MAX_SCORE,
                "confluences": confluences,
                "sd_zone_type": sd_zone_type,
                "sd_zone_tf": sd_zone_tf,
                "leverage": self.cfg.LEVERAGE,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                **levels,
            }
        except Exception as e:
            logger.debug(f"Error analyzing {symbol}: {e}")
            return None

    async def scan_all_pairs(self, watchlist: list[str] | None = None) -> list[dict]:
        """Fetch active pairs and analyze concurrently.

        Args:
            watchlist: If provided, scan ONLY these symbols (from /scan command or watchlist).
                       If None, auto-fetch top pairs by volume.
        """
        if watchlist:
            pairs = watchlist
            logger.info(f"Scanning watchlist: {pairs}")
        else:
            logger.info("Fetching active futures pairs...")
            pairs = await asyncio.to_thread(
                self.client.get_futures_pairs,
                self.cfg.MIN_VOLUME_USDT,
                self.cfg.MAX_PAIRS,
            )
        logger.info(f"Scanning {len(pairs)} pairs...")

        # Run analysis with limited concurrency to avoid rate limits
        semaphore = asyncio.Semaphore(5)
        signals = []

        async def analyze_with_semaphore(symbol: str):
            async with semaphore:
                result = await asyncio.to_thread(self._analyze_pair, symbol)
                if result:
                    signals.append(result)
                await asyncio.sleep(0.2)

        tasks = [analyze_with_semaphore(p) for p in pairs]
        await asyncio.gather(*tasks, return_exceptions=True)
        return signals
