
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from xauusd_pem_vwap_research import (
    build_pem_signals,
    backtest_pem,
    atr,
    ema,
    summarize_trades,
)


def attach_pem_context(df_m15: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    if len(trades) == 0:
        return trades.copy()

    sig = build_pem_signals(df_m15).copy()
    sig["atr14"] = atr(sig, 14)
    sig["ema55"] = ema(sig["close"], 55)
    sig["ema55_slope_5"] = sig["ema55"] - sig["ema55"].shift(5)
    sig["ema55_slope_norm"] = sig["ema55_slope_5"] / sig["atr14"].replace(0, np.nan)
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
        raw=False
    )
    sig["vol_bucket"] = pd.cut(
        sig["atr_pct_rank"],
        bins=[-np.inf, 0.33, 0.66, np.inf],
        labels=["LowVol", "MidVol", "HighVol"]
    )
    sig["trend_bucket"] = pd.cut(
        sig["ema55_slope_norm"].abs(),
        bins=[-np.inf, 0.10, 0.25, np.inf],
        labels=["Flat", "Moderate", "Strong"]
    )

    ctx = sig[["hour", "session", "atr14", "atr_pct_rank", "vol_bucket", "ema55_slope_norm", "trend_bucket", "close", "ema55", "vwap"]].copy()
    ctx.index.name = "entry_time"

    t = trades.copy()
    t["entry_time"] = pd.to_datetime(t["entry_time"], utc=True)
    return t.merge(ctx.reset_index(), on="entry_time", how="left")


def group_metrics(df: pd.DataFrame, by: str) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(by, dropna=False):
        m = summarize_trades(g)
        rows.append({
            by: key,
            "total_trades": m["total_trades"],
            "win_rate": m["win_rate"],
            "profit_factor": m["profit_factor"],
            "expectancy_r": m["expectancy_r"],
            "sum_r": m["sum_r"],
            "max_drawdown_r": m["max_drawdown_r"],
            "avg_holding_bars": m["avg_holding_bars"],
        })
    return pd.DataFrame(rows).sort_values("expectancy_r", ascending=False)


def _run_filtered(sig: pd.DataFrame, mask: pd.Series, name: str) -> pd.DataFrame:
    sig2 = sig.copy()
    sig2["signal_long"] = sig2["signal_long"] & mask.fillna(False)
    sig2["signal_short"] = sig2["signal_short"] & mask.fillna(False)

    trades = []
    i = 0
    n = len(sig2)
    while i < n - 1:
        row = sig2.iloc[i]
        if row["signal_long"] or row["signal_short"]:
            entry_idx = i + 1
            if entry_idx >= n:
                break
            direction = "long" if row["signal_long"] else "short"
            entry_price = float(sig2.iloc[entry_idx]["open"])
            sl_price = float(row["signal_sl"])
            if np.isnan(sl_price):
                i += 1
                continue
            risk = entry_price - sl_price if direction == "long" else sl_price - entry_price
            if risk <= 0:
                i += 1
                continue
            tp_price = entry_price + 2.0 * risk if direction == "long" else entry_price - 2.0 * risk

            exit_time = None
            exit_price = np.nan
            reason = "timeout"
            bars_held = 0

            for j in range(entry_idx, min(n, entry_idx + 12 + 1)):
                bar = sig2.iloc[j]
                bars_held = j - entry_idx + 1
                low, high = float(bar["low"]), float(bar["high"])
                if direction == "long":
                    hit_sl = low <= sl_price
                    hit_tp = high >= tp_price
                else:
                    hit_sl = high >= sl_price
                    hit_tp = low <= tp_price

                if hit_sl and hit_tp:
                    exit_price = sl_price
                    exit_time = sig2.index[j]
                    reason = "sl_first_ambiguous"
                    break
                elif hit_sl:
                    exit_price = sl_price
                    exit_time = sig2.index[j]
                    reason = "sl"
                    break
                elif hit_tp:
                    exit_price = tp_price
                    exit_time = sig2.index[j]
                    reason = "tp"
                    break

            if exit_time is None:
                timeout_idx = min(n - 1, entry_idx + 12)
                exit_time = sig2.index[timeout_idx]
                exit_price = float(sig2.iloc[timeout_idx]["close"])
                reason = "timeout"
                bars_held = timeout_idx - entry_idx + 1

            pnl_r = (exit_price - entry_price) / risk if direction == "long" else (entry_price - exit_price) / risk
            trades.append({
                "strategy": "PEM",
                "timeframe": "M15",
                "direction": direction,
                "entry_time": sig2.index[entry_idx],
                "exit_time": exit_time,
                "entry_price": entry_price,
                "exit_price": float(exit_price),
                "sl_price": sl_price,
                "tp_price": float(tp_price),
                "bars_held": int(bars_held),
                "reason": reason,
                "pnl_r": float(pnl_r),
                "filter_name": name,
            })
            i = sig2.index.get_loc(exit_time)
        else:
            i += 1

    return pd.DataFrame(trades)


