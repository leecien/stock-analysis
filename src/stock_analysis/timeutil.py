"""時間工具：台灣時間、交易時段。"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TW = ZoneInfo("Asia/Taipei")
NY = ZoneInfo("America/New_York")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_tw(dt: datetime) -> datetime:
    return dt.astimezone(TW)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def hour_key(dt: datetime) -> str:
    """以 UTC 小時當作統計桶的 key，例如 2026-11-17T02。"""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H")


def tw_market_open(dt: datetime) -> bool:
    t = to_tw(dt)
    return t.weekday() < 5 and (9, 0) <= (t.hour, t.minute) <= (13, 30)


def us_market_open(dt: datetime) -> bool:
    t = dt.astimezone(NY)
    return t.weekday() < 5 and (9, 30) <= (t.hour, t.minute) <= (16, 0)


def session_label(dt: datetime) -> str:
    if tw_market_open(dt):
        return "台股盤中"
    if us_market_open(dt):
        return "美股盤中"
    return "休市時段"
