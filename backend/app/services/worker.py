from fastapi import BackgroundTasks
from app.ingestion.parser import ResumeParser
from app.ingestion.chunker import ResumeChunker
from app.ingestion.metadata import MetadataExtractor
from app.services.embedding_service import EmbeddingService
from app.db.vector_db import VectorDB
from app.core.logging import logger
import os

class IngestionWorker:
    def __init__(self):
        self.parser = ResumeParser()
        self.chunker = ResumeChunker()
        self.metadata_extractor = MetadataExtractor()
        self.embedding_service = EmbeddingService()
        self.vector_db = VectorDB()

    async def process_resume_task(self, file_path: str, filename: str):
        try:
            logger.info(f"Starting background processing for {filename}")
            
            # 1. Parse
            text = self.parser.parse(file_path)
            if not text:
                logger.error(f"Failed to parse {filename}")
                return

            # 2. Extract Metadata (LLM)
            metadata = self.metadata_extractor.extract_metadata(text)
            
            # 3. Chunk
            chunks = self.chunker.chunk(text)
            
            # 4. Embed
            embeddings = self.embedding_service.get_embeddings(chunks)
            
            # 5. Prepare Metadatas
            metadatas = []
            for _ in chunks:
                meta = {"filename": filename, "source": file_path}
                meta.update(metadata)
                metadatas.append(meta)
            
            # 6. Index
            self.vector_db.add_documents(chunks, embeddings, metadatas)
            
            logger.success(f"Successfully indexed {filename} with {len(chunks)} chunks")
            
        except Exception as e:
            logger.exception(f"Error processing {filename}: {e}")

worker = IngestionWorker()
