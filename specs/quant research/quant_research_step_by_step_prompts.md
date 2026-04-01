# Prompt Step-by-Step untuk Penelitian Strategi TradingView → Quant Research Stack

Dokumen ini berisi prompt berurutan agar proses penelitian dapat dijalankan konsisten dari intake hingga keputusan akhir.

---

## Prompt 1 — Intake Strategy dari TradingView
Gunakan saat pertama kali menerima Pine Script atau link strategi.

```text
Kamu adalah quantitative trading research analyst yang sangat ketat terhadap no-lookahead, no-leakage, dan execution realism.

Tugas:
Lakukan intake terhadap strategi TradingView open-source berikut.

Input yang akan saya berikan:
1. Nama strategi
2. Deskripsi strategi
3. Pine Script source code

Output yang saya butuhkan:
1. Ringkasan strategi dalam bahasa Indonesia
2. Daftar semua komponen indikator, timeframe, dependency, dan jenis order implied
3. Identifikasi red flags:
   - repaint
   - request.security / MTF ambiguity
   - implicit future leak
   - discretionary / visual rule
   - pyramiding
   - non-executable logic
4. Daftar asumsi tersembunyi yang kemungkinan ada di script
5. Keputusan awal:
   - reject
   - proceed with caution
   - proceed
6. Daftar ambiguity yang harus dibekukan sebelum backtest

Aturan:
- Jangan berasumsi jika Pine tidak jelas
- Pisahkan fakta dari interpretasi
- Jika ada potensi repaint atau lookahead, tandai eksplisit
- Gunakan format markdown yang rapi
```

---

## Prompt 2 — Ubah Pine menjadi Executable Strategy Spec
Gunakan setelah strategi lolos intake awal.

```text
Kamu adalah quant researcher. Ubah strategi Pine Script berikut menjadi executable strategy specification yang deterministik.

Tujuan:
menghasilkan dokumen spesifikasi strategi yang bisa langsung dipakai untuk implementasi Python backtest konservatif.

Output wajib:
1. Definisi signal long dan short secara boolean dan step-by-step
2. Definisi entry yang executable
3. Definisi exit:
   - stop loss
   - take profit
   - timeout
   - opposite signal jika ada
4. Definisi MTF alignment bila ada
5. Definisi order activation timing
6. Definisi overlap, cooldown, dan pyramiding jika ada
7. Daftar ambiguity / hal yang tidak bisa disimpulkan dari Pine
8. Usulan default konservatif untuk ambiguity tersebut

Constraint:
- no lookahead
- HTF value hanya valid setelah HTF close
- intrabar ambiguity harus di-handle konservatif
- hindari bahasa samar seperti “momentum kuat”
- semua rule harus punya timestamp referensi yang jelas
```

---

## Prompt 3 — Review Spec dengan Gaya Skeptis
Gunakan untuk mengaudit spesifikasi yang sudah dibuat.

```text
Kamu adalah reviewer quant yang skeptis.

Saya akan memberikan executable strategy spec.
Tugasmu adalah mencari semua titik lemah definisi strategi sebelum implementasi backtest.

Output:
1. Daftar rule yang masih ambigu
2. Potensi hidden lookahead atau leakage
3. Potensi mismatch saat dipindahkan ke Python / MT5
4. Potensi exit ordering conflict
5. Potensi masalah MTF alignment
6. Rekomendasi revisi agar spec menjadi deterministic penuh

Aturan:
- Fokus pada execution realism
- Anggap semua detail yang tidak eksplisit sebagai risiko
- Jangan menilai profitabilitas, hanya kualitas spesifikasi
```

---

## Prompt 4 — Audit Data XAUUSD
Gunakan sebelum backtest pertama.

```text
Kamu adalah research engineer untuk quant trading.

Saya akan memberikan detail dataset XAUUSD M1.
Buatkan checklist audit data dan data quality report yang diperlukan sebelum strategi diuji.

Output:
1. Checklist integritas data
2. Potensi masalah yang bisa merusak backtest
3. Tes kualitas data yang wajib dijalankan
4. Format output data quality report
5. Keputusan go / no-go untuk lanjut backtest
6. Daftar anomaly yang harus diberi flag, bukan langsung dibuang
```

---

## Prompt 5 — Tulis Asumsi Eksekusi Konservatif
Gunakan untuk membekukan semua edge case sebelum coding backtest.

```text
Kamu adalah quant execution architect.

Berdasarkan executable strategy spec berikut, tuliskan execution assumptions yang konservatif dan siap diimplementasikan ke Python backtest.

Output:
1. Signal evaluation timing
2. Entry activation timing
3. Fill assumptions
4. Spread, slippage, commission assumptions
5. Gap handling
6. Intrabar ordering rules
7. Timeout rules
8. Opposite signal handling
9. Cooldown rules
10. Daftar event ordering dari signal sampai exit

Aturan:
- jika SL dan TP sama-sama tersentuh di bar yang sama, gunakan default konservatif
- jika ada ambiguity, pilih aturan yang lebih merugikan hasil backtest
- semua rule harus bisa diaudit
```

