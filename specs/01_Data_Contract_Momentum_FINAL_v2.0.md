# 01 – Data Contract (FINAL v2.0)
## XAUUSD – Momentum Candle (M15) + Microstructure Snapshot (M1/M5) – Jesse/Notebook

Dokumen ini mengunci kontrak data untuk riset strategi **Momentum Candle** pada timeframe utama **M15**.
Tujuan kontrak: memastikan pipeline **reproducible**, **no-leakage**, dan siap dipakai di:
- Notebook (playground/EDA)
- Jesse (backtest, mining, dataset export)

---

## 0) Scope & Assumptions (Locked)
- Symbol: **XAUUSD**
- Data range: **5 tahun**
- Raw dataset: **M1 OHLCV CSV** (UTC)
- Resample: M1 → M5, M15 (right-closed)
- Model costs (baseline):
  - Spread: **0**
  - Commission: **0.11 USD per 0.01 lot per side** (= 11 USD/lot/side; 22 USD/lot/round-turn)
- Leverage: 1:1000 (tidak mempengaruhi PnL per lot, hanya margin)

---

## 1) Raw Input Schema (M1)
### 1.1 CSV format (as provided)
Kolom setelah load:
- index: `timestamp` (UTC, tz-aware)
- columns: `open`, `high`, `low`, `close`, `volume`

Constraints:
- `timestamp` strictly increasing (no duplicates).
- Tidak dilakukan gap-fill (jika ada gap, tetap gap).
- `volume` boleh 0/NaN → treat as 0.

### 1.2 Loader reference
Fungsi loader yang dipakai (locked) adalah milik user; output DataFrame harus sesuai schema di atas.

---

## 2) Derived Bars Schema (M5, M15)
### 2.1 Resample rule (Locked)
Right-closed, label = close boundary:
- M5 candle timestamp = `...:05, :10, :15, ...` (UTC), merepresentasikan interval `(t-5m, t]`
- M15 candle timestamp = `...:15, :30, :45, :00` (UTC), interval `(t-15m, t]`

Aggregation:
- open = open pertama dalam interval
- high = max(high)
- low = min(low)
- close = close terakhir
- volume = sum(volume)

No gap-fill:
- jika interval kosong → candle tidak dibuat.

### 2.2 Schema M5/M15
Index: `timestamp` (UTC)
Columns: `open`, `high`, `low`, `close`, `volume`

---

## 3) Indicator Schema (derived, time-aligned)
Semua indikator dihitung **per timeframe** dan hanya menggunakan bar yang sudah close.

### 3.1 Indicators (v2.0)
Minimal:
- ATR14 (M15) – untuk filter kualitas (opsional/tunable)
- EMA50 (M5) – hanya untuk **optional alignment filter** (default OFF)

Optional (untuk ML snapshot, bukan rule):
- returns, volatility, ranges, wick/body stats (M1/M5)

Indicator alignment constraints:
- Saat evaluasi signal pada `t_feat = close_time M15`, indikator M15 harus memakai bar M15 yang close di `t_feat`.
- Snapshot M5/M1 harus memakai bar terakhir yang close `<= t_feat`.

---

## 4) Event (Signal) Table Schema (M15)
Satu record = satu candidate signal dari rule primary.

Columns (minimal):
- `event_id` (string, unique)
- `symbol` (string)
- `t_signal` (UTC timestamp)  : close time M15 saat signal terdeteksi
- `side` ∈ {LONG, SHORT}
- `signal_type` = "M15_MOMENTUM_ENGULF_BODY"
- `open_t`, `high_t`, `low_t`, `close_t` (M15 signal candle)
- `prev_open`, `prev_high`, `prev_low`, `prev_close` (M15 t-1)
- `filters_passed` (bool)
- `params_hash` (string) : hash dari parameter config (audit)

Event ID format (locked):
`{SYMBOL}-{t_signal_isoZ}-{SIDE}-{SEQ4}`

---

## 5) Trade Table Schema (Executed)
Entry selalu dilakukan pada open candle berikutnya (M15).

Columns (minimal):
- `event_id`
- `symbol`
- `side`
- `t_entry` (UTC)
- `entry_price`
- `t_exit` (UTC)
- `exit_price`
- `exit_reason` ∈ {SL, TP, TIME}
- `sl_price`
- `tp_price`
- `risk_price = abs(entry_price - sl_price)`
- `tp_R` (float)
- `commission_usd` (per 1 lot) : open+close
- `pnl_usd_per_1lot`
- `pnl_R`

---

## 6) Microstructure Feature Snapshot Table (for ML)
Microstructure digunakan sebagai **feature** meta-model, **bukan rule wajib**.
Snapshot diambil pada:
- `t_feat = t_signal` (close M15 candle signal)

No leakage:
- semua fitur berasal dari data yang close `<= t_feat`.

Columns (minimal):
Keys:
- `event_id`, `t_feat`, `side`

M1 features (windows end at t_feat):
- `m1_ret_1`, `m1_ret_5`, `m1_ret_15`
- `m1_vol_20` (std returns 20 bars)
- `m1_range_pct_20_mean`
- `m1_body_pct_20_mean`
- `m1_wick_up_pct_20_mean`, `m1_wick_down_pct_20_mean`
- `m1_break_count_high_30`, `m1_break_count_low_30`

M5 features (last closed M5 at/before t_feat):
- `m5_close_dir` ∈ {+1,-1,0}
- `m5_ema50_dist_pct` (if EMA50 available)
- `m5_atr14` (optional)

M15 features (signal candle + context):
- `m15_body_pct`
- `m15_range_pct`
- `m15_atr14` (optional)

---

## 7) Artifacts Directory Contract
All runs must export:
- `artifacts/run_manifest.json`
- `artifacts/events.csv`
- `artifacts/trades.csv`
- `artifacts/features.parquet`
- `artifacts/metrics.json`
- `artifacts/decision_log.jsonl` (optional)

---

## Versioning
- Strategy family: **Momentum Candle**
- Version: **v2.0**
- Status: **FINAL**
