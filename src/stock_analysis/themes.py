"""產業主題對照：從文字找出相關的主題、總經因素、個股。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import Config


def _compile(keyword: str) -> re.Pattern:
    kw = re.escape(keyword.strip())
    if re.fullmatch(r"[\x00-\x7f]+", keyword):
        # 英文關鍵字要比對完整單字，避免 "EV" 比對到 "every"
        return re.compile(rf"(?<![A-Za-z0-9]){kw}(?![A-Za-z0-9])", re.IGNORECASE)
    return re.compile(kw)


@dataclass
class Match:
    themes: list[str] = field(default_factory=list)
    macros: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    tickers: list[str] = field(default_factory=list)


class ThemeIndex:
    def __init__(self, cfg: Config):
        self.themes = cfg.themes
        self.macros = cfg.macro_factors
        self._theme_kw = {
            tid: [(k, _compile(k)) for k in t.get("keywords", [])] for tid, t in self.themes.items()
        }
        self._macro_kw = {
            mid: [(k, _compile(k)) for k in m.get("keywords", [])] for mid, m in self.macros.items()
        }
        # 代號 → 名稱；名稱 → 代號（用來從新聞找出個股）
        self.symbol_names: dict[str, str] = {}
        for t in self.themes.values():
            for sym in t.get("us", []) or []:
                self.symbol_names.setdefault(sym, sym)
            for sym, name in (t.get("tw") or {}).items():
                self.symbol_names[sym] = name
        for s in cfg.watchlist:
            self.symbol_names[s["symbol"]] = s.get("name", s["symbol"])
        self._name_patterns = []
        for sym, name in self.symbol_names.items():
            pats = [_compile(name)]
            if not sym[0].isdigit() and "." not in sym and len(sym) >= 2:
                pats.append(re.compile(rf"(?<![A-Za-z0-9$]){re.escape(sym)}(?![A-Za-z0-9])"))
            code = sym.split(".")[0]
            if code.isdigit():
                pats.append(re.compile(rf"(?<!\d){code}(?!\d)"))
            self._name_patterns.append((sym, pats))

    def theme_name(self, tid: str) -> str:
        return self.themes.get(tid, {}).get("name", tid)

    def macro_name(self, mid: str) -> str:
        return self.macros.get(mid, {}).get("name", mid)

    def theme_symbols(self, tid: str) -> list[str]:
        t = self.themes.get(tid, {})
        return list(t.get("us", []) or []) + list((t.get("tw") or {}).keys())

    def all_symbols(self) -> list[str]:
        return sorted(self.symbol_names)

    def match(self, text: str) -> Match:
        m = Match()
        for tid, kws in self._theme_kw.items():
            hit = [k for k, p in kws if p.search(text)]
            if hit:
                m.themes.append(tid)
                m.keywords.extend(hit)
        for mid, kws in self._macro_kw.items():
            hit = [k for k, p in kws if p.search(text)]
            if hit:
                m.macros.append(mid)
                m.keywords.extend(hit)
        for sym, pats in self._name_patterns:
            if any(p.search(text) for p in pats):
                m.tickers.append(sym)
        m.keywords = list(dict.fromkeys(m.keywords))
        return m

    def prompt_catalog(self) -> str:
        """給 AI 看的主題清單（固定內容，可被 prompt cache 快取）。"""
        lines = ["## 產業主題（id：名稱｜關鍵字｜代表個股｜典型漲跌原因）"]
        for tid, t in self.themes.items():
            syms = ", ".join(self.theme_symbols(tid)[:8])
            kws = "、".join(t.get("keywords", [])[:10])
            drivers = "；".join(t.get("drivers", []))
            lines.append(f"- {tid}：{t.get('name')}｜{kws}｜{syms}｜{drivers}")
        lines.append("\n## 總經與政治因素（id：名稱｜類別｜關鍵字）")
        for mid, mf in self.macros.items():
            kws = "、".join(mf.get("keywords", [])[:8])
            lines.append(f"- {mid}：{mf.get('name')}｜{mf.get('category')}｜{kws}")
        return "\n".join(lines)