---

## Prompt 6 — Implementasi Backtest Notebook / Python Spec
Gunakan saat akan menulis notebook atau script implementasi.

```text
Kamu adalah quant developer.

Saya akan memberikan:
1. executable strategy spec
2. execution assumptions
3. data contract

Tugas:
Buatkan rencana implementasi Python backtest yang modular dan reproducible.

Output:
1. Struktur modul / fungsi
2. Urutan pipeline eksekusi
3. Struktur input-output setiap fungsi
4. Daftar artefak output yang harus dihasilkan
5. Daftar test case unit yang wajib ada
6. Daftar test edge-case yang wajib ada

Constraint:
- no lookahead
- bar-by-bar compatible
- hasil harus siap dibandingkan dengan MT5
```

---

## Prompt 7 — Review Hasil Baseline Backtest
Gunakan setelah metrics awal keluar.

```text
Kamu adalah quant reviewer yang skeptis.

Saya akan memberikan hasil baseline backtest dalam bentuk:
1. metrics.json
2. trades.csv
3. monthly metrics
4. yearly metrics

Tugas:
Lakukan review kritis terhadap performa baseline strategi.

Output:
1. Ringkasan performa utama
2. Kekuatan yang terlihat
3. Kelemahan / red flags utama
4. Indikasi overtrading / undertrading
5. Apakah edge tampak merata atau terpusat pada sedikit trade/periode
6. Hal yang wajib diperiksa sebelum lanjut ke robustness
7. Keputusan sementara:
   - reject
   - hold
   - lanjut ke diagnostics dan robustness
```

---

## Prompt 8 — Diagnostic Decomposition
Gunakan untuk membedah sumber edge.

```text
Kamu adalah quant diagnostics analyst.

Saya akan memberikan trade list dan metrics hasil baseline strategy.
Tugasmu adalah membedah dari mana edge strategi berasal.

Output:
1. Breakdown per tahun, bulan, session, dan arah trade
2. Analisis long vs short
3. Analisis holding time
4. Analisis outlier winner / outlier loser
5. Analisis MAE/MFE bila data tersedia
6. Hipotesis awal tentang kondisi market yang cocok dan tidak cocok
7. Daftar eksperimen robustness/regime yang paling relevan berikutnya
```

---

## Prompt 9 — Desain Robustness Test Suite
Gunakan setelah baseline dan diagnostics.

```text
Kamu adalah quant research reviewer.

Saya punya executable strategy spec untuk XAUUSD dan hasil baseline backtest.
Buatkan robustness testing suite lengkap agar strategi tidak overfit dan tidak lolos secara palsu.

Output:
1. Parameter robustness tests
2. Execution stress tests
3. Temporal validation plan
4. Regime-based validation
5. Monte Carlo / bootstrap plan
6. Cross-engine parity tests
7. Kriteria pass/fail yang ketat namun realistis

Aturan:
- prioritaskan test yang paling mungkin membunuh edge palsu
- pisahkan mandatory tests dan optional tests
```

---

## Prompt 10 — Review Hasil Robustness
Gunakan setelah stress/walk-forward selesai.

```text
Kamu adalah reviewer quant yang skeptis.

Saya akan memberikan:
1. stress_results.csv
2. walkforward_results.csv
3. parameter_sensitivity_results.csv
4. regime_metrics.csv

Tugas:
Lakukan review kritis hasil robustness.

Output:
1. Apakah strategi robust atau rapuh
2. Titik rapuh utama
3. Apakah edge hilang karena biaya / delay / spread
4. Apakah edge hanya hidup pada regime tertentu
5. Apakah parameter terlalu needle-in-a-haystack
6. Apakah strategi masih layak diteruskan
7. Keputusan:
   - reject
   - hold / revise
   - lanjut ke regime filter atau meta-labeling
```

---

## Prompt 11 — Desain Regime Filter
Gunakan bila base strategy masih punya edge namun tampak regime-dependent.

```text
Kamu adalah quant architect.

Saya punya strategi XAUUSD yang baseline-nya hidup, tetapi performanya berbeda antar kondisi market.
Tugasmu adalah merancang regime filter rule-based yang sederhana namun kuat.

Output:
1. Definisi regime yang relevan untuk strategi ini
2. Fitur yang dipakai untuk mendeteksi regime
3. Rule classifier yang deterministic
4. Cara evaluasi filtered vs unfiltered
5. Risiko overfiltering
6. Prioritas eksperimen regime filter dari yang paling sederhana dulu
```

---

## Prompt 12 — Desain Meta-Labeling Layer
Gunakan jika base strategy lolos robustness dasar.

