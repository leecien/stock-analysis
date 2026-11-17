"""命令列入口：python -m stock_analysis.cli 2330"""

from __future__ import annotations

import argparse

from .backtest import sma_crossover
from .data import fetch_history, normalize_symbol
from .indicators import add_indicators


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="股票分析")
    parser.add_argument("symbols", nargs="+", help="股票代號，例如 2330 0050 AAPL")
    parser.add_argument("--period", default="2y", help="資料期間，例如 6mo、1y、5y")
    args = parser.parse_args(argv)

    for symbol in args.symbols:
        ticker = normalize_symbol(symbol)
        print(f"\n===== {ticker} =====")
        df = add_indicators(fetch_history(symbol, period=args.period))
        last = df.iloc[-1]
        print(f"日期: {df.index[-1].date()}  收盤: {last['Close']:.2f}")
        print(f"SMA20: {last['SMA20']:.2f}  SMA60: {last['SMA60']:.2f}")
        print(f"RSI14: {last['RSI14']:.1f}  MACD: {last['macd']:.3f}")
        print("--- SMA20/60 交叉回測 ---")
        print(sma_crossover(df["Close"]).summary())


if __name__ == "__main__":
    main()
