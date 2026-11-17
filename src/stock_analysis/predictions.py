"""預測紀錄與準確率追蹤：每次深度分析的預測都存下來，到期後比對實際漲跌。"""

from __future__ import annotations

from collections import defaultdict

import pandas as pd

FLAT_PCT = 1.0  # 漲跌在 ±1% 內算「持平」


def record(state: dict, provider: str, created_at: str, preds: list[dict], prices: dict[str, pd.DataFrame]) -> int:
    items = state.setdefault("items", [])
    n = 0
    for p in preds:
        df = prices.get(p.get("target"))
        if df is None or df.empty:
            continue
        items.append({
            "provider": provider,
            "created_at": created_at,
            "target": p["target"],
            "horizon_days": int(p.get("horizon_days", 5)),
            "direction": p.get("direction", "flat"),
            "confidence": int(p.get("confidence", 50)),
            "base_date": df.index[-1].strftime("%Y-%m-%d"),
            "base_close": float(df["Close"].iloc[-1]),
            "status": "pending",
        })
        n += 1
    return n


def _actual(ret_pct: float) -> str:
    return "up" if ret_pct > FLAT_PCT else "down" if ret_pct < -FLAT_PCT else "flat"


def evaluate(state: dict, prices: dict[str, pd.DataFrame]) -> int:
    """把已到期的預測標成 correct / wrong。回傳這次評分的筆數。"""
    n = 0
    for it in state.get("items", []):
        if it["status"] != "pending":
            continue
        df = prices.get(it["target"])
        if df is None:
            continue
        idx = df.index
        p = int(idx.searchsorted(pd.Timestamp(it["base_date"]), side="right"))
        q = p - 1 + it["horizon_days"]
        if q >= len(idx):
            continue
        ret = (float(df["Close"].iloc[q]) / it["base_close"] - 1) * 100
        it["actual_pct"] = round(ret, 2)
        it["actual"] = _actual(ret)
        it["eval_date"] = idx[q].strftime("%Y-%m-%d")
        it["status"] = "correct" if it["actual"] == it["direction"] else "wrong"
        n += 1
    # 只保留最近 2000 筆
    state["items"] = state.get("items", [])[-2000:]
    return n


def summary(state: dict) -> dict:
    by = defaultdict(lambda: {"correct": 0, "wrong": 0, "pending": 0})
    for it in state.get("items", []):
        by[it["provider"]][it["status"]] += 1
    providers = {}
    for name, c in by.items():
        done = c["correct"] + c["wrong"]
        providers[name] = {**c, "accuracy": round(c["correct"] / done, 3) if done else None}
    done = [it for it in state.get("items", []) if it["status"] != "pending"]
    recent = sorted(done, key=lambda x: x.get("eval_date", ""), reverse=True)[:30]
    return {"flat_threshold_pct": FLAT_PCT, "by_provider": providers, "recent": recent}
