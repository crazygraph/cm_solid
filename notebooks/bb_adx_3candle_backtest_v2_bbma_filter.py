"""
# BB-ADX 3-Candle Continuation M5 — Notebook v2 (BBMA OA Trend Filter + Data Mining)

Versi ini menambahkan:
- filter trend berbasis konsep BBMA/OA,
- EMA50, BB mid, LWMA 5/10 high-low,
- analytics tambahan,
- data mining RR 1R–4R,
- grid filter BBMA trend,
- cache per-stage dan per-grid agar tidak komputasi ulang.
"""


"""
## 1. Imports
"""


import os
import json
import math
import hashlib
import itertools
from dataclasses import dataclass, asdict, replace
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


"""
## 2. Config
"""


DATA_PATH = Path("/path/to/XAUUSD_M1.csv")   # ganti ke path Anda
OUTPUT_DIR = Path("./bb_adx_3candle_runs_v2")
CACHE_DIR = OUTPUT_DIR / "cache"
RUN_NAME = "xauusd_m5_bb_adx_3candle_v2"

@dataclass(frozen=True)
class StrategyConfig:
    symbol: str = "XAUUSD"
    source_tf: str = "M1"
    trade_tf: str = "5min"
    timezone: str = "UTC"

    bb_length: int = 20
    bb_stddev: float = 2.0
    adx_length: int = 14
    ema_length: int = 50

    rr_multiple: float = 2.0
    use_adx_three_step_rise: bool = True
    adx_threshold: Optional[float] = None

    trend_filter_mode: str = "none"
    # valid values:
    # none, ema50, bbmid_ema50, bbma_basic, bbma_strict, bbma_strict_expand

    one_position_only: bool = True
    sl_tie_priority: str = "SL_FIRST"
    gap_entry_policy: str = "CANCEL_INVALID_GEOMETRY"
    gap_stop_enabled: bool = True

CFG = StrategyConfig()

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

print(CFG)


"""
## 3. Loader
"""


def load_ohlcv(path: str) -> pd.DataFrame:
    names = ['date', 'time', 'open', 'high', 'low', 'close', 'volume']
    df = pd.read_csv(path, header=None, names=names, dtype={'date': str, 'time': str}, skiprows=1)
    df['timestamp'] = pd.to_datetime(df['date'] + ' ' + df['time'], format='%Y.%m.%d %H:%M', utc=True)
    df = df.drop(columns=['date', 'time']).sort_values('timestamp').reset_index(drop=True)
    return df.set_index('timestamp')

def resample_ohlcv(df_m1: pd.DataFrame, tf: str) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    return df_m1.resample(tf, closed="right", label="right").agg(agg).dropna()


"""
## 4. Utilities
"""


def stable_json_hash(obj: Dict[str, Any]) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return hashlib.md5(payload).hexdigest()

def file_fingerprint(path: Path) -> Dict[str, Any]:
    st = path.stat()
    return {"path": str(path.resolve()), "size": st.st_size, "mtime_ns": st.st_mtime_ns}

def build_cache_key(data_path: Path, cfg: StrategyConfig, stage: str, extra: Optional[Dict[str, Any]] = None) -> str:
    payload = {"stage": stage, "file": file_fingerprint(data_path), "cfg": asdict(cfg), "extra": extra or {}}
    return stable_json_hash(payload)

def cache_path(data_path: Path, cfg: StrategyConfig, stage: str, ext: str = ".pkl", extra: Optional[Dict[str, Any]] = None) -> Path:
    key = build_cache_key(data_path, cfg, stage, extra=extra)
    return CACHE_DIR / f"{stage}_{key}{ext}"

def validate_ohlcv(df: pd.DataFrame, expected_freq: Optional[str] = None) -> Dict[str, Any]:
    assert isinstance(df.index, pd.DatetimeIndex), "index harus DatetimeIndex"
    assert df.index.is_monotonic_increasing, "timestamp harus ascending"
    assert not df.index.has_duplicates, "duplicate timestamp terdeteksi"
    required = ["open", "high", "low", "close", "volume"]
    missing_cols = [c for c in required if c not in df.columns]
    assert not missing_cols, f"missing columns: {missing_cols}"
    assert df[["open", "high", "low", "close"]].notna().all().all(), "OHLC mengandung NaN"
    assert (df["high"] >= df[["open", "close"]].max(axis=1)).all(), "high < max(open, close)"
    assert (df["low"] <= df[["open", "close"]].min(axis=1)).all(), "low > min(open, close)"
    assert (df["high"] >= df["low"]).all(), "high < low"
    out = {"rows": int(len(df)), "start": str(df.index.min()), "end": str(df.index.max())}
    if expected_freq is not None and len(df) >= 3:
        diffs = pd.Series(df.index[1:] - df.index[:-1])
        out["all_deltas_match_expected"] = bool((diffs == pd.Timedelta(expected_freq)).all())
    return out

