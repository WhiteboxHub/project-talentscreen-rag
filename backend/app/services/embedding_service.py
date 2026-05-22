from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np
from app.core.config import settings

from app.services.cache_service import cache
from app.core.logging import logger

class EmbeddingService:
    def __init__(self, model_name: str = None):
        model_name = model_name or settings.EMBEDDING_MODEL
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        results = []
        missing_texts = []
        missing_indices = []

        for i, text in enumerate(texts):
            cached = cache.get_embedding(text)
            if cached:
                results.append(cached)
            else:
                results.append(None)
                missing_texts.append(text)
                missing_indices.append(i)

        if missing_texts:
            new_embeddings = self.model.encode(missing_texts).tolist()
            for i, emb in zip(missing_indices, new_embeddings):
                results[i] = emb
                cache.set_embedding(texts[i], emb)

        return results

    def get_embedding(self, text: str) -> List[float]:
        cached = cache.get_embedding(text)
        if cached: return cached
        
        embedding = self.model.encode([text])[0].tolist()
        cache.set_embedding(text, embedding)
        return embedding

    @staticmethod
    def cosine_similarity(v1, v2):
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
