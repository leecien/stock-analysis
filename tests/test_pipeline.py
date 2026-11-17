import json
from types import SimpleNamespace

from stock_analysis.ai.claude import ClaudeProvider
from stock_analysis.analysis import consensus, report_schema
from stock_analysis.pipeline import run_build_history, run_hourly
from stock_analysis.store import Store


def test_end_to_end_demo(cfg, tmp_path):
    st = Store(tmp_path / "state", tmp_path / "public")
    h = run_build_history(cfg, st, demo=True)
    assert h["events"] > 50 and h["ai"] == "mock"
    res = run_hourly(cfg, st, demo=True, force_deep=True)
    assert res["news_new"] > 0 and res["deep_ran"]
    latest = json.loads((tmp_path / "public" / "latest.json").read_text())
    assert latest["schema_version"] == 1
    assert latest["markets"]["us"]["indices"] and latest["markets"]["tw"]["indices"]
    assert len(latest["themes"]) == len(cfg.themes)
    assert len(latest["watchlist"]) == len(cfg.watchlist)
    assert latest["deep"]["providers"]["mock"]["predictions"]
    # 第二次執行：同樣的新聞不會重複分析
    res2 = run_hourly(cfg, st, demo=True)
    assert res2["news_new"] == 0 and res2["events_24h"] == res["events_24h"]


def test_consensus():
    c = consensus({
        "claude": {"us": {"stance": "bullish"}, "tw": {"stance": "neutral"}, "stocks": [{"symbol": "NVDA", "stance": "bullish"}]},
        "gemini": {"us": {"stance": "bullish"}, "tw": {"stance": "bearish"}, "stocks": [{"symbol": "NVDA", "stance": "bearish"}]},
    })
    assert c["us"] == {"stance": "bullish", "agreement": 1.0, "votes": {"claude": "bullish", "gemini": "bullish"}}
    assert c["NVDA"]["agreement"] == 0.5


class _FakeMessages:
    def __init__(self, sink):
        self.sink = sink

    def create(self, **kw):
        self.sink.append(kw)
        usage = SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=100, cache_creation_input_tokens=0)
        return SimpleNamespace(stop_reason="end_turn", usage=usage,
                               content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text='{"ok": true}')])


def test_claude_provider_request_shape(monkeypatch):
    import anthropic

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    calls = []
    p = ClaudeProvider({"env_key": "ANTHROPIC_API_KEY", "fast_model": "claude-haiku-5-5", "deep_model": "claude-sonnet-5-5"})
    p.client = SimpleNamespace(messages=_FakeMessages(calls), beta=SimpleNamespace(messages=_FakeMessages(calls)))
    schema = report_schema(False)
    data, u = p.generate_json(tier="fast", system="s", user="u", schema=schema)
    assert data == {"ok": True} and u.cache_read_tokens == 100
    assert calls[0]["model"] == "claude-haiku-5-5"
    assert calls[0]["output_config"]["format"]["schema"] == schema
    assert calls[0]["output_config"]["effort"] == "low"
    assert "betas" not in calls[0]
    p.generate_json(tier="deep", system="s", user="u", schema=schema)
    assert calls[1]["model"] == "claude-sonnet-5-5" and calls[1]["fallbacks"] == "default"
    assert anthropic  # SDK 已安裝
