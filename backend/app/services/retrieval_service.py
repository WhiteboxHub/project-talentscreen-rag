"""Hybrid Retrieval Service (PDF Parts 7, 8).

Implements the complete retrieval pipeline specified in the TalentScreen RAG Study Guide:
  - Part 7.2: BM25 sparse keyword retrieval
  - Part 7.3: Milvus dense vector retrieval
  - Part 7.4: Metadata filtering (experience, role, skills, document type)
  - Part 7.5: Reciprocal Rank Fusion (RRF) to merge results
  - Part 8.2: BGE Cross-Encoder reranking for precision ranking
  - Part 8.3: Relevance scoring
  - Part 8.4: Final top-K candidate selection
"""

from typing import List, Dict, Any, Optional
from app.db.vector_db import VectorDB
from app.services.embedding_service import EmbeddingService
from app.services.observability import observability
from app.core.logging import logger
from rank_bm25 import BM25Okapi
import numpy as np

try:
    from sentence_transformers import CrossEncoder
    from app.core.config import settings
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False


class HybridRetrievalService:
    """Production hybrid retrieval service.

    Combines BM25 keyword search with Milvus vector search via Reciprocal
    Rank Fusion (RRF), then applies BGE Cross-Encoder reranking to select
    the highest-quality results before passing context to the LLM.

    Reference: PDF Parts 7 & 8 — Hybrid Retrieval and Reranking.
    """

    def __init__(self, vector_db: VectorDB, embedding_service: EmbeddingService):
        self.vector_db = vector_db
        self.embedding_service = embedding_service

        # BM25 state (Part 7.2)
        self.documents: List[str] = []
        self.doc_metadatas: List[Dict[str, Any]] = []
        self.bm25: Optional[BM25Okapi] = None

        # BGE Cross-Encoder reranker (Part 8.2)
        self.reranker = None
        self.use_reranker = False

        if CROSS_ENCODER_AVAILABLE:
            try:
                model_name = getattr(settings, "RERANKER_MODEL", "BAAI/bge-reranker-base")
                logger.info(f"Loading Cross-Encoder reranker model ({model_name})...")
                self.reranker = CrossEncoder(model_name)
                self.use_reranker = True
                logger.info("Cross-Encoder reranker loaded successfully.")
            except Exception as e:
                logger.warning(f"Could not load Cross-Encoder: {e}. Reranking will be disabled.")
        else:
            logger.warning("sentence-transformers not installed. Reranking will be disabled.")

    # ================================================================
    # BM25 INDEX MANAGEMENT (Part 7.2)
    # ================================================================

    def initialize_bm25(self, texts: List[str], metadatas: List[Dict[str, Any]] = None):
        """Initialize BM25 sparse keyword index with document corpus."""
        if not texts:
            logger.info("BM25 initialized with empty corpus.")
            self.bm25 = None
            self.documents = []
            self.doc_metadatas = []
            return

        tokenized_corpus = [doc.lower().split() for doc in texts]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.documents = texts
        self.doc_metadatas = metadatas or [{} for _ in texts]
        logger.info(f"BM25 index built with {len(texts)} documents.")

    def reload_bm25(self):
        """Reload BM25 index from the Milvus vector DB on startup or re-index."""
        try:
            texts, metadatas = self.vector_db.get_all_documents_with_metadata()
            if texts:
                self.initialize_bm25(texts, metadatas)
                logger.info(f"Loaded {len(texts)} documents into BM25 corpus.")
            else:
                logger.info("No documents found in database to initialize BM25.")
                self.bm25 = None
                self.documents = []
        except Exception as e:
            # Graceful degradation — fall back to texts-only if method not available
            try:
                texts = self.vector_db.get_all_documents()
                if texts:
                    self.initialize_bm25(texts)
                    logger.info(f"Loaded {len(texts)} documents into BM25 corpus.")
            except Exception as inner_e:
                logger.error(f"Failed to reload BM25: {inner_e}")

    # ================================================================
    # METADATA FILTERING (PDF Part 7.4)
    # ================================================================

    def _apply_metadata_filter(
        self,
        results: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter retrieved results based on structured metadata constraints.

        Supports the following filter keys (as per PDF Part 7.4):
          - min_experience: int — minimum years of experience
          - max_experience: int — maximum years of experience
          - document_type: str — e.g. 'resume', 'job_description', 'interview_guide'
          - job_role: str — partial match against candidate role
          - skills: List[str] — candidate must have at least one of these skills
          - education: str — required education level (e.g. "Master's", "Bachelor's")

        Reference: PDF Part 7.4 — Metadata Filtering.
        """
        if not filters:
            return results

        filtered = []
        for result in results:
            meta = result.get("metadata", {}) or {}
            passed = True

            # Filter by minimum years of experience
            if "min_experience" in filters:
                exp = meta.get("years_of_experience", 0) or 0
                if exp < filters["min_experience"]:
                    passed = False

            # Filter by maximum years of experience
            if passed and "max_experience" in filters:
                exp = meta.get("years_of_experience", 0) or 0
                if exp > filters["max_experience"]:
                    passed = False

            # Filter by document type (e.g. only resumes)
            if passed and "document_type" in filters:
                doc_type = meta.get("document_type", "")
                if doc_type and doc_type != filters["document_type"]:
                    passed = False

            # Filter by job role (partial case-insensitive match)
            if passed and "job_role" in filters:
                role = meta.get("job_role", "").lower()
                if role and filters["job_role"].lower() not in role:
                    passed = False

            # Filter by required skills (candidate must have at least one)
            if passed and "skills" in filters:
                required = [s.lower() for s in filters["skills"]]
                candidate_skills = [s.lower() for s in (meta.get("skills") or [])]
                if required and candidate_skills:
                    if not any(r in candidate_skills for r in required):
                        passed = False

            # Filter by education level
            if passed and "education" in filters:
                edu = meta.get("education", "")
                if edu and filters["education"].lower() not in edu.lower():
                    passed = False

            if passed:
                filtered.append(result)

        logger.info(
            f"[MetadataFilter] {len(results)} results → {len(filtered)} after filtering with {filters}"
        )
        return filtered

    # ================================================================
    # VECTOR SEARCH (PDF Part 7.3)
    # ================================================================

    def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Dense vector search using Milvus HNSW index (PDF Parts 5.6, 7.3).

        Converts query to embedding via the same SentenceTransformer model used
        during document ingestion, then performs approximate nearest-neighbour
        search in Milvus. Metadata filters are applied post-retrieval.
        """
        query_embedding = self.embedding_service.get_embedding(query)
        raw_results = self.vector_db.search(query_embedding, top_k=top_k * 2)

        formatted_results = []
        if not raw_results or not raw_results.get("ids") or not raw_results["ids"][0]:
            return formatted_results

        for i in range(len(raw_results["ids"][0])):
            formatted_results.append({
                "id": raw_results["ids"][0][i],
                "text": raw_results["documents"][0][i],
                "metadata": (raw_results.get("metadatas") or [[]])[0][i] if raw_results.get("metadatas") else {},
                "score": (raw_results.get("distances") or [[]])[0][i] if raw_results.get("distances") else 0.0,
                "source": "vector",
            })

        # Apply metadata filtering (Part 7.4)
        if filters:
            formatted_results = self._apply_metadata_filter(formatted_results, filters)

        observability.trace_retrieval(query, formatted_results[:top_k], "vector")
        return formatted_results[:top_k]

    # ================================================================
    # BM25 KEYWORD SEARCH (PDF Part 7.2)
    # ================================================================

    def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Sparse keyword search using BM25 (PDF Part 7.2).

        Calculates term-frequency relevance scores to surface exact
        keyword matches for skills, technologies, certifications, and titles.
        """
        if not self.bm25 or not self.documents:
            return []

        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)

        # Collect non-zero scoring results
        top_indices = [i for i in np.argsort(scores)[::-1] if scores[i] > 0][:top_k * 2]

        results = []
        for idx in top_indices:
            meta = self.doc_metadatas[idx] if idx < len(self.doc_metadatas) else {}
            results.append({
                "id": f"bm25_{idx}",
                "text": self.documents[idx],
                "metadata": meta,
                "score": float(scores[idx]),
                "source": "bm25",
            })

        # Apply metadata filtering (Part 7.4)
        if filters:
            results = self._apply_metadata_filter(results, filters)

        observability.trace_retrieval(query, results[:top_k], "bm25")
        return results[:top_k]

    # ================================================================
    # HYBRID SEARCH: RRF + RERANKING (PDF Parts 7.5, 8)
    # ================================================================

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Full hybrid retrieval pipeline (PDF Parts 7 & 8).

        Steps:
          1. BM25 keyword retrieval (Part 7.2)
          2. Milvus vector retrieval (Part 7.3)
          3. Metadata filtering (Part 7.4)
          4. Reciprocal Rank Fusion — RRF (Part 7.5)
          5. BGE Cross-Encoder reranking (Part 8.2 & 8.3)
          6. Final top-K selection (Part 8.4)
        """
        candidate_k = top_k * 3

        # Step 1 — BM25 keyword retrieval (Part 7.2)
        keyword_results = self.keyword_search(query, top_k=candidate_k, filters=filters)

        # Step 2 — Milvus vector retrieval (Part 7.3)
        semantic_results = self.semantic_search(query, top_k=candidate_k, filters=filters)

        # Step 3 — Retrieval Fusion via RRF (Part 7.5)
        # RRF formula: score(d) = Σ 1 / (k + rank(d))
        rrf_k = 60
        rrf_scores: Dict[str, float] = {}
        doc_store: Dict[str, Dict] = {}

        for rank, res in enumerate(semantic_results):
            doc_id = str(res.get("id", hash(res["text"][:100])))
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank + 1)
            doc_store[doc_id] = res

        for rank, res in enumerate(keyword_results):
            doc_id = str(hash(res["text"][:100]))
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank + 1)
            if doc_id not in doc_store:
                doc_store[doc_id] = res

        # Sort by RRF score descending
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        fused_results = []
        for doc_id, score in sorted_ids[:top_k * 2]:
            fused_results.append({**doc_store[doc_id], "rrf_score": score})

        observability.trace_retrieval(query, fused_results, "hybrid_rrf")

        # Step 4 — BGE Cross-Encoder Reranking (PDF Part 8.2)
        if self.use_reranker and self.reranker and fused_results:
            try:
                pairs = [[query, doc["text"]] for doc in fused_results]
                rrank_scores = self.reranker.predict(pairs)

                for idx, score in enumerate(rrank_scores):
                    fused_results[idx]["rrank_score"] = float(score)

                # Re-sort by cross-encoder relevance score (Part 8.3)
                fused_results = sorted(
                    fused_results,
                    key=lambda x: x.get("rrank_score", 0.0),
                    reverse=True
                )
                observability.trace_reranking(query, len(fused_results), min(len(fused_results), top_k))
                logger.info(
                    f"[Reranker] Re-ranked {len(fused_results)} results. "
                    f"Top score: {fused_results[0].get('rrank_score', 0):.4f}"
                )
            except Exception as e:
                logger.error(f"Reranking failed: {e}. Using RRF order as fallback.")

        # Step 5 — Final top-K candidate selection (PDF Part 8.4)
        return fused_results[:top_k]
