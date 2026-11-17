"""技術面快照：每檔股票 / 指數的漲跌幅、均線、RSI、MACD 與趨勢分數。"""

from __future__ import annotations

import math

import pandas as pd

from .indicators import macd, rsi, sma


def _r(x, n=2):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    return round(float(x), n)


def _pct(close: pd.Series, n: int):
    if len(close) <= n:
        return None
    return _r((close.iloc[-1] / close.iloc[-1 - n] - 1) * 100)


def snapshot(symbol: str, name: str, df: pd.DataFrame, series_len: int = 60) -> dict:
    close = df["Close"].astype(float)
    s20, s60 = sma(close, 20), sma(close, 60)
    r = rsi(close, 14)
    m = macd(close)
    last = close.iloc[-1]

    score = 0.0
    if not math.isnan(s20.iloc[-1]):
        score += 1 if last > s20.iloc[-1] else -1
    if not math.isnan(s60.iloc[-1]) and not math.isnan(s20.iloc[-1]):
        score += 1 if s20.iloc[-1] > s60.iloc[-1] else -1
    score += 1 if m["hist"].iloc[-1] > 0 else -1
    rv = r.iloc[-1]
    if not math.isnan(rv):
        if rv > 75:
            score -= 0.5  # 過熱
        elif rv < 25:
            score += 0.5  # 超賣
    return {
        "symbol": symbol,
        "name": name,
        "date": close.index[-1].strftime("%Y-%m-%d"),
        "close": _r(last, 4 if last < 10 else 2),
        "change_pct": _pct(close, 1),
        "change_5d_pct": _pct(close, 5),
        "change_20d_pct": _pct(close, 20),
        "sma20": _r(s20.iloc[-1]),
        "sma60": _r(s60.iloc[-1]),
        "rsi": _r(rv, 1),
        "macd_hist": _r(m["hist"].iloc[-1], 3),
        "trend_score": score,
        "trend": "偏多" if score >= 1.5 else "偏空" if score <= -1.5 else "盤整",
        "series": [_r(v, 4 if last < 10 else 2) for v in close.iloc[-series_len:].tolist()],
        "series_dates": [d.strftime("%Y-%m-%d") for d in close.index[-series_len:]],
    }


def snapshots(prices: dict[str, pd.DataFrame], names: dict[str, str], symbols: list[str]) -> list[dict]:
    out = []
    for s in symbols:
        df = prices.get(s)
        if df is not None and len(df) >= 2:
            out.append(snapshot(s, names.get(s, s), df))
    return out
