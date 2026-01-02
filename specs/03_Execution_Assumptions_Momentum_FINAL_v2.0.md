# 03 – Execution Assumptions (FINAL v2.0)
## Momentum Candle (M15) – Conservative Bar-Based Execution

Tujuan: hasil Python/Jesse bisa dibandingkan dengan MT5 secara trade-by-trade.

---

## 0) Market Model (Locked)
- Spread baseline: 0
- Commission: 0.11 USD per 0.01 lot per side
- Slippage baseline: 0 (diuji dalam stress)

Fill:
- Entry: open bar M15 berikutnya
- Exit: bar-based OHLC + tie-breaking konservatif

---

## 1) Ordering (Deterministic)
1) Pada close bar M15 t: deteksi signal → schedule entry di open t+1
2) Pada open bar M15 t+1: execute entry (jika belum ada posisi)
3) Setelah open: pada setiap bar M15 evaluasi exit

---

## 2) SL/TP evaluation & intrabar ambiguity (Conservative)
LONG:
- SL hit jika `low <= sl`
- TP hit jika `high >= tp`
Jika keduanya pada bar yang sama → **SL first**.

SHORT:
- SL hit jika `high >= sl`
- TP hit jika `low <= tp`
Jika keduanya pada bar yang sama → **SL first**.

---

## 3) Gap handling
Jika open bar sudah melewati SL/TP:
- adverse gap ke SL → exit di open (worst-case)
- favorable gap melewati TP → exit di open
Jika open melewati keduanya → exit SL (worst-case).

---

## 4) Time stop (if enabled)
TIME condition dievaluasi pada close bar, exit di open berikutnya.

---

## 5) Commission accounting (per-side)
- Commission dibebankan di entry dan di exit (dua side).
Normalisasi per 1 lot:
- 11 USD per side; 22 USD round-turn.

---

## Versioning
- Strategy: Momentum Candle
- Version: **v2.0**
- Status: **FINAL**
