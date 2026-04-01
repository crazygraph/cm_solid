# Quant Research Pipeline & Spesifikasi

## 1. Tujuan
Dokumen ini mendefinisikan pipeline riset untuk menguji strategi open-source TradingView pada XAUUSD dengan pendekatan quant yang konservatif, reproducible, dan siap dipetakan ke MT5. Fokus utamanya adalah memisahkan edge nyata dari ilusi backtest.

## 2. Prinsip Non-Negotiable
- No look-ahead bias
- No data leakage
- Semua rule harus executable
- HTF hanya valid setelah candle HTF close
- Backtest harus bar-by-bar / event-driven
- Intrabar ambiguity diselesaikan konservatif
- SL-first jika SL dan TP tersentuh pada bar yang sama
- Semua run wajib menghasilkan manifest
- Discovery, validation, dan final test harus dipisah
- Satu perubahan asumsi = satu eksperimen baru

## 3. Ruang Lingkup
### Input
- Pine Script open-source dari TradingView
- Data XAUUSD minimal M1, idealnya 5 tahun atau lebih
- Opsional: tick / 1-second / bid-ask / spread historis

### Output
- Executable strategy spec
- Backtest konservatif
- Diagnostic breakdown
- Robustness suite
- Regime-filter integration
- Meta-labeling integration
- MT5 parity mapping
- Decision log: reject / hold / promote

## 4. Pipeline End-to-End

### Phase 0 — Strategy Intake & Triage
Tujuan: menyaring strategi yang layak diteliti.

#### Aktivitas
- Kumpulkan nama, link, author, Pine version
- Simpan source code mentah
- Ringkas logika utama
- Identifikasi indikator, timeframe, dependency, MTF usage
- Periksa red flags:
  - repaint
  - future leak
  - request.security ambiguity
  - visual/discretionary rule
  - pyramiding implicit
  - exit yang tidak executable

#### Keputusan
- Reject
- Proceed with caution
- Proceed

#### Deliverables
- `00_intake.md`
- `pine_source.pine`

---

### Phase 1 — Rule Extraction & Executable Spec
Tujuan: membekukan strategi ke bentuk rule deterministik.

#### Yang harus dibakukan
- Definisi long signal dan short signal
- Kapan signal dianggap valid
- Jenis order: market / stop / limit
- Harga dan waktu entry
- Stop loss
- Take profit
- Timeout
- Cooldown
- Satu posisi atau multi posisi
- Opposite signal handling
- MTF alignment
- Gap handling
- Intrabar ordering

#### Aturan drafting
Semua rule harus ditulis sebagai kondisi boolean atau event eksplisit.
Contoh benar:
- Long signal valid pada close bar t jika A && B && C
- Entry di open bar t+1
- SL di low signal bar dikurangi buffer
- TP = 2R

#### Deliverables
- `01_strategy_spec_executable.md`

---

### Phase 2 — Data Contract & Preprocessing
Tujuan: memastikan semua strategi diuji di basis data yang seragam.

#### Schema minimal
- timestamp_utc
- open
- high
- low
- close
- volume
- spread (opsional)
- symbol

#### Aturan preprocessing
- Sort ascending by timestamp
- Remove duplicates
- Audit missing bars / gap
- Audit outlier candles
- Resample right-closed, right-labeled
- HTF bar hanya tersedia setelah close
- Tidak ada forward fill OHLC

#### Data quality tests
- Duplicate timestamp check
- Missing interval check
- Session coverage check
- Extreme wick / zero range anomaly check
- Volume anomaly check
- Cross-day continuity review

#### Deliverables
- `02_data_contract.md`
- `03_data_quality_report.md`

---

### Phase 3 — Conservative Baseline Backtest
Tujuan: mengukur edge mentah strategi dengan asumsi yang jujur.

#### Asumsi baseline
- Signal dievaluasi hanya pada candle close
- Entry aktif setelah signal confirmed
- Jika SL dan TP tersentuh di bar yang sama: SL-first
- Spread dan commission eksplisit
- Gap stop diisi konservatif
- Tidak ada partial fills kecuali memang dispesifikkan
- Tidak ada pyramiding kecuali rule aslinya jelas
- Single-position mode default, kecuali disebut lain

