# 串接設定（API 金鑰、每小時排程、App 連線）

整套系統已經可以在「沒有任何金鑰」的情況下運作。以下步驟可以分開做，做完一步就多一項功能。

## 1. 開啟每小時自動分析（免費）

1. GitHub repo → **Settings → Secrets and variables → Actions → Variables** 分頁
2. 按 **New repository variable**：名稱 `PIPELINE_ENABLED`，值 `true`
3. 之後每小時會自動執行。也可以到 **Actions → 每小時 AI 分析 → Run workflow** 手動執行

第一次執行會建立 20 年歷史事件庫（約 1～3 分鐘），結果存到 `data` 分支。
沒有 AI 金鑰時使用模擬 AI，股價和新聞都是真實資料。

## 2. App 連線到後端

私人 repo 需要一組「只能讀這個 repo」的 Token：

1. GitHub 右上角頭像 → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**
2. Repository access 選 **Only select repositories** → `stock-analysis`
3. Permissions → Repository permissions → **Contents：Read-only**
4. 產生後複製 Token
5. App → 右上角 ⚙️ 設定 → 資料來源選 **GitHub** → 貼上 Token → **測試連線** → **儲存**

## 3. 接上 Claude（主要 AI，付費）

1. 到 <https://console.anthropic.com> 註冊並儲值（先 US$10～20）
2. **API Keys → Create Key**，複製金鑰
3. GitHub repo → **Settings → Secrets and variables → Actions → Secrets → New repository secret**
   - 名稱：`ANTHROPIC_API_KEY`
   - 值：貼上金鑰
4. 到 Actions 手動執行一次「每小時 AI 分析」，勾選「重建 20 年歷史事件庫」，讓 AI 標註歷史漲跌原因

⚠️ 金鑰只放在 GitHub Secrets，不要貼到聊天或寫進程式碼。

使用的模型（可在 `config/settings.yaml` 修改）：

| 用途 | 模型 | 頻率 |
|---|---|---|
| 新聞抽取、每小時報告 | `claude-haiku-5-5` | 每小時 |
| 深度分析、歷史事件標註 | `claude-sonnet-5-5` | 每天 2 次 |

## 4. 接上 Gemini（交叉比對，免費額度）

1. 到 <https://aistudio.google.com> → **Get API key**
2. GitHub Secrets 新增 `GEMINI_API_KEY`
3. 到 <https://ai.google.dev/gemini-api/docs/models> 確認目前可用的模型名稱，必要時修改 `config/settings.yaml` 的 `gemini.fast_model / deep_model`

## 5. 接上 ChatGPT（交叉驗證）

程式已經設定好：只要 GitHub Secrets 有 `OPENAI_API_KEY`，每天 08:00、22:00 的深度分析就會多一家 ChatGPT，
和 Claude、Gemini 各自獨立分析、各自預測，再比對意見一致度與事後準確率。

1. 到 <https://platform.openai.com> 用帳號登入（ChatGPT Plus 訂閱不能給程式用，API 要另外儲值）
2. **Settings → Billing**：儲值 US$5～10；在 **Limits** 設每月上限，避免超支
3. **API keys → Create new secret key**，複製金鑰
4. GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**：名稱 `OPENAI_API_KEY`
5. 到 <https://openai.com/api/pricing/> 確認目前最便宜的 mini / nano 模型名稱與價格，
   和 `config/settings.yaml` 的 `openai.deep_model`、`pricing` 不同時請更新（價格只影響 App 顯示的花費統計）
6. Actions → 每小時 AI 分析 → Run workflow，勾選「強制執行深度分析」測試一次

驗證結果在 App：
- 總覽 → AI 深度分析：每家 AI 一個分頁，最下方有「各家 AI 意見一致度」
- 大盤卡與自選股：顯示每家 AI 的偏多 / 中性 / 偏空
- AI 預測準確率與花費：每家 AI 各自的答對率（預測 5 個交易日後到期才會開始累積）

## 預算控管

`config/settings.yaml` 的 `budget`：

- `monthly_twd: 600`：每月預算（台幣）
- 花費到 85% → 暫停深度分析
- 花費到 100% → 全部改用模擬 AI，不再花錢

App 的「AI 預測準確率與花費」頁面可以看到本月花費。另外，Claude API 是預先儲值制，儲值多少最多就只會用多少。

## 修改自選股和產業主題

- 自選股：`config/watchlist.yaml`
- 產業主題、關鍵字、代表個股：`config/themes.yaml`
- 歷史重大事件：`data/seed/major_events.yaml`

改完 commit 到 main，下一次排程就會套用。

## （選用）正式簽章金鑰

APK 預設使用 repo 內固定的除錯金鑰簽章，每次更新都可以直接覆蓋安裝。
想改用自己的金鑰時，在 GitHub Secrets 設定：
`ANDROID_KEYSTORE_BASE64`、`ANDROID_KEYSTORE_PASSWORD`、`ANDROID_KEY_ALIAS`、`ANDROID_KEY_PASSWORD`。
換金鑰後第一次更新需要先移除舊版 App。

## GitHub Actions 用量

私人 repo 每月有 2,000 分鐘免費額度。每小時分析每次約 1～2 分鐘，加上偶爾編譯 APK，通常在額度內。
到 **Settings → Billing** 可以查看用量；額度不夠時，可以在 `.github/workflows/pipeline.yml` 把排程改成每 2 小時一次（`7 */2 * * *`）。
