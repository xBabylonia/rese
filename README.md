# 🤖 Futures Signal Bot — Binance CCXT

Bot trading signal otomatis untuk Binance Futures dengan analisis teknikal lengkap dan notifikasi Telegram.

---

## 📊 Analisis yang Digunakan

| Kategori | Indikator |
|---|---|
| **Trend** | EMA 8/21/50/200, Supertrend |
| **Momentum** | RSI, MACD, Stochastic RSI |
| **Volume** | Volume Avg, OBV, VWAP |
| **Volatilitas** | ATR, Bollinger Bands |
| **S/R Level** | Pivot Points, Swing High/Low |
| **S&D Zone** | DBD, DBR, RBD, RBR detection |
| **Pattern** | Engulfing, Pin Bar, Hammer, Shooting Star |

### Scoring System (0–13 poin)
| Kondisi | Poin |
|---|---|
| EMA Trend Aligned (4H) | +2 |
| Supertrend Confirmed (1H) | +1 |
| MACD Crossover (15m) | +2 |
| RSI Confirmed | +1 |
| Volume Spike (>1.5x avg) | +1 |
| VWAP Confirmed | +1 |
| Stochastic RSI | +1 |
| OBV Divergence | +1 |
| Candlestick Pattern | +1 |
| S&D Zone (4H) | +3 |
| Fresh Zone (bonus) | +1 |

**Signal dikirim jika score ≥ 6**

---

## ⚙️ Setup

### 1. Clone & Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Environment Variables
```bash
cp .env.example .env
# Edit .env dengan token dan chat ID kamu
```

### 3. Dapatkan Telegram Bot Token
- Buka [@BotFather](https://t.me/BotFather) di Telegram
- Ketik `/newbot` dan ikuti instruksi
- Copy token ke `.env`

### 4. Dapatkan Chat ID
- Untuk channel: forward pesan dari channel ke [@userinfobot](https://t.me/userinfobot)
- Untuk grup: tambahkan bot ke grup, lalu cek dengan `/getid`
- Untuk DM pribadi: buka [@userinfobot](https://t.me/userinfobot)

### 5. Jalankan Bot
```bash
python bot.py
```

---

## 📁 Struktur File

```
trading_bot/
├── bot.py          # Main bot & Telegram formatter
├── analyzer.py     # Analisis teknikal & signal engine
├── config.py       # Konfigurasi semua parameter
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Kustomisasi (config.py)

```python
MIN_SCORE = 6         # Naikkan ke 8-9 untuk signal lebih selektif
MIN_VOLUME_USDT = 50_000_000  # Filter volume minimum
MAX_PAIRS = 50        # Jumlah pair yang di-scan
LEVERAGE = 10         # Leverage default yang ditampilkan
TF_SIGNAL = "15m"     # Timeframe entry
SL_ATR_MULT = 1.5     # Stop loss = 1.5x ATR
```

---

## 📈 Contoh Output Telegram

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃  🟢 BTC/USDT  ·  LONG 📈
┃  ⚡ Strength: 💪 STRONG  ███████░
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃  💰 Entry:    43250.5000
┃  🛑 Stop:     42800.0000  (-1.0%)
┃  🎯 TP1:      43925.0000  (+15.2%)
┃  🎯 TP2:      44600.0000  (+25.3%)
┃  🎯 TP3:      46000.0000  (+64.1%)
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃  📊 Timeframe: 15m
┃  🔧 Leverage:  10x
┃  ⚖️  RR Ratio:  1:2.5
┃  📦 S&D Zone: DBR (4h)
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃  🔍 Confluences:
┃    📈 EMA Trend Aligned
┃    ⚡ MACD Crossover
┃    📊 RSI Confirmed
┃    📦 Volume Spike
┃    🟩 Demand Zone
┃    ✨ Fresh Zone
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕐 2024-01-15 08:15 UTC  ·  Score: 10/13
```

---

## ⚠️ Disclaimer

Bot ini hanya untuk **sinyal informasi** dan **bukan saran finansial**.
Trading futures mengandung risiko tinggi. Selalu gunakan manajemen risiko yang baik.