#### Output minimal
- Trade list lengkap
- Equity curve dalam R
- Monthly metrics
- Yearly metrics
- Manifest run

#### Deliverables
- `04_execution_assumptions.md`
- `trades.csv`
- `metrics.json`
- `monthly_metrics.csv`
- `yearly_metrics.csv`
- `run_manifest.json`

---

### Phase 4 — Diagnostic Decomposition
Tujuan: memahami edge datang dari mana.

#### Breakdown wajib
- Per tahun
- Per kuartal
- Per bulan
- Long vs short
- Per session (Asia / London / NY)
- Per holding period bucket
- Per volatility bucket
- Per regime bucket
- Winner/loser distribution
- MAE / MFE

#### Pertanyaan utama
- Apakah profit hanya datang dari satu periode?
- Apakah hanya long atau hanya short yang bekerja?
- Apakah edge hanya muncul saat high-vol?
- Apakah hasil ditopang sedikit outlier winner?
- Apakah banyak trade jelek terkonsentrasi pada satu session?

#### Deliverables
- `05_diagnostics.md`
- `trades_enriched.csv`
- `regime_metrics.csv`

---

### Phase 5 — Robustness Testing
Tujuan: memisahkan strategi yang stabil dari strategi yang hanya kebetulan cocok.

#### 5.1 Parameter Robustness
Uji sensitivitas parameter inti dengan neighborhood, bukan hanya best point.

Contoh:
- TP: 1.5R / 2R / 2.5R / 3R
- Timeout: 6 / 12 / 18 bar
- Stop lookback: 3 / 5 / 7

Lulus jika performa tidak hanya hidup pada satu kombinasi sempit.

#### 5.2 Execution Robustness
Uji edge terhadap eksekusi yang lebih buruk.

Stress minimal:
- Entry delay +1 bar
- Spread dinaikkan
- Slippage ditambahkan
- TP haircut
- Cancel rule diperketat
- Stop widened / tightened kecil

#### 5.3 Temporal Robustness
Gunakan walk-forward.

Contoh:
- Train 12 bulan
- Validate 3 bulan
- Test 3 bulan
- Rolling forward

#### 5.4 Regime Robustness
Uji performa pada:
- trend up
- trend down
- chop
- expansion
- compression
- high vol vs low vol
- Asia / London / NY

#### 5.5 Trade Sequence Robustness
Gunakan:
- Monte Carlo reshuffle
- Bootstrap expectancy
- Confidence interval untuk drawdown / expectancy / PF

#### 5.6 Cross-Engine Robustness
Bandingkan hasil:
- Pine logic intent
- Python backtest
- MT5 approximation

Bandingkan trade-by-trade, bukan hanya net profit.

#### Deliverables
- `06_robustness_plan.md`
- `stress_results.csv`
- `walkforward_results.csv`
- `parity_report.csv`

---

### Phase 6 — Regime Integration
Tujuan: menguji apakah edge membaik setelah hanya mengambil trade pada state market yang cocok.

#### Regime classes yang disarankan
- Trend Up
- Trend Down
- Chop
- Expansion
- Compression

#### Pendekatan awal
Mulai dari rule-based regime classifier:
- EMA slope
- BB width
- realized volatility percentile
- trend efficiency ratio
- session context

#### Evaluasi
Bandingkan:
- baseline strategy
- baseline + regime filter

#### Deliverables
- `07_regime_design.md`
- `regime_metrics.csv`
- `filtered_vs_unfiltered.csv`

---

### Phase 7 — Meta-Labeling Integration
Tujuan: menjadikan strategi TradingView sebagai base signal engine, lalu ML hanya memutuskan take/skip.

#### Label schema
Gunakan triple barrier:
- upper barrier = TP
- lower barrier = SL
- vertical barrier = timeout

#### Features snapshot
Ambil hanya data yang tersedia saat signal muncul:
- regime state
- volatility percentile
- spread proxy
- wick/body ratios
- sweep strength
- slope HTF
- session
- distance to HTF structure
- compression/expansion state

