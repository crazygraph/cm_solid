"""
# BB-ADX 3-Candle Continuation M5 — Backtest Notebook\n\nNotebook ini mengimplementasikan baseline backtest yang konsisten dengan spesifikasi:\n- signal pada close Candle-3\n- entry di open bar berikutnya\n- SL default = extreme Candle-2 dan Candle-3\n- TP default = 2R\n- ADX(14) harus increasing\n- intrabar tie = SL-first\n- fokus efisiensi: menyimpan artefak reusable agar tidak komputasi ulang
"""


"""
## 1. Imports dan konfigurasi
"""


import os
import json
import math
import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# USER CONFIG
# ============================================================

DATA_PATH = Path("/path/to/XAUUSD_M1.csv")   # ganti ke path file Anda
OUTPUT_DIR = Path("./bb_adx_3candle_runs")
CACHE_DIR = OUTPUT_DIR / "cache"
RUN_NAME = "xauusd_m5_bb_adx_3candle_baseline"

@dataclass(frozen=True)
class StrategyConfig:
    symbol: str = "XAUUSD"
    source_tf: str = "M1"
    trade_tf: str = "5min"     # pandas resample alias untuk M5
    timezone: str = "UTC"

    bb_length: int = 20
    bb_stddev: float = 2.0
    adx_length: int = 14

    rr_multiple: float = 2.0

    one_position_only: bool = True
    sl_tie_priority: str = "SL_FIRST"
    gap_entry_policy: str = "CANCEL_INVALID_GEOMETRY"
    gap_stop_enabled: bool = True

    use_adx_three_step_rise: bool = True

CFG = StrategyConfig()

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

print(CFG)


"""
## 2. Loader yang sudah Anda gunakan
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
## 3. Utilities: hash config, cache, dan integrity checks
"""


def stable_json_hash(obj: Dict[str, Any]) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return hashlib.md5(payload).hexdigest()

def file_fingerprint(path: Path) -> Dict[str, Any]:
    st = path.stat()
    return {
        "path": str(path.resolve()),
        "size": st.st_size,
        "mtime_ns": st.st_mtime_ns,
    }

def build_cache_key(data_path: Path, cfg: StrategyConfig, stage: str) -> str:
    payload = {
        "stage": stage,
        "file": file_fingerprint(data_path),
        "cfg": asdict(cfg),
    }
    return stable_json_hash(payload)

def cache_path(data_path: Path, cfg: StrategyConfig, stage: str, ext: str = ".pkl") -> Path:
    key = build_cache_key(data_path, cfg, stage)
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

    out = {
        "rows": int(len(df)),
        "start": str(df.index.min()),
        "end": str(df.index.max()),
        "has_duplicates": bool(df.index.has_duplicates),
    }

    if expected_freq is not None and len(df) >= 3:
        diffs = pd.Series(df.index[1:] - df.index[:-1])
        out["top_deltas"] = diffs.value_counts().head(5).astype(str).to_dict()
        expected_td = pd.Timedelta(expected_freq)
        out["all_deltas_match_expected"] = bool((diffs == expected_td).all())

    return out

def save_pickle(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.to_pickle(obj, path)

def load_pickle(path: Path) -> Any:
    return pd.read_pickle(path)


"""
## 4. Cached data pipeline
"""


def get_m1_data(data_path: Path) -> pd.DataFrame:
    stage = "m1_raw"
    cp = cache_path(data_path, CFG, stage)
    if cp.exists():
        print(f"[cache hit] {stage}: {cp.name}")
        return load_pickle(cp)

    print(f"[build] {stage}")
    df_m1 = load_ohlcv(str(data_path))
    validate_ohlcv(df_m1, expected_freq="1min")
    save_pickle(df_m1, cp)
    return df_m1

def get_m5_data(data_path: Path) -> pd.DataFrame:
    stage = "m5_resampled"
    cp = cache_path(data_path, CFG, stage)
    if cp.exists():
        print(f"[cache hit] {stage}: {cp.name}")
        return load_pickle(cp)

    print(f"[build] {stage}")
    df_m1 = get_m1_data(data_path)
    df_m5 = resample_ohlcv(df_m1, CFG.trade_tf)
    validate_ohlcv(df_m5, expected_freq="5min")
    save_pickle(df_m5, cp)
    return df_m5


"""
## 5. Indicators dengan cache reusable
"""


def compute_bollinger(close: pd.Series, length: int, stddev: float) -> pd.DataFrame:
    mid = close.rolling(length, min_periods=length).mean()
    sd = close.rolling(length, min_periods=length).std(ddof=0)
    upper = mid + stddev * sd
    lower = mid - stddev * sd
    return pd.DataFrame({
        "bb_mid": mid,
        "bb_upper": upper,
        "bb_lower": lower,
    }, index=close.index)

def compute_adx(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    up_move = high - prev_high
    down_move = prev_low - low

    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=df.index
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=df.index
    )

    tr_components = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1)
    tr = tr_components.max(axis=1)

    # Wilder smoothing
    atr = tr.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    plus_dm_sm = plus_dm.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    minus_dm_sm = minus_dm.ewm(alpha=1/length, adjust=False, min_periods=length).mean()

    plus_di = 100 * (plus_dm_sm / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm_sm / atr.replace(0, np.nan))

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    return adx.rename("adx_14")

