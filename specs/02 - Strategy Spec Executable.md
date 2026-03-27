# 02 - Strategy Spec Executable.md

## 1. Objective

Dokumen ini mendefinisikan spesifikasi executable untuk strategi **BB-ADX 3-Candle Continuation M5** dalam bentuk rule yang tegas, terukur, dan dapat diimplementasikan secara konsisten ke backtest Python maupun mapping ke MT5.

Dokumen ini dibuat agar:

- tidak ambigu,
- tidak look-ahead,
- selaras dengan workflow penelitian sistematis,
- mudah diuji robustness pada tahap data mining berikutnya.

---

## 2. Strategy Identity

- **Strategy Name**: BB-ADX 3-Candle Continuation M5
- **Market Style**: continuation / momentum continuation
- **Timeframe**: M5
- **Indicators**:
  - Bollinger Band (20, 2)
  - ADX(14)
- **Pattern Core**: 3-candle continuation after close outside Bollinger Band
- **Signal Timing**: confirmed on close Candle-3
- **Entry Timing**: next bar open

---

## 3. Indicator Definitions

### 3.1 Bollinger Band
Default parameter:

- length = `20`
- stddev = `2.0`
- source = `close`
- basis = SMA(close, 20)

Derived values:
- `bb_mid[t]`
- `bb_upper[t]`
- `bb_lower[t]`

### 3.2 ADX
Default parameter:

- length = `14`

Derived value:
- `adx[t]`

Filter baseline:
- ADX harus **increasing** pada 3 titik berturut-turut:
  - `adx[t] > adx[t-1] > adx[t-2]`

Catatan:
- baseline belum memakai threshold minimum ADX
- baseline belum memakai +DI / -DI

---

## 4. Candle Indexing Convention

Untuk setiap kandidat signal pada bar `t`:

- `c1 = t-2`  -> Candle-1
- `c2 = t-1`  -> Candle-2
- `c3 = t`    -> Candle-3

Signal hanya dianggap sah bila seluruh syarat dapat diverifikasi **saat Candle-3 sudah close**.

---

## 5. Long Setup Definition

Long signal valid bila seluruh kondisi berikut terpenuhi.

### L1. Candle-1 breakout di atas upper BB
- `close[c1] > bb_upper[c1]`

Interpretasi:
- Candle-1 harus menutup di atas upper Bollinger Band
- rule memakai **close**, bukan high, agar tidak ambigu intrabar

### L2. Candle-2 retrace bearish
- `close[c2] < open[c2]`

Interpretasi:
- Candle-2 harus berlawanan arah dengan Candle-1 long impulse
- baseline belum mewajibkan ukuran retrace minimum / maksimum

### L3. Candle-3 continuation bullish
- `close[c3] > open[c3]`

### L4. Candle-3 close break di atas open Candle-2
- `close[c3] > open[c2]`

Interpretasi:
- syarat ini mendefinisikan “break dan close di atas open Candle-2”
- rule menggunakan close final Candle-3, bukan sekadar wick/high

### L5. ADX increasing
- `adx[c3] > adx[c2] > adx[c1]`

### L6. Long signal final
Jika L1 sampai L5 semuanya terpenuhi pada close bar `t`, maka:
- `long_signal[t] = 1`

Jika tidak:
- `long_signal[t] = 0`

---

## 6. Short Setup Definition

Short signal valid bila seluruh kondisi berikut terpenuhi.

### S1. Candle-1 breakout di bawah lower BB
- `close[c1] < bb_lower[c1]`

### S2. Candle-2 retrace bullish
- `close[c2] > open[c2]`

### S3. Candle-3 continuation bearish
- `close[c3] < open[c3]`

### S4. Candle-3 close break di bawah open Candle-2
- `close[c3] < open[c2]`

### S5. ADX increasing
- `adx[c3] > adx[c2] > adx[c1]`

### S6. Short signal final
Jika S1 sampai S5 semuanya terpenuhi pada close bar `t`, maka:
- `short_signal[t] = 1`

Jika tidak:
- `short_signal[t] = 0`

---

## 7. Signal Confirmation Rule

Signal **tidak boleh** dinyatakan valid sebelum Candle-3 selesai.

Artinya:
- strategi tidak boleh entry di tengah Candle-3,
- strategi tidak boleh memakai partial information dari Candle-3,
- strategi tidak boleh melakukan intrabar anticipation.

Signal timestamp:
- waktu signal = timestamp close dari Candle-3 / bar `t`

---

## 8. Entry Rule

### 8.1 Long Entry
Jika `long_signal[t] = 1` dan tidak ada posisi aktif, maka:

- entry side = `long`
- entry bar = `t+1`
- entry price = `open[t+1]`

### 8.2 Short Entry
Jika `short_signal[t] = 1` dan tidak ada posisi aktif, maka:

- entry side = `short`
- entry bar = `t+1`
- entry price = `open[t+1]`

### 8.3 Constraints
- satu posisi aktif per symbol
- signal baru selama ada posisi aktif => diabaikan
- baseline tidak memakai pending order
- baseline tidak memakai entry filter tambahan

---

## 9. Stop Loss Rule

Default stop loss diubah sesuai keputusan terbaru:

### 9.1 Long Stop Loss
- `sl = min(low[c2], low[c3])`

Artinya:
- SL hanya memakai extreme **Candle-2 dan Candle-3**
- Candle-1 tidak dipakai dalam default SL baseline

### 9.2 Short Stop Loss
- `sl = max(high[c2], high[c3])`

