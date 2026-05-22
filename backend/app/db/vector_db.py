import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from app.core.config import settings
import uuid

class VectorDB:
    def __init__(self, collection_name: str = "resumes"):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_documents(self, texts: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        ids = [str(uuid.uuid4()) for _ in texts]
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )

    def search(self, query_embedding: List[float], top_k: int = 5, filters: Optional[Dict[str, Any]] = None):
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filters
        )
        return results

    def delete_collection(self, collection_name: str):
        self.client.delete_collection(name=collection_name)
