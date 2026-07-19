import logging
import os
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings

logger = logging.getLogger(__name__)


class _ProjectEmbeddingFunction:
    """ChromaDB-compatible embedding function backed by the project's EmbeddingModel.

    Avoids downloading ChromaDB's default ONNX model from AWS S3 (very slow in China).
    Uses BAAI/bge-small-zh-v1.5 via sentence-transformers instead.
    """

    def __init__(self) -> None:
        self._model = None

    def name(self) -> str:
        """Return a stable name for ChromaDB 1.5+ compatibility."""
        return "project_bge_small_zh_v1_5"

    def is_legacy(self) -> bool:
        """Declare this as a non-legacy embedding function."""
        return False

    def _get_model(self):
        if self._model is None:
            from app.rag.embeddings import get_embedding_model

            self._model = get_embedding_model()
        return self._model

    def __call__(self, input: list[str]) -> list[list[float]]:
        embeddings = self._get_model().encode(input)
        return embeddings.tolist()


# Module-level singleton so all collections share the same model instance
_default_ef = _ProjectEmbeddingFunction()


class VectorStore:
    def __init__(self, collection_name: str):
        settings = get_settings()
        self.collection_name = collection_name
        self.path = settings.vector_db_path
        os.makedirs(self.path, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=self.path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # 手动计算 embeddings 传入 Chroma，避免自定义 EmbeddingFunction 的兼容性问题
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ):
        if metadatas is None:
            metadatas = [{} for _ in ids]
        # Chroma requires metadata values to be primitive types
        clean_metadatas = []
        for m in metadatas:
            clean = {}
            for k, v in m.items():
                if isinstance(v, (list, dict)):
                    clean[k] = str(v)
                else:
                    clean[k] = v
            clean_metadatas.append(clean)
        embeddings = _default_ef(documents)
        self.collection.upsert(
            ids=ids, embeddings=embeddings, documents=documents, metadatas=clean_metadatas
        )

    def query(
        self,
        query_texts: list[str],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ):
        embeddings = _default_ef(query_texts)
        kwargs: dict[str, Any] = {
            "query_embeddings": embeddings,
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where
        return self.collection.query(**kwargs)

    def delete_all(self):
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(name=self.collection_name)
