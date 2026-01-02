# 02 – Strategy Spec (Executable) (FINAL v2.0)
## XAUUSD – Momentum Candle (M15) + Optional M5 Alignment (OFF) + Microstructure Snapshot (ML)

Strategi ini dibuat sederhana untuk data mining:
- timeframe utama: **M15**
- signal: **Momentum Candle** (body engulf previous range)
- entry: **next open**
- exit: SL/TP fixed-R (+ optional time stop)

Microstructure (M1/M5) **bukan rule wajib**, hanya disimpan sebagai **feature snapshot** untuk meta-model.

---

## 0) Locked Execution Principles
- Decision pada **close M15** (`t_signal`).
- Entry pada **open M15 berikutnya** (`t_entry = t_signal + 15m`).
- Exit dievaluasi konservatif (SL-first tie).

---

## 1) Parameters (defaults v2.0)
Core (mining-eligible):
- `tp_R = 2.0`
- `sl_buffer_ticks = 0` (tick_size = 0.01)
- `engulf_buffer_ticks = 0`
- `use_quality_filter = true`
- `min_body_pct = 0.60`
- `min_body_atr = 0.0` (0 disables ATR filter)
- `max_hold_m15 = 0` (0 disables time stop)
- `cooldown_m15 = 0`

Optional M5 alignment (OFF by default):
- `m5_align_mode = "NONE"` ∈ {"NONE","CLOSE_DIR","EMA50"}
- `m5_align_lookback = 1`

---

## 2) Deterministic Definitions
Given M15 candle t (signal) and t-1 (previous):

### 2.1 Candle direction
- Bullish: `close_t > open_t`
- Bearish: `close_t < open_t`
- Doji: `close_t == open_t` → NO SIGNAL

### 2.2 Body bounds (signal candle)
- `body_low = min(open_t, close_t)`
- `body_high = max(open_t, close_t)`

### 2.3 Previous range bounds
- `prev_low = low_{t-1}`
- `prev_high = high_{t-1}`

### 2.4 Momentum engulf (CORE)
Body candle t menelan high/low candle sebelumnya:
- `body_low <= prev_low - engulf_buffer_ticks * tick_size`
- `body_high >= prev_high + engulf_buffer_ticks * tick_size`

Tidak ada syarat arah candle t-1.

### 2.5 Quality filter (default ON)
Compute:
- `range_t = high_t - low_t` (must be > 0)
- `body_t = abs(close_t - open_t)`
- `body_pct = body_t / range_t`

If `use_quality_filter`:
- `body_pct >= min_body_pct`
- If `min_body_atr > 0`: `body_t >= min_body_atr * ATR14_M15(t)`

### 2.6 Optional M5 alignment (default OFF)
Ambil M5 terakhir dengan close `<= t_signal`.

Mode:
- NONE: PASS
- CLOSE_DIR:
  - LONG: close_m5 > open_m5
  - SHORT: close_m5 < open_m5
- EMA50:
  - LONG: close_m5 > ema50_m5
  - SHORT: close_m5 < ema50_m5

Jika EMA50 belum warmup → FAIL (konservatif).

---

## 3) Signal Rules
### 3.1 LONG signal
Trigger pada close M15 t jika:
1) bullish candle t
2) momentum engulf true
3) quality filter PASS (if enabled)
4) m5 alignment PASS (if enabled)

### 3.2 SHORT signal
Trigger pada close M15 t jika:
1) bearish candle t
2) momentum engulf true
3) quality filter PASS (if enabled)
4) m5 alignment PASS (if enabled)

Constraints:
- 1 posisi per symbol
- ignore signal bila posisi/pending entry ada
- optional cooldown setelah exit

---

## 4) Entry/SL/TP/Time Stop
Entry:
- `t_entry = open_time(M15 t+1)`
- `entry_price = open_{t+1}`

SL:
- LONG: `sl = low_t - sl_buffer_ticks * tick_size`
- SHORT: `sl = high_t + sl_buffer_ticks * tick_size`

TP (fixed R):
- `risk = abs(entry_price - sl)`; require risk>0
- LONG: `tp = entry_price + tp_R * risk`
- SHORT: `tp = entry_price - tp_R * risk`

Time stop (optional):
- if `max_hold_m15>0`: exit TIME pada open setelah N bar close berlalu sejak entry.

---

## 5) Microstructure Snapshot (for ML, not rule)
At `t_feat = t_signal`, export M1/M5 features per Data Contract.

---

## Versioning
- Strategy: Momentum Candle (M15)
- Version: **v2.0**
- Status: **FINAL**