def save_pickle(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.to_pickle(obj, path)

def load_pickle(path: Path) -> Any:
    return pd.read_pickle(path)


"""
## 5. Cached raw/resampled pipeline
"""


def get_m1_data(data_path: Path, cfg: StrategyConfig) -> pd.DataFrame:
    stage = "m1_raw"
    cp = cache_path(data_path, cfg, stage)
    if cp.exists():
        print(f"[cache hit] {stage}: {cp.name}")
        return load_pickle(cp)
    print(f"[build] {stage}")
    df_m1 = load_ohlcv(str(data_path))
    validate_ohlcv(df_m1, expected_freq="1min")
    save_pickle(df_m1, cp)
    return df_m1

def get_m5_data(data_path: Path, cfg: StrategyConfig) -> pd.DataFrame:
    stage = "m5_resampled"
    cp = cache_path(data_path, cfg, stage)
    if cp.exists():
        print(f"[cache hit] {stage}: {cp.name}")
        return load_pickle(cp)
    print(f"[build] {stage}")
    df_m1 = get_m1_data(data_path, cfg)
    df_m5 = resample_ohlcv(df_m1, cfg.trade_tf)
    validate_ohlcv(df_m5, expected_freq="5min")
    save_pickle(df_m5, cp)
    return df_m5


"""
## 6. Indicators (BB, EMA50, LWMA 5/10 hi-low, ADX)
"""


def lwma(series: pd.Series, length: int) -> pd.Series:
    weights = np.arange(1, length + 1, dtype=float)
    return series.rolling(length, min_periods=length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def compute_bollinger(close: pd.Series, length: int, stddev: float) -> pd.DataFrame:
    mid = close.rolling(length, min_periods=length).mean()
    sd = close.rolling(length, min_periods=length).std(ddof=0)
    upper = mid + stddev * sd
    lower = mid - stddev * sd
    width = upper - lower
    return pd.DataFrame({"bb_mid": mid, "bb_upper": upper, "bb_lower": lower, "bb_width": width}, index=close.index)

def compute_ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False, min_periods=length).mean()

def compute_adx(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high = df["high"]; low = df["low"]; close = df["close"]
    prev_high = high.shift(1); prev_low = low.shift(1); prev_close = close.shift(1)
    up_move = high - prev_high
    down_move = prev_low - low
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    tr_components = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1)
    tr = tr_components.max(axis=1)
    atr = tr.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    plus_dm_sm = plus_dm.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    minus_dm_sm = minus_dm.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    plus_di = 100 * (plus_dm_sm / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm_sm / atr.replace(0, np.nan))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    return adx.rename("adx_14")

def get_feature_data(data_path: Path, cfg: StrategyConfig) -> pd.DataFrame:
    stage = "m5_features_v2"
    cp = cache_path(data_path, cfg, stage)
    if cp.exists():
        print(f"[cache hit] {stage}: {cp.name}")
        return load_pickle(cp)
    print(f"[build] {stage}")
    df = get_m5_data(data_path, cfg).copy()
    bb = compute_bollinger(df["close"], cfg.bb_length, cfg.bb_stddev)
    ema50 = compute_ema(df["close"], cfg.ema_length).rename("ema50")
    adx = compute_adx(df, cfg.adx_length)
    ma5_high = lwma(df["high"], 5).rename("ma5_high")
    ma10_high = lwma(df["high"], 10).rename("ma10_high")
    ma5_low = lwma(df["low"], 5).rename("ma5_low")
    ma10_low = lwma(df["low"], 10).rename("ma10_low")
    df = pd.concat([df, bb, ema50, adx, ma5_high, ma10_high, ma5_low, ma10_low], axis=1)
    df["candle_dir"] = np.sign(df["close"] - df["open"]).astype("int8")
    save_pickle(df, cp)
    return df


"""
## 7. Operationalisasi trend filter BBMA/OA
"""


def add_bbma_trend_filters(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["bb_expanding"] = out["bb_width"] > out["bb_width"].shift(1)
    out["bull_ema50"] = out["close"] > out["ema50"]
    out["bear_ema50"] = out["close"] < out["ema50"]
    out["bull_bbmid_ema50"] = (out["close"] > out["bb_mid"]) & (out["bb_mid"] > out["ema50"])
    out["bear_bbmid_ema50"] = (out["close"] < out["bb_mid"]) & (out["bb_mid"] < out["ema50"])
    out["bull_bbma_basic"] = (
        (out["ma5_low"] > out["bb_mid"]) &
        (out["ma10_low"] > out["bb_mid"]) &
        (out["bb_mid"] > out["ema50"])
    )
    out["bear_bbma_basic"] = (
        (out["ma5_high"] < out["bb_mid"]) &
        (out["ma10_high"] < out["bb_mid"]) &
        (out["bb_mid"] < out["ema50"])
    )
    out["bull_bbma_strict"] = out["bull_bbma_basic"] & (out["ma5_low"] >= out["ma10_low"])
    out["bear_bbma_strict"] = out["bear_bbma_basic"] & (out["ma5_high"] <= out["ma10_high"])
    out["bull_bbma_strict_expand"] = out["bull_bbma_strict"] & out["bb_expanding"]
    out["bear_bbma_strict_expand"] = out["bear_bbma_strict"] & out["bb_expanding"]
    return out

def pick_trend_masks(df: pd.DataFrame, mode: str) -> Tuple[pd.Series, pd.Series]:
    if mode == "none":
        return pd.Series(True, index=df.index), pd.Series(True, index=df.index)
    if mode == "ema50":
        return df["bull_ema50"], df["bear_ema50"]
    if mode == "bbmid_ema50":
        return df["bull_bbmid_ema50"], df["bear_bbmid_ema50"]
    if mode == "bbma_basic":
        return df["bull_bbma_basic"], df["bear_bbma_basic"]
    if mode == "bbma_strict":
        return df["bull_bbma_strict"], df["bear_bbma_strict"]
    if mode == "bbma_strict_expand":
        return df["bull_bbma_strict_expand"], df["bear_bbma_strict_expand"]
    raise ValueError(f"unknown trend_filter_mode: {mode}")


"""
## 8. Signal generation v2
"""


def generate_signals(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    out = add_bbma_trend_filters(df)
    c1_close = out["close"].shift(2)
    c1_bb_upper = out["bb_upper"].shift(2)
    c1_bb_lower = out["bb_lower"].shift(2)
    c2_open = out["open"].shift(1)
    c2_close = out["close"].shift(1)
    c3_open = out["open"]
    c3_close = out["close"]
    adx_c1 = out["adx_14"].shift(2)
    adx_c2 = out["adx_14"].shift(1)
    adx_c3 = out["adx_14"]
    adx_rising = (adx_c3 > adx_c2) & (adx_c2 > adx_c1)
    if cfg.adx_threshold is not None:
        adx_rising = adx_rising & (adx_c3 >= cfg.adx_threshold)
    base_long = (
        (c1_close > c1_bb_upper) &
        (c2_close < c2_open) &
        (c3_close > c3_open) &
        (c3_close > c2_open) &
        adx_rising
    )
    base_short = (
        (c1_close < c1_bb_lower) &
        (c2_close > c2_open) &
        (c3_close < c3_open) &
        (c3_close < c2_open) &
        adx_rising
    )
    bull_mask, bear_mask = pick_trend_masks(out, cfg.trend_filter_mode)
    out["long_signal"] = (base_long & bull_mask).fillna(False)
    out["short_signal"] = (base_short & bear_mask).fillna(False)
    out["long_sl_candidate"] = np.minimum(out["low"].shift(1), out["low"])
    out["short_sl_candidate"] = np.maximum(out["high"].shift(1), out["high"])
    out["signal_tag"] = np.select([out["long_signal"], out["short_signal"]], ["LONG", "SHORT"], default="")
    return out

def get_signal_data(data_path: Path, cfg: StrategyConfig) -> pd.DataFrame:
    stage = "m5_signals_v2"
    cp = cache_path(data_path, cfg, stage)
    if cp.exists():
        print(f"[cache hit] {stage}: {cp.name}")
        return load_pickle(cp)
    print(f"[build] {stage}")
    df = get_feature_data(data_path, cfg)
    df = generate_signals(df, cfg)
    save_pickle(df, cp)
    return df


"""
## 9. Backtest engine
"""


def summarize_metrics(trades: pd.DataFrame) -> Dict[str, Any]:
    if trades.empty:
        return {"total_trades": 0, "win_rate": np.nan, "profit_factor": np.nan, "expectancy_r": np.nan, "avg_r": np.nan, "median_r": np.nan, "sum_r": 0.0, "max_drawdown_r": 0.0, "max_losing_streak": 0, "avg_holding_bars": np.nan}
    r = trades["net_r"].astype(float)
    wins = r[r > 0]
    losses = r[r < 0]
    equity = r.cumsum()
    dd = equity - equity.cummax()
    max_ls = 0; cur_ls = 0
    for val in r:
        if val < 0:
            cur_ls += 1; max_ls = max(max_ls, cur_ls)
        else:
            cur_ls = 0
    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else np.inf
    return {"total_trades": int(len(trades)), "win_rate": float((r > 0).mean()), "profit_factor": float(pf), "expectancy_r": float(r.mean()), "avg_r": float(r.mean()), "median_r": float(r.median()), "sum_r": float(r.sum()), "max_drawdown_r": float(dd.min()), "max_losing_streak": int(max_ls), "avg_holding_bars": float(trades["holding_bars"].mean())}

def backtest_bb_adx_3candle(df: pd.DataFrame, cfg: StrategyConfig) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    records = []
    position = None
    trade_id = 0
    timestamps = df.index
    n = len(df)
    for i in range(n - 1):
        row = df.iloc[i]
        if position is not None:
            cur = row
            side = position["side"]
            exit_reason = None; exit_price = None
            if side == "LONG":
                if cfg.gap_stop_enabled and cur["open"] <= position["sl"]:
                    exit_reason = "GAP_STOP"; exit_price = float(cur["open"])
                else:
                    hit_sl = cur["low"] <= position["sl"]
                    hit_tp = cur["high"] >= position["tp"]
                    if hit_sl and hit_tp:
                        exit_reason = "SL_TIE_FIRST"; exit_price = float(position["sl"])
                    elif hit_sl:
                        exit_reason = "STOP_LOSS"; exit_price = float(position["sl"])
                    elif hit_tp:
                        exit_reason = "TAKE_PROFIT"; exit_price = float(position["tp"])
                if exit_reason is not None:
                    risk = position["entry_price"] - position["sl"]
                    gross_r = (exit_price - position["entry_price"]) / risk if risk > 0 else np.nan
            else:
                if cfg.gap_stop_enabled and cur["open"] >= position["sl"]:
                    exit_reason = "GAP_STOP"; exit_price = float(cur["open"])
                else:
                    hit_sl = cur["high"] >= position["sl"]
                    hit_tp = cur["low"] <= position["tp"]
                    if hit_sl and hit_tp:
                        exit_reason = "SL_TIE_FIRST"; exit_price = float(position["sl"])
                    elif hit_sl:
                        exit_reason = "STOP_LOSS"; exit_price = float(position["sl"])
                    elif hit_tp:
                        exit_reason = "TAKE_PROFIT"; exit_price = float(position["tp"])
                if exit_reason is not None:
                    risk = position["sl"] - position["entry_price"]
                    gross_r = (position["entry_price"] - exit_price) / risk if risk > 0 else np.nan
            if exit_reason is not None:
                records.append({"trade_id": position["trade_id"], "symbol": cfg.symbol, "side": position["side"], "signal_bar_index": position["signal_bar_index"], "signal_bar_time": position["signal_bar_time"], "entry_bar_index": position["entry_bar_index"], "entry_bar_time": position["entry_bar_time"], "entry_price": position["entry_price"], "sl_price": position["sl"], "tp_price": position["tp"], "exit_bar_index": i, "exit_bar_time": timestamps[i], "exit_price": exit_price, "exit_reason": exit_reason, "risk_r": 1.0, "gross_r": float(gross_r), "net_r": float(gross_r), "holding_bars": i - position["entry_bar_index"] + 1})
                position = None
        if position is None and i + 1 < n:
            next_open = float(df["open"].iloc[i + 1])
            signal_time = timestamps[i]
            if bool(row["long_signal"]):
                sl = float(row["long_sl_candidate"])
                if next_open > sl:
                    risk = next_open - sl
                    tp = next_open + cfg.rr_multiple * risk
                    trade_id += 1
                    position = {"trade_id": trade_id, "side": "LONG", "signal_bar_index": i, "signal_bar_time": signal_time, "entry_bar_index": i + 1, "entry_bar_time": timestamps[i + 1], "entry_price": next_open, "sl": sl, "tp": tp}
            elif bool(row["short_signal"]):
                sl = float(row["short_sl_candidate"])
                if next_open < sl:
                    risk = sl - next_open
                    tp = next_open - cfg.rr_multiple * risk
                    trade_id += 1
                    position = {"trade_id": trade_id, "side": "SHORT", "signal_bar_index": i, "signal_bar_time": signal_time, "entry_bar_index": i + 1, "entry_bar_time": timestamps[i + 1], "entry_price": next_open, "sl": sl, "tp": tp}
    trades = pd.DataFrame(records)
    return trades, summarize_metrics(trades)


"""
## 10. Analytics helpers
"""


def enrich_trade_time_columns(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    out = trades.copy()
    out["signal_bar_time"] = pd.to_datetime(out["signal_bar_time"], utc=True)
    out["entry_bar_time"] = pd.to_datetime(out["entry_bar_time"], utc=True)
    out["exit_bar_time"] = pd.to_datetime(out["exit_bar_time"], utc=True)
    out["entry_year"] = out["entry_bar_time"].dt.year
    out["entry_month"] = out["entry_bar_time"].dt.to_period("M").astype(str)
    out["entry_hour_utc"] = out["entry_bar_time"].dt.hour
    return out

def build_breakdowns(trades: pd.DataFrame):
    t = enrich_trade_time_columns(trades)
    if t.empty:
        empty = pd.DataFrame()
        return {"by_side": empty, "by_year": empty, "by_hour_utc": empty, "by_month": empty}
    by_side = pd.DataFrame([{**summarize_metrics(g), "side": side} for side, g in t.groupby("side")]).sort_values("side")
    by_year = pd.DataFrame([{**summarize_metrics(g), "entry_year": int(yr)} for yr, g in t.groupby("entry_year")]).sort_values("entry_year")
    by_hour = pd.DataFrame([{**summarize_metrics(g), "entry_hour_utc": int(hr)} for hr, g in t.groupby("entry_hour_utc")]).sort_values("entry_hour_utc")
    by_month = t.groupby("entry_month")["net_r"].agg(["sum", "count", "mean"]).reset_index()
    by_month.columns = ["entry_month", "sum_r", "trade_count", "avg_r"]
    return {"by_side": by_side, "by_year": by_year, "by_hour_utc": by_hour, "by_month": by_month}

def plot_equity_and_monthly(trades: pd.DataFrame) -> None:
    if trades.empty:
        print("Tidak ada trade untuk diplot.")
        return
    t = trades.copy()
    t["exit_bar_time"] = pd.to_datetime(t["exit_bar_time"], utc=True)
    t = t.sort_values("exit_bar_time").reset_index(drop=True)
    t["equity_r"] = t["net_r"].cumsum()
    plt.figure(figsize=(12, 5))
    plt.plot(t["exit_bar_time"], t["equity_r"])
    plt.title("Equity Curve (R)")
    plt.xlabel("Exit Time"); plt.ylabel("Cumulative R"); plt.grid(True); plt.show()
    monthly = t.set_index("exit_bar_time")["net_r"].resample("M").sum()
    plt.figure(figsize=(14, 5))
    monthly.plot(kind="bar")
    plt.title("Monthly Net R")
    plt.xlabel("Month"); plt.ylabel("Net R")
    plt.xticks(rotation=45, ha="right")
    plt.grid(True, axis="y"); plt.tight_layout(); plt.show()


"""
## 11. Single run baseline v2
"""


cfg_single = replace(CFG, trend_filter_mode="bbma_basic", rr_multiple=2.0, adx_threshold=20.0)
df_signal = get_signal_data(DATA_PATH, cfg_single)
print(df_signal[["long_signal", "short_signal"]].sum())
trades, metrics = backtest_bb_adx_3candle(df_signal, cfg_single)
print(json.dumps(metrics, indent=2))
breakdowns = build_breakdowns(trades)
print("\nBy side:"); print(breakdowns["by_side"])
print("\nBy year:"); print(breakdowns["by_year"])
print("\nBy hour UTC:"); print(breakdowns["by_hour_utc"].head())
plot_equity_and_monthly(trades)


"""
## 12. Export single run
"""


def export_run_artifacts(run_name: str, cfg: StrategyConfig, trades: pd.DataFrame, metrics: Dict[str, Any], breakdowns) -> Path:
    run_dir = OUTPUT_DIR / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(run_dir / "trades.csv", index=False)
    with open(run_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, default=str)
    manifest = {"strategy_name": "BB-ADX 3-Candle Continuation M5 v2", "cfg": asdict(cfg), "data_path": str(DATA_PATH), "data_file_fingerprint": file_fingerprint(DATA_PATH), "notes": "v2 with BBMA OA trend filters and grid mining"}
    with open(run_dir / "run_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    for name, df_part in breakdowns.items():
        df_part.to_csv(run_dir / f"{name}.csv", index=False)
    return run_dir

single_run_dir = export_run_artifacts("single_run_bbma_basic_rr2", cfg_single, trades, metrics, breakdowns)
print(single_run_dir.resolve())


"""
## 13. Data mining grid
"""


RR_GRID = [1.0, 2.0, 3.0, 4.0]
ADX_THRESHOLD_GRID = [None, 20.0, 25.0]
TREND_FILTER_GRID = ["none", "ema50", "bbmid_ema50", "bbma_basic", "bbma_strict", "bbma_strict_expand"]

grid_rows = []
for rr, adx_thr, trend_mode in itertools.product(RR_GRID, ADX_THRESHOLD_GRID, TREND_FILTER_GRID):
    cfg_i = replace(CFG, rr_multiple=rr, adx_threshold=adx_thr, trend_filter_mode=trend_mode)
    df_i = get_signal_data(DATA_PATH, cfg_i)
    trades_i, metrics_i = backtest_bb_adx_3candle(df_i, cfg_i)
    grid_rows.append({"rr_multiple": rr, "adx_threshold": adx_thr, "trend_filter_mode": trend_mode, **metrics_i})

results = pd.DataFrame(grid_rows).sort_values(by=["profit_factor", "expectancy_r", "sum_r", "total_trades"], ascending=[False, False, False, False]).reset_index(drop=True)
results.head(20)


"""
## 14. Export ranking grid
"""


grid_dir = OUTPUT_DIR / "grid_search"
grid_dir.mkdir(parents=True, exist_ok=True)
results.to_csv(grid_dir / "grid_ranking.csv", index=False)
results.head(10).to_csv(grid_dir / "top_10_configs.csv", index=False)
print((grid_dir / "grid_ranking.csv").resolve())
print((grid_dir / "top_10_configs.csv").resolve())
results.head(10)


"""
## 15. Deep dive top config
"""


best = results.iloc[0].to_dict()
print(best)
cfg_best = replace(CFG, rr_multiple=float(best["rr_multiple"]), adx_threshold=None if pd.isna(best["adx_threshold"]) else float(best["adx_threshold"]), trend_filter_mode=str(best["trend_filter_mode"]))
df_best = get_signal_data(DATA_PATH, cfg_best)
trades_best, metrics_best = backtest_bb_adx_3candle(df_best, cfg_best)
breakdowns_best = build_breakdowns(trades_best)
print(json.dumps(metrics_best, indent=2))
print("\nBy side:"); print(breakdowns_best["by_side"])
print("\nBy year:"); print(breakdowns_best["by_year"])
plot_equity_and_monthly(trades_best)
best_run_dir = export_run_artifacts("best_grid_config", cfg_best, trades_best, metrics_best, breakdowns_best)
print(best_run_dir.resolve())


"""
## 16. Catatan operasionalisasi BBMA/OA

Filter trend di notebook ini adalah **aproksimasi executable** dari konsep BBMA/OA, bukan klaim bahwa seluruh isi PDF sudah dipetakan sempurna.

Yang dioperasionalkan:
- EMA50 sebagai trend/current direction,
- Mid BB sebagai garis pemisah,
- MA5/10 Low untuk bias buy,
- MA5/10 High untuk bias sell,
- hubungan MA terhadap Mid BB,
- opsi BB expanding untuk memilih kondisi momentum.

Ini sengaja dibuat modular supaya mudah diuji dan diperketat lagi setelah kita lihat ranking grid.
"""