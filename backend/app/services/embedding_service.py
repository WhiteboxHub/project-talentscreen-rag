from typing import List
import numpy as np
import hashlib
from app.core.config import settings
from app.services.cache_service import cache
from app.core.logging import logger

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

class EmbeddingService:
    """Embedding service with dynamic SentenceTransformer loading and robust dummy fallback.
    Maintains a consistent dimension of 384 for all-MiniLM-L6-v2 compatibility.
    """

    def __init__(self, model_name: str | None = None):
        self.dim = 384  # Matches all-MiniLM-L6-v2 dimension
        self.model = None
        self.enabled = False
        
        model_name = model_name or settings.EMBEDDING_MODEL
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                logger.info(f"Loading SentenceTransformer model: {model_name}...")
                self.model = SentenceTransformer(model_name)
                self.enabled = True
                logger.info(f"SentenceTransformer model {model_name} loaded successfully.")
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer model: {e}. Falling back to dummy embeddings.")
        else:
            logger.warning("sentence-transformers not installed. Falling back to dummy embeddings.")

    def _text_to_vector(self, text: str) -> List[float]:
        # Create a deterministic vector from SHA256 hash
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Convert bytes to floats in range [0, 1)
        vec = [b / 255.0 for b in h[:self.dim]]
        # Pad if needed
        if len(vec) < self.dim:
            vec += [0.0] * (self.dim - len(vec))
        return vec

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        results: List[List[float]] = []
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
            if self.enabled and self.model:
                try:
                    new_embeddings = self.model.encode(missing_texts).tolist()
                    for i, emb in zip(missing_indices, new_embeddings):
                        results[i] = emb
                        cache.set_embedding(texts[i], emb)
                except Exception as e:
                    logger.error(f"Failed to generate SentenceTransformer embeddings: {e}. Falling back to dummy.")
                    for idx, text in zip(missing_indices, missing_texts):
                        emb = self._text_to_vector(text)
                        results[idx] = emb
                        cache.set_embedding(text, emb)
            else:
                for idx, text in zip(missing_indices, missing_texts):
                    emb = self._text_to_vector(text)
                    results[idx] = emb
                    cache.set_embedding(text, emb)

        return results

    def get_embedding(self, text: str) -> List[float]:
        cached = cache.get_embedding(text)
        if cached:
            return cached
            
        if self.enabled and self.model:
            try:
                emb = self.model.encode([text])[0].tolist()
                cache.set_embedding(text, emb)
                return emb
            except Exception as e:
                logger.error(f"Failed to generate SentenceTransformer embedding: {e}. Falling back to dummy.")
                
        emb = self._text_to_vector(text)
        cache.set_embedding(text, emb)
        return emb

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        v1_arr = np.array(v1)
        v2_arr = np.array(v2)
        dot = np.dot(v1_arr, v2_arr)
        norm = np.linalg.norm(v1_arr) * np.linalg.norm(v2_arr)
        return float(dot / norm) if norm != 0 else 0.0
