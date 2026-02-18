# 🤖 Futures Signal Bot — Binance CCXT

Bot trading signal otomatis untuk Binance Futures dengan analisis teknikal lengkap, watchlist custom, win rate tracker, dan alert TP/SL real-time via Telegram.

---

## 📁 Struktur File

```
trading_bot/
├── bot.py              # Main bot, command handler, auto scan loop
├── analyzer.py         # Engine analisis teknikal & S&D zone
├── config.py           # Konfigurasi parameter + watchlist manager
├── tracker.py          # Win rate tracker & signal storage
├── monitor.py          # Real-time TP/SL price monitor
├── requirements.txt    # Dependencies
├── .env                # Token & API key (buat sendiri dari .env.example)
├── watchlist.json      # Auto-generated saat /addwatch digunakan
└── signals_tracker.json # Auto-generated saat signal pertama masuk
```

---

## 📊 Analisis Teknikal

| Kategori | Indikator |
|---|---|
| **Trend** | EMA 8 / 21 / 50 / 200, Supertrend (10, 3) |
| **Momentum** | RSI (14), MACD (12/26/9), Stochastic RSI |
| **Volume** | Volume Avg (20), OBV, VWAP |
| **Volatilitas** | ATR (14), Bollinger Bands (20, 2) |
| **S/R Level** | Pivot Points (Daily) |
| **S&D Zone** | DBD, DBR, RBD, RBR — auto detection |
| **Pattern** | Engulfing, Pin Bar, Hammer, Shooting Star |

### Multi-Timeframe
| Timeframe | Fungsi |
|---|---|
| `4H` | Bias market & S&D zone detection |
| `1H` | Konfirmasi trend & Supertrend |
| `15m` | Entry signal & scoring |

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

> Signal dikirim jika **score ≥ 6**

---

## 📖 Daftar Command Telegram

| Command | Fungsi |
|---|---|
| `/scan` | Scan semua pair otomatis (top 50 by volume) |
| `/scan BTC` | Scan BTC/USDT saja |
| `/scan BTC ETH SOL` | Scan beberapa pair sekaligus |
| `/watchlist` | Lihat daftar watchlist |
| `/addwatch BTC` | Tambah BTC/USDT ke watchlist |
| `/delwatch BTC` | Hapus BTC/USDT dari watchlist |
| `/stats` | Win rate & statistik semua signal |
| `/open` | Lihat semua signal yang masih open |
| `/help` | Daftar semua perintah |

---

## 🔔 Fitur Utama

### 1. Auto Scan (Setiap 15 Menit)
Bot otomatis scan setiap candle 15m tutup. Jika ada watchlist, pair dalam watchlist **selalu discan** bersamaan dengan top pair by volume.

### 2. Watchlist Custom
```
/addwatch BTC ETH SOL    → tambah 3 pair sekaligus
/delwatch BTC            → hapus dari watchlist
/watchlist               → lihat isi watchlist
```
Watchlist disimpan di `watchlist.json` — **tidak hilang saat bot restart.**

### 3. Win Rate Tracker
Setiap signal yang dikirim otomatis dicatat di `signals_tracker.json`. Status diupdate otomatis saat TP/SL tersentuh.
```
/stats  →  Win Rate: 68.5%  ███████░
           Total Signal: 42
           TP1 Hit: 15  |  TP2 Hit: 9  |  TP3 Hit: 5
           SL Hit: 13   |  Open: 5
```

### 4. Real-Time TP/SL Alert
Monitor cek harga setiap **30 detik**. Notif dikirim otomatis saat TP1/TP2/TP3 atau SL tersentuh, lengkap dengan PnL.

### 5. Anti-Duplikat
Signal yang sama (symbol + direction) tidak akan dikirim ulang dalam **60 menit**.

---

## ⚙️ Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Buat File .env
```bash
cp .env.example .env
```
Isi `.env`:
```env
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
TELEGRAM_CHAT_ID=-1001234567890
BINANCE_API_KEY=
BINANCE_SECRET=
```

### 3. Dapatkan Telegram Token
- Buka [@BotFather](https://t.me/BotFather) → `/newbot` → copy token

### 4. Dapatkan Chat ID
- **Channel/Grup:** Forward pesan ke [@userinfobot](https://t.me/userinfobot)
- **DM Pribadi:** Buka [@userinfobot](https://t.me/userinfobot) langsung

### 5. Jalankan Bot
```bash
python bot.py
```

---

## ⚙️ Kustomisasi (config.py)

```python
MIN_SCORE        = 6      # Naikkan ke 8-9 untuk signal lebih selektif
MIN_VOLUME_USDT  = 50_000_000  # Min volume 24h ($)
MAX_PAIRS        = 50     # Max pair yang di-scan per cycle
LEVERAGE         = 10     # Leverage yang ditampilkan di signal
TF_SIGNAL        = "15m"  # Timeframe entry
SL_ATR_MULT      = 1.5    # Stop loss = 1.5x ATR
TP1_RR           = 1.5    # Risk/Reward TP1
TP2_RR           = 2.5    # Risk/Reward TP2
TP3_RR           = 4.0    # Risk/Reward TP3
```

---

## 📈 Contoh Output Signal

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃  🟢 BTC/USDT  ·  LONG 📈
┃  ⚡ Strength: 💪 STRONG  ███████░
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃  💰 Entry:    43250.5000
┃  🛑 Stop Loss: 42800.0000  (-1.0%)
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

## 📈 Contoh Output TP/SL Alert

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃  🎯 TP2 HIT  ·  ✅ WIN
┃  🟢 BTC/USDT  ·  LONG
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃  📥 Entry:  43250.5000
┃  🏁 Close:  44598.2000
┃  💰 PnL:    +31.2%  (10x)
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕐 2024-01-15 10:45 UTC
```

---

## ⚠️ Disclaimer

Bot ini hanya untuk **sinyal informasi** dan **bukan saran finansial**.
Trading futures mengandung risiko tinggi. Selalu gunakan manajemen risiko yang baik.
