"""20 年歷史事件庫：

1. 自動偵測指數「大漲大跌日」與「修正波段」
2. 對應人工整理的重大事件（data/seed/major_events.yaml）
3. 沒對應到的日子交給 AI 標註原因（結果會快取，不重複花錢）
4. 計算每個事件後 1/5/20/60 個交易日的漲跌 → 各類事件的歷史統計
5. 提供「類似歷史事件」查詢給每小時分析使用
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import date

import numpy as np
import pandas as pd

from .ai.base import AIError, AIProvider
from .extract import EVENT_TYPES

log = logging.getLogger(__name__)

US_BENCH, TW_BENCH = "^GSPC", "^TWII"


def _r(x, n=2):
    return None if x is None or pd.isna(x) else round(float(x), n)


def pos_on_or_after(idx: pd.DatetimeIndex, d) -> int | None:
    p = int(idx.searchsorted(pd.Timestamp(d)))
    return p if p < len(idx) else None


def forward_returns(close: pd.Series, d, days: list[int]) -> dict[str, float | None] | None:
    """以事件日「前一個交易日收盤」為基準，計算第 1、5、20、60 個交易日的累積漲跌幅（%）。
    第 1 天 = 事件當天的漲跌。"""
    p = pos_on_or_after(close.index, d)
    if p is None or p == 0:
        return None
    base = close.iloc[p - 1]
    out = {}
    for n in days:
        q = p - 1 + n
        out[str(n)] = _r((close.iloc[q] / base - 1) * 100) if q < len(close) else None
    return out


def detect_moves(close: pd.Series, z_thr: float, abs_pct: float) -> pd.DataFrame:
    ret = close.pct_change()
    vol = ret.rolling(60, min_periods=40).std().shift(1)
    z = ret / vol
    mask = (z.abs() >= z_thr) | (ret.abs() * 100 >= abs_pct)
    return pd.DataFrame({"ret": ret[mask] * 100, "z": z[mask]}).dropna(subset=["ret"])


def detect_drawdowns(close: pd.Series, pct: float) -> list[dict]:
    """找出從高點回檔超過 pct% 的波段。"""
    out = []
    peak_v, peak_d = close.iloc[0], close.index[0]
    trough_v, trough_d = peak_v, peak_d
    in_dd = False
    for d, v in close.items():
        if v >= peak_v:
            if in_dd:
                out.append({"peak": peak_d, "trough": trough_d, "depth": (trough_v / peak_v - 1) * 100, "recovered": d})
                in_dd = False
            peak_v, peak_d, trough_v, trough_d = v, d, v, d
            continue
        if v < trough_v:
            trough_v, trough_d = v, d
        if (trough_v / peak_v - 1) * 100 <= -pct:
            in_dd = True
    if in_dd:
        out.append({"peak": peak_d, "trough": trough_d, "depth": (trough_v / peak_v - 1) * 100, "recovered": None})
    return [
        {
            "peak": x["peak"].strftime("%Y-%m-%d"),
            "trough": x["trough"].strftime("%Y-%m-%d"),
            "recovered": x["recovered"].strftime("%Y-%m-%d") if x["recovered"] is not None else None,
            "depth_pct": _r(x["depth"]),
            "days_to_trough": int(np.busday_count(x["peak"].date(), x["trough"].date())),
        }
        for x in out
    ]


def _abs_threshold(cfg, sym: str) -> float:
    conf = cfg.get("history.abs_move_pct", 3.5)
    if isinstance(conf, dict):
        return float(conf.get(sym, conf.get("default", 3.5)))
    return float(conf)


def market_move_days(cfg, prices: dict[str, pd.DataFrame]) -> dict[str, dict]:
    """各指數的大漲大跌日合併成 {日期: {指數: {ret, z}}}。"""
    z_thr = float(cfg.get("history.zscore_threshold", 3.0))
    days: dict[str, dict] = defaultdict(dict)
    for sym in cfg.get("history.indices", []):
        df = prices.get(sym)
        if df is None or len(df) < 80:
            continue
        mv = detect_moves(df["Close"], z_thr, _abs_threshold(cfg, sym))
        for d, row in mv.iterrows():
            days[d.strftime("%Y-%m-%d")][sym] = {"ret": _r(row["ret"]), "z": _r(row["z"], 1)}
    return dict(sorted(days.items()))


def stock_abnormal_moves(cfg, prices: dict[str, pd.DataFrame], symbol: str) -> list[dict]:
    """個股扣除大盤（beta）後的異常漲跌日。"""
    df = prices.get(symbol)
    bench = TW_BENCH if symbol.endswith((".TW", ".TWO")) else US_BENCH
    bdf = prices.get(bench)
    if df is None or bdf is None or len(df) < 120:
        return []
    r = df["Close"].pct_change()
    m = bdf["Close"].pct_change().reindex(r.index)
    both = pd.concat([r, m], axis=1, keys=["r", "m"]).dropna()
    if len(both) < 100:
        return []
    beta = both["r"].cov(both["m"]) / both["m"].var()
    abn = both["r"] - beta * both["m"]
    z = abn / abn.rolling(120, min_periods=60).std().shift(1)
    thr = float(cfg.get("history.stock_abnormal_z", 3.5))
    flagged = z[z.abs() >= thr].dropna()
    top = flagged.abs().sort_values(ascending=False).index[: int(cfg.get("history.max_stock_moves", 25))]
    days = [int(n) for n in cfg.get("history.forward_days", [1, 5, 20, 60])]
    out = []
    for d in sorted(top):
        out.append(
            {
                "date": d.strftime("%Y-%m-%d"),
                "symbol": symbol,
                "ret": _r(both.loc[d, "r"] * 100),
                "market_ret": _r(both.loc[d, "m"] * 100),
                "abnormal": _r(abn.loc[d] * 100),
                "z": _r(z.loc[d], 1),
                "forward": forward_returns(df["Close"], d, days),
            }
        )
    return out


# ---------------- AI 標註原因 ----------------

ANNOTATION_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "cause": {"type": "string"},
                    "category": {"type": "string", "enum": list(EVENT_TYPES)},
                    "themes": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["key", "cause", "category", "themes", "confidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}

ANNOTATION_SYSTEM = """你是熟悉 2006 年以來全球金融市場歷史的分析師。
使用者會給你一些「股市大漲或大跌的日子」與當天的漲跌幅，請說明最可能的原因。

