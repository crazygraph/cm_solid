# 01 - Data Contract.md

## 1. Objective

Dokumen ini mendefinisikan kontrak data untuk penelitian strategi **BB-ADX 3-Candle Continuation M5** agar seluruh proses riset, backtest, validasi, dan implementasi berjalan deterministik, reproducible, dan bebas ambiguity.

Tujuan utama data contract ini:

- membakukan format input OHLCV,
- membakukan fitur turunan minimum,
- membakukan precondition sebelum signal generation,
- membakukan output schema untuk trade log dan metrics,
- memastikan tidak ada look-ahead bias pada komputasi sinyal.

---

## 2. Strategy Identity

- **Strategy Name**: BB-ADX 3-Candle Continuation M5
- **Timeframe**: M5
- **Signal Style**: Bollinger Band breakout continuation + 3-candle pattern + ADX rising filter
- **Primary Execution Mode**: signal on bar close, entry on next bar open
- **Primary Use Case**: research baseline, backtest, robustness testing, MT5 parity planning

---

## 3. Raw Input Data Contract

### 3.1 Required Columns

Dataset input minimum wajib memiliki kolom berikut:

- `timestamp`
- `open`
- `high`
- `low`
- `close`
- `volume`

### 3.2 Column Definitions

#### `timestamp`
- Tipe: timezone-aware datetime
- Timezone final: **UTC**
- Granularity: 5 menit
- Harus merepresentasikan waktu pembukaan bar M5

#### `open`
- Tipe: float
- Harga open bar

#### `high`
- Tipe: float
- Harga high bar

#### `low`
- Tipe: float
- Harga low bar

#### `close`
- Tipe: float
- Harga close bar

#### `volume`
- Tipe: numeric
- Nilai volume dari source
- Tidak dipakai pada baseline signal logic, tetapi tetap wajib tersedia untuk integritas dataset

---

## 4. Structural Requirements

Dataset wajib memenuhi semua kondisi berikut:

1. Urut **ascending by timestamp**
2. Tidak boleh ada duplicate `timestamp`
3. Seluruh bar harus berada pada interval **M5 konsisten**
4. Tidak boleh ada missing value pada `open/high/low/close`
5. Relasi OHLC harus valid:
   - `high >= max(open, close)`
   - `low <= min(open, close)`
   - `high >= low`
6. Dataset final harus sudah berada pada timezone **UTC**
7. Jika sumber awal bukan M5, proses resampling harus dibakukan dan dicatat di run manifest

---

## 5. Missing Bar Policy

### 5.1 Default Policy
- Missing bar **tidak boleh diisi sintetis secara diam-diam**
- Missing bar harus:
  - dideteksi,
  - dicatat,
  - dan diputuskan secara eksplisit apakah range data tetap dipakai atau dipotong

### 5.2 Research Baseline Recommendation
Untuk baseline:
- gunakan hanya segmen data yang lolos continuity check
- bila ditemukan missing bar:
  - tandai range terpengaruh,
  - jangan gunakan area tersebut untuk evaluasi signal/trade jika dapat menimbulkan ambiguity

---

## 6. Indicator Feature Contract

Fitur turunan minimum yang wajib tersedia:

- `bb_mid`
- `bb_upper`
- `bb_lower`
- `adx_14`

### 6.1 Bollinger Band Definition
Default parameter baseline:

- length = `20`
- stddev = `2.0`
- source = `close`
- basis = SMA(close, 20)

Derived columns:
- `bb_mid`
- `bb_upper`
- `bb_lower`

### 6.2 ADX Definition
Default parameter baseline:

- ADX length = `14`

Derived column:
- `adx_14`

Catatan:
- baseline hanya memakai ADX line
- +DI / -DI tidak dipakai dalam signal logic baseline

---

## 7. Pattern Helper Columns

Untuk mempermudah audit dan debugging, sangat disarankan menyiapkan kolom bantu berikut:

- `candle_dir`
- `long_signal`
- `short_signal`
- `signal_tag`
- `entry_price_candidate`
- `sl_price_candidate`
- `tp_price_candidate`

### 7.1 `candle_dir`
Definisi:
- `1` jika `close > open`
- `-1` jika `close < open`
- `0` jika `close == open`

### 7.2 `long_signal`
- `1` jika seluruh syarat long signal valid pada bar tersebut
- `0` selain itu

### 7.3 `short_signal`
- `1` jika seluruh syarat short signal valid pada bar tersebut
- `0` selain itu

---

## 8. Warmup Contract

Karena strategi membutuhkan BB(20) dan ADX(14), maka data awal yang belum cukup untuk menghitung indikator secara valid tidak boleh digunakan untuk signal generation.

### 8.1 Rule
Bar hanya boleh dievaluasi sebagai kandidat signal jika:

- seluruh nilai `bb_mid`, `bb_upper`, `bb_lower`, `adx_14` pada bar:
  - `t`
  - `t-1`
  - `t-2`
  tersedia dan valid (non-NaN)

### 8.2 Recommendation
Gunakan warmup buffer yang konservatif pada engine backtest agar:
- indikator stabil,
- sinyal awal tidak tercemar efek startup indikator.

---

## 9. Signal Computation Contract

Notasi:

