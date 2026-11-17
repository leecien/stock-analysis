"""主流程：每小時分析、建立歷史事件庫。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from . import alerts as alerts_mod
from . import predictions
from .ai import build_providers
from .ai.base import MockProvider
from .analysis import STANCE_ZH, build_context, consensus, make_report
from .budget import Budget
from .config import Config
from .data import load_prices
from .extract import EVENT_TYPES, extract, relevance
from .history import build_history, find_analogs
from .keywords import keyword_heat, theme_sentiment, update_keyword_state, update_theme_state
from .market import snapshots
from .news import NewsItem, collect_news, demo_news
from .store import Store
from .themes import ThemeIndex
from .timeutil import hour_key, iso, parse_iso, session_label, to_tw, utcnow

log = logging.getLogger(__name__)
SCHEMA_VERSION = 1


def _providers(cfg: Config, budget: Budget, tier: str, mock_ai: bool):
    if mock_ai or not budget.allow(tier):
        if not mock_ai:
            log.warning("本月 AI 花費已達上限（%.0f%%），%s 改用模擬 AI", budget.ratio * 100, tier)
        return [MockProvider()]
    return build_providers(cfg, tier)


def _filter_new(items: list[NewsItem], seen: dict, now: datetime) -> list[NewsItem]:
    cutoff = now - timedelta(days=7)
    for k in [k for k, v in seen.items() if parse_iso(v) < cutoff]:
        del seen[k]
    return [i for i in items if i.id not in seen]


def run_hourly(cfg: Config, store: Store, *, now: datetime | None = None, demo: bool = False,
               force_deep: bool = False, mock_ai: bool = False) -> dict:
    now = now or utcnow()
    now_tw = to_tw(now)
    index = ThemeIndex(cfg)
    budget = Budget(cfg, store.load_state("budget"), now)
    usages = []

    # ---------- 1. 股價 ----------
    names = {**index.symbol_names, **cfg.index_names}
    us_idx = list(cfg.get("markets.us.indices", {}))
    tw_idx = list(cfg.get("markets.tw.indices", {}))
    macro_syms = list(cfg.get("markets.macro", {}))
    symbols = us_idx + tw_idx + macro_syms + cfg.watchlist_symbols + index.all_symbols()
    prices, price_demo = load_prices(symbols, period="1y", demo=demo)

    # ---------- 2. 新聞 ----------
    sources: dict[str, str] = {}
    if demo:
        raw_news, news_demo = demo_news(now), True
    else:
        raw_news, sources = collect_news(cfg, now)
        news_demo = False
        if not raw_news and sources and all(v.startswith("error") for v in sources.values()):
            log.warning("所有新聞來源都失敗，改用示範新聞")
            raw_news, news_demo = demo_news(now), True
    seen = store.load_state("news_seen")
    new_items = _filter_new(raw_news, seen, now)
    new_items.sort(key=lambda n: relevance(n, index), reverse=True)
    new_items = new_items[: int(cfg.get("ai.max_news_per_hour", 120))]

    # ---------- 3. AI 抽取 ----------
    fast = _providers(cfg, budget, "fast", mock_ai)[0]
    events_new, u = extract(fast, new_items, index, int(cfg.get("ai.news_batch_size", 20)))
    usages += u
    for n in new_items:
        seen[n.id] = iso(now)

    recent = store.load_state("events_recent", {"items": []})["items"]
    cutoff = iso(now - timedelta(hours=48))
    recent = [e for e in recent if e.get("published", "") >= cutoff and e["id"] not in {x["id"] for x in events_new}]
    recent = sorted(events_new + recent, key=lambda e: e.get("published", ""), reverse=True)[:500]
    events_24h = [e for e in recent if e.get("published", "") >= iso(now - timedelta(hours=24))]

    # ---------- 4. 關鍵字與主題情緒 ----------
    kw_state = update_keyword_state(store.load_state("keywords"), now, events_new)
    th_state = update_theme_state(store.load_state("themes"), now, events_new)
    keywords = keyword_heat(kw_state, now)
    theme_stats = theme_sentiment(th_state, now)
    for t in index.themes:
        theme_stats.setdefault(t, {"news_24h": 0, "sentiment": 0.0, "daily": [None] * 7})

    # ---------- 5. 技術面 ----------
    idx_snaps = snapshots(prices, names, us_idx + tw_idx)
    macro_snaps = snapshots(prices, names, macro_syms)
    watch_snaps = snapshots(prices, names, cfg.watchlist_symbols)
    theme_snaps = {s["symbol"]: s for s in snapshots(prices, names, index.all_symbols())}

    # ---------- 6. 歷史類比 ----------
    history = store.load_output("history")
    analogs = []
    if history.get("events"):
        for e in sorted(events_24h, key=lambda e: -e.get("importance", 0))[:8]:
            if e.get("importance", 0) >= 3:
                m = find_analogs(history, e)
                if m:
                    analogs.append({"news_id": e["id"], "title": e.get("ai_summary") or e["title"], "matches": m})

    # ---------- 7. 每小時報告 ----------
    ctx_raw = {"indices": idx_snaps, "watchlist": watch_snaps, "events": events_24h, "themes": theme_stats, "analogs": analogs}
    ctx_ai = build_context(
        now_tw=now_tw.strftime("%Y-%m-%d %H:%M"), session=session_label(now), indices=idx_snaps,
        macro=macro_snaps, watchlist=watch_snaps, themes=theme_stats, index=index, keywords=keywords,
        events=events_24h, analogs=analogs, category_stats=history.get("category_stats", []),
    )
    report, u = make_report(fast, ctx_ai, ctx_raw, index, deep=False)
    usages += u

    # ---------- 8. 深度分析（每天固定時段，多家 AI） ----------
    deep_state = store.load_state("deep")
    deep_hours = [int(h) for h in cfg.get("schedule.deep_analysis_hours", [8, 22])]
    hk_tw = now_tw.strftime("%Y-%m-%dT%H")
    do_deep = force_deep or (now_tw.hour in deep_hours and deep_state.get("last_hour") != hk_tw)
    pred_state = store.load_state("predictions", {"items": []})
    if do_deep:
        reports = {}
        for p in _providers(cfg, budget, "deep", mock_ai):
            r, u = make_report(p, ctx_ai, ctx_raw, index, deep=True)
            usages += u
            reports[p.name] = r
            predictions.record(pred_state, r.get("by", p.name), iso(now), r.get("predictions", []), prices)
        deep_state = {"last_hour": hk_tw, "generated_at": iso(now), "reports": reports, "consensus": consensus(reports)}

    # ---------- 9. 準確率 ----------
    predictions.evaluate(pred_state, prices)
    accuracy = predictions.summary(pred_state)

    # ---------- 10. 警示 ----------
    new_alerts = alerts_mod.build_alerts(
        cfg, now, events=events_new, watchlist=watch_snaps, indices=idx_snaps, keywords=keywords,
        reports={"hourly": report, **(deep_state.get("reports", {}) if do_deep else {})},
    )
    alert_state = store.load_state("alerts", {"items": []})
    all_alerts, fresh = alerts_mod.merge_alerts(alert_state, new_alerts, now)

    # ---------- 11. 花費 ----------
    for x in usages:
        budget.add(x)

    # ---------- 12. 輸出給 App ----------
    latest = assemble_latest(
        cfg, index, now=now, report=report, deep_state=deep_state, idx_snaps=idx_snaps, macro_snaps=macro_snaps,
        watch_snaps=watch_snaps, theme_snaps=theme_snaps, theme_stats=theme_stats, keywords=keywords,
        events=recent, analogs=analogs, alerts=all_alerts, accuracy=accuracy, budget=budget.summary(),
        mode={
            "demo_prices": price_demo, "demo_news": news_demo, "fast_ai": fast.name,
            "deep_ai": list(deep_state.get("reports", {}).keys()), "deep_ran": do_deep, "sources": sources,
        },
    )
    store.save_output("latest", latest)
    store.save_state("news_seen", seen)
    store.save_state("events_recent", {"items": recent})
    store.save_state("keywords", kw_state)
    store.save_state("themes", th_state)
    store.save_state("deep", deep_state)
    store.save_state("predictions", pred_state)
    store.save_state("alerts", alert_state)
    store.save_state("budget", budget.state())
    return {
        "news_new": len(new_items), "events_24h": len(events_24h), "deep_ran": do_deep,
        "fresh_alerts": len(fresh), "ai": fast.name, "spent_twd": round(budget.spent_twd, 2),
        "demo_prices": price_demo, "demo_news": news_demo,
    }


def assemble_latest(cfg, index: ThemeIndex, *, now, report, deep_state, idx_snaps, macro_snaps, watch_snaps,
                    theme_snaps, theme_stats, keywords, events, analogs, alerts, accuracy, budget, mode) -> dict:
    now_tw = to_tw(now)
    rep_theme = {t["id"]: t for t in report.get("themes", [])}
    rep_stock = {s["symbol"]: s for s in report.get("stocks", [])}
    cons = deep_state.get("consensus", {})

    def market(key: str, label: str, syms: list[str]) -> dict:
        v = report.get(key, {})
        return {
            "name": label, "stance": v.get("stance", "neutral"), "stance_zh": STANCE_ZH.get(v.get("stance"), "中性"),
            "confidence": v.get("confidence", 0), "summary": v.get("summary", ""),
            "drivers": v.get("drivers", []), "risks": v.get("risks", []),
            "indices": [s for s in idx_snaps if s["symbol"] in syms],
            "consensus": cons.get(key),
        }

    themes = []
    for tid, t in index.themes.items():
        st = theme_stats.get(tid, {})
        r = rep_theme.get(tid, {})
        stance = r.get("stance") or ("bullish" if st.get("sentiment", 0) > 0.25 else "bearish" if st.get("sentiment", 0) < -0.25 else "neutral")
        themes.append({
            "id": tid, "name": t.get("name", tid), "stance": stance, "stance_zh": STANCE_ZH[stance],
            "reason": r.get("reason", "近 24 小時沒有相關新聞" if not st.get("news_24h") else ""),
            "news_24h": st.get("news_24h", 0), "sentiment": st.get("sentiment", 0.0),
            "sentiment_daily": st.get("daily", []), "drivers": t.get("drivers", []),
            "keywords": t.get("keywords", [])[:12],
            "stocks": [
                {k: theme_snaps[s].get(k) for k in ("symbol", "name", "close", "change_pct", "change_5d_pct", "trend")}
                for s in index.theme_symbols(tid) if s in theme_snaps
            ],
        })
    themes.sort(key=lambda x: (x["news_24h"], abs(x["sentiment"])), reverse=True)

    watch = []
    theme_of: dict[str, list[str]] = {}
    for tid in index.themes:
        for s in index.theme_symbols(tid):
            theme_of.setdefault(s, []).append(tid)
    for s in watch_snaps:
        r = rep_stock.get(s["symbol"], {})
        stance = r.get("stance", "neutral")
        rel_themes = theme_of.get(s["symbol"], [])
        rel_news = [e["id"] for e in events if s["symbol"] in e.get("tickers", [])][:5]
        if len(rel_news) < 5:
            rel_news += [e["id"] for e in events if set(rel_themes) & set(e.get("themes", [])) and e["id"] not in rel_news][: 5 - len(rel_news)]
        watch.append({**s, "stance": stance, "stance_zh": STANCE_ZH[stance], "reason": r.get("reason", ""),
                      "themes": rel_themes, "news": rel_news, "consensus": cons.get(s["symbol"])})

    news = []
    for e in events[:80]:
        news.append({k: e.get(k) for k in (
            "id", "title", "ai_summary", "url", "source", "published", "sentiment", "importance",
            "event_type", "themes", "macro_factors", "tickers", "keywords", "region", "analyzed_by")})
        news[-1]["event_type_zh"] = EVENT_TYPES.get(e.get("event_type"), "其他")

    deep = None
    if deep_state.get("reports"):
        deep = {
            "generated_at": deep_state["generated_at"],
            "providers": {
                name: {k: r.get(k) for k in ("headline", "us", "tw", "outlook", "historical_view", "predictions", "model", "by")}
                for name, r in deep_state["reports"].items()
            },
            "consensus": cons,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso(now),
        "generated_at_tw": now_tw.strftime("%Y-%m-%d %H:%M"),
        "session": session_label(now),
        "mode": mode,
        "headline": report.get("headline", ""),
        "report_by": report.get("by"),
        "markets": {
            "us": market("us", "美股", list(cfg.get("markets.us.indices", {}))),
            "tw": market("tw", "台股", list(cfg.get("markets.tw.indices", {}))),
        },
        "macro": macro_snaps,
        "keywords": keywords,
        "themes": themes,
        "watchlist": watch,
        "news": news,
        "analogs": analogs,
        "deep": deep,
        "alerts": alerts[:50],
        "accuracy": accuracy,
        "budget": budget,
        "disclaimer": "本內容由程式與 AI 自動產生，僅供研究參考，不構成任何投資建議。",
    }


def run_build_history(cfg: Config, store: Store, *, demo: bool = False, mock_ai: bool = False) -> dict:
    now = utcnow()
    budget = Budget(cfg, store.load_state("budget"), now)
    provider = _providers(cfg, budget, "deep", mock_ai)[0]
    syms = list(dict.fromkeys(cfg.get("history.indices", []) + cfg.get("history.context", []) + cfg.watchlist_symbols))
    prices, is_demo = load_prices(syms, start=cfg.get("history.start", "2006-01-01"), demo=demo)
    cache = store.load_state("history_annotations")
    history, usages = build_history(cfg, prices, provider, cache, is_demo)
    for u in usages:
        budget.add(u)
    history["generated_at"] = iso(now)
    history["annotated_by"] = provider.name
    store.save_output("history", history)
    store.save_state("history_annotations", cache)
    store.save_state("budget", budget.state())
    return {
        "events": len(history["events"]),
        "detected": sum(1 for e in history["events"] if e["source"] == "detected"),
        "annotated": len(cache), "demo": is_demo, "ai": provider.name, "spent_twd": round(budget.spent_twd, 2),
    }
