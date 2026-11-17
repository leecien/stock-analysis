# stock-analysis

股票分析工具（Python）：抓取台股／美股股價、計算技術指標、回測簡單策略。

## 功能

- **資料抓取**：使用 yfinance，台股代號自動補 `.TW`（例如 `2330` → `2330.TW`）
- **技術指標**：SMA、EMA、RSI、MACD
- **回測**：SMA 均線交叉策略（含手續費、避免前視偏差），輸出報酬、最大回撤、交易次數

## 安裝

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 使用

```bash
PYTHONPATH=src python -m stock_analysis.cli 2330 0050 AAPL --period 2y
```

## 測試

```bash
pytest
```

## 專案結構

```
src/stock_analysis/
  data.py        # 股價資料抓取
  indicators.py  # 技術指標
  backtest.py    # 策略回測
  cli.py         # 命令列入口
tests/           # 單元測試
```

> 本專案僅供學習研究，不構成任何投資建議。
