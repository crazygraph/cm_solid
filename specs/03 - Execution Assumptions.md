# 03 - Execution Assumptions.md

## 1. Objective

Dokumen ini membakukan asumsi eksekusi untuk strategi **BB-ADX 3-Candle Continuation M5** agar hasil backtest tetap konservatif, tidak bias, dan mudah disejajarkan ke implementasi MT5.

---

## 2. Core Principles

1. **Signal hanya valid pada close Candle-3**
2. **Entry baseline dilakukan pada open bar berikutnya**
3. **Tidak ada intrabar clairvoyance**
4. **Jika SL dan TP sama-sama tersentuh pada satu bar, asumsi default adalah SL kena lebih dulu**
5. **Gap harus diperlakukan eksplisit**
6. **Trade yang menghasilkan risk geometry tidak valid harus dibatalkan**

---

## 3. Timing Convention

Untuk signal yang terdeteksi pada bar `t`:

- Candle-1 = `t-2`
- Candle-2 = `t-1`
- Candle-3 = `t`

Signal diketahui hanya ketika bar `t` telah selesai.

---

## 4. Entry Assumptions

### 4.1 Entry Rule
Jika `long_signal[t] = 1` atau `short_signal[t] = 1`, maka entry baseline adalah:

- entry bar = `t+1`
- entry price = `open[t+1]`

### 4.2 No Close Fill
Backtest baseline **tidak boleh** mengasumsikan fill pada `close[t]`.

Alasan:
- mencegah optimistic fill,
- menjaga no look-ahead,
- lebih mudah dipetakan ke eksekusi live.

---

## 5. Gap Handling

### 5.1 Long
Jika pada long setup:
- `open[t+1] <= sl`

maka trade dianggap **invalid entry geometry** dan dibatalkan.

### 5.2 Short
Jika pada short setup:
- `open[t+1] >= sl`

maka trade dianggap **invalid entry geometry** dan dibatalkan.

### 5.3 Rationale
Dengan rule ini:
- kita tidak memaksakan entry pada kondisi risk sudah tidak logis,
- kita menghindari hasil backtest yang terlalu optimis atau terlalu arbitrer.

---

## 6. Stop Loss and Take Profit Monitoring

Setelah posisi terbuka, setiap bar berikutnya dievaluasi menggunakan OHLC bar M5.

### 6.1 Long
- Jika `open <= sl`: exit pada `open` sebagai **gap stop**
- Else jika `low <= sl` dan `high >= tp` pada bar yang sama: **SL-first**
- Else jika `low <= sl`: exit pada `sl`
- Else jika `high >= tp`: exit pada `tp`

### 6.2 Short
- Jika `open >= sl`: exit pada `open` sebagai **gap stop**
- Else jika `high >= sl` dan `low <= tp` pada bar yang sama: **SL-first**
- Else jika `high >= sl`: exit pada `sl`
- Else jika `low <= tp`: exit pada `tp`

---

## 7. Position Constraints

- satu posisi aktif per symbol
- tidak ada hedging
- tidak ada pyramiding
- signal baru saat posisi aktif diabaikan

---

## 8. Cost Model

### 8.1 Baseline
- spread = 0
- commission = 0

### 8.2 Future Realism Pass
Pada tahap realism / MT5 parity berikutnya, model dapat diperluas menjadi:
- fixed spread,
- variable spread,
- commission per lot,
- slippage model.

---

## 9. Output Logging Requirements

Setiap trade minimal harus mencatat:

- waktu signal
- waktu entry
- side
- entry price
- sl
- tp
- waktu exit
- exit price
- exit reason
- gross R
- net R
- holding bars

---

## 10. Versioning

- **Document Name**: 03 - Execution Assumptions.md
- **Strategy**: BB-ADX 3-Candle Continuation M5
- **Version**: v0.1 baseline
- **Status**: executable research draft