"""常用技術指標。"""

from __future__ import annotations

import pandas as pd


def sma(close: pd.Series, window: int) -> pd.Series:
    """簡單移動平均線。"""
    return close.rolling(window).mean()


def ema(close: pd.Series, span: int) -> pd.Series:
    """指數移動平均線。"""
    return close.ewm(span=span, adjust=False).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """相對強弱指標（Wilder 平滑法）。"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss
    out = 100 - 100 / (1 + rs)
    # 只漲不跌時 avg_loss 為 0，RSI 應為 100
    return out.where(avg_loss != 0, 100.0).where(avg_gain.notna())


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD：回傳 macd、signal、hist 三欄。"""
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    return pd.DataFrame(
        {"macd": macd_line, "signal": signal_line, "hist": macd_line - signal_line}
    )


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """在股價表上加入常用指標欄位。"""
    out = df.copy()
    close = out["Close"]
    out["SMA20"] = sma(close, 20)
    out["SMA60"] = sma(close, 60)
    out["RSI14"] = rsi(close, 14)
    out = out.join(macd(close))
    return out
