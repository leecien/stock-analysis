"""簡單的均線交叉策略回測。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .indicators import sma


@dataclass
class BacktestResult:
    total_return: float
    buy_hold_return: float
    max_drawdown: float
    trades: int
    equity: pd.Series

    def summary(self) -> str:
        return (
            f"策略報酬: {self.total_return:.2%}\n"
            f"買進持有: {self.buy_hold_return:.2%}\n"
            f"最大回撤: {self.max_drawdown:.2%}\n"
            f"交易次數: {self.trades}"
        )


def sma_crossover(
    close: pd.Series, short: int = 20, long: int = 60, fee: float = 0.001425
) -> BacktestResult:
    """短均線站上長均線時持有，跌破時出場。

    訊號以收盤價計算，隔天才生效，避免前視偏差。
    fee 為單邊手續費率（預設台股 0.1425%）。
    """
    if short >= long:
        raise ValueError("short 必須小於 long")

    signal = (sma(close, short) > sma(close, long)).astype(int)
    position = signal.shift(1).fillna(0)
    daily_ret = close.pct_change().fillna(0)

    changes = position.diff().abs().fillna(position.abs())
    strat_ret = position * daily_ret - changes * fee

    equity = (1 + strat_ret).cumprod()
    drawdown = equity / equity.cummax() - 1

    return BacktestResult(
        total_return=float(equity.iloc[-1] - 1),
        buy_hold_return=float(close.iloc[-1] / close.iloc[0] - 1),
        max_drawdown=float(drawdown.min()),
        trades=int(changes.sum()),
        equity=equity,
    )
