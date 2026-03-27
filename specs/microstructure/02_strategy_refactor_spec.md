# Strategy Refactor Spec — MTF Microstructure System
Version: 1.0
Status: EXECUTABLE SPEC

## 1. Research Goal
Current result is promising but unverified. This spec defines a modular refactor for destructive robustness testing.

## 2. Data and Timeframes
- Source: M1
- Context TF: H1
- Signal TF: M15
- Optional refinement TF: M5, OFF by default
- Resample must use completed higher-timeframe bars only.
- For an M15 signal at time t, all H1 features must come from H1 bars with close <= t.

## 3. Data Quality Controls
Mandatory:
- duplicate index = 0
- no nonpositive prices
- missing M1 gaps logged
- robustness mode can exclude gap-adjacent events

## 4. Architecture
1. Context Layer (H1)
2. Signal Family Layer (M15)
3. Execution Layer (M15 default)
4. Risk Layer (R-multiple accounting)

## 5. Context Layer (H1)
Features:
- EMA20, EMA50
- EMA20 slope
- ATR / realized volatility
- BB width or vol expansion proxy
- session label

Regimes:
- Bull: EMA20 > EMA50, EMA20 slope > 0, close >= EMA20
- Bear: EMA20 < EMA50, EMA20 slope < 0, close <= EMA20
- Neutral: otherwise

Default:
- Longs only in bull / neutral-bull
- Shorts only in bear / neutral-bear

## 6. Session Layer
Sessions:
- asia
- london
- ny
- ny_overlap

Baseline:
- run all sessions
- then london only
- then london + ny
- then exclude asia

## 7. Signal Families (M15)
### A. Sweep Reclaim (CORE)
Long:
1. low breaks prior rolling low N
2. close reclaims above that level
3. close bullish or in upper half

Short:
1. high breaks prior rolling high N
2. close reclaims below that level
3. close bearish or in lower half

### B. Rejection (RESEARCH)
Long:
1. lower wick >= wick multiple * body
2. close in upper X% of range
3. near rolling low / EMA / reclaim zone

Short:
1. upper wick >= wick multiple * body
2. close in lower X% of range
3. near rolling high / EMA / reclaim zone

### C. Compression Expansion (SECONDARY)
Long:
1. prior vol compressed
2. current bar expands
3. close breaks above local range

Short:
1. prior vol compressed
2. current bar expands
3. close breaks below local range

### D. Momentum Break (SUSPECT)
Keep disabled by default in core runs.

## 8. Family Status
Core:
- sweep_reclaim_long
- sweep_reclaim_short

Research:
- rejection_long
- rejection_short
- compression_expansion_long
- compression_expansion_short

Disabled by default:
- momentum_break_long
- momentum_break_short

## 9. Entry Rules
- Entry at next M15 bar open
- No same-bar entry
- Default concurrency: one-position-at-a-time
- Optional robustness mode: cooldown 0, 1, 2 bars

## 10. Stop Loss Rules
Default structural stop must be backward-looking only.

Long:
- lowest low of prior swing_lookback completed bars before entry

Short:
- highest high of prior swing_lookback completed bars before entry

Forbidden:
- any pivot needing future bars
- symmetric fractal confirmation

Robustness options:
- ATR floor
- ATR cap

## 11. Take Profit Rules
Default:
- TP = 2R

Variants:
- 1.5R
- 2.0R
- 2.5R

## 12. Timeout Rules
Default M15 timeout:
- 16 bars

Variants:
- 8, 12, 16, 20

## 13. Execution Assumptions
- If SL and TP are touched in the same bar, assume SL first
- Gap beyond stop fills at worse stop-side price
- Baseline spread = 0
- Robustness modes add synthetic spread/slippage/delay

## 14. Feature Integrity Rules
- all features backward-looking only
- higher timeframe features only from completed HTF bars
- no target leakage
- no future confirmation unless explicitly delayed and modeled

## 15. Evaluation Hierarchy
Report:
1. overall
2. by split
3. by year
4. by session
5. by family
6. by family × session
7. by family × year

## 16. Metrics
Mandatory:
- total_trades
- win_rate
- profit_factor
- expectancy_r
- avg_r
- median_r
- sum_r
- max_drawdown_r
- max_losing_streak
- avg_holding_bars

## 17. Refactor Milestones
1. Engine integrity
2. Family isolation
3. Combined core candidate
4. Adverse execution
5. Plateau testing

## 18. Decision Rules
Promote to live-candidate research bucket only if:
- OOS PF > 1.10
- survives adverse execution with PF > 1.05
- no evidence of leakage
- acceptable plateau around parameters

Reject or quarantine if:
- edge disappears under small parameter changes
- edge depends on suspect family only
- edge collapses under mild execution stress