- `c1 = t-2`
- `c2 = t-1`
- `c3 = t`

Signal hanya boleh dihitung pada **close bar `t`**.

### 9.1 Long Signal
`long_signal[t] = 1` jika seluruh kondisi berikut terpenuhi:

1. `close[c1] > bb_upper[c1]`
2. `close[c2] < open[c2]`
3. `close[c3] > open[c3]`
4. `close[c3] > open[c2]`
5. `adx_14[c3] > adx_14[c2] > adx_14[c1]`

Jika salah satu gagal:
- `long_signal[t] = 0`

### 9.2 Short Signal
`short_signal[t] = 1` jika seluruh kondisi berikut terpenuhi:

1. `close[c1] < bb_lower[c1]`
2. `close[c2] > open[c2]`
3. `close[c3] < open[c3]`
4. `close[c3] < open[c2]`
5. `adx_14[c3] > adx_14[c2] > adx_14[c1]`

Jika salah satu gagal:
- `short_signal[t] = 0`

---

## 10. No Look-Ahead Contract

Semua implementasi wajib mematuhi aturan berikut:

1. Signal pada bar `t` hanya boleh memakai informasi hingga **close bar `t`**
2. Tidak boleh memakai data dari `t+1` atau sesudahnya untuk:
   - validasi signal,
   - validasi pattern,
   - validasi ADX rising,
   - validasi posisi relatif terhadap Bollinger Band
3. Entry baseline tidak boleh dilakukan pada close candle sinyal dengan asumsi fill ideal
4. Entry baseline dilakukan pada **open bar berikutnya**

---

## 11. Trade Construction Contract

Jika signal valid pada bar `t`, kandidat trade dibentuk sebagai berikut.

### 11.1 Entry Candidate
- Entry bar = `t+1`
- Entry price = `open[t+1]`

### 11.2 Stop Loss Candidate

#### Long
Default SL:
- `sl = min(low[t-1], low[t])`
- yaitu hanya extreme dari **Candle-2 dan Candle-3**

#### Short
Default SL:
- `sl = max(high[t-1], high[t])`
- yaitu hanya extreme dari **Candle-2 dan Candle-3**

### 11.3 Take Profit Candidate

Default TP:
- `2R`

Definisi:

#### Long
- `risk = entry_price - sl`
- `tp = entry_price + 2.0 * risk`

#### Short
- `risk = sl - entry_price`
- `tp = entry_price - 2.0 * risk`

Catatan:
- rentang TP untuk data mining berikutnya: `1R` sampai `4R`
- tetapi baseline contract ini menetapkan default = `2R`

---

## 12. Position State Contract

Default baseline:

- satu posisi aktif per symbol
- tidak hedging
- tidak scale in
- tidak scale out
- signal baru saat posisi masih terbuka => diabaikan
- long dan short tidak boleh aktif bersamaan pada symbol yang sama

---

## 13. Execution Assumption References

Data contract ini mengasumsikan execution model berikut, yang harus konsisten dengan dokumen execution assumptions / strategy spec:

1. Signal diketahui di close Candle-3
2. Entry di open bar berikutnya
3. Gap harus diperlakukan eksplisit
4. Jika dalam satu bar setelah entry, SL dan TP tersentuh bersamaan menurut OHLC:
   - gunakan **SL-first tie priority** sebagai default konservatif

---

## 14. Output Data Contract

### 14.1 trades.csv
Kolom minimum yang direkomendasikan:

- `trade_id`
- `symbol`
- `side`
- `signal_bar_index`
- `signal_bar_time`
- `entry_bar_index`
- `entry_bar_time`
- `entry_price`
- `sl_price`
- `tp_price`
- `exit_bar_index`
- `exit_bar_time`
- `exit_price`
- `exit_reason`
- `risk_r`
- `gross_r`
- `net_r`
- `holding_bars`

### 14.2 metrics.json
Minimal metrics:

- `total_trades`
- `win_rate`
- `profit_factor`
- `expectancy_r`
- `avg_r`
- `median_r`
- `sum_r`
- `max_drawdown_r`
- `max_losing_streak`
- `avg_holding_bars`

### 14.3 run_manifest.json
Minimal metadata:

- `strategy_name`
- `symbol`
- `timeframe`
- `data_source`
- `timezone`
- `start_date`
- `end_date`
- `bb_length`
- `bb_stddev`
- `adx_length`
- `sl_rule`
- `tp_rule`
- `entry_rule`
- `execution_tie_rule`
- `spread_model`
- `commission_model`
- `notes`

---

## 15. Integrity and Validation Checklist

Sebelum backtest dijalankan, dataset wajib lolos pemeriksaan berikut:

- timestamp ascending
- tidak ada duplicate timestamp
- interval M5 konsisten
- timezone UTC
- OHLC valid
- volume tersedia
- indikator non-NaN setelah warmup
- tidak ada signal yang dihitung pada bar yang belum lengkap
- entry hanya menggunakan next bar open
- SL/TP dibentuk dari rule yang sudah dibakukan

---

## 16. Versioning

- **Document Name**: 01 - Data Contract.md
- **Strategy**: BB-ADX 3-Candle Continuation M5
- **Version**: v0.1 baseline
- **Status**: executable research draft
