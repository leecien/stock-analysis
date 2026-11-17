# 股票 AI 分析系統

每小時自動抓新聞、用 AI 抽取關鍵字，分析美股和台股的大盤、產業主題與個股，
並對照 2006 年至今的歷史事件（戰爭、政治、利率、疫情、產業報價……）。
結果顯示在 Android App 上，有重大事件時會推播通知。

> 沒有 AI 金鑰也能完整運作：系統會改用「模擬 AI」（規則式分析），畫面與功能都一樣。
> 接上金鑰後自動切換成真正的 AI 分析，見 [docs/SETUP.md](docs/SETUP.md)。

## 架構

```
GitHub Actions（每小時自動執行，免費）
  ├ 抓股價：美股、台股、指數、總經（yfinance）
  ├ 抓新聞：Google News、鉅亨網、Yahoo Finance、CNBC、Fed
  ├ AI 抽取：關鍵字、事件類型、情緒、重要性、受影響的主題與個股
  ├ 關鍵字熱度：近 24 小時 vs 前 7 天，找出突然暴增的關鍵字
  ├ 歷史類比：從 20 年事件庫找類似事件，以及當時大盤之後的漲跌
  ├ 每小時報告：美股 / 台股大盤 → 產業主題 → 自選股
  ├ 深度分析：每天 08:00、22:00，多家 AI 交叉比對並做預測
  ├ 準確率：預測到期後自動比對實際漲跌
  └ 結果存到 data 分支 → App 讀取

Android App（Flutter）
  總覽｜熱門關鍵字與新聞｜產業主題｜自選股｜20 年歷史事件｜警示通知｜AI 準確率與花費
```

## 專案結構

```
config/
  settings.yaml        排程、AI 模型、預算、警示門檻、新聞來源
  watchlist.yaml       自選股
  themes.yaml          產業主題對照表（關鍵字 → 主題 → 個股）與總經因素
data/seed/
  major_events.yaml    2006 年至今重大事件（人工整理）
src/stock_analysis/
  pipeline.py          主流程
  news.py              新聞抓取
  extract.py           新聞 → 結構化事件（AI / 規則式）
  keywords.py          關鍵字熱度、主題情緒
  history.py           20 年歷史事件庫
  analysis.py          大盤、主題、個股分析與多家 AI 共識
  predictions.py       預測紀錄與準確率
  alerts.py            警示規則
  budget.py            AI 花費控管（每月台幣預算）
  ai/                  Claude、Gemini、OpenAI、模擬 AI
app/                   Android App（Flutter）
.github/workflows/     自動測試、編譯 APK、每小時分析
```

## 在電腦上執行（選用）

```bash
pip install -e ".[dev]"

# 用示範資料跑一次（不需要網路和金鑰）
python -m stock_analysis --demo history
python -m stock_analysis --demo hourly --deep

# 真實資料（沒有金鑰時自動用模擬 AI）
python -m stock_analysis history
python -m stock_analysis hourly

python -m stock_analysis status         # 檢查金鑰與花費
python -m stock_analysis analyze 2330   # 快速看個股技術面
pytest                                  # 測試
```

結果會寫到 `public/latest.json`、`public/history.json`。

## 安裝 App

1. 打開 GitHub 上這個 repo 的 **Releases**，下載最新的 `stock-ai-xx.apk`
2. 在手機上點開安裝（第一次需要允許「安裝不明來源的應用程式」）
3. App 預設顯示內建示範資料；後端架好後到「設定」切換成 GitHub

每次修改 `app/` 底下的程式，GitHub Actions 都會自動編譯新版 APK。

---

本系統內容由程式與 AI 自動產生，僅供研究參考，不構成任何投資建議。
