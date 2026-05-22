from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from app.core.config import settings
from app.core.logging import logger
from typing import List, Dict, Any, Optional

class MilvusDB:
    def __init__(self, collection_name: str = "talent_resumes"):
        self.collection_name = collection_name
        self._connect()
        self._create_collection()

    def _connect(self):
        try:
            connections.connect(
                alias="default", 
                host=settings.MILVUS_HOST, 
                port=settings.MILVUS_PORT
            )
            logger.info(f"Connected to Milvus at {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")

    def _create_collection(self):
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            return

        # Define Schema
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384), # 384 for all-MiniLM-L6-v2
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata", dtype=DataType.JSON)
        ]
        schema = CollectionSchema(fields, "Resume chunks for Talent Screen")
        self.collection = Collection(self.collection_name, schema)
        
        # Create Index
        index_params = {
            "metric_type": "L2",
            "index_type": "HNSW",
            "params": {"M": 8, "efConstruction": 64}
        }
        self.collection.create_index(field_name="embedding", index_params=index_params)
        logger.info(f"Created Milvus collection: {self.collection_name}")

    def add_documents(self, texts: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        data = [
            embeddings,
            texts,
            metadatas
        ]
        self.collection.insert(data)
        self.collection.flush()

    def search(self, query_embedding: List[float], top_k: int = 5, filters: str = None):
        self.collection.load()
        search_params = {"metric_type": "L2", "params": {"ef": 64}}
        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=filters,
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
