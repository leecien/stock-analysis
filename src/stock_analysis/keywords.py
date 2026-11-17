"""關鍵字熱度與主題情緒統計（以小時為單位累積在 state）。"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from .timeutil import hour_key

KEEP_HOURS = 24 * 8


def _norm(k: str) -> str:
    k = k.strip()
    return k.upper() if k.isascii() and len(k) <= 6 else k


def _prune(buckets: dict, now: datetime) -> dict:
    cutoff = hour_key(now - timedelta(hours=KEEP_HOURS))
    return {k: v for k, v in buckets.items() if k >= cutoff}


def update_keyword_state(state: dict, now: datetime, events: list[dict]) -> dict:
    """把這小時抽到的關鍵字加進統計。"""
    hk = hour_key(now)
    hourly = state.get("hourly", {})
    c = Counter(hourly.get(hk, {}))
    themes_of: dict = state.get("themes_of", {})
    for e in events:
        for k in e.get("keywords", []):
            nk = _norm(k)
            c[nk] += 1
            if e.get("themes"):
                themes_of[nk] = sorted(set(themes_of.get(nk, [])) | set(e["themes"][:3]))
    hourly[hk] = dict(c)
    hourly = _prune(hourly, now)
    alive = {k for b in hourly.values() for k in b}
    return {"hourly": hourly, "themes_of": {k: v for k, v in themes_of.items() if k in alive}}


def keyword_heat(state: dict, now: datetime, top: int = 30) -> list[dict]:
    """近 24 小時次數 vs 前 7 天平均每日次數 → 熱度倍數。"""
    hourly = state.get("hourly", {})
    last24 = {hour_key(now - timedelta(hours=h)) for h in range(24)}
    series_keys = [hour_key(now - timedelta(hours=h)) for h in range(47, -1, -1)]
    recent: Counter = Counter()
    base: Counter = Counter()
    for hk, bucket in hourly.items():
        if hk in last24:
            recent.update(bucket)
        else:
            base.update(bucket)
    # 基準期間 = 最舊的統計時間 到 24 小時前（最長 7 天），用實際時間長度計算，而不是有資料的小時數
    older = [k for k in hourly if k not in last24]
    if older:
        oldest = datetime.strptime(min(older), "%Y-%m-%dT%H").replace(tzinfo=timezone.utc)
        span_h = (now - timedelta(hours=24) - oldest).total_seconds() / 3600 + 1
        base_days = max(1.0, span_h / 24)
    else:
        base_days = 1.0
    rows = []
    for k, cnt in recent.items():
        baseline = base[k] / base_days
        ratio = (cnt + 1) / (baseline + 1)
        rows.append(
            {
                "keyword": k,
                "count_24h": cnt,
                "baseline": round(baseline, 2),
                "ratio": round(ratio, 2),
                "score": round(ratio * math.log1p(cnt), 3),
                "themes": state.get("themes_of", {}).get(k, []),
                "series": [hourly.get(h, {}).get(k, 0) for h in series_keys],
            }
        )
    rows.sort(key=lambda r: (r["score"], r["count_24h"]), reverse=True)
    return rows[:top]


def update_theme_state(state: dict, now: datetime, events: list[dict]) -> dict:
    """累積每個主題每小時的新聞數與情緒總和（依重要性加權）。"""
    hk = hour_key(now)
    hourly = state.get("hourly", {})
    cur = hourly.get(hk, {})
    for e in events:
        w = float(e.get("importance", 2))
        for t in e.get("themes", []):
            s = cur.setdefault(t, {"n": 0, "w": 0.0, "s": 0.0})
            s["n"] += 1
            s["w"] += w
            s["s"] += w * float(e.get("sentiment", 0))
    hourly[hk] = cur
    return {"hourly": _prune(hourly, now)}


def theme_sentiment(state: dict, now: datetime) -> dict[str, dict]:
    """每個主題：近 24 小時新聞數、加權情緒、近 7 天每日情緒走勢。"""
    hourly = state.get("hourly", {})
    out: dict[str, dict] = defaultdict(lambda: {"news_24h": 0, "sentiment": 0.0, "daily": []})
    last24 = {hour_key(now - timedelta(hours=h)) for h in range(24)}
    acc = defaultdict(lambda: [0, 0.0, 0.0])
    days = [(now - timedelta(days=d)).astimezone(timezone.utc).strftime("%Y-%m-%d") for d in range(6, -1, -1)]
    daily = defaultdict(lambda: {d: [0.0, 0.0] for d in days})
    for hk, bucket in hourly.items():
        day = hk[:10]
        for t, s in bucket.items():
            if hk in last24:
                a = acc[t]
                a[0] += s["n"]
                a[1] += s["w"]
                a[2] += s["s"]
            if day in daily[t]:
                daily[t][day][0] += s["w"]
                daily[t][day][1] += s["s"]
    for t in set(acc) | set(daily):
        n, w, s = acc.get(t, [0, 0.0, 0.0])
        out[t] = {
            "news_24h": n,
            "sentiment": round(s / w, 3) if w else 0.0,
            "daily": [round(v[1] / v[0], 3) if v[0] else None for v in daily[t].values()],
        }
    return dict(out)
