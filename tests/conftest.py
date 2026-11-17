import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(autouse=True)
def _no_keys(monkeypatch):
    """測試時一律不使用真的 AI 金鑰。"""
    for k in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("STOCK_ROOT", str(ROOT))


@pytest.fixture
def cfg():
    from stock_analysis.config import load_config

    return load_config(ROOT)
