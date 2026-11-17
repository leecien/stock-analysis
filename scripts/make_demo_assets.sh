#!/usr/bin/env bash
# 用示範資料跑一次後端，產生 App 內建的示範資料（app/assets/demo/）
set -euo pipefail
cd "$(dirname "$0")/.."
TMP=$(mktemp -d)
export PYTHONPATH=src STOCK_ROOT=$PWD
python -m stock_analysis --demo --mock-ai --state-dir "$TMP/state" --out-dir "$TMP/public" history
python -m stock_analysis --demo --mock-ai --state-dir "$TMP/state" --out-dir "$TMP/public" hourly --deep
cp "$TMP/public/latest.json" "$TMP/public/history.json" app/assets/demo/
echo "已更新 app/assets/demo/"
