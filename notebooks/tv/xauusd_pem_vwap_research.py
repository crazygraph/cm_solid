
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def load_ohlcv(path: str) -> pd.DataFrame:
    names = ['date', 'time', 'open', 'high', 'low', 'close', 'volume']
    df = pd.read_csv(path, names=names, skiprows=1)
    ts = pd.to_datetime(df['date'] + ' ' + df['time'], format='%Y.%m.%d %H:%M', utc=True)
    df = df.drop(columns=['date', 'time'])
    df.index = ts
    df.index.name = 'timestamp'
    df = df.sort_index()
    return df


def resample_ohlcv(df: pd.DataFrame, rule: str, label='right', closed='right') -> pd.DataFrame:
    agg = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }
    return df.resample(rule, label=label, closed=closed).agg(agg).dropna()


def ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()


def sma(s: pd.Series, length: int) -> pd.Series:
    return s.rolling(length).mean()


def true_range(df: pd.DataFrame) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - pc).abs(),
        (df["low"] - pc).abs()
    ], axis=1).max(axis=1)
    return tr


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    tr = true_range(df)
    return tr.ewm(alpha=1 / length, adjust=False).mean()


def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    roll_up = up.ewm(alpha=1 / length, adjust=False).mean()
    roll_down = down.ewm(alpha=1 / length, adjust=False).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def session_vwap(df: pd.DataFrame) -> pd.Series:
    px = (df["high"] + df["low"] + df["close"]) / 3.0
    grp = df.index.floor("D")
    num = (px * df["volume"]).groupby(grp).cumsum()
    den = df["volume"].groupby(grp).cumsum().replace(0, np.nan)
    return num / den


@dataclass
class Trade:
    strategy: str
    timeframe: str
    direction: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    sl_price: float
    tp_price: float
    bars_held: int
    reason: str
    pnl_r: float


