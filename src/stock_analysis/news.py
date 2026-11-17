"""新聞抓取：Google News、RSS、Yahoo Finance、鉅亨網。"""

from __future__ import annotations

import hashlib
import html
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from .config import Config
from .timeutil import iso, parse_iso

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (compatible; stock-analysis/0.2; personal research)"
TIMEOUT = 15


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published: str  # ISO UTC
    summary: str = ""
    lang: str = "zh"
    id: str = field(default="")

    def __post_init__(self):
        self.title = clean_text(self.title)
        self.summary = clean_text(self.summary)[:400]
        if not self.id:
            self.id = news_id(self.title)

    def to_dict(self) -> dict:
        return asdict(self)


def clean_text(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def news_id(title: str) -> str:
    norm = re.sub(r"[\W_]+", "", title.lower())
    return hashlib.sha1(norm.encode()).hexdigest()[:12]


def _http_get(url: str) -> bytes:
    import requests

    r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.content


def _entry_time(entry) -> str:
    for key in ("published", "updated"):
        val = entry.get(key)
        if val:
            try:
                dt = parsedate_to_datetime(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return iso(dt)
            except (TypeError, ValueError):
                try:
                    return iso(parse_iso(val))
                except ValueError:
                    pass
    return iso(datetime.now(timezone.utc))


def parse_rss(content: bytes, source: str, lang: str = "zh", split_source: bool = False) -> list[NewsItem]:
    """解析 RSS/Atom。split_source=True 時把標題結尾的「 - 來源」拆出來（Google News 格式）。"""
    import feedparser

    feed = feedparser.parse(content)
    items = []
    for e in feed.entries:
        title = e.get("title", "")
        src = source
        if split_source and " - " in title:
            title, src = title.rsplit(" - ", 1)
        if not title:
            continue
        items.append(
            NewsItem(
                title=title,
                url=e.get("link", ""),
                source=src,
                published=_entry_time(e),
                summary=e.get("summary", ""),
                lang=lang,
            )
        )
    return items


def parse_cnyes(data: dict) -> list[NewsItem]:
    items = []
    for d in (data.get("items") or {}).get("data", []) or []:
        title = d.get("title")
        if not title:
            continue
        ts = d.get("publishAt")
        published = iso(datetime.fromtimestamp(ts, timezone.utc)) if ts else iso(datetime.now(timezone.utc))
        items.append(
            NewsItem(
                title=title,
                url=f"https://news.cnyes.com/news/id/{d.get('newsId')}",
                source="鉅亨網",
                published=published,
                summary=d.get("summary", "") or "",
                lang="zh",
            )
        )
    return items


def fetch_google_news(query: str, params: str, lang: str) -> list[NewsItem]:
    url = f"https://news.google.com/rss/search?q={quote_plus(query + ' when:1d')}&{params}"
    return parse_rss(_http_get(url), "Google News", lang=lang, split_source=True)


def fetch_yahoo(symbols: list[str]) -> list[NewsItem]:
    url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=" + ",".join(symbols) + "&region=US&lang=en-US"
    return parse_rss(_http_get(url), "Yahoo Finance", lang="en")


def fetch_cnyes(category: str) -> list[NewsItem]:
    import json

    url = f"https://api.cnyes.com/media/api/v1/newslist/category/{category}?limit=30"
    return parse_cnyes(json.loads(_http_get(url)))


def collect_news(cfg: Config, now: datetime) -> tuple[list[NewsItem], dict[str, str]]:
    """從所有來源抓新聞，回傳 (新聞, 各來源狀態)。單一來源失敗不影響其他來源。"""
    jobs = []
    gn = cfg.get("news.google_news", {}) or {}
    for lang, conf in gn.items():
        for q in conf.get("queries", []):
            jobs.append((f"Google News:{q}", lambda q=q, conf=conf, lang=lang: fetch_google_news(q, conf["params"], lang)))
    for name, url in (cfg.get("news.rss", {}) or {}).items():
        jobs.append((name, lambda name=name, url=url: parse_rss(_http_get(url), name, lang="en")))
    ysyms = cfg.get("news.yahoo_finance_symbols", []) or []
    if ysyms:
        jobs.append(("Yahoo Finance", lambda: fetch_yahoo(ysyms)))
    for cat in cfg.get("news.cnyes_categories", []) or []:
        jobs.append((f"鉅亨網:{cat}", lambda cat=cat: fetch_cnyes(cat)))

    status: dict[str, str] = {}
    items: list[NewsItem] = []
    for name, job in jobs:
        try:
            got = job()
            items.extend(got)
            status[name] = f"ok ({len(got)})"
        except Exception as e:
            status[name] = f"error: {type(e).__name__}"
            log.warning("新聞來源 %s 失敗：%s", name, e)

    cutoff = now - timedelta(hours=float(cfg.get("news.lookback_hours", 3)))
    return dedupe([i for i in items if parse_iso(i.published) >= cutoff]), status


def dedupe(items: list[NewsItem]) -> list[NewsItem]:
    seen: dict[str, NewsItem] = {}
    for it in items:
        if it.id not in seen:
            seen[it.id] = it
    return sorted(seen.values(), key=lambda x: x.published, reverse=True)


_DEMO_HEADLINES = [
    ("DRAM 合約價下季再漲15%，記憶體原廠產能吃緊", "TrendForce 指出 AI 伺服器 HBM 需求排擠一般 DRAM 產能，南亞科、華邦電受惠", "經濟日報"),
    ("美光財報優於預期，HBM 訂單滿到明年", "美光上修財測，記憶體報價持續走升", "鉅亨網"),
    ("輝達新一代 GPU 出貨放量，廣達、緯穎 AI 伺服器營收創新高", "雲端大廠上修資本支出，AI 伺服器供應鏈訂單暢旺", "工商時報"),
    ("台積電 CoWoS 產能明年再擴充，先進封裝設備廠受惠", "萬潤、弘塑接單暢旺", "經濟日報"),
    ("聯準會官員發表鷹派談話，暗示降息步調放緩", "市場預期明年降息次數減少，美債殖利率走高", "Reuters"),
    ("美國 CPI 高於預期，核心通膨仍具黏性", "通膨數據使市場擔憂升息循環延長", "CNBC"),
    ("中東局勢升溫，以色列與伊朗衝突擴大，油價急漲", "布蘭特原油上漲4%，避險資金湧入黃金", "Bloomberg"),
    ("美國擬擴大對中國半導體出口管制", "市場擔心實體清單擴大衝擊供應鏈", "Reuters"),
    ("SCFI 運價連三週下跌，貨櫃航運股承壓", "新船交付增加，運力過剩疑慮升溫", "鉅亨網"),
    ("液冷散熱滲透率快速提升，奇鋐、雙鴻營收大漲", "AI 晶片功耗提高帶動水冷板需求", "MoneyDJ"),
    ("Nvidia shares jump after strong data center guidance", "Data center revenue beat expectations as cloud capex rises", "CNBC"),
    ("Stocks fall as Treasury yields climb on hawkish Fed comments", "S&P 500 slips as investors reassess rate cut path", "Reuters"),
    ("台股加權指數創新高，外資買超台積電", "半導體權值股領漲，成交量放大", "中央社"),
    ("颱風來襲，部分工廠停工檢查", "電子廠表示影響有限", "中央社"),
    ("中國人行宣布降準，陸股大漲", "中國刺激政策加碼，鋼鐵、塑化股走強", "鉅亨網"),
    ("蘋果新款 iPhone 銷售不如預期，供應鏈下修拉貨", "大立光、和碩股價走弱", "經濟日報"),
]


def demo_news(now: datetime) -> list[NewsItem]:
    """示範新聞（沒有網路時用）。標題固定、時間隨執行時間變動。"""
    out = []
    for i, (title, summary, src) in enumerate(_DEMO_HEADLINES):
        lang = "en" if title.isascii() else "zh"
        out.append(
            NewsItem(
                title=title,
                summary=summary,
                url="https://example.com/demo",
                source=src + "（示範）",
                published=iso(now - timedelta(minutes=7 * i)),
                lang=lang,
            )
        )
    return out
