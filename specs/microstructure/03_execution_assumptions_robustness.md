# Robustness Checklist and Test Plan — MTF Microstructure System
Version: 1.0
Status: DESTRUCTIVE VALIDATION SPEC

## 1. Principle
Treat the current backtest as untrusted until it survives destructive robustness testing.

## 2. Mandatory Pre-Checks
### Data Integrity
- confirm source start/end
- confirm missing M1 gaps count
- confirm no duplicates
- confirm no zero/negative prices

### Resample Integrity
- H1 features must align only to completed H1 bars
- M15 event bars cannot access partial future H1 state
- signal bar and entry bar must be distinct

### Stop Integrity
- structural stop must use only past bars
- no future-dependent pivot logic

### Trade Accounting Integrity
- verify one-position-at-a-time mode
- verify deterministic opens/closes

## 3. Battery A — Family Isolation
Run independently:
1. sweep_reclaim only
2. rejection only
3. compression_expansion only
4. momentum_break only

Then combinations:
5. sweep + rejection
6. sweep + compression
7. all except momentum_short
8. all families

Pass:
- at least one plausible family survives independently

## 4. Battery B — Session Isolation
Run:
- all
- asia only
- london only
- ny only
- london + ny
- exclude asia

Pass:
- session dependence remains logical and stable

## 5. Battery C — Year Isolation
Run yearly metrics and leave-one-year-out testing.

Pass:
- majority of years positive
- no single year contributes almost all profits

## 6. Battery D — Parameter Perturbation
Required grid:
- TP multiple: 1.5, 2.0, 2.5
- swing_lookback: 2, 3, 4, 5
- rolling_level_n: 10, 20, 30
- timeout_bars: 8, 12, 16, 20
- cooldown: 0, 1, 2
- session filter: all, london, london+ny, no_asia

Pass:
- plateau, not a sharp peak
Fail:
- one exact point works and nearby points die

## 7. Battery E — Adverse Execution
Required:
1. baseline spread 0
2. mild spread shock
3. mild slippage shock
4. one-bar delay
5. worse breakout fill

Pass:
- PF remains > 1.05 under mild degradation

## 8. Battery F — Gap Sensitivity
Required:
1. baseline full data
2. remove events near M1 gaps
3. remove days with large gap clusters
4. compare

Pass:
- conclusions remain directionally similar

## 9. Battery G — Overlap and Clustering
Modes:
1. one-position-at-a-time
2. overlapping allowed
3. one trade per family
4. cooldown 1 bar
5. cooldown 2 bars

Pass:
- strategy remains profitable in one-position-at-a-time mode

## 10. Battery H — Monte Carlo Trade Reordering
Outputs:
- shuffled / bootstrap equity paths
- DD distribution
- losing streak distribution

Note:
- Monte Carlo does not prove the edge, only stress-tests the realized distribution

## 11. Data Snooping Controls
Every run must log:
- exact config
- family set
- session filter
- cost/slippage mode
- split metrics
- yearly metrics
- run id

Do not report only best run. Also report:
- median grid performance
- profitable config count
- count with PF > 1.1

## 12. Credibility Threshold
Research-credible only if:
1. OOS PF > 1.10
2. OOS expectancy > 0
3. at least 3 major years positive
4. family isolation identifies plausible core edge
5. one-position-at-a-time remains profitable
6. mild adverse execution keeps PF > 1.05
7. parameter neighborhood is stable
8. no evidence of HTF leakage or future swing stop

## 13. Required Deliverables
Tables:
- overall
- split
- yearly
- session
- family
- family × year
- family × session

Robustness:
- parameter grid summary
- adverse execution summary
- overlap/cooldown summary
- gap sensitivity summary

Files:
- robustness_runs.csv
- robustness_summary.json
- selected_core_trades.csv
- monte_carlo_summary.json
- experiment_manifest.json

## 14. Execution Order
1. integrity audit
2. family isolation
3. session isolation
4. overlap / cooldown
5. parameter perturbation
6. adverse execution
7. gap sensitivity
8. Monte Carlo
9. select core candidate
10. only then rebuild meta-labeling
