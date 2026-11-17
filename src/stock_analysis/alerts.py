"""警示規則：重大新聞、自選股大漲大跌、大盤大漲大跌、關鍵字暴增，以及 AI 提出的警示。"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from .timeutil import iso, parse_iso


def _aid(*parts) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:10]


def build_alerts(cfg, now: datetime, *, events, watchlist, indices, keywords, reports) -> list[dict]:
    a = cfg.get("alerts", {}) or {}
    out = []
    day = now.strftime("%Y-%m-%d")

    for e in events:
        if e.get("importance", 0) >= int(a.get("news_importance", 5)):
            out.append({
                "id": _aid("news", e["id"]), "level": "critical" if abs(e.get("sentiment", 0)) >= 0.5 else "warning",
                "kind": "news", "title": "重大新聞", "body": e.get("ai_summary") or e["title"], "url": e.get("url"),
            })
    for s in watchlist:
        ch = s.get("change_pct")
        if ch is not None and abs(ch) >= float(a.get("stock_move_pct", 5)):
            out.append({
                "id": _aid("stock", s["symbol"], s["date"]), "level": "warning", "kind": "stock",
                "title": f"{s['name']} {'大漲' if ch > 0 else '大跌'} {ch:+.2f}%",
                "body": f"{s['symbol']} 收 {s['close']}，5 日 {s.get('change_5d_pct')}%", "symbol": s["symbol"],
            })
    for s in indices:
        ch = s.get("change_pct")
        if ch is not None and abs(ch) >= float(a.get("index_move_pct", 2)):
            out.append({
                "id": _aid("index", s["symbol"], s["date"]), "level": "critical" if abs(ch) >= 3 else "warning",
                "kind": "index", "title": f"{s['name']} {'大漲' if ch > 0 else '大跌'} {ch:+.2f}%",
                "body": f"收 {s['close']}", "symbol": s["symbol"],
            })
    for k in keywords:
        if k["ratio"] >= float(a.get("keyword_spike_ratio", 3)) and k["count_24h"] >= int(a.get("keyword_spike_min_count", 5)):
            out.append({
                "id": _aid("kw", k["keyword"], day), "level": "info", "kind": "keyword",
                "title": f"關鍵字暴增：{k['keyword']}",
                "body": f"近 24 小時 {k['count_24h']} 次，是平常的 {k['ratio']} 倍",
            })
    for name, r in reports.items():
        for al in r.get("alerts", []):
            out.append({
                "id": _aid("ai", name, al.get("title"), day), "level": al.get("level", "info"), "kind": "ai",
                "title": al.get("title", ""), "body": al.get("body", ""), "by": name,
            })
    for x in out:
        x["created_at"] = iso(now)
    return out


def merge_alerts(state: dict, new: list[dict], now: datetime, keep_hours: int = 72) -> tuple[list[dict], list[dict]]:
    """合併到歷史警示；回傳 (全部近期警示, 這次新增的)。"""
    old = state.get("items", [])
    seen = {x["id"] for x in old}
    fresh = [x for x in new if x["id"] not in seen]
    cutoff = now - timedelta(hours=keep_hours)
    items = [x for x in old + fresh if parse_iso(x["created_at"]) >= cutoff]
    items.sort(key=lambda x: x["created_at"], reverse=True)
    state["items"] = items[:200]
    return state["items"], fresh
