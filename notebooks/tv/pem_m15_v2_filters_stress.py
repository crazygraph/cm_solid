
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from xauusd_pem_vwap_research import (
    load_ohlcv,
    resample_ohlcv,
    build_pem_signals,
    atr,
    summarize_trades,
)


def prepare_sig_with_filters(df_m15: pd.DataFrame) -> pd.DataFrame:
    sig = build_pem_signals(df_m15).copy()
    sig["atr14"] = atr(sig, 14)
    sig["hour"] = sig.index.hour

    def map_session(h):
        if 0 <= h < 7:
            return "Asia"
        elif 7 <= h < 13:
            return "London"
        elif 13 <= h < 17:
            return "NY_Overlap"
        return "NY_Late"

    sig["session"] = sig["hour"].map(map_session)

    roll = sig["atr14"].rolling(96, min_periods=30)
    sig["atr_pct_rank"] = roll.apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(pd.Series(x).dropna()) > 0 else np.nan,
        raw=False,
    )
    return sig


def backtest_pem_from_signals(
    sig: pd.DataFrame,
    timeframe: str = "M15",
    rr_target: float = 2.0,
    timeout_bars: int = 12,
    entry_delay_bars: int = 0,
    spread_add: float = 0.0,
    slippage_add: float = 0.0,
    tp_multiplier: float = 1.0,
):
    trades = []
    i = 0
    n = len(sig)
    while i < n - 1:
        row = sig.iloc[i]
        if row["signal_long"] or row["signal_short"]:
            entry_idx = i + 1 + entry_delay_bars
            if entry_idx >= n:
                break

            direction = "long" if row["signal_long"] else "short"
            raw_entry = float(sig.iloc[entry_idx]["open"])
            entry_price = raw_entry + spread_add + slippage_add if direction == "long" else raw_entry - spread_add - slippage_add

            sl_price = float(row["signal_sl"])
            if np.isnan(sl_price):
                i += 1
                continue

            risk = entry_price - sl_price if direction == "long" else sl_price - entry_price
            if risk <= 0:
                i += 1
                continue

            tp_price = entry_price + rr_target * tp_multiplier * risk if direction == "long" else entry_price - rr_target * tp_multiplier * risk

            exit_time = None
            exit_price = np.nan
            reason = "timeout"
            bars_held = 0

            for j in range(entry_idx, min(n, entry_idx + timeout_bars + 1)):
                bar = sig.iloc[j]
                bars_held = j - entry_idx + 1
                low = float(bar["low"])
                high = float(bar["high"])

                if direction == "long":
                    hit_sl = low <= sl_price
                    hit_tp = high >= tp_price
                else:
                    hit_sl = high >= sl_price
                    hit_tp = low <= tp_price

                if hit_sl and hit_tp:
                    exit_price = sl_price
                    exit_time = sig.index[j]
                    reason = "sl_first_ambiguous"
                    break
                elif hit_sl:
                    exit_price = sl_price
                    exit_time = sig.index[j]
                    reason = "sl"
                    break
                elif hit_tp:
                    exit_price = tp_price
                    exit_time = sig.index[j]
                    reason = "tp"
                    break

            if exit_time is None:
                timeout_idx = min(n - 1, entry_idx + timeout_bars)
                exit_time = sig.index[timeout_idx]
                exit_price = float(sig.iloc[timeout_idx]["close"])
                reason = "timeout"
                bars_held = timeout_idx - entry_idx + 1

            pnl_r = (exit_price - entry_price) / risk if direction == "long" else (entry_price - exit_price) / risk

            trades.append({
                "strategy": "PEM_M15_V2",
                "timeframe": timeframe,
                "direction": direction,
                "entry_time": sig.index[entry_idx],
                "exit_time": exit_time,
                "entry_price": entry_price,
                "exit_price": float(exit_price),
                "sl_price": sl_price,
                "tp_price": float(tp_price),
                "bars_held": int(bars_held),
                "reason": reason,
                "pnl_r": float(pnl_r),
                "session": row.get("session"),
                "hour": row.get("hour"),
                "atr_pct_rank": row.get("atr_pct_rank"),
            })
            i = sig.index.get_loc(exit_time)
        else:
            i += 1

    return pd.DataFrame(trades)


def apply_variant(sig: pd.DataFrame, variant: str) -> pd.DataFrame:
    s = sig.copy()
    mask = pd.Series(True, index=s.index)

    if variant == "baseline":
        pass
    elif variant == "block_ny_overlap":
        mask &= s["session"] != "NY_Overlap"
    elif variant == "mid_high_vol_only":
        mask &= s["atr_pct_rank"] >= 0.33
    elif variant == "block_ny_overlap_mid_high_vol":
        mask &= (s["session"] != "NY_Overlap") & (s["atr_pct_rank"] >= 0.33)
    elif variant == "asia_only":
        mask &= s["session"] == "Asia"
    elif variant == "asia_plus_ny_late":
        mask &= s["session"].isin(["Asia", "NY_Late"])
    elif variant == "asia_mid_high_vol":
        mask &= (s["session"] == "Asia") & (s["atr_pct_rank"] >= 0.33)
    else:
        raise ValueError(f"Unknown variant: {variant}")

    s["signal_long"] = s["signal_long"] & mask.fillna(False)
    s["signal_short"] = s["signal_short"] & mask.fillna(False)
    return s


