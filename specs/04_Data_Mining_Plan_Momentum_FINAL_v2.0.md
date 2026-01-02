# 04 – Data Mining Plan (FINAL v2.0)
## Momentum Candle (M15) – Robust Edge Discovery + Microstructure Snapshot for Meta-Model

Tujuan: menemukan edge stabil dari rule primary sederhana dan menyiapkan dataset microstructure (M1/M5) untuk meta-model.

---

## 0) Locked vs Tunable
Locked:
- M15 primary signal: body menelan range candle sebelumnya (spec 02)
- Entry next open
- Exit ordering SL-first (spec 03)
- Microstructure snapshot adalah feature ML, bukan rule wajib

Tunable (search space):
- tp_R, buffers, filter kualitas, time stop, cooldown
- optional M5 alignment (OFF by default)

---

## 1) Search Space
Primary:
- `tp_R` ∈ {1.0, 1.5, 2.0, 2.5, 3.0}
- `sl_buffer_ticks` ∈ {0,1,2}
- `engulf_buffer_ticks` ∈ {0,1,2}
- `use_quality_filter` ∈ {true,false}
- `min_body_pct` ∈ {0.50,0.60,0.70} (ignored if filter off)
- `min_body_atr` ∈ {0.0,0.25,0.35} (0 disables ATR filter)
- `max_hold_m15` ∈ {0, 8, 16}
- `cooldown_m15` ∈ {0,1,2}

Optional M5 alignment (extra experiment):
- `m5_align_mode` ∈ {"NONE","CLOSE_DIR","EMA50"} (default NONE)

Recommended: random search 500–1000 config (seed fixed).

---

## 2) Walk-forward split
Rolling:
- Train 24m / Val 6m / Test 6m
- Step 6m
No shuffle. Test is holdout.

---

## 3) Fail-fast constraints (Train+Val)
- `trade_count_train >= 150`
- `PF_train >= 1.12`
- `MDD_train <= 30%`

Jika gagal → buang config.

---

## 4) Ranking objective
Gunakan ranking agregat:
score = 0.35*rank(PF) + 0.25*rank(Net_R) - 0.25*rank(MDD) - 0.15*rank(stability_vol)

---

## 5) Robustness suite (Top K)
Top 30 configs:
1) Cost stress: commission x1.25/x1.5 + slippage 1/2 ticks
   - PASS worst stress: PF>=1.05, MDD_stress<=1.5× baseline
2) Regime stability: year + ATR tertile
   - FAIL jika 1 periode >60% Net_R
3) Neighborhood sensitivity: ±1 step params kunci
   - FAIL jika cliff drop ekstrim

---

## 6) Artifacts output
Folder: `artifacts/mining/momentum_v2/`
Wajib:
- run_manifest.json, search_space.json
- results_all.parquet, results_summary.parquet, top_configs.json

Untuk top configs:
- events_{id}.csv
- trades_{id}.csv
- features_{id}.parquet (microstructure snapshot, no leakage)

---

## 7) Notebook + Jesse workflow
Notebook:
- nb00_data_check.ipynb
- nb01_signal_scan_m15.ipynb
- nb02_single_run_debug.ipynb
- nb03_microstructure_features.ipynb

Jesse:
- strategy implements spec v2.0
- mining runner batches walk-forward
- export artifacts sesuai Data Contract

---

## Versioning
- Strategy: Momentum Candle (M15)
- Version: **v2.0**
- Status: **FINAL / Ready to Code**
