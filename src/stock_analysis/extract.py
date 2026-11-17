"""新聞 → 結構化事件（關鍵字、事件類型、情緒、重要性、相關主題與個股）。"""

from __future__ import annotations

import json
import logging

from .ai.base import AIError, AIProvider
from .news import NewsItem
from .themes import ThemeIndex

log = logging.getLogger(__name__)

EVENT_TYPES = {
    "war": "戰爭/地緣政治",
    "politics": "政治/政策",
    "central_bank": "央行/利率",
    "macro_data": "經濟數據",
    "trade": "關稅/貿易",
    "pandemic": "疫情",
    "financial_crisis": "金融危機",
    "disaster": "天災",
    "supply_price": "產業供需/報價",
    "earnings": "財報/營收",
    "technology": "技術/產業趨勢",
    "corporate": "公司消息",
    "market": "市場/資金面",
    "other": "其他",
}
REGIONS = ["us", "tw", "cn", "jp", "kr", "eu", "me", "global", "other"]


def extraction_schema(theme_ids: list[str], macro_ids: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "summary": {"type": "string"},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                        "event_type": {"type": "string", "enum": list(EVENT_TYPES)},
                        "sentiment": {"type": "number"},
                        "importance": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
                        "themes": {"type": "array", "items": {"type": "string", "enum": theme_ids}},
                        "macro_factors": {"type": "array", "items": {"type": "string", "enum": macro_ids}},
                        "tickers": {"type": "array", "items": {"type": "string"}},
                        "region": {"type": "string", "enum": REGIONS},
                    },
                    "required": [
                        "id", "summary", "keywords", "event_type", "sentiment",
                        "importance", "themes", "macro_factors", "tickers", "region",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    }


def system_prompt(index: ThemeIndex) -> str:
    return f"""你是專業的台股與美股財經新聞分析師。你的工作是把每則新聞轉成結構化資料，
讓系統統計關鍵字熱度、判斷各產業與大盤的多空。

每則新聞請輸出：
- summary：一句話繁體中文摘要（30 字內），寫出「發生什麼事、影響誰」
- keywords：3~6 個關鍵字，用市場常用說法（例如「HBM」「DRAM 合約價」「升息」「關稅」），中英文都可
- event_type：事件類型
- sentiment：對「相關股票」的影響，-1（非常負面）到 +1（非常正面），0 為中性
- importance：1~5，5 代表會明顯影響大盤或整個產業的重大事件
- themes / macro_factors：只能從下方清單挑選 id
- tickers：受影響的個股，用 Yahoo 代號（台股上市 2330.TW、上櫃 8299.TWO、美股 NVDA）
- region：事件發生的主要區域

判斷原則：
- 想清楚「因果鏈」：例如記憶體報價上漲 → 記憶體廠營收增加 → 南亞科、華邦電偏多；
  油價大漲 → 航空股成本上升偏空、塑化股偏多
- 標題聳動但沒有實質內容的新聞，importance 給低分
- 不確定的事情不要編造，tickers 可以留空

{index.prompt_catalog()}
"""


def ai_extract(provider: AIProvider, items: list[NewsItem], index: ThemeIndex, batch_size: int = 20):
    """用 AI 抽取；回傳 (結果 dict list, usage list)。"""
    schema = extraction_schema(list(index.themes), list(index.macros))
    system = system_prompt(index)
    results, usages = [], []
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        payload = [{"id": n.id, "title": n.title, "summary": n.summary, "source": n.source} for n in batch]
        user = "請分析以下新聞：\n" + json.dumps(payload, ensure_ascii=False)
        try:
            data, usage = provider.generate_json(
                tier="fast", system=system, user=user, schema=schema, max_tokens=8000
            )
        except AIError as e:
            log.warning("%s 新聞抽取失敗，這批改用規則式：%s", provider.name, e)
            results.extend(rule_extract(batch, index))
            continue
        usages.append(usage)
        by_id = {d.get("id"): d for d in data.get("items", [])}
        for n in batch:
            d = by_id.get(n.id)
            results.append(_merge(n, d, provider.name) if d else rule_extract([n], index)[0])
    return results, usages


