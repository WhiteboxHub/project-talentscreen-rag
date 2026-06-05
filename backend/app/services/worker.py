"""Asynchronous Ingestion Worker (PDF Part 5).

Multi-threaded processing pipeline for documents:
Upload → Parse → Metadata Extraction → Semantic Chunking → Embeddings → Indexing.
Records progress to PostgreSQL and indexes vectors in Milvus/ChromaDB.
"""

from fastapi import BackgroundTasks
from app.ingestion.parser import ResumeParser
from app.ingestion.chunker import ResumeChunker
from app.ingestion.metadata import MetadataExtractor
from app.services.embedding_service import EmbeddingService
from app.db.vector_db import VectorDB
from app.db.session import SessionLocal
from app.models.database import DocumentRecord, AuditRecord
from app.core.logging import logger
import os
import uuid
import json


class IngestionWorker:
    def __init__(self):
        self.parser = ResumeParser()
        self.chunker = ResumeChunker()
        self.metadata_extractor = MetadataExtractor()
        self.embedding_service = EmbeddingService()
        self.vector_db = VectorDB()

    async def process_resume_task(self, file_path: str, filename: str, document_type: str = None):
        """Asynchronously process an uploaded document (PDF Part 5.2)."""
        db = SessionLocal()
        doc_id = str(uuid.uuid4())
        
        try:
            logger.info(f"Starting background processing for {filename} (Type: {document_type or 'auto'})")
            
            # 1. Create DB Record (PDF Part 10.3)
            doc_record = DocumentRecord(
                document_id=doc_id,
                filename=filename,
                processing_status="processing",
                storage_reference=file_path,
                file_size_bytes=os.path.getsize(file_path) if os.path.exists(file_path) else 0
            )
            db.add(doc_record)
            db.commit()

            # 2. Parse (PDF Part 4.3)
            logger.info(f"Parsing {filename}...")
            text = self.parser.parse(file_path)
            if not text or len(text.strip()) < 10:
                raise ValueError(f"Parser returned empty or invalid text for {filename}")
            
            doc_record.parsed_text = text
            db.commit()

            # 3. Detect Document Type (if not provided)
            if not document_type:
                document_type = self.metadata_extractor.detect_document_type(text)
            doc_record.document_type = document_type
            db.commit()

            # 4. Extract Metadata (LLM) (PDF Part 4.5)
            logger.info(f"Extracting metadata for {filename}...")
            metadata = self.metadata_extractor.extract_metadata(text, document_type)
            doc_record.metadata_json = json.dumps(metadata)
            db.commit()
            
            # 5. Semantic Chunking (PDF Part 4.4)
            logger.info(f"Chunking {filename}...")
            chunks = self.chunker.chunk(text)
            doc_record.chunk_count = len(chunks)
            db.commit()
            
            # 6. Embed (PDF Part 4.6)
            logger.info(f"Generating embeddings for {len(chunks)} chunks...")
            embeddings = self.embedding_service.get_embeddings(chunks)
            
            # 7. Prepare Metadatas for Vector DB
            metadatas = []
            for i, _ in enumerate(chunks):
                # We need to ensure values are simple strings/ints/floats for Chroma/Milvus
                meta = {
                    "document_id": doc_id,
                    "filename": filename,
                    "document_type": document_type,
                    "chunk_index": i
                }
                
                # Add domain/role/experience directly to metadata for filtering
                if "domain" in metadata and isinstance(metadata["domain"], str):
                    meta["domain"] = metadata["domain"]
                if "job_role" in metadata and isinstance(metadata["job_role"], str):
                    meta["job_role"] = metadata["job_role"]
                if "years_of_experience" in metadata and isinstance(metadata["years_of_experience"], (int, float)):
                    meta["experience"] = metadata["years_of_experience"]
                
                # We can't store complex nested JSON in Chroma/Milvus metadata easily,
                # so we serialize skills to a comma-separated string
                if "skills" in metadata and isinstance(metadata["skills"], list):
                    meta["skills"] = ", ".join(metadata["skills"][:20])  # limit to top 20
                
                metadatas.append(meta)
            
            # 8. Index (PDF Part 4.7)
            logger.info(f"Indexing {len(chunks)} vectors...")
            self.vector_db.add_documents(chunks, embeddings, metadatas)
            
            # 9. Update Status to Complete
            doc_record.processing_status = "completed"
            
            # 10. Audit Log
            audit = AuditRecord(
                action="document_ingestion",
                details=json.dumps({"filename": filename, "document_type": document_type, "chunks": len(chunks), "status": "success"})
            )
            db.add(audit)
            db.commit()
            
            # Reload BM25 index dynamically to make new documents immediately searchable
            try:
                from app.core.services import retrieval_service
                retrieval_service.reload_bm25()
            except Exception as ex:
                logger.warning(f"Could not reload BM25 index dynamically: {ex}")
                
            logger.info(f"Successfully indexed {filename} with {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            
            # Record failure in DB
            try:
                doc = db.query(DocumentRecord).filter(DocumentRecord.document_id == doc_id).first()
                if doc:
                    doc.processing_status = f"failed: {str(e)[:100]}"
                
                audit = AuditRecord(
                    action="document_ingestion",
                    details=json.dumps({"filename": filename, "status": "failed", "error": str(e)[:200]})
                )
                db.add(audit)
                db.commit()
            except Exception as db_e:
                logger.error(f"Failed to record error state in DB: {db_e}")
                
        finally:
            db.close()


worker = IngestionWorker()
