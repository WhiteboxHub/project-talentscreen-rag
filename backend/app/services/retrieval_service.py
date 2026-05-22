from typing import List, Dict, Any
from app.db.vector_db import VectorDB
from app.services.embedding_service import EmbeddingService
from rank_bm25 import BM25Okapi
import numpy as np

class HybridRetrievalService:
    def __init__(self, vector_db: VectorDB, embedding_service: EmbeddingService):
        self.vector_db = vector_db
        self.embedding_service = embedding_service
        self.documents = []
        self.bm25 = None

    def initialize_bm25(self, texts: List[str]):
        tokenized_corpus = [doc.lower().split() for doc in texts]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.documents = texts

    def semantic_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        query_embedding = self.embedding_service.get_embedding(query)
        results = self.vector_db.search(query_embedding, top_k=top_k)
        
        # Flatten results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                "id": results['ids'][0][i],
                "text": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "score": results['distances'][0][i]  # Chroma uses distance, smaller is better
            })
        return formatted_results

    def keyword_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        if not self.bm25:
            return []
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        top_n_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_n_indices:
            results.append({
                "text": self.documents[idx],
                "score": scores[idx]
            })
        return results

    def hybrid_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # 1. Get Vector Results
        semantic_results = self.semantic_search(query, top_k=top_k * 2)
        
        # 2. Get BM25 Results
        keyword_results = self.keyword_search(query, top_k=top_k * 2)
        
        # 3. Reciprocal Rank Fusion (RRF)
        # RRF formula: score = sum( 1 / (k + rank) )
        k = 60
        rrf_scores = {}
        
        # Doc storage to keep original object
        doc_store = {}
        
        for rank, res in enumerate(semantic_results):
            doc_id = res.get('id') or res['text'][:50] # Fallback if no ID
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank + 1)
            doc_store[doc_id] = res

        for rank, res in enumerate(keyword_results):
            doc_id = res.get('id') or res['text'][:50]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank + 1)
            if doc_id not in doc_store:
                doc_store[doc_id] = res

        # Sort by RRF score
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        final_results = []
        for doc_id, score in sorted_ids[:top_k]:
            final_results.append({
                **doc_store[doc_id],
                "rrf_score": score
            })
            
        return final_results
