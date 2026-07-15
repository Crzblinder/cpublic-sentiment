import logging
import os
from functools import lru_cache
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingModel:
    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self._model: Any | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            cache_dir = os.path.join(os.getcwd(), "models_cache")
            os.makedirs(cache_dir, exist_ok=True)
            logger.info(f"Loading embedding model {self.model_name}...")
            self._model = SentenceTransformer(self.model_name, cache_folder=cache_dir)
        return self._model

    def encode(self, texts: str | list[str]) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        return self.model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)

    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()


@lru_cache
def get_embedding_model() -> EmbeddingModel:
    return EmbeddingModel()
