# PEM M15 Asia Mid/High Vol — Production Grade Strategy Spec v1

## 1. Objective

Membangun versi production-grade dari strategi PEM M15 berdasarkan hasil riset yang sudah dilakukan.

Strategi ini diposisikan sebagai:
- event-driven breakout/expansion strategy
- hanya aktif pada kondisi pasar tertentu
- deterministic
- no-lookahead
- MT5-aware
- siap untuk parity testing dan dry-run forward test

## 2. Final Research Decision

### Strategy family
PEM compression-breakout-confirmation

### Chosen deployment candidate
`asia_mid_high_vol`

### Why this variant
Berdasarkan hasil riset:
- edge terbaik muncul di sesi Asia
- kualitas edge membaik saat volatilitas bukan low-vol
- drawdown jauh lebih kecil dibanding baseline
- PF dan expectancy lebih baik
- lebih bersih dibanding varian yang memasukkan London / NY overlap

### Important limitation
Edge sangat sensitif terhadap keterlambatan entry.
- delay 1 bar: edge hampir hilang
- delay 2 bar: edge hilang

Implikasi:
- implementasi harus mengeksekusi segera setelah close candle signal
- tidak cocok untuk workflow manual yang lambat

## 3. Market / Timeframe

- Symbol utama: XAUUSD
- Base timeframe production: M15
- Timezone research: UTC
- Session aktif utama: Asia
- Session non-priority: London
- Session blok: NY Overlap

## 4. Strategy Thesis

Strategi menangkap pola berikut:
1. muncul candle impuls kuat
2. diikuti fase kompresi singkat
3. terjadi breakout dari area kompresi
4. breakout harus dikonfirmasi candle berikutnya
5. hanya diambil jika searah filter trend dan berada di atas/bawah VWAP
6. hanya diambil pada sesi Asia
7. hanya diambil ketika volatilitas bukan low-vol regime

Hipotesis ekonomi:
- di Asia, struktur price action cenderung lebih rapi
- pola compression → breakout → confirmation lebih sedikit terganggu spike kasar
- trade yang lolos bukan sekadar trend-following, tetapi structured expansion event

## 5. Exact Entry Logic

### 5.1 Indicators
- ATR(14), RMA style
- EMA(55)
- Session VWAP menggunakan HLC3 dan cumulative intraday volume weighting

### 5.2 Candle features
For each M15 bar:
- `bar_range = high - low`
- `body = abs(close - open)`
- `body_frac = body / bar_range`, jika `bar_range > 0`, else 0

### 5.3 Impulse detection
- `strong_up = close > open AND bar_range > ATR(14) * 1.1`
- `strong_down = close < open AND bar_range > ATR(14) * 1.1`

Jika `state == 0` dan salah satu kondisi di atas true:
- `state = 1`

### 5.4 Compression detection
Small candle:
- `small_candle = bar_range < ATR(14) * 0.7`

Transisi:
- jika `state == 1` dan `small_candle`: masuk `state = 2`
- jika `state == 2` dan `small_candle`: tambahkan `stall_count`

Compression boundaries:
- `comp_high = max(high dari semua small candles compression)`
- `comp_low = min(low dari semua small candles compression)`

Valid compression:
- `state == 2`
- `stall_count >= 2`

Reset invalid compression:
- jika `stall_count > 15`, reset ke `state = 0`

### 5.5 Breakout
- `bull_break = valid_comp AND close > comp_high`
- `bear_break = valid_comp AND close < comp_low`
- `break_clean = body_frac >= 0.20`

Fire event:
- `(bull_break OR bear_break) AND break_clean`

Saat fire:
- simpan arah breakout
- simpan `comp_high` / `comp_low`
- reset state machine

### 5.6 Confirmation candle
Pada candle berikutnya setelah fire:
- long confirm jika `close > open`
- short confirm jika `close < open`

### 5.7 Trend/VWAP filter
- long valid jika `close > EMA55 AND close > VWAP`
- short valid jika `close < EMA55 AND close < VWAP`

### 5.8 Session filter
Trade hanya boleh diambil jika entry signal berada di sesi Asia.

Definisi sesi UTC:
- Asia: 00:00–06:59
- London: 07:00–12:59
- NY Overlap: 13:00–16:59
- NY Late: 17:00–23:59

Filter production:
- allow: Asia only

### 5.9 Volatility filter
Gunakan ATR percentile rank rolling 96 bar M15.

Hitung:
- `atr_pct_rank = percentile rank ATR(14) terakhir dalam rolling 96 bar`

Filter production:
- hanya ambil trade jika `atr_pct_rank >= 0.33`

Interpretasi:
- hanya mid-vol atau high-vol
- low-vol diblok

### 5.10 Entry trigger
Jika semua kondisi valid pada close bar `t`:
- order masuk pada open bar `t+1`

Order type production:
- market order at bar open proxy
- di MT5 dapat dieksekusi sebagai market order saat candle baru terbentuk

## 6. Stop Loss / Take Profit / Exit

