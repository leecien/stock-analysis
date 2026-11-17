"""Claude（Anthropic API）。"""

from __future__ import annotations

import os

from .base import AIError, AIProvider, Usage, parse_json_text


class ClaudeProvider(AIProvider):
    name = "claude"

    def __init__(self, conf: dict):
        super().__init__(conf)
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=os.environ[conf.get("env_key", "ANTHROPIC_API_KEY")])

    def generate_json(self, *, tier, system, user, schema, max_tokens=8000):
        anthropic = self._anthropic
        model = self.model_for(tier)
        effort = self.conf.get(f"{tier}_effort", "low" if tier == "fast" else "medium")
        kwargs = dict(
            model=model,
            max_tokens=max_tokens,
            # 系統提示固定不變（主題清單等），標記快取以節省費用
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        )
        try:
            if model.startswith(("claude-sonnet-5-5", "claude-opus-5-5", "claude-fable")):
                # 遇到安全機制拒答時，由伺服器自動改用其他模型重試
                resp = self.client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs
                )
            else:
                resp = self.client.messages.create(**kwargs)
        except anthropic.AuthenticationError as e:
            raise AIError("Claude API 金鑰無效") from e
        except anthropic.RateLimitError as e:
            raise AIError("Claude API 請求太頻繁或額度用完") from e
        except anthropic.APIStatusError as e:
            raise AIError(f"Claude API 錯誤 {e.status_code}：{e.message}") from e
        except anthropic.APIConnectionError as e:
            raise AIError("無法連線到 Claude API") from e

        u = resp.usage
        usage = Usage(
            provider=self.name,
            model=model,
            input_tokens=u.input_tokens or 0,
            output_tokens=u.output_tokens or 0,
            cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
        )
        if resp.stop_reason == "refusal":
            raise AIError("Claude 拒絕回答這次請求")
        if resp.stop_reason == "max_tokens":
            raise AIError("Claude 回應超過長度上限")
        text = next((b.text for b in resp.content if b.type == "text"), "")
        return parse_json_text(text), usage
