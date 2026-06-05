from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger
import uuid

try:
    from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False

import chromadb

class VectorDB:
    def __init__(self, collection_name: str = "resumes"):
        self.use_milvus = False
        self.milvus_collection = None
        self.collection_name = collection_name
        
        # Try Milvus first
        if MILVUS_AVAILABLE:
            try:
                connections.connect(
                    alias="default", 
                    host=settings.MILVUS_HOST, 
                    port=settings.MILVUS_PORT,
                    timeout=5.0
                )
                self._create_milvus_collection()
                self.use_milvus = True
                logger.info(f"Using Milvus vector database on stand-alone server: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
            except Exception as e:
                logger.warning(f"Failed to connect to Milvus ({e}). Falling back to ChromaDB.")
        
        if not self.use_milvus:
            self.chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
            self.chroma_collection = self.chroma_client.get_or_create_collection(name=collection_name)
            logger.info(f"Using ChromaDB local vector database at: {settings.CHROMA_DB_PATH}")

    def _create_milvus_collection(self):
        if utility.has_collection(self.collection_name):
            self.milvus_collection = Collection(self.collection_name)
            return

        # Define Schema
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384), # 384 for all-MiniLM-L6-v2
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata", dtype=DataType.JSON)
        ]
        schema = CollectionSchema(fields, "Resume chunks for Talent Screen")
        self.milvus_collection = Collection(self.collection_name, schema)
        
        # Create Index
        index_params = {
            "metric_type": "L2",
            "index_type": "HNSW",
            "params": {"M": 8, "efConstruction": 64}
        }
        self.milvus_collection.create_index(field_name="embedding", index_params=index_params)
        logger.info(f"Created Milvus collection: {self.collection_name}")

    def add_documents(self, texts: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        if self.use_milvus and self.milvus_collection:
            try:
                data = [
                    embeddings,
                    texts,
                    metadatas
                ]
                self.milvus_collection.insert(data)
                self.milvus_collection.flush()
                logger.info(f"Inserted {len(texts)} documents into Milvus.")
                return
            except Exception as e:
                logger.error(f"Milvus insert failed: {e}. Falling back to ChromaDB.")
                
        ids = [str(uuid.uuid4()) for _ in texts]
        self.chroma_collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )
        logger.info(f"Inserted {len(texts)} documents into ChromaDB.")

    def search(self, query_embedding: List[float], top_k: int = 5, filters: Optional[Dict[str, Any]] = None):
        if self.use_milvus and self.milvus_collection:
            try:
                self.milvus_collection.load()
                search_params = {"metric_type": "L2", "params": {"ef": 64}}
                
                # Convert dict filter to Milvus expression string if needed
                expr = None
                if filters:
                    # Simple equality conversion for demo filter
                    expr_parts = []
                    for k, v in filters.items():
                        if isinstance(v, str):
                            expr_parts.append(f"metadata['{k}'] == '{v}'")
                        else:
                            expr_parts.append(f"metadata['{k}'] == {v}")
                    expr = " and ".join(expr_parts)

                results = self.milvus_collection.search(
                    data=[query_embedding],
                    anns_field="embedding",
                    param=search_params,
                    limit=top_k,
                    expr=expr,
                    output_fields=["text", "metadata"]
                )
                
                # Format results to match ChromaDB style for compatibility
                formatted = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
                for hits in results:
                    for hit in hits:
                        formatted["ids"][0].append(hit.id)
                        formatted["documents"][0].append(hit.entity.get('text'))
                        formatted["metadatas"][0].append(hit.entity.get('metadata'))
                        formatted["distances"][0].append(hit.distance)
                return formatted
            except Exception as e:
                logger.error(f"Milvus search failed: {e}. Falling back to ChromaDB.")

        # ChromaDB search
        results = self.chroma_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filters
        )
        return results

    def delete_collection(self, collection_name: str):
        if self.use_milvus:
            try:
                utility.drop_collection(collection_name)
                return
            except Exception as e:
                logger.error(f"Failed to delete Milvus collection: {e}")
        try:
            self.chroma_client.delete_collection(name=collection_name)
        except Exception as e:
            logger.error(f"Failed to delete ChromaDB collection: {e}")

    def get_all_documents(self) -> List[str]:
        """Retrieve all document texts from the vector store (for BM25 index rebuild)."""
        texts, _ = self.get_all_documents_with_metadata()
        return texts

    def get_all_documents_with_metadata(self) -> tuple:
        """Retrieve all document texts AND metadata from the vector store.

        Used by HybridRetrievalService to rebuild the BM25 index with metadata
        so metadata filtering (PDF Part 7.4) can be applied during keyword search.

        Returns:
            Tuple of (texts: List[str], metadatas: List[Dict[str, Any]])
        """
        if self.use_milvus and self.milvus_collection:
            try:
                self.milvus_collection.load()
                res = self.milvus_collection.query(
                    expr="id >= 0",
                    output_fields=["text", "metadata"]
                )
                texts = []
                metadatas = []
                for item in res:
                    texts.append(item.get("text", ""))
                    meta = {}
                    if "metadata" in item and isinstance(item["metadata"], dict):
                        meta = item["metadata"]
                    metadatas.append(meta)
                return texts, metadatas
            except Exception as e:
                logger.error(f"Milvus get_all_documents_with_metadata failed: {e}")

        # ChromaDB fallback
        try:
            res = self.chroma_collection.get(include=["documents", "metadatas"])
            texts = res.get("documents", [])
            metadatas = res.get("metadatas", [{} for _ in texts])
            return texts, metadatas
        except Exception as e:
            logger.error(f"ChromaDB get_all_documents_with_metadata failed: {e}")
            return [], []

