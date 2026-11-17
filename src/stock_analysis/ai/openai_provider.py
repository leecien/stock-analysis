"""OpenAI（ChatGPT 的 API）。預設不啟用。"""

from __future__ import annotations

import json
import os

from .base import AIError, AIProvider, Usage, parse_json_text


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, conf: dict):
        super().__init__(conf)
        import openai

        self._openai = openai
        self.client = openai.OpenAI(api_key=os.environ[conf.get("env_key", "OPENAI_API_KEY")])

    def generate_json(self, *, tier, system, user, schema, max_tokens=8000):
        model = self.model_for(tier)
        prompt = f"{user}\n\n請只輸出符合以下 JSON Schema 的 JSON：\n{json.dumps(schema, ensure_ascii=False)}"
        try:
            resp = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_completion_tokens=max_tokens,
            )
        except self._openai.OpenAIError as e:
            raise AIError(f"OpenAI API 錯誤：{e}") from e
        u = resp.usage
        cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0
        usage = Usage(
            provider=self.name,
            model=model,
            input_tokens=(u.prompt_tokens or 0) - cached,
            output_tokens=u.completion_tokens or 0,
            cache_read_tokens=cached,
        )
        return parse_json_text(resp.choices[0].message.content or ""), usage