def _merge(n: NewsItem, d: dict, by: str) -> dict:
    out = n.to_dict()
    out.update(
        {
            "ai_summary": d.get("summary", ""),
            "keywords": [k.strip() for k in d.get("keywords", []) if k.strip()][:8],
            "event_type": d.get("event_type", "other"),
            "sentiment": max(-1.0, min(1.0, float(d.get("sentiment", 0)))),
            "importance": int(d.get("importance", 2)),
            "themes": d.get("themes", []),
            "macro_factors": d.get("macro_factors", []),
            "tickers": d.get("tickers", []),
            "region": d.get("region", "other"),
            "analyzed_by": by,
        }
    )
    return out


# ---------------- 規則式（模擬 AI） ----------------

_POS = ["漲", "上漲", "大漲", "飆", "創新高", "新高", "優於預期", "超乎預期", "上修", "調升", "成長", "暢旺",
        "受惠", "利多", "擴產", "買超", "降息", "回升", "走強", "強勁", "滿到",
        "jump", "surge", "soar", "rally", "beat", "record", "upgrade", "raise", "strong", "gain", "rise"]
_NEG = ["跌", "下跌", "重挫", "暴跌", "崩", "下修", "低於預期", "不如預期", "衰退", "利空", "承壓", "走弱",
        "賣超", "制裁", "管制", "衝突", "戰爭", "倒閉", "違約", "裁員", "停工", "疑慮", "擔憂", "鷹派",
        "fall", "drop", "plunge", "slump", "miss", "cut", "downgrade", "weak", "slip", "fear", "tariff", "war"]
_STRONG = ["暴跌", "重挫", "崩", "大漲", "創新高", "史上", "急漲", "plunge", "soar", "record", "crash"]

_TYPE_HINTS = [
    ("earnings", ["財報", "營收", "獲利", "EPS", "財測", "earnings", "guidance", "revenue"]),
    ("supply_price", ["報價", "合約價", "現貨價", "漲價", "減產", "運價", "產能", "price"]),
    ("technology", ["新一代", "技術", "量產", "發表", "launch"]),
]


def rule_extract(items: list[NewsItem], index: ThemeIndex) -> list[dict]:
    out = []
    for n in items:
        text = f"{n.title} {n.summary}"
        m = index.match(text)
        low = text.lower()
        pos = sum(low.count(w.lower()) for w in _POS)
        neg = sum(low.count(w.lower()) for w in _NEG)
        sentiment = 0.0 if pos == neg else round((pos - neg) / (pos + neg), 2)

        event_type = "other"
        if m.macros:
            event_type = index.macros[m.macros[0]].get("category", "other")
        else:
            for et, hints in _TYPE_HINTS:
                if any(h.lower() in low for h in hints):
                    event_type = et
                    break
            else:
                if m.themes or m.tickers:
                    event_type = "corporate"

        importance = 2 + min(2, len(m.themes) + len(m.macros))
        if any(w.lower() in low for w in _STRONG):
            importance += 1
        if event_type in ("war", "financial_crisis", "pandemic"):
            importance += 1
        importance = max(1, min(5, importance))

        # 總經因素對主題的影響方向（例如戰爭 → 國防偏多）
        for mid in m.macros:
            for tid in index.macros[mid].get("impact", {}):
                if tid in index.themes and tid not in m.themes:
                    m.themes.append(tid)

        d = n.to_dict()
        d.update(
            {
                "ai_summary": n.title,
                "keywords": m.keywords[:6],
                "event_type": event_type,
                "sentiment": sentiment,
                "importance": importance,
                "themes": m.themes,
                "macro_factors": m.macros,
                "tickers": m.tickers,
                "region": "tw" if any(t.endswith((".TW", ".TWO")) for t in m.tickers) else "global",
                "analyzed_by": "mock",
            }
        )
        out.append(d)
    return out


def extract(provider: AIProvider, items: list[NewsItem], index: ThemeIndex, batch_size: int = 20):
    if provider.is_mock:
        return rule_extract(items, index), []
    return ai_extract(provider, items, index, batch_size)


def relevance(n: NewsItem, index: ThemeIndex) -> int:
    """新聞與我們關心的主題有多相關（用來在 AI 分析前先篩選，節省費用）。"""
    m = index.match(f"{n.title} {n.summary}")
    return len(m.themes) * 2 + len(m.macros) * 2 + len(m.tickers)
