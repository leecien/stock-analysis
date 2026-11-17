"""綜合分析：大盤（美股、台股）→ 產業主題 → 個股。

- hourly：每小時快速報告（便宜模型）
- deep：每天 2 次深度分析（較強模型，可多家 AI），含預測，事後追蹤準確率
沒有 AI 時使用規則式分析（技術面 + 新聞情緒），結構完全相同。
"""

from __future__ import annotations

import json
import logging
from collections import Counter

from .ai.base import AIError, AIProvider
from .themes import ThemeIndex

log = logging.getLogger(__name__)

STANCES = ["bullish", "neutral", "bearish"]
STANCE_ZH = {"bullish": "偏多", "neutral": "中性", "bearish": "偏空"}

_VIEW = {
    "type": "object",
    "properties": {
        "stance": {"type": "string", "enum": STANCES},
        "confidence": {"type": "integer"},
        "summary": {"type": "string"},
        "drivers": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["stance", "confidence", "summary", "drivers", "risks"],
    "additionalProperties": False,
}


def _obj(props: dict) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def report_schema(deep: bool) -> dict:
    props = {
        "headline": {"type": "string"},
        "us": _VIEW,
        "tw": _VIEW,
        "themes": {"type": "array", "items": _obj({
            "id": {"type": "string"},
            "stance": {"type": "string", "enum": STANCES},
            "reason": {"type": "string"},
        })},
        "stocks": {"type": "array", "items": _obj({
            "symbol": {"type": "string"},
            "stance": {"type": "string", "enum": STANCES},
            "reason": {"type": "string"},
        })},
        "alerts": {"type": "array", "items": _obj({
            "level": {"type": "string", "enum": ["info", "warning", "critical"]},
            "title": {"type": "string"},
            "body": {"type": "string"},
        })},
    }
    if deep:
        props["outlook"] = _obj({"short_term": {"type": "string"}, "medium_term": {"type": "string"}})
        props["historical_view"] = {"type": "string"}
        props["predictions"] = {"type": "array", "items": _obj({
            "target": {"type": "string"},
            "horizon_days": {"type": "integer", "enum": [1, 5, 20]},
            "direction": {"type": "string", "enum": ["up", "down", "flat"]},
            "confidence": {"type": "integer"},
            "rationale": {"type": "string"},
        })}
    return _obj(props)


SYSTEM_BASE = """你是資深的台股與美股策略分析師，服務對象是一位自己做研究的個人投資人。
你會拿到：大盤與自選股的技術面數據、近期新聞的結構化分析、關鍵字熱度、
產業主題情緒，以及「歷史上類似事件發生後大盤的漲跌」。

分析要求：
- 由上而下：先判斷美股、台股大盤，再看產業主題，最後看個股
- 每個判斷都要說出「因果鏈」與依據（新聞、數據、歷史類比），不要空泛
- 美股走勢常在隔天影響台股；費城半導體與台積電 ADR 對台股電子股特別重要
- 新聞情緒與技術面矛盾時，要說明你比較相信哪一個、為什麼
- confidence 為 0~100 的整數；資料不足時降低 confidence，不要硬給結論
- alerts 只放真正重要、需要立即注意的事（沒有就給空陣列）
- 這是研究參考，不是投資建議；不要使用保證獲利之類的字眼
- 一律使用繁體中文
"""

DEEP_EXTRA = """
這是「深度分析」，請額外提供：
- outlook：短期（1~5 個交易日）與中期（1~3 個月）展望
- historical_view：目前情勢和哪些歷史事件相似、當時後來怎麼走、這次有什麼不同
- predictions：對 ^GSPC、^TWII 以及每檔自選股，各給 horizon_days 為 5 的方向預測
  （up / down / flat，flat 代表漲跌在 ±1% 內）。系統會在到期後自動比對實際結果
"""


def build_context(
    *, now_tw: str, session: str, indices: list[dict], macro: list[dict], watchlist: list[dict],
    themes: dict, index: ThemeIndex, keywords: list[dict], events: list[dict], analogs: list[dict],
    category_stats: list[dict],
) -> dict:
    def strip(s: dict) -> dict:
        return {k: s.get(k) for k in ("symbol", "name", "close", "change_pct", "change_5d_pct", "change_20d_pct", "rsi", "trend")}

    present = {e.get("event_type") for e in events}
    top_news = sorted(events, key=lambda e: (e.get("importance", 0), e.get("published", "")), reverse=True)[:25]
    return {
        "time_tw": now_tw,
        "session": session,
        "indices": [strip(s) for s in indices],
        "macro": [strip(s) for s in macro],
        "watchlist": [strip(s) for s in watchlist],
        "themes": [
            {"id": t, "name": index.theme_name(t), "news_24h": v["news_24h"], "sentiment": v["sentiment"]}
            for t, v in sorted(themes.items(), key=lambda kv: kv[1]["news_24h"], reverse=True)
            if v["news_24h"] > 0
        ],
        "trending_keywords": [{"k": k["keyword"], "n": k["count_24h"], "x": k["ratio"]} for k in keywords[:15]],
        "news": [
            {
                "title": e["title"], "summary": e.get("ai_summary", ""), "type": e.get("event_type"),
                "sentiment": e.get("sentiment"), "importance": e.get("importance"),
                "themes": e.get("themes", []), "tickers": e.get("tickers", []),
            }
            for e in top_news
        ],
        "historical_analogs": analogs[:6],
        "history_stats": [c for c in category_stats if c["category"] in present][:6],
    }


def ai_report(provider: AIProvider, ctx: dict, index: ThemeIndex, deep: bool) -> tuple[dict, list]:
    system = SYSTEM_BASE + (DEEP_EXTRA if deep else "") + "\n" + index.prompt_catalog()
    user = "以下是目前的市場資料（JSON）：\n" + json.dumps(ctx, ensure_ascii=False)
    data, usage = provider.generate_json(
        tier="deep" if deep else "fast", system=system, user=user,
        schema=report_schema(deep), max_tokens=16000,
    )
    for k in ("us", "tw"):
        data[k]["confidence"] = max(0, min(100, int(data[k].get("confidence", 50))))
    for p in data.get("predictions", []):
        p["confidence"] = max(0, min(100, int(p.get("confidence", 50))))
    data["by"] = provider.name
    data["model"] = usage.model
    return data, [usage]


# ---------------- 規則式（模擬 AI） ----------------


def _stance(score: float, hi: float = 0.6) -> str:
    return "bullish" if score >= hi else "bearish" if score <= -hi else "neutral"


def _region_sentiment(events: list[dict], regions: set[str]) -> float:
    w = s = 0.0
    for e in events:
        if e.get("region") in regions or e.get("region") == "global":
            wt = float(e.get("importance", 2))
            w += wt
            s += wt * float(e.get("sentiment", 0))
    return s / w if w else 0.0


def rule_report(ctx_raw: dict, index: ThemeIndex, deep: bool) -> dict:
    indices, watchlist, events, themes = ctx_raw["indices"], ctx_raw["watchlist"], ctx_raw["events"], ctx_raw["themes"]
    by_sym = {s["symbol"]: s for s in indices + watchlist}

    def view(syms: list[str], regions: set[str], label: str) -> dict:
        snaps = [by_sym[s] for s in syms if s in by_sym]
        tech = sum(s["trend_score"] for s in snaps) / len(snaps) if snaps else 0.0
        senti = _region_sentiment(events, regions)
        score = tech / 3 + senti
        rel = [e for e in events if e.get("region") in regions | {"global"}]
        pos = [e for e in sorted(rel, key=lambda e: -e.get("importance", 0)) if e.get("sentiment", 0) > 0.2][:3]
        neg = [e for e in sorted(rel, key=lambda e: -e.get("importance", 0)) if e.get("sentiment", 0) < -0.2][:3]
        moves = "、".join(f"{s['name']} {s['change_pct']:+.2f}%" for s in snaps if s.get("change_pct") is not None)
        st = _stance(score, 0.35)
        return {
            "stance": st,
            "confidence": int(min(75, 40 + abs(score) * 30)),
            "summary": f"{label}技術面{('偏多' if tech > 0.5 else '偏空' if tech < -0.5 else '中性')}"
            f"（{moves or '無資料'}），新聞情緒 {senti:+.2f}，綜合判斷{STANCE_ZH[st]}。",
            "drivers": [e.get("ai_summary") or e["title"] for e in pos],
            "risks": [e.get("ai_summary") or e["title"] for e in neg],
        }

    us = view(["^GSPC", "^IXIC", "^SOX"], {"us"}, "美股")
    tw = view(["^TWII"], {"tw"}, "台股")

    theme_rows = []
    for tid, v in sorted(themes.items(), key=lambda kv: kv[1]["news_24h"], reverse=True):
        if v["news_24h"] == 0:
            continue
        st = _stance(v["sentiment"], 0.25)
        theme_rows.append({
            "id": tid,
            "stance": st,
            "reason": f"近 24 小時 {v['news_24h']} 則相關新聞，情緒 {v['sentiment']:+.2f}，判斷{STANCE_ZH[st]}。",
        })

    theme_of_symbol: dict[str, list[str]] = {}
    for tid in index.themes:
        for s in index.theme_symbols(tid):
            theme_of_symbol.setdefault(s, []).append(tid)
    stock_rows = []
    for s in watchlist:
        ts = [themes[t]["sentiment"] for t in theme_of_symbol.get(s["symbol"], []) if t in themes and themes[t]["news_24h"]]
        senti = sum(ts) / len(ts) if ts else 0.0
        mentioned = [e for e in events if s["symbol"] in e.get("tickers", [])]
        if mentioned:
            senti = (senti + sum(e.get("sentiment", 0) for e in mentioned) / len(mentioned)) / 2
        score = s["trend_score"] / 3 + senti
        st = _stance(score, 0.35)
        stock_rows.append({
            "symbol": s["symbol"],
            "stance": st,
            "reason": f"技術面{s['trend']}（RSI {s.get('rsi')}），相關新聞 {len(mentioned)} 則、產業情緒 {senti:+.2f}，判斷{STANCE_ZH[st]}。",
            "_score": score,
        })

    top = max(events, key=lambda e: (e.get("importance", 0), e.get("published", "")), default=None)
    report = {
        "headline": (top.get("ai_summary") or top["title"]) if top else "目前沒有重大新聞",
        "us": us,
        "tw": tw,
        "themes": theme_rows,
        "stocks": [{k: v for k, v in r.items() if k != "_score"} for r in stock_rows],
        "alerts": [],
        "by": "mock",
        "model": "rule-based",
    }
    if deep:
        preds = []
        for sym, v in (("^GSPC", us), ("^TWII", tw)):
            preds.append(_pred(sym, {"bullish": 1, "neutral": 0, "bearish": -1}[v["stance"]], v["confidence"]))
        for r in stock_rows:
            preds.append(_pred(r["symbol"], r["_score"], int(min(70, 40 + abs(r["_score"]) * 25))))
        report["outlook"] = {
            "short_term": f"美股{STANCE_ZH[us['stance']]}、台股{STANCE_ZH[tw['stance']]}（規則式判斷，僅供參考）。",
            "medium_term": "中期展望需要接上 AI 後才會產生。",
        }
        report["historical_view"] = "；".join(
            f"{a['title']} → 類似：{a['matches'][0]['title']}（{a['matches'][0]['date']}）"
            for a in ctx_raw.get("analogs", []) if a.get("matches")
        )[:400] or "目前沒有找到明顯類似的歷史事件。"
        report["predictions"] = preds
    return report


def _pred(target: str, score: float, conf: int) -> dict:
    d = "up" if score >= 0.35 else "down" if score <= -0.35 else "flat"
    return {"target": target, "horizon_days": 5, "direction": d, "confidence": conf, "rationale": "規則式：技術面 + 新聞情緒"}


def make_report(provider: AIProvider, ctx_ai: dict, ctx_raw: dict, index: ThemeIndex, deep: bool) -> tuple[dict, list]:
    if provider.is_mock:
        return rule_report(ctx_raw, index, deep), []
    try:
        return ai_report(provider, ctx_ai, index, deep)
    except AIError as e:
        log.warning("%s 分析失敗，改用規則式：%s", provider.name, e)
        r = rule_report(ctx_raw, index, deep)
        r["fallback_reason"] = str(e)
        return r, []


def consensus(reports: dict[str, dict]) -> dict:
    """多家 AI 的看法比較：每個標的的多數意見與一致程度。"""
    targets: dict[str, list[tuple[str, str]]] = {}
    for name, r in reports.items():
        for k in ("us", "tw"):
            if r.get(k):
                targets.setdefault(k, []).append((name, r[k]["stance"]))
        for s in r.get("stocks", []):
            targets.setdefault(s["symbol"], []).append((name, s["stance"]))
    out = {}
    for t, votes in targets.items():
        c = Counter(v for _, v in votes)
        stance, n = c.most_common(1)[0]
        out[t] = {"stance": stance, "agreement": round(n / len(votes), 2), "votes": dict(votes)}
    return out
