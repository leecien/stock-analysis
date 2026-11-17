import numpy as np
import pandas as pd
import pytest

from stock_analysis.backtest import sma_crossover
from stock_analysis.data import normalize_symbol
from stock_analysis.indicators import macd, rsi, sma


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
    noisy = pd.Series(100 + rng.normal(0, 1, 300).cumsum())
    r = rsi(noisy).dropna()
    assert ((r >= 0) & (r <= 100)).all()


def test_macd_columns():
    s = pd.Series(np.linspace(10, 20, 100))
    out = macd(s)
    assert list(out.columns) == ["macd", "signal", "hist"]
    assert out["macd"].iloc[-1] > 0


def test_backtest_uptrend():
    s = pd.Series(np.linspace(100, 200, 300))
    res = sma_crossover(s, 5, 20, fee=0)
    assert res.total_return > 0
    assert res.trades == 1
    assert res.max_drawdown == pytest.approx(0.0)
