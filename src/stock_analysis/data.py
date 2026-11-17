"""股價資料抓取（使用 yfinance，支援台股與美股）。"""

from __future__ import annotations

import pandas as pd


def normalize_symbol(symbol: str) -> str:
    """台股代號自動補上 .TW，例如 '2330' -> '2330.TW'；美股維持原樣。"""
    symbol = symbol.strip().upper()
    if symbol.isdigit():
        return f"{symbol}.TW"
    return symbol


def fetch_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """抓取歷史股價，回傳含 Open/High/Low/Close/Volume 欄位的 DataFrame。"""
    import yfinance as yf

    ticker = normalize_symbol(symbol)
    df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
    if df.empty:
        raise ValueError(f"找不到 {ticker} 的資料")
    return df[["Open", "High", "Low", "Close", "Volume"]]