def get_feature_data(data_path: Path) -> pd.DataFrame:
    stage = "m5_features"
    cp = cache_path(data_path, CFG, stage)
    if cp.exists():
        print(f"[cache hit] {stage}: {cp.name}")
        return load_pickle(cp)

    print(f"[build] {stage}")
    df = get_m5_data(data_path).copy()

    bb = compute_bollinger(df["close"], CFG.bb_length, CFG.bb_stddev)
    adx = compute_adx(df, CFG.adx_length)

    df = pd.concat([df, bb, adx], axis=1)
    df["candle_dir"] = np.sign(df["close"] - df["open"]).astype("int8")
    save_pickle(df, cp)
    return df


"""
## 6. Signal generation
"""


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

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

    long_signal = (
        (c1_close > c1_bb_upper) &
        (c2_close < c2_open) &
        (c3_close > c3_open) &
        (c3_close > c2_open) &
        (adx_c3 > adx_c2) &
        (adx_c2 > adx_c1)
    )

    short_signal = (
        (c1_close < c1_bb_lower) &
        (c2_close > c2_open) &
        (c3_close < c3_open) &
        (c3_close < c2_open) &
        (adx_c3 > adx_c2) &
        (adx_c2 > adx_c1)
    )

    out["long_signal"] = long_signal.fillna(False)
    out["short_signal"] = short_signal.fillna(False)

    # kandidat SL dari candle-2 dan candle-3
    out["long_sl_candidate"] = np.minimum(out["low"].shift(1), out["low"])
    out["short_sl_candidate"] = np.maximum(out["high"].shift(1), out["high"])

    # optional debug tags
    out["signal_tag"] = np.select(
        [out["long_signal"], out["short_signal"]],
        ["LONG", "SHORT"],
        default=""
    )

    return out

def get_signal_data(data_path: Path) -> pd.DataFrame:
    stage = "m5_signals"
    cp = cache_path(data_path, CFG, stage)
    if cp.exists():
        print(f"[cache hit] {stage}: {cp.name}")
        return load_pickle(cp)

    print(f"[build] {stage}")
    df = get_feature_data(data_path)
    df = generate_signals(df)
    save_pickle(df, cp)
    return df


"""
## 7. Backtest engine bar-by-bar
"""