def run_variants(df_m15: pd.DataFrame):
    sig = prepare_sig_with_filters(df_m15)
    variants = [
        "baseline",
        "block_ny_overlap",
        "mid_high_vol_only",
        "block_ny_overlap_mid_high_vol",
        "asia_only",
        "asia_plus_ny_late",
        "asia_mid_high_vol",
    ]
    out = {}
    for v in variants:
        out[v] = backtest_pem_from_signals(apply_variant(sig, v))
    return out


def summarize_variant_runs(variant_runs):
    rows = []
    for name, trades in variant_runs.items():
        if len(trades) == 0:
            m = {
                "total_trades": 0,
                "win_rate": np.nan,
                "profit_factor": np.nan,
                "expectancy_r": np.nan,
                "median_r": np.nan,
                "sum_r": 0.0,
                "max_drawdown_r": 0.0,
                "max_losing_streak": 0,
                "avg_holding_bars": np.nan,
            }
        else:
            m = summarize_trades(trades)
        rows.append({"variant": name, **m})
    return pd.DataFrame(rows).sort_values(["expectancy_r", "profit_factor"], ascending=False)


def run_stress_tests_for_variant(sig_variant: pd.DataFrame, variant_name: str):
    scenarios = [
        {"scenario": "baseline", "entry_delay_bars": 0, "spread_add": 0.0, "slippage_add": 0.0, "tp_multiplier": 1.0},
        {"scenario": "delay_1", "entry_delay_bars": 1, "spread_add": 0.0, "slippage_add": 0.0, "tp_multiplier": 1.0},
        {"scenario": "delay_2", "entry_delay_bars": 2, "spread_add": 0.0, "slippage_add": 0.0, "tp_multiplier": 1.0},
        {"scenario": "spread_0p05", "entry_delay_bars": 0, "spread_add": 0.05, "slippage_add": 0.0, "tp_multiplier": 1.0},
        {"scenario": "spread_0p10", "entry_delay_bars": 0, "spread_add": 0.10, "slippage_add": 0.0, "tp_multiplier": 1.0},
        {"scenario": "slip_0p05", "entry_delay_bars": 0, "spread_add": 0.0, "slippage_add": 0.05, "tp_multiplier": 1.0},
        {"scenario": "slip_0p10", "entry_delay_bars": 0, "spread_add": 0.0, "slippage_add": 0.10, "tp_multiplier": 1.0},
        {"scenario": "tp_haircut_90", "entry_delay_bars": 0, "spread_add": 0.0, "slippage_add": 0.0, "tp_multiplier": 0.90},
        {"scenario": "tp_haircut_80", "entry_delay_bars": 0, "spread_add": 0.0, "slippage_add": 0.0, "tp_multiplier": 0.80},
    ]
    rows = []
    for sc in scenarios:
        trades = backtest_pem_from_signals(
            sig_variant,
            entry_delay_bars=sc["entry_delay_bars"],
            spread_add=sc["spread_add"],
            slippage_add=sc["slippage_add"],
            tp_multiplier=sc["tp_multiplier"],
        )
        if len(trades) == 0:
            m = {
                "total_trades": 0,
                "win_rate": np.nan,
                "profit_factor": np.nan,
                "expectancy_r": np.nan,
                "median_r": np.nan,
                "sum_r": 0.0,
                "max_drawdown_r": 0.0,
                "max_losing_streak": 0,
                "avg_holding_bars": np.nan,
            }
        else:
            m = summarize_trades(trades)
        rows.append({"variant": variant_name, "scenario": sc["scenario"], **m})
    return pd.DataFrame(rows).sort_values(["expectancy_r", "profit_factor"], ascending=False)


def plot_bar(df: pd.DataFrame, x: str, y: str, title: str):
    d = df.copy().sort_values(y, ascending=False)
    plt.figure(figsize=(10, 4))
    plt.bar(d[x].astype(str), d[y].astype(float))
    plt.title(title)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.xticks(rotation=30)
    plt.grid(True, axis="y", alpha=0.3)
    plt.show()


def save_outputs(out_dir: str, variant_summary: pd.DataFrame, stress_df: pd.DataFrame, variant_runs):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    variant_summary.to_csv(out / "pem_m15_v2_variants.csv", index=False)
    stress_df.to_csv(out / "pem_m15_v2_stress_tests.csv", index=False)
    for name, trades in variant_runs.items():
        trades.to_csv(out / f"{name}_trades.csv", index=False)
