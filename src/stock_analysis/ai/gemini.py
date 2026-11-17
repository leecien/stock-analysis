"""Google Gemini。"""

from __future__ import annotations

import json
import os

from .base import AIError, AIProvider, Usage, parse_json_text


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, conf: dict):
        super().__init__(conf)
        from google import genai

        self.client = genai.Client(api_key=os.environ[conf.get("env_key", "GEMINI_API_KEY")])

    def generate_json(self, *, tier, system, user, schema, max_tokens=8000):
        from google.genai import types

        model = self.model_for(tier)
        prompt = f"{user}\n\n請只輸出符合以下 JSON Schema 的 JSON：\n{json.dumps(schema, ensure_ascii=False)}"
        try:
            resp = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    max_output_tokens=max_tokens,
                ),
            )
        except Exception as e:  # google-genai 的錯誤類別依版本不同
            raise AIError(f"Gemini API 錯誤：{e}") from e
        meta = resp.usage_metadata
        usage = Usage(
            provider=self.name,
            model=model,
            input_tokens=getattr(meta, "prompt_token_count", 0) or 0,
            output_tokens=(getattr(meta, "candidates_token_count", 0) or 0)
            + (getattr(meta, "thoughts_token_count", 0) or 0),
            cache_read_tokens=getattr(meta, "cached_content_token_count", 0) or 0,
        )
        if not resp.text:
            raise AIError("Gemini 沒有回傳內容")
        return parse_json_text(resp.text), usage