def filter_experiments(df_m15: pd.DataFrame):
    base_trades = backtest_pem(df_m15, timeframe="M15", rr_target=2.0, timeout_bars=12)
    base_ctx = attach_pem_context(df_m15, base_trades)

    sig = build_pem_signals(df_m15).copy()
    sig["atr14"] = atr(sig, 14)
    sig["ema55"] = ema(sig["close"], 55)
    sig["ema55_slope_5"] = sig["ema55"] - sig["ema55"].shift(5)
    sig["ema55_slope_norm"] = sig["ema55_slope_5"] / sig["atr14"].replace(0, np.nan)
    sig["hour"] = sig.index.hour
    roll = sig["atr14"].rolling(96, min_periods=30)
    sig["atr_pct_rank"] = roll.apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(pd.Series(x).dropna()) > 0 else np.nan,
        raw=False
    )

    experiments = {}
    experiments["baseline"] = base_ctx
    experiments["london_ny_only"] = attach_pem_context(df_m15, _run_filtered(sig, sig["hour"].between(7, 16), "london_ny_only"))
    experiments["exclude_asia"] = attach_pem_context(df_m15, _run_filtered(sig, ~sig["hour"].between(0, 6), "exclude_asia"))
    experiments["mid_high_vol_only"] = attach_pem_context(df_m15, _run_filtered(sig, sig["atr_pct_rank"] >= 0.33, "mid_high_vol_only"))
    experiments["high_vol_only"] = attach_pem_context(df_m15, _run_filtered(sig, sig["atr_pct_rank"] >= 0.66, "high_vol_only"))
    experiments["moderate_strong_slope"] = attach_pem_context(df_m15, _run_filtered(sig, sig["ema55_slope_norm"].abs() >= 0.10, "moderate_strong_slope"))
    experiments["strong_slope_only"] = attach_pem_context(df_m15, _run_filtered(sig, sig["ema55_slope_norm"].abs() >= 0.25, "strong_slope_only"))
    combo_mask = sig["hour"].between(7, 16) & (sig["atr_pct_rank"] >= 0.33) & (sig["ema55_slope_norm"].abs() >= 0.10)
    experiments["combo_london_ny_midvol_slope"] = attach_pem_context(df_m15, _run_filtered(sig, combo_mask, "combo_london_ny_midvol_slope"))
    return experiments


def experiment_summary(experiments):
    rows = []
    for name, t in experiments.items():
        if len(t) == 0:
            rows.append({
                "experiment": name,
                "total_trades": 0,
                "win_rate": np.nan,
                "profit_factor": np.nan,
                "expectancy_r": np.nan,
                "median_r": np.nan,
                "sum_r": 0.0,
                "max_drawdown_r": 0.0,
                "max_losing_streak": 0,
                "avg_holding_bars": np.nan,
            })
        else:
            rows.append({"experiment": name, **summarize_trades(t)})
    return pd.DataFrame(rows).sort_values(["expectancy_r", "profit_factor"], ascending=False)


def plot_group_bar(df: pd.DataFrame, x: str, y: str, title: str):
    d = df.copy().sort_values(y, ascending=False)
    plt.figure(figsize=(10, 4))
    plt.bar(d[x].astype(str), d[y].astype(float))
    plt.title(title)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.xticks(rotation=30)
    plt.grid(True, axis="y", alpha=0.3)
    plt.show()


def save_edge_outputs(out_dir: str, pem_ctx: pd.DataFrame, by_session: pd.DataFrame, by_hour: pd.DataFrame, by_vol: pd.DataFrame, by_trend: pd.DataFrame, exp_summary: pd.DataFrame):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pem_ctx.to_csv(out / "pem_m15_trades_with_context.csv", index=False)
    by_session.to_csv(out / "pem_m15_by_session.csv", index=False)
    by_hour.to_csv(out / "pem_m15_by_hour.csv", index=False)
    by_vol.to_csv(out / "pem_m15_by_vol_bucket.csv", index=False)
    by_trend.to_csv(out / "pem_m15_by_trend_bucket.csv", index=False)
    exp_summary.to_csv(out / "pem_m15_filter_experiments.csv", index=False)