def summarize_trades(trades: pd.DataFrame) -> Dict[str, float]:
    if len(trades) == 0:
        return {
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
    pnl = trades["pnl_r"].astype(float)
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = wins.sum()
    gross_loss = losses.sum()
    equity = pnl.cumsum()
    dd = equity - equity.cummax()
    losing_streak = 0
    max_losing_streak = 0
    for x in pnl:
        if x < 0:
            losing_streak += 1
            max_losing_streak = max(max_losing_streak, losing_streak)
        else:
            losing_streak = 0
    return {
        "total_trades": int(len(trades)),
        "win_rate": float((pnl > 0).mean()),
        "profit_factor": float(gross_profit / abs(gross_loss)) if gross_loss < 0 else np.inf,
        "expectancy_r": float(pnl.mean()),
        "median_r": float(pnl.median()),
        "sum_r": float(pnl.sum()),
        "max_drawdown_r": float(dd.min()),
        "max_losing_streak": int(max_losing_streak),
        "avg_holding_bars": float(trades["bars_held"].mean()),
    }


def plot_equity(trades: pd.DataFrame, title: str = "Equity in R"):
    if len(trades) == 0:
        print("No trades to plot")
        return
    eq = trades["pnl_r"].cumsum()
    plt.figure(figsize=(10, 4))
    plt.plot(eq.index, eq.values)
    plt.title(title)
    plt.xlabel("Trade #")
    plt.ylabel("Cumulative R")
    plt.grid(True, alpha=0.3)
    plt.show()


def build_pem_signals(
    df: pd.DataFrame,
    atr_len: int = 14,
    impulse_mult: float = 1.1,
    compress_pct: float = 0.7,
    stall_bars: int = 2,
    min_body_frac: float = 0.20,
    ema_slow_len: int = 55,
) -> pd.DataFrame:
    out = df.copy()
    out["ema_slow"] = ema(out["close"], ema_slow_len)
    out["vwap"] = session_vwap(out)
    out["atr"] = atr(out, atr_len)
    out["bar_range"] = out["high"] - out["low"]
    out["body"] = (out["close"] - out["open"]).abs()
    out["body_frac"] = np.where(out["bar_range"] > 0, out["body"] / out["bar_range"], 0.0)

    state = 0
    comp_high = np.nan
    comp_low = np.nan
    stall_count = 0
    fire_dir = 0
    fire_comp_high = np.nan
    fire_comp_low = np.nan
    fire_idx = None

    signal_long = np.zeros(len(out), dtype=bool)
    signal_short = np.zeros(len(out), dtype=bool)
    sig_sl = np.full(len(out), np.nan)

    for i in range(len(out)):
        row = out.iloc[i]
        strong_up = (row["close"] > row["open"]) and (row["bar_range"] > row["atr"] * impulse_mult)
        strong_down = (row["close"] < row["open"]) and (row["bar_range"] > row["atr"] * impulse_mult)

        if state == 0 and (strong_up or strong_down):
            state = 1
            stall_count = 0
            comp_high = np.nan
            comp_low = np.nan

        small_candle = row["bar_range"] < row["atr"] * compress_pct

        if state == 1 and small_candle:
            state = 2
            stall_count = 1
            comp_high = row["high"]
            comp_low = row["low"]
        elif state == 2 and small_candle:
            stall_count += 1
            comp_high = max(comp_high, row["high"])
            comp_low = min(comp_low, row["low"])

        valid_comp = (state == 2 and stall_count >= stall_bars)
        bull_break = valid_comp and (row["close"] > comp_high)
        bear_break = valid_comp and (row["close"] < comp_low)
        break_clean = row["body_frac"] >= min_body_frac
        fire = (bull_break or bear_break) and break_clean

        if fire:
            fire_dir = 1 if bull_break else -1
            fire_comp_high = comp_high
            fire_comp_low = comp_low
            fire_idx = i
            state = 0
            stall_count = 0
            comp_high = np.nan
            comp_low = np.nan

        if state != 0 and stall_count > 15:
            state = 0
            stall_count = 0
            comp_high = np.nan
            comp_low = np.nan

        is_confirm = fire_idx is not None and i == fire_idx + 1
        confirm_long = is_confirm and fire_dir == 1 and row["close"] > row["open"]
        confirm_short = is_confirm and fire_dir == -1 and row["close"] < row["open"]

        filter_long = (row["close"] > row["ema_slow"]) and (row["close"] > row["vwap"])
        filter_short = (row["close"] < row["ema_slow"]) and (row["close"] < row["vwap"])

        if confirm_long and filter_long:
            signal_long[i] = True
            sig_sl[i] = fire_comp_low
            fire_idx = None
        elif confirm_short and filter_short:
            signal_short[i] = True
            sig_sl[i] = fire_comp_high
            fire_idx = None

    out["signal_long"] = signal_long
    out["signal_short"] = signal_short
    out["signal_sl"] = sig_sl
    return out


def backtest_pem(df: pd.DataFrame, timeframe: str, rr_target: float = 2.0, timeout_bars: int = 24) -> pd.DataFrame:
    sig = build_pem_signals(df)
    trades: List[Trade] = []
    i = 0
    n = len(sig)
    while i < n - 1:
        row = sig.iloc[i]
        if row["signal_long"] or row["signal_short"]:
            entry_idx = i + 1
            if entry_idx >= n:
                break
            direction = "long" if row["signal_long"] else "short"
            entry_price = float(sig.iloc[entry_idx]["open"])
            sl_price = float(row["signal_sl"])
            if np.isnan(sl_price):
                i += 1
                continue
            risk = entry_price - sl_price if direction == "long" else sl_price - entry_price
            if risk <= 0:
                i += 1
                continue
            tp_price = entry_price + rr_target * risk if direction == "long" else entry_price - rr_target * risk

            exit_time = None
            exit_price = np.nan
            reason = "timeout"
            bars_held = 0

            for j in range(entry_idx, min(n, entry_idx + timeout_bars + 1)):
                bar = sig.iloc[j]
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
            trades.append(Trade("PEM", timeframe, direction, sig.index[entry_idx], exit_time, entry_price, float(exit_price), sl_price, float(tp_price), int(bars_held), reason, float(pnl_r)))
            i = sig.index.get_loc(exit_time)
        else:
            i += 1

    return pd.DataFrame([asdict(t) for t in trades])


def build_vwap_mr_signals(
    df: pd.DataFrame,
    vwap_length: int = 60,
    rsi_length: int = 14,
    rsi_overbought: int = 65,
    rsi_oversold: int = 25,
    enable_vol_filter: bool = True,
    vol_lookback: int = 20,
    vol_multiplier: float = 3.0,
) -> pd.DataFrame:
    out = df.copy()
    src = out["close"]

    basis = (src * out["volume"]).rolling(vwap_length).sum() / out["volume"].rolling(vwap_length).sum().replace(0, np.nan)
    abs_dev = (out["volume"] * (src - basis).abs()).rolling(vwap_length).sum() / out["volume"].rolling(vwap_length).sum().replace(0, np.nan)
    upper2 = basis + abs_dev * 2.0
    lower2 = basis - abs_dev * 2.0
    rsi_value = rsi(src, rsi_length)

    avg_vol = sma(out["volume"], vol_lookback)
    extreme_vol = out["volume"] > avg_vol * vol_multiplier
    vol_condition = (~enable_vol_filter) | (~extreme_vol)

    long_condition = (src.shift(1) >= lower2.shift(1)) & (src < lower2) & (rsi_value < rsi_oversold) & vol_condition
    short_condition = (src.shift(1) <= upper2.shift(1)) & (src > upper2) & (rsi_value > rsi_overbought) & vol_condition

    out["basis"] = basis
    out["signal_long"] = long_condition.fillna(False)
    out["signal_short"] = short_condition.fillna(False)
    return out


def backtest_vwap_mr(df: pd.DataFrame, timeframe: str, timeout_bars: int = 20, stop_loss_pct: float = 0.005) -> pd.DataFrame:
    sig = build_vwap_mr_signals(df)
    trades: List[Trade] = []
    i = 0
    n = len(sig)
    while i < n - 1:
        row = sig.iloc[i]
        if row["signal_long"] or row["signal_short"]:
            entry_idx = i + 1
            if entry_idx >= n:
                break
            direction = "long" if row["signal_long"] else "short"
            entry_price = float(sig.iloc[entry_idx]["open"])
            tp_price = float(row["basis"])
            if np.isnan(tp_price):
                i += 1
                continue

            if direction == "long":
                sl_price = entry_price * (1 - stop_loss_pct)
                risk = entry_price - sl_price
            else:
                sl_price = entry_price * (1 + stop_loss_pct)
                risk = sl_price - entry_price

            exit_time = None
            exit_price = np.nan
            reason = "timeout"
            bars_held = 0

            for j in range(entry_idx, min(n, entry_idx + timeout_bars + 1)):
                bar = sig.iloc[j]
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
            trades.append(Trade("VWAP_MR", timeframe, direction, sig.index[entry_idx], exit_time, entry_price, float(exit_price), float(sl_price), float(tp_price), int(bars_held), reason, float(pnl_r)))
            i = sig.index.get_loc(exit_time)
        else:
            i += 1

    return pd.DataFrame([asdict(t) for t in trades])
