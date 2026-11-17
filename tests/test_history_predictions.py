from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from stock_analysis import predictions
from stock_analysis.ai.base import Usage
from stock_analysis.budget import Budget
from stock_analysis.history import detect_drawdowns, detect_moves, find_analogs, forward_returns
from stock_analysis.keywords import keyword_heat, update_keyword_state


def _series(vals, start="2024-01-01"):
    return pd.Series(vals, index=pd.bdate_range(start, periods=len(vals)), dtype=float)


def test_forward_returns():
    s = _series([100, 110, 121, 133.1, 146.41, 161.051])
    fr = forward_returns(s, s.index[1], [1, 2, 10])
    assert fr["1"] == 10.0 and fr["2"] == 21.0 and fr["10"] is None


def test_detect_moves_finds_crash():
    rng = np.random.default_rng(1)
    vals = 100 * np.exp(np.cumsum(rng.normal(0, 0.005, 200)))
    vals[150:] *= 0.9  # 單日 -10%
    mv = detect_moves(_series(vals), 3.0, 3.5)
    assert any(abs(r) > 9 for r in mv["ret"])


def test_drawdowns():
    s = _series([100, 105, 90, 80, 95, 106, 107])
    dd = detect_drawdowns(s, 10)
    assert len(dd) == 1 and dd[0]["depth_pct"] < -20 and dd[0]["recovered"] is not None


def test_find_analogs():
    hist = {"events": [
        {"id": "a", "date": "2022-02-24", "title": "俄羅斯入侵烏克蘭", "category": "war", "themes": ["defense"], "confidence": "high", "reactions": {}},
        {"id": "b", "date": "2020-03-16", "title": "疫情", "category": "pandemic", "themes": [], "confidence": "high", "reactions": {}},
    ]}
    res = find_analogs(hist, {"event_type": "war", "themes": ["defense"], "keywords": ["烏克蘭"]})
    assert [r["id"] for r in res] == ["a"]


def test_keyword_heat_spike():
    now = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
    st = {}
    for h in range(30, 24 * 7, 6):  # 過去一週偶爾出現
        st = update_keyword_state(st, now - timedelta(hours=h), [{"keywords": ["HBM"], "themes": ["memory"]}])
    for h in range(5):
        st = update_keyword_state(st, now - timedelta(hours=h), [{"keywords": ["HBM"]}] * 3)
    heat = keyword_heat(st, now)
    hbm = next(k for k in heat if k["keyword"] == "HBM")
    assert hbm["count_24h"] == 15 and hbm["ratio"] > 3 and hbm["themes"] == ["memory"]
    assert len(hbm["series"]) == 48


def test_predictions_evaluate():
    df = pd.DataFrame({"Close": [100, 101, 102, 103, 104, 106, 107]}, index=pd.bdate_range("2026-11-02", periods=7))
    st = {"items": []}
    predictions.record(st, "claude", "x", [{"target": "AAA", "horizon_days": 5, "direction": "up", "confidence": 60}], {"AAA": df.iloc[:1]})
    predictions.evaluate(st, {"AAA": df})
    it = st["items"][0]
    assert it["status"] == "correct" and it["actual_pct"] == 6.0
    assert predictions.summary(st)["by_provider"]["claude"]["accuracy"] == 1.0


def test_budget(cfg):
    b = Budget(cfg, {}, datetime(2026, 11, 17, tzinfo=timezone.utc))
    cost = b.add(Usage("claude", "claude-sonnet-5-5", input_tokens=1_000_000, output_tokens=100_000))
    assert abs(cost - 3.0) < 1e-9
    assert b.allow("fast")
    b.add(Usage("claude", "claude-sonnet-5-5", input_tokens=8_000_000))
    assert not b.allow("deep")


def test_moves_match_nearest_seed_event(cfg):
    from stock_analysis.ai.base import MockProvider
    from stock_analysis.history import build_history

    idx = pd.bdate_range("2025-01-01", periods=120)
    vals = np.full(120, 100.0) * np.exp(np.random.default_rng(3).normal(0, 0.002, 120).cumsum())
    p3, p7, p9 = idx.get_loc(pd.Timestamp("2025-04-03")), idx.get_loc(pd.Timestamp("2025-04-07")), idx.get_loc(pd.Timestamp("2025-04-09"))
    vals[p3:] *= 0.94
    vals[p7:] *= 0.90
    vals[p9:] *= 1.10
    df = pd.DataFrame({"Close": vals}, index=idx)
    cfg.seed_events = [
        {"date": pd.Timestamp("2025-04-03").date(), "title": "A", "category": "trade"},
        {"date": pd.Timestamp("2025-04-07").date(), "title": "B", "category": "trade"},
        {"date": pd.Timestamp("2025-04-09").date(), "title": "C", "category": "trade"},
    ]
    cfg.watchlist = []
    hist, _ = build_history(cfg, {"^GSPC": df}, MockProvider(), {}, demo=True)
    by_id = {e["id"]: e for e in hist["events"]}
    assert by_id["seed-2025-04-07"]["moves"]["^GSPC"]["ret"] < -9
    assert by_id["seed-2025-04-09"]["moves"]["^GSPC"]["ret"] > 9
