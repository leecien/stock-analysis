from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass


class AIError(Exception):
    """AI 呼叫失敗（金鑰錯誤、拒答、回傳格式錯誤等）。"""


@dataclass
class Usage:
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


class AIProvider(ABC):
    """所有 AI 供應商共用的介面：給系統提示、使用者內容、JSON Schema，回傳 dict。"""

    name: str = "base"
    is_mock: bool = False

    def __init__(self, conf: dict | None = None):
        self.conf = conf or {}

    def model_for(self, tier: str) -> str:
        return self.conf.get(f"{tier}_model", "")

    @abstractmethod
    def generate_json(
        self, *, tier: str, system: str, user: str, schema: dict, max_tokens: int = 8000
    ) -> tuple[dict, Usage]:
        ...


class MockProvider(AIProvider):
    """模擬 AI：不呼叫任何外部服務。各分析模組看到 is_mock 會改用規則式邏輯。"""

    name = "mock"
    is_mock = True

    def model_for(self, tier: str) -> str:
        return "rule-based"

    def generate_json(self, **kwargs) -> tuple[dict, Usage]:
        raise AIError("MockProvider 不產生 AI 回應，請改用規則式邏輯")


def parse_json_text(text: str) -> dict:
    """解析 AI 回傳的 JSON（容忍 ```json 區塊）。"""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise AIError(f"AI 回傳的不是合法 JSON：{e}") from e
    if not isinstance(data, dict):
        raise AIError("AI 回傳的 JSON 不是物件")
    return data