#### Model baseline
- Logistic Regression
- XGBoost / LightGBM
- Random Forest sebagai baseline pembanding

#### Evaluasi utama
- precision / recall untuk take class
- expectancy setelah filtering
- PF uplift
- trade reduction vs quality improvement

#### Deliverables
- `08_meta_labeling_plan.md`
- `labels.csv`
- `meta_features.csv`
- `meta_results.json`

---

### Phase 8 — MT5 Mapping & Parity
Tujuan: memetakan definisi riset ke implementasi EA tanpa distorsi.

#### Yang harus dipetakan
- Signal evaluation timing
- Pending activation timing
- Fill rule
- SL/TP handling intrabar
- Gap handling
- Order cancellation logic
- Session/day reset logic
- Logging fields

#### Logging minimal di EA
- signal_timestamp
- order_timestamp
- entry_price_expected
- entry_price_filled
- sl_price
- tp_price
- exit_timestamp
- exit_reason
- slippage
- spread
- bar_id / candle reference

#### Deliverables
- `09_mt5_mapping.md`
- `ea_parity_test_cases.md`

---

### Phase 9 — Decision & Promotion
Tujuan: memutuskan status akhir strategi.

#### Status akhir
- Reject
- Hold / continue research
- Promote to candidate

#### Kriteria umum promote
- OOS tetap positif
- Tidak runtuh di stress ringan
- Tidak sangat sensitif pada satu titik parameter
- Mismatch lintas engine kecil atau bisa dijelaskan
- Drawdown masih dalam batas yang diterima

#### Deliverables
- `10_decision_log.md`
- `candidate_promotion_list.md`

## 5. Metrik Penelitian

### 5.1 Core Performance
- total_trades
- win_rate
- gross_profit
- gross_loss
- net_profit
- profit_factor
- expectancy
- expectancy_r
- avg_win
- avg_loss
- payoff_ratio
- median_r
- sum_r

### 5.2 Risk
- max_drawdown_nominal
- max_drawdown_pct
- max_drawdown_r
- average_drawdown
- ulcer_index
- longest_losing_streak
- average_losing_streak
- worst_trade_r
- downside_deviation

### 5.3 Efficiency
- sharpe
- sortino
- calmar
- MAR
- return_over_drawdown
- exposure_time
- average_holding_bars
- capital_efficiency

### 5.4 Stability
- profitable_months_pct
- monthly_hit_rate
- annual_consistency
- rolling_3m_expectancy
- rolling_6m_pf
- regime_stability_score
- parameter_stability_score

### 5.5 Execution Realism
- ambiguous_bar_pct
- gap_exit_pct
- timeout_exit_pct
- delay_sensitivity_slope
- spread_sensitivity_slope
- slippage_sensitivity
- trade_count_drift_vs_reference

### 5.6 Meta-Research Control
- number_of_variants_tested
- number_of_promoted_variants
- train_test_pf_decay
- train_test_expectancy_decay
- selection_bias_warning_count

## 6. Pass/Fail Baseline
Contoh baseline awal yang dapat disesuaikan:
- OOS PF > 1.10
- OOS expectancy_r > 0
- Test sample cukup; jika kecil wajib diberi flag sampel kecil
- Strategy tidak runtuh pada stress ringan
- Tidak bergantung pada satu outlier ekstrem
- Parameter tidak needle-in-a-haystack

