import logging
import os
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings

logger = logging.getLogger(__name__)


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
        self.collection.upsert(ids=ids, documents=documents, metadatas=clean_metadatas)

    def query(
        self,
        query_texts: list[str],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ):
        kwargs: dict[str, Any] = {"query_texts": query_texts, "n_results": n_results}
        if where:
            kwargs["where"] = where
        return self.collection.query(**kwargs)

    def delete_all(self):
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(name=self.collection_name)