def backtest_bb_adx_3candle(df: pd.DataFrame, cfg: StrategyConfig) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    records = []

    position = None
    trade_id = 0

    timestamps = df.index
    n = len(df)

    for i in range(n - 1):  # butuh i+1 untuk entry
        row = df.iloc[i]

        # ====================================================
        # 1) manage open position on current bar
        # ====================================================
        if position is not None:
            cur = row
            side = position["side"]
            exit_reason = None
            exit_price = None

            if side == "LONG":
                if cfg.gap_stop_enabled and cur["open"] <= position["sl"]:
                    exit_reason = "GAP_STOP"
                    exit_price = float(cur["open"])
                else:
                    hit_sl = cur["low"] <= position["sl"]
                    hit_tp = cur["high"] >= position["tp"]

                    if hit_sl and hit_tp:
                        exit_reason = "SL_TIE_FIRST"
                        exit_price = float(position["sl"])
                    elif hit_sl:
                        exit_reason = "STOP_LOSS"
                        exit_price = float(position["sl"])
                    elif hit_tp:
                        exit_reason = "TAKE_PROFIT"
                        exit_price = float(position["tp"])

                if exit_reason is not None:
                    risk = position["entry_price"] - position["sl"]
                    gross_r = (exit_price - position["entry_price"]) / risk if risk > 0 else np.nan

            else:  # SHORT
                if cfg.gap_stop_enabled and cur["open"] >= position["sl"]:
                    exit_reason = "GAP_STOP"
                    exit_price = float(cur["open"])
                else:
                    hit_sl = cur["high"] >= position["sl"]
                    hit_tp = cur["low"] <= position["tp"]

                    if hit_sl and hit_tp:
                        exit_reason = "SL_TIE_FIRST"
                        exit_price = float(position["sl"])
                    elif hit_sl:
                        exit_reason = "STOP_LOSS"
                        exit_price = float(position["sl"])
                    elif hit_tp:
                        exit_reason = "TAKE_PROFIT"
                        exit_price = float(position["tp"])

                if exit_reason is not None:
                    risk = position["sl"] - position["entry_price"]
                    gross_r = (position["entry_price"] - exit_price) / risk if risk > 0 else np.nan

            if exit_reason is not None:
                records.append({
                    "trade_id": position["trade_id"],
                    "symbol": cfg.symbol,
                    "side": position["side"],
                    "signal_bar_index": position["signal_bar_index"],
                    "signal_bar_time": position["signal_bar_time"],
                    "entry_bar_index": position["entry_bar_index"],
                    "entry_bar_time": position["entry_bar_time"],
                    "entry_price": position["entry_price"],
                    "sl_price": position["sl"],
                    "tp_price": position["tp"],
                    "exit_bar_index": i,
                    "exit_bar_time": timestamps[i],
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "risk_r": 1.0,
                    "gross_r": float(gross_r),
                    "net_r": float(gross_r),  # baseline: no cost
                    "holding_bars": i - position["entry_bar_index"] + 1,
                })
                position = None

        # ====================================================
        # 2) open new trade only if no position and there is room
        # ====================================================
        if position is None and i + 1 < n:
            next_open = float(df["open"].iloc[i + 1])
            signal_time = timestamps[i]

            if bool(row["long_signal"]):
                sl = float(row["long_sl_candidate"])
                if next_open > sl:
                    risk = next_open - sl
                    tp = next_open + cfg.rr_multiple * risk
                    trade_id += 1
                    position = {
                        "trade_id": trade_id,
                        "side": "LONG",
                        "signal_bar_index": i,
                        "signal_bar_time": signal_time,
                        "entry_bar_index": i + 1,
                        "entry_bar_time": timestamps[i + 1],
                        "entry_price": next_open,
                        "sl": sl,
                        "tp": tp,
                    }

            elif bool(row["short_signal"]):
                sl = float(row["short_sl_candidate"])
                if next_open < sl:
                    risk = sl - next_open
                    tp = next_open - cfg.rr_multiple * risk
                    trade_id += 1
                    position = {
                        "trade_id": trade_id,
                        "side": "SHORT",
                        "signal_bar_index": i,
                        "signal_bar_time": signal_time,
                        "entry_bar_index": i + 1,
                        "entry_bar_time": timestamps[i + 1],
                        "entry_price": next_open,
                        "sl": sl,
                        "tp": tp,
                    }

    trades = pd.DataFrame(records)

    metrics = summarize_metrics(trades)
    return trades, metrics

def summarize_metrics(trades: pd.DataFrame) -> Dict[str, Any]:
    if trades.empty:
        return {
            "total_trades": 0,
            "win_rate": np.nan,
            "profit_factor": np.nan,
            "expectancy_r": np.nan,
            "avg_r": np.nan,
            "median_r": np.nan,
            "sum_r": 0.0,
            "max_drawdown_r": 0.0,
            "max_losing_streak": 0,
            "avg_holding_bars": np.nan,
        }

    r = trades["net_r"].astype(float)
    wins = r[r > 0]
    losses = r[r < 0]

    equity = r.cumsum()
    dd = equity - equity.cummax()

    # max losing streak
    max_ls = 0
    cur_ls = 0
    for val in r:
        if val < 0:
            cur_ls += 1
            max_ls = max(max_ls, cur_ls)
        else:
            cur_ls = 0

    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else np.inf

    return {
        "total_trades": int(len(trades)),
        "win_rate": float((r > 0).mean()),
        "profit_factor": float(pf),
        "expectancy_r": float(r.mean()),
        "avg_r": float(r.mean()),
        "median_r": float(r.median()),
        "sum_r": float(r.sum()),
        "max_drawdown_r": float(dd.min()),
        "max_losing_streak": int(max_ls),
        "avg_holding_bars": float(trades["holding_bars"].mean()),
    }