## 7. Struktur Folder Rekomendasi
```text
quant_research/
├── README.md
├── configs/
│   ├── research_config.yaml
│   ├── cost_model.yaml
│   ├── stress_tests.yaml
│   └── pass_fail_criteria.yaml
├── data/
│   ├── raw/
│   ├── processed/
│   ├── resampled/
│   └── diagnostics/
├── research/
│   └── strategies/
│       └── <strategy_id>/
│           ├── 00_intake.md
│           ├── pine_source.pine
│           ├── 01_strategy_spec_executable.md
│           ├── 02_data_contract.md
│           ├── 03_data_quality_report.md
│           ├── 04_execution_assumptions.md
│           ├── 05_diagnostics.md
│           ├── 06_robustness_plan.md
│           ├── 07_regime_design.md
│           ├── 08_meta_labeling_plan.md
│           ├── 09_mt5_mapping.md
│           └── 10_decision_log.md
├── notebooks/
│   ├── 00_data_audit.ipynb
│   ├── 01_rule_parsing_and_spec.ipynb
│   ├── 02_baseline_backtest.ipynb
│   ├── 03_diagnostics.ipynb
│   ├── 04_robustness_tests.ipynb
│   ├── 05_walkforward.ipynb
│   ├── 06_regime_filter.ipynb
│   ├── 07_meta_labeling.ipynb
│   └── 08_mt5_parity.ipynb
├── src/
│   ├── loaders/
│   ├── resampling/
│   ├── strategies/
│   ├── execution/
│   ├── metrics/
│   ├── diagnostics/
│   ├── robustness/
│   ├── regimes/
│   ├── labels/
│   └── reports/
└── outputs/
    └── <strategy_id>/<run_id>/
        ├── trades.csv
        ├── trades_enriched.csv
        ├── metrics.json
        ├── monthly_metrics.csv
        ├── yearly_metrics.csv
        ├── regime_metrics.csv
        ├── stress_results.csv
        ├── walkforward_results.csv
        ├── parity_report.csv
        └── run_manifest.json
```

## 8. File Konfigurasi yang Disarankan

### `research_config.yaml`
```yaml
symbol: XAUUSD
base_timeframe: M1
timezone: UTC
initial_capital: 10000
commission_per_0_01_lot: 0.11
default_spread_points: 0
risk_mode: fixed_r
allow_long: true
allow_short: true
single_position_only: true
```

### `cost_model.yaml`
```yaml
spread_mode: fixed
spread_points: 0
slippage_mode: fixed
slippage_points: 0
commission_mode: per_lot
commission_per_0_01_lot: 0.11
gap_stop_mode: conservative
intrabar_tie_break: sl_first
```

### `stress_tests.yaml`
```yaml
tests:
  - name: delay_1_bar
    entry_delay_bars: 1
  - name: spread_plus_10
    spread_points_add: 10
  - name: slippage_plus_5
    slippage_points_add: 5
  - name: tp_haircut_10pct
    tp_multiplier: 0.9
  - name: stricter_cancel
    cancel_if_delay_bar_close_breaches_sl: true
```

### `pass_fail_criteria.yaml`
```yaml
minimum_test_trades: 150
minimum_pf_oos: 1.10
minimum_expectancy_r_oos: 0.0
maximum_dd_r: 50
maximum_train_test_pf_decay_pct: 35
require_positive_stress_median: true
require_parameter_stability: true
```

## 9. Urutan Kerja yang Disarankan
1. Intake 5–10 strategi TradingView
2. Reject cepat strategi bermasalah
3. Buat executable spec untuk kandidat terbaik
4. Jalankan conservative baseline
5. Lakukan diagnostics
6. Jalankan robustness suite
7. Tambahkan regime filter
8. Tambahkan meta-labeling bila base edge masih hidup
9. Bangun parity mapping ke MT5
10. Putuskan reject / hold / promote

## 10. Deliverables Akhir per Strategi
- `00_intake.md`
- `01_strategy_spec_executable.md`
- `03_data_quality_report.md`
- `04_execution_assumptions.md`
- `05_diagnostics.md`
- `06_robustness_plan.md`
- `07_regime_design.md`
- `08_meta_labeling_plan.md`
- `09_mt5_mapping.md`
- `10_decision_log.md`
- `trades.csv`
- `metrics.json`
- `stress_results.csv`
- `walkforward_results.csv`
- `parity_report.csv`

## 11. Definisi Selesai
Sebuah strategi dianggap selesai pada tahap penelitian ini bila:
- Rule sudah executable dan terdokumentasi
- Hasil baseline dapat direproduksi
- Hasil robustness tersedia
- Regime suitability dipahami
- Keputusan akhir terdokumentasi
- Jalur implementasi MT5 sudah jelas
