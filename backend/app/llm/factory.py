from __future__ import annotations

import logging

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import Settings

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """根据环境变量配置，实例化对应的 LangChain 统一 LLM 客户端。

    - USE_LOCAL_LLM=false（默认）→ ChatOpenAI（兼容 OpenAI / 第三方 OpenAI-compatible API）
    - USE_LOCAL_LLM=true          → ChatOllama（本地 Ollama 服务，零成本免密）
    """

    @staticmethod
    def create(settings: Settings) -> BaseChatModel:
        """返回 LangChain BaseChatModel 实例，上层 Agent 无需关心底层实现。"""
        if settings.use_local_llm:
            try:
                from langchain_ollama import ChatOllama
            except ImportError as exc:
                raise ImportError(
                    "本地 Ollama 模式需要安装 langchain-ollama：pip install langchain-ollama>=0.3.0"
                ) from exc

            logger.info(
                "初始化 Ollama 客户端：model=%s, base_url=%s",
                settings.ollama_model,
                settings.ollama_base_url,
            )
            return ChatOllama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                temperature=0.3,
            )

        from langchain_openai import ChatOpenAI

        api_key = settings.openai_api_key or "dummy"
        logger.info(
            "初始化 OpenAI-compatible 客户端：model=%s, base_url=%s, has_key=%s",
            settings.openai_model,
            settings.openai_base_url,
            bool(settings.openai_api_key and settings.openai_api_key != "dummy"),
        )
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=api_key,
            base_url=settings.openai_base_url,
            temperature=0.3,
            timeout=60.0,
        )