"""
## 8. Run pipeline
"""


df_signal = get_signal_data(DATA_PATH)
print(df_signal.tail(3))
print(df_signal[["long_signal", "short_signal"]].sum())

trades, metrics = backtest_bb_adx_3candle(df_signal, CFG)
print(metrics)
trades.head()


"""
## 9. Export hasil
"""


run_dir = OUTPUT_DIR / RUN_NAME
run_dir.mkdir(parents=True, exist_ok=True)

trades_path = run_dir / "trades.csv"
metrics_path = run_dir / "metrics.json"
manifest_path = run_dir / "run_manifest.json"

trades.to_csv(trades_path, index=False)

with open(metrics_path, "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=2)

manifest = {
    "strategy_name": "BB-ADX 3-Candle Continuation M5",
    "symbol": CFG.symbol,
    "source_tf": CFG.source_tf,
    "trade_tf": CFG.trade_tf,
    "timezone": CFG.timezone,
    "data_path": str(DATA_PATH),
    "data_file_fingerprint": file_fingerprint(DATA_PATH),
    "bb_length": CFG.bb_length,
    "bb_stddev": CFG.bb_stddev,
    "adx_length": CFG.adx_length,
    "rr_multiple": CFG.rr_multiple,
    "sl_rule": "extreme candle-2 and candle-3 only",
    "tp_rule": "fixed 2R baseline",
    "entry_rule": "next bar open",
    "signal_rule": "3-candle BB continuation + ADX rising",
    "execution_tie_rule": CFG.sl_tie_priority,
    "gap_entry_policy": CFG.gap_entry_policy,
    "gap_stop_enabled": CFG.gap_stop_enabled,
    "cache_dir": str(CACHE_DIR.resolve()),
    "notes": "baseline backtest, no spread, no commission",
}

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, default=str)

print("Saved:")
print(trades_path.resolve())
print(metrics_path.resolve())
print(manifest_path.resolve())


"""
## 10. Equity curve dan monthly net R
"""


if not trades.empty:
    trades_plot = trades.copy()
    trades_plot["exit_bar_time"] = pd.to_datetime(trades_plot["exit_bar_time"], utc=True)
    trades_plot = trades_plot.sort_values("exit_bar_time").reset_index(drop=True)
    trades_plot["equity_r"] = trades_plot["net_r"].cumsum()

    plt.figure(figsize=(12, 5))
    plt.plot(trades_plot["exit_bar_time"], trades_plot["equity_r"])
    plt.title("Equity Curve (R)")
    plt.xlabel("Exit Time")
    plt.ylabel("Cumulative R")
    plt.grid(True)
    plt.show()

    monthly = trades_plot.set_index("exit_bar_time")["net_r"].resample("M").sum()

    plt.figure(figsize=(12, 5))
    monthly.plot(kind="bar")
    plt.title("Monthly Net R")
    plt.xlabel("Month")
    plt.ylabel("Net R")
    plt.grid(True, axis="y")
    plt.show()
else:
    print("Tidak ada trade untuk diplot.")


"""
## 11. Audit cepat
"""


print("Rows M5:", len(df_signal))
print("Long signals:", int(df_signal["long_signal"].sum()))
print("Short signals:", int(df_signal["short_signal"].sum()))
print("Trades:", len(trades))
print(json.dumps(metrics, indent=2))


"""
## 12. Catatan implementasi\n\nNotebook ini sengaja dibuat dengan cache per stage:\n- `m1_raw`\n- `m5_resampled`\n- `m5_features`\n- `m5_signals`\n\nJadi saat Anda mengulang eksperimen yang sama, loader tidak akan menghitung ulang bagian yang sudah ada.\n\nJika parameter diubah, cache key ikut berubah otomatis sehingga artefak lama tidak tertukar.
"""