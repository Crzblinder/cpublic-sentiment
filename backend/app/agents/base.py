import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.prompts.loader import PromptLoader

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    name: str = "base"

    def __init__(self, prompt_variant: str | None = None):
        self.settings = get_settings()
        self.prompt_variant = prompt_variant or "default"
        self._llm = None  # 延迟初始化 LangChain BaseChatModel
        self.loader = PromptLoader()

    # ------------------------------------------------------------------
    # LLM 客户端（懒加载，通过工厂统一创建）
    # ------------------------------------------------------------------
    @property
    def llm(self):
        if self._llm is None:
            from app.llm.factory import LLMClientFactory

            self._llm = LLMClientFactory.create(self.settings)
        return self._llm

    # ------------------------------------------------------------------
    # 是否具备真实 LLM 调用能力
    # ------------------------------------------------------------------
    def _has_real_llm(self) -> bool:
        if self.settings.use_local_llm:
            # Ollama 模式下，只要地址配置了即视为可用
            return bool(self.settings.ollama_base_url)
        return bool(self.settings.openai_api_key and self.settings.openai_api_key != "dummy")

    # ------------------------------------------------------------------
    # 标准化链式调用（提示词组装 -> LLM -> JSON 解析 -> 容灾降级）
    # ------------------------------------------------------------------
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
        """通过 LangChain 统一接口调用大模型，强制 JSON 输出，异常时降级到规则引擎。"""
        from langchain_core.messages import HumanMessage, SystemMessage

        start = time.time()

        # ---- 无 LLM 配置时直接走确定性降级 ----
        if not self._has_real_llm():
            logger.warning("No LLM configured (use_local_llm=%s); deterministic fallback",
                           self.settings.use_local_llm)
            return self._simulate_response(system_prompt, user_prompt)

        # ---- 组装 LangChain 消息列表 ----
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            # 通过 LangChain BaseChatModel 统一调用
            response = self.llm.invoke(messages)
            content = response.content if hasattr(response, "content") else str(response)

            elapsed_ms = int((time.time() - start) * 1000)
            parsed = self._parse_json(content)
            parsed["_latency_ms"] = elapsed_ms

            # 若 JSON 解析失败（返回了 raw wrapper），视为异常触发降级
            if parsed.get("parsed") is False:
                logger.warning("LLM returned non-JSON content; triggering fallback")
                fallback = self._simulate_response(system_prompt, user_prompt)
                fallback["_latency_ms"] = elapsed_ms
                fallback["_fallback_reason"] = "non_json_response"
                return fallback

            return parsed

        except Exception as e:
            logger.error("LLM call failed: %s; triggering deterministic fallback", e)
            elapsed_ms = int((time.time() - start) * 1000)
            fallback = self._simulate_response(system_prompt, user_prompt)
            fallback["_latency_ms"] = elapsed_ms
            fallback["_fallback_reason"] = str(e)
            return fallback

    # ------------------------------------------------------------------
    # JSON 解析（保留原有逻辑）
    # ------------------------------------------------------------------
    def _parse_json(self, content: str) -> dict[str, Any]:
        content = content.strip()
        # 去除 Markdown 代码块包裹
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:].strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("LLM did not return valid JSON; wrapping raw text")
            return {"raw": content, "parsed": False}

    # ------------------------------------------------------------------
    # 确定性降级基类实现（各子类可覆盖）
    # ------------------------------------------------------------------
    def _simulate_response(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Deterministic fallback when no LLM key is provided, so the project runs out-of-box."""
        return {"simulated": True, "note": "LLM not configured; deterministic fallback used"}

    # ------------------------------------------------------------------
    # 提示词加载（从外部 .txt 文件读取）
    # ------------------------------------------------------------------
    def _load_prompt(self) -> str:
        """根据 Agent 名称和当前变体，从外部文件加载提示词模板。"""
        variant = self._resolve_variant()
        return self.loader.load(self.name, variant)

    def _resolve_variant(self) -> str:
        """将 prompt_variant 标准化为文件名格式。"""
        v = self.prompt_variant or "default"
        # 将 "scanner-zero-shot" 这类全名转换为 "zero_shot"
        if "-" in v:
            parts = v.split("-", 1)
            if len(parts) == 2:
                v = parts[1]
        # 标准化映射
        aliases = {
            "default": "zero_shot",
            "zero-shot": "zero_shot",
            "Zero-Shot": "zero_shot",
            "cot": "cot",
            "CoT": "cot",
            "few-shot": "few_shot",
            "Few-Shot": "few_shot",
            "roleplay": "roleplay",
            "RolePlay": "roleplay",
        }
        return aliases.get(v, v)

    @abstractmethod
    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