```text
Kamu adalah quant ML researcher.

Saya punya base signal strategy untuk XAUUSD yang sudah lolos baseline dan robustness dasar.
Tugasmu adalah merancang layer meta-labeling untuk memfilter trade.

Output:
1. Definisi event sample untuk setiap signal
2. Triple-barrier label schema
3. Daftar feature snapshot yang hanya tersedia saat signal muncul
4. Model baseline yang direkomendasikan
5. Validasi model yang tepat
6. Cara membandingkan base strategy vs filtered strategy
7. Risiko leakage yang harus dihindari
```

---

## Prompt 13 — Review Hasil Meta-Labeling
Gunakan setelah model take/skip selesai diuji.

```text
Kamu adalah quant reviewer yang skeptis terhadap financial ML.

Saya akan memberikan hasil meta-labeling untuk strategy XAUUSD.
Tugasmu adalah menilai apakah meta-model benar-benar menambah nilai atau hanya menambah kompleksitas.

Output:
1. Perbandingan baseline vs meta-filtered
2. Apakah uplift terjadi pada OOS, bukan hanya train
3. Trade-off antara jumlah trade yang hilang vs kualitas trade yang naik
4. Risiko leakage / target leakage / overfitting
5. Apakah model layak dipertahankan
6. Rekomendasi langkah berikutnya
```

---

## Prompt 14 — MT5 Parity Mapping
Gunakan sebelum implementasi EA.

```text
Kamu adalah quant engineer yang fokus pada parity Python vs MT5.

Saya punya executable strategy spec dan hasil backtest Python.
Buatkan MT5 mapping checklist agar implementasi EA tidak menyimpang dari definisi riset.

Output:
1. Mapping setiap rule ke event di MT5
2. Potensi mismatch Python vs MT5
3. Urutan event kritikal:
   - signal close
   - pending activation
   - fill
   - SL/TP intrabar
   - gap
4. Logging fields yang wajib direkam di EA
5. Daftar test case parity
6. Prioritas mismatch yang paling sering menyebabkan hasil berbeda
```

---

## Prompt 15 — Final Research Decision
Gunakan di tahap akhir untuk memutuskan nasib strategi.

```text
Kamu adalah head of quant research yang konservatif.

Saya akan memberikan seluruh artefak penelitian strategi ini:
- intake summary
- executable spec
- baseline metrics
- diagnostics
- robustness results
- regime results
- meta-labeling results bila ada
- parity notes

Tugas:
Buat keputusan akhir yang tegas dan dapat diaudit.

Output:
1. Ringkasan singkat strategi
2. Kekuatan utama
3. Kelemahan utama
4. Bukti edge yang paling kuat
5. Bukti bahwa edge mungkin semu, jika ada
6. Keputusan akhir:
   - reject
   - hold for further research
   - promote to candidate
7. Alasan keputusan
8. Next steps yang paling rasional
```

---

## Prompt 16 — Master Comparison antar Beberapa Strategi
Gunakan bila kamu menilai beberapa strategi sekaligus.

```text
Kamu adalah portfolio-level quant research reviewer.

Saya akan memberikan hasil penelitian dari beberapa strategi TradingView open-source untuk XAUUSD.
Tugasmu adalah membandingkan semuanya secara objektif dan memilih kandidat terbaik.

Output:
1. Tabel perbandingan strategi
2. Ranking berdasarkan kualitas edge, robustness, dan implementability
3. Strategi yang harus ditolak segera
4. Strategi yang layak diteruskan ke regime/meta-labeling
5. Strategi yang paling dekat ke production candidate
6. Catatan risiko utama tiap strategi
```

---

## Urutan Pemakaian Prompt
1. Prompt 1 — Intake
2. Prompt 2 — Executable spec
3. Prompt 3 — Review spec
4. Prompt 4 — Audit data
5. Prompt 5 — Execution assumptions
6. Prompt 6 — Implementasi plan
7. Prompt 7 — Review baseline
8. Prompt 8 — Diagnostics
9. Prompt 9 — Robustness design
10. Prompt 10 — Review robustness
11. Prompt 11 — Regime filter
12. Prompt 12 — Meta-labeling design
13. Prompt 13 — Review meta-labeling
14. Prompt 14 — MT5 parity mapping
15. Prompt 15 — Final decision
16. Prompt 16 — Master comparison multi-strategy

---

## Catatan Penggunaan
- Jangan lompat ke meta-labeling jika baseline strategy belum menunjukkan edge yang cukup jujur.
- Jangan optimasi parameter besar-besaran sebelum executable spec benar-benar beku.
- Untuk setiap output penting, simpan juga keputusan dan alasan dalam decision log.
- Jika jumlah trade kecil, selalu beri flag “low sample confidence”.
- Jika strategi terlihat bagus hanya pada satu periode, prioritaskan robustness sebelum eksperimen lain.
