import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx
from openai import AsyncOpenAI, OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    name: str = "base"

    def __init__(self, prompt_variant: str | None = None):
        self.settings = get_settings()
        self.prompt_variant = prompt_variant or "default"
        self._client: OpenAI | None = None
        self._async_client: AsyncOpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=self.settings.openai_api_key or "dummy",
                base_url=self.settings.openai_base_url,
                http_client=httpx.Client(timeout=60.0),
            )
        return self._client

    @property
    def async_client(self) -> AsyncOpenAI:
        if self._async_client is None:
            self._async_client = AsyncOpenAI(
                api_key=self.settings.openai_api_key or "dummy",
                base_url=self.settings.openai_base_url,
                http_client=httpx.AsyncClient(timeout=60.0),
            )
        return self._async_client

    def _has_real_llm(self) -> bool:
        return bool(self.settings.openai_api_key and self.settings.openai_api_key != "dummy")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        start = time.time()
        if not self._has_real_llm():
            logger.warning("No LLM API key configured; returning simulated response")
            return self._simulate_response(system_prompt, user_prompt)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            kwargs: dict[str, Any] = {
                "model": self.settings.openai_model,
                "messages": messages,
                "temperature": temperature,
            }
            if response_format:
                kwargs["response_format"] = response_format
            completion = self.client.chat.completions.create(**kwargs)
            content = completion.choices[0].message.content or "{}"
            elapsed_ms = int((time.time() - start) * 1000)
            parsed = self._parse_json(content)
            parsed["_latency_ms"] = elapsed_ms
            return parsed
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_json(self, content: str) -> dict[str, Any]:
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:].strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("LLM did not return valid JSON; wrapping raw text")
            return {"raw": content, "parsed": False}

    def _simulate_response(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Deterministic fallback when no LLM key is provided, so the project runs out-of-box."""
        return {"simulated": True, "note": "LLM not configured; deterministic fallback used"}

    @abstractmethod
    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