### 6.1 Stop loss
- long: `SL = comp_low`
- short: `SL = comp_high`

Stop dibekukan saat signal valid dan tidak berubah setelah entry.

### 6.2 Take profit
Gunakan fixed-R target:
- `TP = entry_price + 2R` untuk long
- `TP = entry_price - 2R` untuk short

Dengan:
- `R = abs(entry_price - SL)`

### 6.3 Timeout
- maksimum hold = 12 bar M15

Jika sampai `t+12` sejak entry tidak kena SL/TP:
- keluar di close timeout bar

### 6.4 Intrabar ambiguity
Jika pada bar yang sama:
- SL dan TP keduanya tersentuh

Aturan wajib:
- `SL first`

Ini non-negotiable demi konservatisme dan parity.

## 7. Execution Assumptions

### Research / production assumptions
- no lookahead
- signal baru valid setelah candle close
- entry dilakukan di candle berikutnya
- single position only
- no pyramiding
- no re-entry dalam trade yang sama
- no overlapping position

### Why single position only
Edge PEM datang dari timing presisi.
Menambah basket / DCA berisiko merusak attribution dan meningkatkan mismatch MT5.

## 8. Risk Management

### Initial production risk
- fixed fractional risk
- risk per trade: 0.25% sampai 0.50% equity
- mulai dari 0.25% saat dry run

### Hard guards
- max 1 posisi terbuka
- max daily loss: 1.0% equity
- max consecutive losses per day: 3
- setelah 3 loss berturut-turut dalam hari yang sama → stop trading sampai hari berikutnya
- no trade saat spread abnormal

### Spread guard
Untuk XAUUSD, aktifkan guard:
- skip trade jika spread > threshold broker-specific
- threshold awal ditentukan saat parity/live diagnostics

## 9. Production Filters Final

### Mandatory
- timeframe = M15
- session = Asia
- atr_pct_rank >= 0.33
- signal close confirmed
- entry next bar
- single position only

### Optional, not enabled by default
- news blackout
- day-of-week blacklist
- tighter spread guard
- trade frequency cap

## 10. What is explicitly NOT included

Agar production v1 tetap bersih, hal berikut belum dipakai:
- meta-labeling
- dynamic position sizing by confidence
- pyramiding
- multi-target exits
- London / NY deployment
- higher timeframe bias filter tambahan
- deep learning / probabilistic regime engine

## 11. MT5 Mapping Notes

### On new M15 bar
Saat terbentuk bar baru:
1. finalize bar sebelumnya
2. hitung semua indikator berdasarkan data close yang sudah fix
3. evaluasi state machine PEM
4. jika signal valid pada closed bar:
   - hitung SL
   - hitung risk
   - hitung TP 2R
   - kirim market order segera di awal bar baru

### Required EA log fields
Untuk setiap signal / trade, simpan:
- signal_time
- entry_time
- direction
- entry_price
- sl_price
- tp_price
- comp_high
- comp_low
- atr14
- atr_pct_rank
- session_bucket
- ema55
- vwap
- exit_time
- exit_reason
- pnl_money
- pnl_r

### Required parity checks
Bandingkan Python vs MT5:
- trade count
- entry timestamps
- direction
- entry price deviation
- SL/TP values
- exit reason
- timeout count
- ambiguous-bar resolution count

## 12. Pass / Fail Criteria for Production Candidate

Agar strategi lanjut ke forward test, kandidat harus:
- tetap positif setelah spread/slippage ringan
- tidak hancur pada TP haircut ringan
- tidak ada mismatch besar Python vs MT5
- distribusi trade harian masih wajar
- max DD tetap dalam batas yang diterima

### Known weakness
- delay 1–2 bar merusak edge
Jadi kalau MT5/live tidak bisa entry presisi, kandidat harus diturunkan statusnya.

## 13. Forward Test Plan

### Stage 1 — Demo / paper
Durasi awal:
- 2 sampai 4 minggu

Yang diamati:
- fill slippage
- spread distribution saat signal
- trade count vs notebook
- session timing mismatch
- real-time signal integrity

### Stage 2 — Small capital live
Hanya jika Stage 1 lolos.
Mulai dengan:
- 0.25% risk
- no scaling
- no optimization tambahan

## 14. Recommended Next Files

Untuk melanjutkan ke deployment, dokumen berikut disarankan:
- `01_strategy_spec_executable.md`
- `02_execution_assumptions.md`
- `03_mt5_mapping.md`
- `04_forward_test_checklist.md`
- `05_daily_monitoring_template.md`

## 15. Final Production Statement

Production candidate v1:

**PEM M15 Asia Mid/High Vol**
- session: Asia only
- volatility: ATR percentile rank >= 0.33
- entry: next bar open after valid confirmation
- SL: compression opposite boundary
- TP: fixed 2R
- timeout: 12 bars
- intrabar tie: SL first
- risk: fixed fractional, single position only

Status:
- **Approved for MT5 parity implementation and dry-run forward testing**
- **Not yet approved for full live capital deployment**
