# Multi-Timeframe Microstructure Data Mining Plan (M1 Source -> M5 / M15 / H1 Research)
Version: 2.0  
Status: EXECUTABLE SPEC  
Author: Quant Research Pipeline  

---

# 1. OBJECTIVE

Mengeksplorasi dan memvalidasi edge berbasis **microstructure proxy** dengan **sumber data M1** tetapi **riset utama dilakukan pada M5, M15, dan H1** agar:

1. komputasi lebih ringan,
2. noise lebih rendah dibanding M1,
3. struktur swing lebih jelas,
4. pipeline lebih cepat untuk iterasi data mining, backtest, dan meta-labeling.

Output utama:
- rule-based candidate strategies,
- multi-timeframe feature library,
- execution-aware backtest results,
- meta-labeling dataset,
- baseline ML results.

---

# 2. DATA CONTRACT

## 2.1 Source
- Instrument: XAUUSD
- Raw timeframe: M1
- Research timeframe turunan: M5, M15, H1
- Durasi: ~5 tahun
- Timezone: UTC+0

## 2.2 Loader (MANDATORY)

```python
def load_ohlcv(path: str) -> pd.DataFrame:
    names = ['date', 'time', 'open', 'high', 'low', 'close', 'volume']
```

## 2.3 Loader Rules
- skip header row,
- parse datetime `%Y.%m.%d %H:%M`,
- jadikan timestamp sebagai index UTC,
- sort ascending,
- no duplicate index,
- missing bar wajib dideteksi dan dilaporkan.

## 2.4 Resampling Rules
Raw M1 di-resample menjadi:
- M5
- M15
- H1

OHLCV aggregation:
- open = first
- high = max
- low = min
- close = last
- volume = sum

Default:
- right-labeled, right-closed resampling agar event timestamp konsisten dengan close candle.

---

# 3. RESEARCH ARCHITECTURE

## 3.1 Peran timeframe
- **H1** = context / regime filter
- **M15** = primary signal timeframe
- **M5** = optional execution refinement / timing filter

## 3.2 Default research mode
Mode awal:
- H1 context enabled
- M15 event mining enabled
- M5 entry refinement optional

## 3.3 Why not M1 first
M1 tetap dipakai sebagai sumber data, tetapi bukan primary mining timeframe karena:
- terlalu noisy,
- event count terlalu besar,
- komputasi lebih lambat,
- rawan false discovery.

---

# 4. RESEARCH SPLIT (NO LEAKAGE)

Time-based split:
- Train = 60%
- Validation = 20%
- Test = 20%

STRICT RULES:
- no shuffle,
- no future leakage,
- tuning hanya pada validation,
- test dipakai sekali untuk evaluasi final.

Opsional:
- rolling walk-forward validation.

---

# 5. EXECUTION ASSUMPTIONS

## 5.1 Entry
Default:
- signal lahir di M15 close,
- entry di open candle M15 berikutnya.

Optional refinement:
- signal tetap dari M15,
- entry hanya dieksekusi bila filter M5 lolos pada window sesudah signal.

## 5.2 SL / TP
- **SL default = structural swing high / swing low**
- **TP default = 2R**
- spread = 0 baseline

## 5.3 Timeout
Karena timeframe riset berubah, timeout tidak lagi 50 bar untuk semua TF.

Default timeout:
- M5 signal mode = 30 bar
- M15 signal mode = 16 bar
- H1 signal mode = 8 bar

Untuk mode default pipeline ini:
- **M15 signal -> timeout = 16 bar**

## 5.4 Intrabar Rule
Jika dalam satu candle TP dan SL sama-sama tersentuh:
- **SL FIRST**

## 5.5 Gap Handling
Jika open berikutnya gap melewati SL:
- exit di harga gap/open yang lebih buruk.

---

# 6. FEATURE LIBRARY

Semua feature wajib hanya memakai data historis.

## 6.1 Candle Anatomy
Untuk M5, M15, H1:
- range
- body
- upper_wick
- lower_wick
- body_ratio
- close_position
- signed_range

## 6.2 Returns / Momentum
- ret_1, ret_2, ret_3, ret_5
- rolling cumulative return
- streak up/down
- directional efficiency

## 6.3 Volatility
- rolling std
- ATR
- BB width
- compression ratio
- expansion ratio

## 6.4 Structure
- rolling high/low
- distance to rolling high/low
- breakout distance
- reversion distance
- swing high / swing low markers

