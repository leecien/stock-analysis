"""依設定與環境變數建立 AI 供應商；沒有金鑰就用模擬 AI。"""

from __future__ import annotations

import logging
import os

from .base import AIProvider, MockProvider

log = logging.getLogger(__name__)


def _make(name: str, conf: dict) -> AIProvider | None:
    key_env = conf.get("env_key", "")
    if not os.environ.get(key_env):
        return None
    try:
        if name == "claude":
            from .claude import ClaudeProvider
            return ClaudeProvider(conf)
        if name == "gemini":
            from .gemini import GeminiProvider
            return GeminiProvider(conf)
        if name == "openai":
            from .openai_provider import OpenAIProvider
            return OpenAIProvider(conf)
    except Exception as e:
        log.warning("無法建立 AI 供應商 %s：%s", name, e)
        return None
    log.warning("不認得的 AI 供應商：%s", name)
    return None


def build_providers(cfg, tier: str, force_mock: bool = False) -> list[AIProvider]:
    """tier='fast' 或 'deep'。回傳可用的供應商清單；一個都沒有時回傳 [MockProvider]。"""
    if force_mock:
        return [MockProvider()]
    names = cfg.get(f"ai.{tier}_providers", []) or []
    confs = cfg.get("ai.providers", {}) or {}
    out = [p for n in names if (p := _make(n, confs.get(n, {}))) is not None]
    return out or [MockProvider()]