規則：
- cause：繁體中文 40 字內，寫出具體事件（例如「美國 CPI 高於預期，升息預期升溫」）
- 只寫你有把握的事實；不確定就把 confidence 設為 low，並寫「可能與…有關」
- 不要編造不存在的新聞或數字
- category 選最主要的原因類別；themes 填受影響最大的產業主題 id（可留空）
"""


def annotate(provider: AIProvider, records: list[dict], cache: dict, theme_ids: list[str], usages: list) -> None:
    """records 每筆需有 key 與 desc；結果寫入 cache[key]。已有快取的會跳過。"""
    todo = [r for r in records if r["key"] not in cache]
    if not todo or provider.is_mock:
        return
    system = ANNOTATION_SYSTEM + "\n可用的產業主題 id：" + ", ".join(theme_ids)
    for i in range(0, len(todo), 15):
        batch = todo[i : i + 15]
        user = "請標註以下日子的漲跌原因：\n" + json.dumps(
            [{"key": r["key"], "desc": r["desc"]} for r in batch], ensure_ascii=False
        )
        try:
            data, usage = provider.generate_json(
                tier="deep", system=system, user=user, schema=ANNOTATION_SCHEMA, max_tokens=8000
            )
        except AIError as e:
            log.warning("歷史標註失敗：%s", e)
            return
        usages.append(usage)
        for it in data.get("items", []):
            if it.get("key"):
                cache[it["key"]] = {
                    "cause": it.get("cause", ""),
                    "category": it.get("category", "other"),
                    "themes": [t for t in it.get("themes", []) if t in theme_ids],
                    "confidence": it.get("confidence", "low"),
                    "by": provider.name,
                }


# ---------------- 組合成歷史事件庫 ----------------


def _seed_id(e: dict) -> str:
    return f"seed-{e['date']}"


def build_history(cfg, prices: dict[str, pd.DataFrame], provider: AIProvider, cache: dict, demo: bool) -> tuple[dict, list]:
    usages: list = []
    days = [int(n) for n in cfg.get("history.forward_days", [1, 5, 20, 60])]
    react_syms = list(dict.fromkeys(cfg.get("history.indices", []) + cfg.get("history.context", [])))

    def reactions(d) -> dict:
        out = {}
        for s in react_syms:
            df = prices.get(s)
            if df is not None:
                fr = forward_returns(df["Close"], d, days)
                if fr:
                    out[s] = fr
        return out

    # 1. 種子事件
    events = []
    seed_trading_days = {}
    ref = prices.get(US_BENCH) if prices.get(US_BENCH) is not None else next(iter(prices.values()), None)
    for e in cfg.seed_events:
        d = e["date"] if isinstance(e["date"], date) else pd.Timestamp(e["date"]).date()
        ev = {
            "id": _seed_id(e),
            "date": d.isoformat(),
            "date_precision": e.get("date_precision", "day"),
            "title": e["title"],
            "category": e.get("category", "other"),
            "category_name": EVENT_TYPES.get(e.get("category", "other"), "其他"),
            "region": e.get("region", "global"),
            "themes": e.get("themes", []) or [],
            "source": "seed",
            "confidence": "high",
            "reactions": reactions(d),
        }
        events.append(ev)
        if ref is not None:
            p = pos_on_or_after(ref.index, d)
            if p is not None:
                seed_trading_days[ev["id"]] = p

    # 2. 自動偵測的大漲大跌日
    move_days = market_move_days(cfg, prices)
    unmatched = []
    detected = []
    for d, moves in move_days.items():
        matched = None
        if ref is not None:
            p = pos_on_or_after(ref.index, d)
            if p is not None:
                # 事件前 1 天到後 3 個交易日內，取最接近的事件（同一天優先）
                near = [(abs(p - sp), p - sp < 0, sid) for sid, sp in seed_trading_days.items() if -1 <= p - sp <= 3]
                if near:
                    matched = min(near)[2]
        rec = {"date": d, "moves": moves, "matched_event": matched}
        detected.append(rec)
        if not matched:
            desc = "、".join(f"{s} {v['ret']:+.1f}%" for s, v in moves.items())
            unmatched.append({"key": f"mkt-{d}", "desc": f"{d}：{desc}"})

    theme_ids = list(cfg.themes)
    annotate(provider, unmatched, cache, theme_ids, usages)
    for rec in detected:
        if rec["matched_event"]:
            continue
        key = f"mkt-{rec['date']}"
        ann = cache.get(key)
        big = max(rec["moves"].values(), key=lambda v: abs(v["ret"] or 0))
        direction = "大漲" if (big["ret"] or 0) > 0 else "大跌"
        events.append(
            {
                "id": key,
                "date": rec["date"],
                "date_precision": "day",
                "title": ann["cause"] if ann else f"市場{direction}（原因待標註）",
                "category": ann["category"] if ann else "other",
                "category_name": EVENT_TYPES.get(ann["category"], "其他") if ann else "待標註",
                "region": "global",
                "themes": ann["themes"] if ann else [],
                "source": "detected",
                "confidence": ann["confidence"] if ann else "none",
                "moves": rec["moves"],
                "reactions": reactions(rec["date"]),
            }
        )
    for ev in events:
        if ev["source"] == "seed":
            # 對應到的大漲大跌日中，取最接近事件日期的那一天
            cands = [r for r in detected if r["matched_event"] == ev["id"]]
            cands.sort(key=lambda r: abs(pd.Timestamp(r["date"]) - pd.Timestamp(ev["date"])))
            ev["moves"] = cands[0]["moves"] if cands else {}
    events.sort(key=lambda e: e["date"], reverse=True)

    # 3. 修正波段
    drawdowns = {}
    pct = float(cfg.get("history.drawdown_pct", 10))
    for s in cfg.get("history.indices", []):
        df = prices.get(s)
        if df is not None and len(df) > 60:
            drawdowns[s] = detect_drawdowns(df["Close"], pct)

    # 4. 自選股異常漲跌
    stock_moves = {}
    stock_records = []
    for s in cfg.watchlist_symbols:
        mv = stock_abnormal_moves(cfg, prices, s)
        if mv:
            stock_moves[s] = mv
            for m in mv:
                stock_records.append(
                    {"key": f"stk-{s}-{m['date']}", "desc": f"{m['date']} {s} 漲跌 {m['ret']:+.1f}%（大盤 {m['market_ret']:+.1f}%）"}
                )
    annotate(provider, stock_records, cache, theme_ids, usages)
    for s, mv in stock_moves.items():
        for m in mv:
            ann = cache.get(f"stk-{s}-{m['date']}")
            m["cause"] = ann["cause"] if ann else "原因待標註"
            m["confidence"] = ann["confidence"] if ann else "none"

    history = {
        "demo_data": demo,
        "start": cfg.get("history.start"),
        "forward_days": days,
        "events": events,
        "drawdowns": drawdowns,
        "stock_moves": stock_moves,
        "category_stats": category_stats(events, days),
    }
    return history, usages


def category_stats(events: list[dict], days: list[int]) -> list[dict]:
    """各類事件之後，美股與台股的平均漲跌與上漲機率。"""
    groups: dict[str, list] = defaultdict(list)
    for e in events:
        if e.get("confidence") in ("high", "medium") and e.get("reactions"):
            groups[e["category"]].append(e)
    out = []
    for cat, evs in groups.items():
        row = {"category": cat, "name": EVENT_TYPES.get(cat, cat), "count": len(evs), "avg": {}, "up_ratio": {}}
        for sym in (US_BENCH, TW_BENCH):
            row["avg"][sym], row["up_ratio"][sym] = {}, {}
            for n in days:
                vals = [e["reactions"][sym][str(n)] for e in evs if sym in e["reactions"] and e["reactions"][sym].get(str(n)) is not None]
                if vals:
                    row["avg"][sym][str(n)] = _r(np.mean(vals))
                    row["up_ratio"][sym][str(n)] = _r(np.mean([v > 0 for v in vals]), 2)
        out.append(row)
    out.sort(key=lambda r: r["count"], reverse=True)
    return out


def find_analogs(history: dict, event: dict, top: int = 3) -> list[dict]:
    """找和這則新聞事件最像的歷史事件（同類別、同主題、標題有相同關鍵字）。"""
    cat = event.get("event_type")
    themes = set(event.get("themes", []))
    kws = [k for k in event.get("keywords", []) if len(k) >= 2]
    scored = []
    for h in history.get("events", []):
        if h.get("confidence") == "none":
            continue
        s = 0.0
        if h.get("category") == cat:
            s += 2
        s += len(themes & set(h.get("themes", [])))
        s += 0.5 * sum(1 for k in kws if k.lower() in h.get("title", "").lower())
        if s >= 2:
            scored.append((s, h))
    scored.sort(key=lambda x: (x[0], x[1]["date"]), reverse=True)
    return [
        {
            "id": h["id"],
            "date": h["date"],
            "title": h["title"],
            "category_name": h.get("category_name"),
            "reactions": {k: v for k, v in h.get("reactions", {}).items() if k in (US_BENCH, TW_BENCH)},
            "score": s,
        }
        for s, h in scored[:top]
    ]
