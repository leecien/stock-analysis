"""讀取 config/ 底下的設定檔。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def find_root() -> Path:
    """找專案根目錄（含 config/settings.yaml）。可用環境變數 STOCK_ROOT 指定。"""
    env = os.environ.get("STOCK_ROOT")
    if env:
        return Path(env).resolve()
    for base in [Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parents[2]]:
        if (base / "config" / "settings.yaml").exists():
            return base
    raise FileNotFoundError("找不到 config/settings.yaml，請在專案目錄執行或設定 STOCK_ROOT")


def _load_yaml(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass
class Config:
    root: Path
    settings: dict
    watchlist: list[dict]
    themes: dict
    macro_factors: dict
    seed_events: list[dict] = field(default_factory=list)

    def get(self, dotted: str, default: Any = None) -> Any:
        """用 'ai.news_batch_size' 這種寫法取值。"""
        cur: Any = self.settings
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    @property
    def index_names(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for m in self.settings.get("markets", {}).values():
            if isinstance(m, dict) and "indices" in m:
                out.update(m["indices"])
        out.update(self.settings.get("markets", {}).get("macro", {}))
        return out

    @property
    def watchlist_symbols(self) -> list[str]:
        return [s["symbol"] for s in self.watchlist]


def load_config(root: Path | None = None) -> Config:
    root = Path(root) if root else find_root()
    settings = _load_yaml(root / "config" / "settings.yaml")
    watch = _load_yaml(root / "config" / "watchlist.yaml").get("stocks", [])
    themes_doc = _load_yaml(root / "config" / "themes.yaml")
    seed_path = root / "data" / "seed" / "major_events.yaml"
    seed = _load_yaml(seed_path).get("events", []) if seed_path.exists() else []
    for s in watch:
        s["symbol"] = str(s["symbol"]).strip().upper()
    return Config(
        root=root,
        settings=settings,
        watchlist=watch,
        themes=themes_doc.get("themes", {}),
        macro_factors=themes_doc.get("macro_factors", {}),
        seed_events=seed,
    )