Artinya:
- SL hanya memakai extreme **Candle-2 dan Candle-3**

### 9.3 Validity Constraint
Trade hanya valid jika risk distance positif.

#### Long
- harus memenuhi `entry_price > sl`

#### Short
- harus memenuhi `entry_price < sl`

Jika tidak, trade harus dibatalkan dan dicatat sebagai invalid setup / invalid risk geometry.

---

## 10. Take Profit Rule

Default take profit baseline:

- `TP = 2R`

### 10.1 Long TP
- `risk = entry_price - sl`
- `tp = entry_price + 2.0 * risk`

### 10.2 Short TP
- `risk = sl - entry_price`
- `tp = entry_price - 2.0 * risk`

### 10.3 Planned Mining Range
Untuk tahap data mining selanjutnya, `RR` akan diuji pada rentang:
- `1R`
- `2R`
- `3R`
- `4R`

Namun **default baseline executable spec tetap 2R**.

---

## 11. Position Management

Default position management baseline:

- one position at a time
- no pyramiding
- no scale in
- no partial TP
- no trailing stop
- no breakeven shift
- no reverse-on-opposite-signal saat posisi belum selesai

Exit hanya melalui:
- Stop Loss
- Take Profit
- atau rule tambahan eksplisit jika nanti ditambahkan di versi berikutnya

---

## 12. Execution Assumptions

### 12.1 Signal Timing
- signal diketahui hanya setelah Candle-3 close

### 12.2 Entry Timing
- entry dilakukan pada open bar berikutnya

### 12.3 Fill Philosophy
- baseline memakai next-open execution
- tidak memakai close-fill pada candle sinyal

### 12.4 Gap Handling
#### Long
Jika `open[t+1] <= sl`, maka:
- entry harus dianggap invalid atau terkena gap-through risk sesuai mode engine yang dibakukan

#### Short
Jika `open[t+1] >= sl`, maka:
- entry harus dianggap invalid atau terkena gap-through risk sesuai mode engine

Rekomendasi baseline research:
- bila gap open membuat risk geometry tidak valid, **trade dibatalkan**

### 12.5 Intrabar Conflict Rule
Jika setelah entry terdapat bar yang secara OHLC menyentuh SL dan TP dalam bar yang sama, maka:
- gunakan **SL-first tie priority**

Ini wajib untuk menjaga konservatisme backtest.

---

## 13. Formal Signal Logic

### 13.1 Long
```python
long_signal[t] = (
    close[t-2] > bb_upper[t-2] and
    close[t-1] < open[t-1] and
    close[t]   > open[t] and
    close[t]   > open[t-1] and
    adx[t] > adx[t-1] > adx[t-2]
)
```

### 13.2 Short
```python
short_signal[t] = (
    close[t-2] < bb_lower[t-2] and
    close[t-1] > open[t-1] and
    close[t]   < open[t] and
    close[t]   < open[t-1] and
    adx[t] > adx[t-1] > adx[t-2]
)
```

### 13.3 Entry / SL / TP
```python
if long_signal[t] and no_open_position:
    entry_bar = t + 1
    entry_price = open[entry_bar]
    sl = min(low[t-1], low[t])
    risk = entry_price - sl
    tp = entry_price + 2.0 * risk

if short_signal[t] and no_open_position:
    entry_bar = t + 1
    entry_price = open[entry_bar]
    sl = max(high[t-1], high[t])
    risk = sl - entry_price
    tp = entry_price - 2.0 * risk
```

---

## 14. Anti-Bias Guarantees

Spesifikasi ini sengaja dibangun agar menghindari bias berikut:

### 14.1 No look-ahead pada pattern
Semua syarat pattern hanya memakai:
- Candle-1
- Candle-2
- Candle-3
yang sudah selesai terbentuk saat signal dikonfirmasi.

### 14.2 No look-ahead pada entry
Entry dilakukan di `open[t+1]`, bukan di `close[t]`.

### 14.3 No ambiguity pada retrace
Retrace Candle-2 didefinisikan numerik:
- long: `close[c2] < open[c2]`
- short: `close[c2] > open[c2]`

### 14.4 No ambiguity pada break
Break didefinisikan numerik:
- long: `close[c3] > open[c2]`
- short: `close[c3] < open[c2]`

### 14.5 Conservative intrabar handling
Jika SL dan TP sama-sama tersentuh pada bar yang sama:
- asumsi **SL kena duluan**

---

## 15. Known Limitations of Baseline Spec

Beberapa hal sengaja belum dimasukkan agar baseline tetap sederhana:

1. Tidak ada filter session
2. Tidak ada filter spread
3. Tidak ada filter minimum ADX threshold
4. Tidak ada filter ukuran body Candle-1
5. Tidak ada filter slope Bollinger midline
6. Tidak ada filter trend konteks HTF
7. Tidak ada trailing / ZZL / BE logic
8. Tidak ada exit opposite signal

Semua hal di atas bisa menjadi domain tahap robustness / data mining berikutnya.

---

## 16. Parameters Planned for Data Mining

Parameter yang direncanakan diuji pada tahap berikutnya:

- BB length
- BB stddev
- ADX rising definition
- ADX threshold minimum
- RR target dari `1R` sampai `4R`
- session filter
- Candle-1 body size filter
- Candle-2 retrace depth filter
- one-trade-per-signal cluster rules

---

## 17. Versioning

- **Document Name**: 02 - Strategy Spec Executable.md
- **Strategy**: BB-ADX 3-Candle Continuation M5
- **Version**: v0.1 baseline
- **Status**: executable research draft
