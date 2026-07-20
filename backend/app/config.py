from functools import lru_cache

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"

    # LLM — 通用
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # LLM — 模式开关：true 走 Ollama，false 走 OpenAI-compatible API
    use_local_llm: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # 智能体编排：默认使用 LangGraph 图引擎
    use_langgraph: bool = True

    # Database
    database_url: str = "sqlite:///./talentmatch.db"
    database_url_sqlite: str = "sqlite:///./talentmatch.db"

    # Vector store
    vector_db_path: str = "./chroma_data"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def effective_database_url(self) -> str:
        # Prefer MySQL when available; fallback to SQLite for quick local runs
        if "mysql" in self.database_url.lower():
            return self.database_url
        return self.database_url_sqlite


@lru_cache
def get_settings() -> Settings:
    return Settings()
