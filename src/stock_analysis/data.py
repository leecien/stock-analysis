"""股價資料：yfinance 抓取（台股、美股、指數），抓不到時可用示範資料。"""

from __future__ import annotations

import logging
import zlib

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

FIELDS = ["Open", "High", "Low", "Close", "Volume"]

# 示範資料的起始價位（只是讓畫面看起來合理）
_DEMO_LEVEL = {
    "^GSPC": 6000, "^IXIC": 20000, "^DJI": 44000, "^SOX": 5500, "^TWII": 23000,
    "^VIX": 16, "^TNX": 4.2, "TWD=X": 31.5, "CL=F": 70, "GC=F": 2600,
    "2330.TW": 1100, "NVDA": 150, "TSM": 200, "AAPL": 230, "MU": 110, "0050.TW": 190,
}


def normalize_symbol(symbol: str) -> str:
    """台股代號自動補上 .TW，例如 '2330' -> '2330.TW'；其餘轉大寫。"""
    symbol = symbol.strip().upper()
    if symbol.isdigit():
        return f"{symbol}.TW"
    return symbol


def fetch_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """抓取單一股票歷史股價。"""
    import yfinance as yf

    ticker = normalize_symbol(symbol)
    df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
    if df.empty:
        raise ValueError(f"找不到 {ticker} 的資料")
    return _clean(df)


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df[[c for c in FIELDS if c in df.columns]].copy()
    df = df.dropna(subset=["Close"])
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)
    df.index = pd.to_datetime(df.index).normalize()
    return df[~df.index.duplicated(keep="last")].sort_index()


def fetch_many(symbols: list[str], period: str | None = "1y", start: str | None = None) -> dict[str, pd.DataFrame]:
    """一次抓多檔股票，回傳 {代號: DataFrame}；抓不到的代號不會出現在結果裡。"""
    import yfinance as yf

    symbols = sorted({normalize_symbol(s) for s in symbols})
    if not symbols:
        return {}
    kwargs = {"start": start} if start else {"period": period}
    raw = yf.download(
        symbols, group_by="ticker", auto_adjust=True, threads=True, progress=False, **kwargs
    )
    out: dict[str, pd.DataFrame] = {}
    if raw is None or raw.empty:
        return out
    for sym in symbols:
        try:
            df = raw[sym] if isinstance(raw.columns, pd.MultiIndex) else raw
            df = _clean(df)
            if len(df):
                out[sym] = df
        except KeyError:
            continue
    return out


def demo_history(symbol: str, days: int = 400, end: pd.Timestamp | None = None) -> pd.DataFrame:
    """產生示範用的模擬股價（隨機漫步，同一代號每次結果相同）。"""
    seed = zlib.crc32(symbol.encode())
    rng = np.random.default_rng(seed)
    end = (end or pd.Timestamp.today()).normalize()
    idx = pd.bdate_range(end=end, periods=days)
    level = _DEMO_LEVEL.get(symbol, 50 + seed % 450)
    vol = 0.03 if symbol == "^VIX" else 0.015
    rets = rng.normal(0.0004, vol, days)
    close = level * np.exp(np.cumsum(rets) - np.sum(rets))  # 讓最後一天接近 level
    high = close * (1 + np.abs(rng.normal(0, vol / 2, days)))
    low = close * (1 - np.abs(rng.normal(0, vol / 2, days)))
    open_ = np.r_[close[0], close[:-1]]
    volume = rng.integers(1_000_000, 50_000_000, days)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=idx
    )


def load_prices(
    symbols: list[str], period: str = "1y", start: str | None = None, demo: bool = False
) -> tuple[dict[str, pd.DataFrame], bool]:
    """抓股價；demo=True 或網路抓不到時用示範資料。回傳 (資料, 是否為示範資料)。"""
    symbols = sorted({normalize_symbol(s) for s in symbols})
    if not demo:
        try:
            data = fetch_many(symbols, period=period, start=start)
            if data:
                missing = set(symbols) - set(data)
                if missing:
                    log.warning("以下代號抓不到資料：%s", ", ".join(sorted(missing)))
                return data, False
            log.warning("股價全部抓取失敗，改用示範資料")
        except Exception as e:  # 網路錯誤、套件錯誤
            log.warning("股價抓取錯誤（%s），改用示範資料", e)
    days = 400
    if start:
        days = max(60, len(pd.bdate_range(start=start, end=pd.Timestamp.today())))
    return {s: demo_history(s, days=days) for s in symbols}, True
