"""AI 花費追蹤：依每月台幣預算自動降級。"""

from __future__ import annotations

from datetime import datetime

from .ai.base import Usage
from .timeutil import to_tw


class Budget:
    def __init__(self, cfg, state: dict, now: datetime):
        self.cfg = cfg
        self.month = to_tw(now).strftime("%Y-%m")
        self.limit_twd = float(cfg.get("budget.monthly_twd", 600))
        self.rate = float(cfg.get("budget.usd_to_twd", 32))
        self.pricing = cfg.get("ai.pricing", {}) or {}
        months = state.get("months", {})
        self.months = months
        self.cur = months.setdefault(self.month, {"usd": 0.0, "calls": 0, "by_model": {}})

    def cost_usd(self, u: Usage) -> float:
        p = self.pricing.get(u.model)
        if not p:
            return 0.0
        inp, out = float(p.get("input", 0)), float(p.get("output", 0))
        cr = float(p.get("cache_read", inp * 0.1))
        return (
            u.input_tokens * inp
            + u.cache_write_tokens * inp * 1.25
            + u.cache_read_tokens * cr
            + u.output_tokens * out
        ) / 1_000_000

    def add(self, u: Usage) -> float:
        c = self.cost_usd(u)
        self.cur["usd"] = round(self.cur["usd"] + c, 6)
        self.cur["calls"] += 1
        m = self.cur["by_model"].setdefault(u.model, {"usd": 0.0, "calls": 0, "input": 0, "output": 0})
        m["usd"] = round(m["usd"] + c, 6)
        m["calls"] += 1
        m["input"] += u.input_tokens + u.cache_read_tokens + u.cache_write_tokens
        m["output"] += u.output_tokens
        return c

    @property
    def spent_twd(self) -> float:
        return self.cur["usd"] * self.rate

    @property
    def ratio(self) -> float:
        return self.spent_twd / self.limit_twd if self.limit_twd else 0.0

    def allow(self, tier: str) -> bool:
        if self.ratio >= float(self.cfg.get("budget.hard_stop_ratio", 1.0)):
            return False
        if tier == "deep" and self.ratio >= float(self.cfg.get("budget.deep_stop_ratio", 0.85)):
            return False
        return True

    def state(self) -> dict:
        # 只保留最近 12 個月
        keep = sorted(self.months)[-12:]
        return {"months": {k: self.months[k] for k in keep}}

    def summary(self) -> dict:
        return {
            "month": self.month,
            "spent_twd": round(self.spent_twd, 1),
            "limit_twd": self.limit_twd,
            "ratio": round(self.ratio, 3),
            "calls": self.cur["calls"],
            "by_model": self.cur["by_model"],
        }
