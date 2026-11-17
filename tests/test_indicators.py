import numpy as np
import pandas as pd
import pytest

from stock_analysis.backtest import sma_crossover
from stock_analysis.data import demo_history, normalize_symbol
from stock_analysis.indicators import macd, rsi, sma
from stock_analysis.market import snapshot


def test_normalize_symbol():
    assert normalize_symbol("2330") == "2330.TW"
    assert normalize_symbol("aapl") == "AAPL"


def test_sma():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    assert sma(s, 3).tolist()[2:] == [2.0, 3.0, 4.0]


def test_rsi_bounds_and_uptrend():
    up = pd.Series(np.arange(1, 50, dtype=float))
    assert rsi(up).iloc[-1] == pytest.approx(100.0)
    rng = np.random.default_rng(0)
    r = rsi(pd.Series(100 + rng.normal(0, 1, 300).cumsum())).dropna()
    assert ((r >= 0) & (r <= 100)).all()


def test_macd_columns():
    out = macd(pd.Series(np.linspace(10, 20, 100)))
    assert list(out.columns) == ["macd", "signal", "hist"]


def test_backtest_uptrend():
    res = sma_crossover(pd.Series(np.linspace(100, 200, 300)), 5, 20, fee=0)
    assert res.total_return > 0 and res.trades == 1


def test_demo_history_is_deterministic_and_snapshot():
    a, b = demo_history("2330.TW", 120), demo_history("2330.TW", 120)
    assert a["Close"].equals(b["Close"])
    snap = snapshot("2330.TW", "台積電", a)
    assert snap["trend"] in ("偏多", "偏空", "盤整")
    assert len(snap["series"]) == 60 and snap["close"] > 0
