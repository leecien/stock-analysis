"""命令列：

  python -m stock_analysis hourly            每小時分析（GitHub Actions 每小時呼叫）
  python -m stock_analysis hourly --deep     強制執行深度分析
  python -m stock_analysis history           建立 / 更新 20 年歷史事件庫
  python -m stock_analysis status            檢查 AI 金鑰與本月花費
  python -m stock_analysis analyze 2330 NVDA 快速看個股技術面與回測

共用參數：--demo（用示範資料，不上網）、--mock-ai（不呼叫 AI）、--state-dir、--out-dir
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from .config import load_config
from .store import Store


def _store(args, root: Path) -> Store:
    return Store(Path(args.state_dir or root / "state"), Path(args.out_dir or root / "public"))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="stock_analysis", description="股票 AI 分析系統")
    parser.add_argument("--state-dir")
    parser.add_argument("--out-dir")
    parser.add_argument("--demo", action="store_true", help="使用示範資料（不連網）")
    parser.add_argument("--mock-ai", action="store_true", help="不呼叫 AI，使用規則式分析")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hourly", help="每小時分析")
    h.add_argument("--deep", action="store_true", help="強制執行深度分析")
    sub.add_parser("history", help="建立歷史事件庫")
    sub.add_parser("status", help="檢查設定與花費")
    a = sub.add_parser("analyze", help="快速看個股")
    a.add_argument("symbols", nargs="+")
    a.add_argument("--period", default="2y")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    cfg = load_config()

    if args.cmd == "hourly":
        from .pipeline import run_hourly
        res = run_hourly(cfg, _store(args, cfg.root), demo=args.demo, force_deep=args.deep, mock_ai=args.mock_ai)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.cmd == "history":
        from .pipeline import run_build_history
        res = run_build_history(cfg, _store(args, cfg.root), demo=args.demo, mock_ai=args.mock_ai)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.cmd == "status":
        from .budget import Budget
        from .timeutil import utcnow
        st = _store(args, cfg.root)
        b = Budget(cfg, st.load_state("budget"), utcnow())
        print("AI 金鑰：")
        for name, conf in (cfg.get("ai.providers", {}) or {}).items():
            ok = bool(os.environ.get(conf.get("env_key", "")))
            print(f"  {name:8s} {conf.get('env_key')}: {'已設定' if ok else '未設定（使用模擬 AI）'}")
        print(f"本月花費：NT${b.spent_twd:.1f} / NT${b.limit_twd:.0f}（{b.ratio:.0%}）")
    elif args.cmd == "analyze":
        from .backtest import sma_crossover
        from .data import load_prices, normalize_symbol
        from .indicators import add_indicators
        prices, demo = load_prices(args.symbols, period=args.period, demo=args.demo)
        if demo:
            print("（注意：目前使用示範資料）")
        for symbol in args.symbols:
            t = normalize_symbol(symbol)
            df = add_indicators(prices[t])
            last = df.iloc[-1]
            print(f"\n===== {t} =====")
            print(f"日期: {df.index[-1].date()}  收盤: {last['Close']:.2f}")
            print(f"SMA20: {last['SMA20']:.2f}  SMA60: {last['SMA60']:.2f}  RSI14: {last['RSI14']:.1f}  MACD: {last['macd']:.3f}")
            print("--- SMA20/60 交叉回測 ---")
            print(sma_crossover(df["Close"]).summary())


if __name__ == "__main__":
    main()
