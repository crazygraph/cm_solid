# Production Candidate v1 — MTF Microstructure Strategy

Version: 1.0  
Status: Ready for forward-test / broker-cost calibration

## Objective
Build an honest production-candidate from the robustness phase. The goal is not to maximize backtest PF, but to keep the edge as simple and falsifiable as possible.

## Evidence used
- Baseline robustness across all families / all sessions remained profitable in zero-cost assumptions.
- Session isolation showed the strongest PF in `ny_overlap_only` and `london_only`, both around 1.105.
- Event-family isolation did not show one dominant family with both high PF and large sample, but `momentum_break` remained the weakest family and is quarantined.
- Parameter perturbation suggested a reasonably stable plateau around:
  - `tp_r_multiple` 2.0 to 2.5
  - `timeout_bars` 8 to 16
  - `swing_lookback` 2 to 3
- Adverse execution with spread/slippage of 0.1R equivalent destroyed the zero-cost edge. Therefore this production candidate is **backtest-ready and forward-test-ready**, but **not broker-ready until cost calibration is added from real fills / broker spread logs**.

## Production Candidate v1 defaults
- Source timeframe: M1
- Context timeframe: H1
- Signal timeframe: M15
- Execution timeframe: M15
- Position policy: one-position-at-a-time
- Families enabled:
  - `sweep_reclaim`
  - `rejection`
  - `compression_expansion`
- Families disabled:
  - `momentum_break`
- Sessions:
  - `london`
  - `ny_overlap`
- Entry:
  - next-bar open on M15
- Stop:
  - structural backward-only swing stop
  - optional ATR floor / cap controls available but off by default
- Take profit:
  - `2.0R`
- Timeout:
  - `12` bars on M15
- Swing lookback:
  - `2`
- Rolling level:
  - `20`
- Spread:
  - `0` for research baseline only
- Slippage:
  - `0` for research baseline only

## Why these defaults
This candidate intentionally favors:
1. Simplicity
2. Robustness plateau rather than peak
3. Stronger sessions
4. Removal of the weakest family
5. Lower stop lag via swing lookback 2
6. Slightly tighter timeout than the original baseline

## Mandatory warnings
1. Do **not** treat this as live-ready without real broker spread/slippage calibration.
2. Do **not** optimize parameters again before forward-testing.
3. First validation target is forward-test stability, not higher PF.
4. The notebook exports diagnostics that must be reviewed after each run:
   - `metrics.json`
   - `trades.csv`
   - `yearly_metrics.csv`
   - `session_metrics.csv`
   - `family_metrics.csv`
   - `run_manifest.json`

## Promotion criteria to Production Candidate v2
Promote only if:
- forward-test remains profitable after realistic transaction costs
- no single month dominates the full result
- max drawdown remains acceptable under fixed-risk sizing
- M5 confirmation improves results out-of-sample rather than only in-sample
