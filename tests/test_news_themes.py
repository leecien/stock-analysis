import json
from pathlib import Path

from stock_analysis.extract import extraction_schema, rule_extract
from stock_analysis.news import NewsItem, dedupe, parse_cnyes, parse_rss
from stock_analysis.themes import ThemeIndex

FIX = Path(__file__).parent / "fixtures"


def test_parse_google_news_splits_source():
    items = parse_rss((FIX / "google_news.xml").read_bytes(), "Google News", split_source=True)
    assert [i.source for i in items] == ["經濟日報", "Reuters"]
    assert items[0].title == "DRAM 合約價大漲，南亞科營收創新高"
    assert "<a" not in items[0].summary
    assert items[0].published == "2026-11-17T02:00:00Z"


def test_parse_cnyes():
    data = {"items": {"data": [{"newsId": 1, "title": "台股大漲", "summary": "s", "publishAt": 1763344800}]}}
    items = parse_cnyes(data)
    assert items[0].source == "鉅亨網" and items[0].url.endswith("/1")


def test_dedupe_by_title():
    a = NewsItem("台積電 漲停", "u1", "A", "2026-11-17T01:00:00Z")
    b = NewsItem("台積電漲停!", "u2", "B", "2026-11-17T02:00:00Z")
    assert len(dedupe([a, b])) == 1


def test_theme_match(cfg):
    idx = ThemeIndex(cfg)
    m = idx.match("DRAM 合約價上漲，南亞科與 Micron 受惠；聯準會暗示降息")
    assert "memory" in m.themes
    assert "rate_cut" in m.macros
    assert "2408.TW" in m.tickers
    # 英文短關鍵字不能比對到單字中間
    assert "ev" not in idx.match("every investor is nervous").themes


def test_rule_extract(cfg):
    idx = ThemeIndex(cfg)
    n = NewsItem("中東戰爭擴大，油價暴漲，航空股重挫", "u", "X", "2026-11-17T01:00:00Z")
    e = rule_extract([n], idx)[0]
    assert e["event_type"] == "war"
    assert e["importance"] >= 4
    assert "oil_petrochem" in e["themes"] and "defense" in e["themes"]


def test_schema_is_strict(cfg):
    s = extraction_schema(list(cfg.themes), list(cfg.macro_factors))
    item = s["properties"]["items"]["items"]
    assert item["additionalProperties"] is False
    assert set(item["required"]) == set(item["properties"])
    json.dumps(s)