## 6.5 Trend / Context
- EMA 20 / 50
- slope EMA
- distance to EMA
- trend regime
- H1 bias mapped onto M15 / M5

## 6.6 Session Features
- hour
- weekday
- session bucket: Asia / London / NY / overlap

---

# 7. EVENT DEFINITIONS

Semua event dihitung di **M15** pada mode default.

## 7.1 Momentum Break
- candle body_ratio > threshold,
- close break previous rolling high / low.

## 7.2 Sweep + Reclaim
Long failure setup:
- low menembus rolling low(N),
- close kembali di atas rolling low(N).

Short failure setup:
- high menembus rolling high(N),
- close kembali di bawah rolling high(N).

## 7.3 Compression -> Expansion
- BB width / ATR berada di quantile bawah,
- lalu muncul candle expansion di quantile atas.

## 7.4 Inside Cluster Breakout
- 2+ inside bars,
- close breakout dari mother bar range.

## 7.5 Rejection Candle
- wick dominan,
- close berlawanan dari arah wick,
- berada dekat level rolling high/low atau EMA.

---

# 8. H1 CONTEXT FILTER

Default H1 filter:
- bullish jika close > EMA50 dan slope EMA50 > 0
- bearish jika close < EMA50 dan slope EMA50 < 0
- neutral selain itu

Aturan default:
- hanya ambil long event M15 jika H1 bullish
- hanya ambil short event M15 jika H1 bearish

---

# 9. M5 EXECUTION REFINEMENT (OPTIONAL)

Contoh filter M5:
- entry hanya bila candle M5 pertama/dua setelah signal M15 searah bias,
- atau M5 close berada di atas/bawah EMA20 sesuai arah signal,
- atau terjadi rejection kecil pada M5 yang menguntungkan entry.

Mode baseline notebook:
- refinement bisa dimatikan agar baseline tetap sederhana.

---

# 10. LABELING (TRIPLE BARRIER)

## 10.1 Entry
- next open pada timeframe eksekusi baseline (M15)

## 10.2 Barrier
- SL = swing terakhir sebelum entry
- TP = 2R
- timeout = 16 bar (default M15 mode)

## 10.3 Label
- TP hit first = 1
- SL hit first = 0
- timeout = 0 by default pada baseline dataset

---

# 11. BASELINE STAT MINING

Untuk setiap event:
- total trades
- winrate
- avg R
- median R
- expectancy
- profit factor
- max drawdown (R)
- max losing streak
- avg holding bars

Breakdown minimum:
- by year
- by session
- by H1 regime
- by train / val / test split

---

# 12. META-LABELING PLAN

## 12.1 Input
Feature snapshot saat event M15 muncul, ditambah:
- H1 context features,
- optional M5 refinement snapshot.

## 12.2 Target
Triple-barrier label dari backtest baseline.

## 12.3 Baseline models
- Logistic Regression
- HistGradientBoostingClassifier

## 12.4 Goal
Bukan membuat signal baru, tetapi:
- menyaring signal buruk,
- menaikkan PF,
- menurunkan drawdown,
- mengurangi trade count yang tidak efisien.

---

# 13. VALIDATION FRAMEWORK

Required:
- OOS evaluation
- walk-forward optional
- threshold tuning on validation only
- final test once
- parameter sensitivity
- yearly stability

No-go indicators:
- PF test < 1
- hasil hanya hidup di 1 tahun / 1 session
- hasil runtuh setelah threshold dipindah sedikit

---

# 14. OUTPUT ARTIFACTS

Mandatory:
- trades.csv
- metrics.json
- run_manifest.json
- meta_label_dataset.csv

Optional:
- feature_importance.csv
- equity_curve.csv
- yearly_metrics.csv
- session_metrics.csv

---

# 15. DEFAULT CONFIG

```yaml
source_tf: M1
research_tfs: [M5, M15, H1]

context_tf: H1
signal_tf: M15
execution_tf: M15
use_m5_refinement: false

spread_points: 0.0
tp_r_multiple: 2.0
sl_mode: structural_swing
timeout_bars:
  M5: 30
  M15: 16
  H1: 8

split:
  train: 0.60
  validation: 0.20
  test: 0.20
```

---

# 16. NEXT STEPS

1. implement resample pipeline M1 -> M5 / M15 / H1,
2. build multi-timeframe feature extraction,
3. run baseline event mining on M15,
4. add H1 regime filter,
5. optional M5 refinement,
6. generate labeled dataset,
7. train baseline meta-label models,
8. compare baseline vs filtered trades.

---
