"""FastAPI Route Handlers (PDF Part 14).

Defines candidate screening and recruitment assistant endpoints:
  - POST /upload: Asynchronous document ingestion staging
  - GET /documents: List processed resume records
  - GET /search: Hybrid AI-driven candidate semantic search
  - POST /chat: Secure context-grounded recruiter assistant streaming
  - GET /analytics: Recruitment metrics dashboard aggregator
"""

import os
import json
import uuid
from typing import List, Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Body, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.logging import logger
from app.core.guardrails import PIIProtector
from app.core.services import vector_db, embedding_service, retrieval_service, llm_service
from app.services.worker import worker
from app.services.cache_service import cache
from app.db.session import SessionLocal
from app.models.database import DocumentRecord, AuditRecord, ChatSession, ChatMessage
from app.utils.file_utils import is_allowed_extension, save_upload_file

router = APIRouter()

@router.post("/upload")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...), document_type: str = None):
    """Upload and stage a document for asynchronous processing."""
    if not is_allowed_extension(file.filename):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file format. Use PDF, DOCX, TXT, or MD."
        )

    try:
        # Save file to dev staging path using helper utility
        temp_path = save_upload_file(file, settings.LOCAL_STORAGE_PATH)
        filename = os.path.basename(temp_path)
        # Extract original file ID from filename prefix
        file_id = filename.split('_')[0]
        
        logger.info(f"File saved: {temp_path}. Queueing background processing task.")
        
        # Dispatch background parsing worker task
        background_tasks.add_task(
            worker.process_resume_task, 
            temp_path, 
            file.filename, 
            document_type
        )
        
        return {
            "message": "Upload successful. Processing in background.",
            "file_id": file_id,
            "filename": file.filename
        }
    except Exception as e:
        logger.error(f"Staged file upload failed: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/documents")
async def list_documents():
    """Retrieve all candidate resume processing records."""
    db = SessionLocal()
    try:
        docs = db.query(DocumentRecord).order_by(DocumentRecord.upload_timestamp.desc()).all()
        return [{
            "id": d.document_id,
            "filename": d.filename,
            "type": d.document_type,
            "status": d.processing_status,
            "uploaded_at": d.upload_timestamp,
            "chunks": d.chunk_count
        } for d in docs]
    finally:
        db.close()


@router.get("/search")
async def search_candidates(query: str, top_k: int = 5, request: Request = None):
    """Candidate search utilizing query expansion, optimization, and guardrails."""
    if not PIIProtector.validate_content(query):
        raise HTTPException(status_code=400, detail="Invalid search query content detected.")
    
    try:
        # Check caching layer
        cache_key = f"{query}_{top_k}"
        cached_results = cache.get_query_result(cache_key)
        if cached_results:
            logger.info("Serving search results from cache.")
            return cached_results

        # AI Query Understanding and expansion (PDF Part 6)
        optimized_query = llm_service.optimize_query(query)
        expanded_query = llm_service.expand_query(optimized_query)
        query_intent = llm_service.understand_query(query)
        
        logger.info(f"Original: {query} | Optimized: {optimized_query} | Expanded: {expanded_query}")
        
        # Hybrid retrieval (Milvus dense + BM25 sparse + BGE Cross-Encoder reranker)
        results = retrieval_service.hybrid_search(expanded_query, top_k=top_k)
        
        response_data = {
            "query": query,
            "optimized_query": optimized_query,
            "expanded_query": expanded_query,
            "intent": query_intent,
            "results": results
        }
        
        # Cache the processed response
        cache.set_query_result(cache_key, response_data)
        
        # Log auditable action
        db = SessionLocal()
        try:
            audit = AuditRecord(
                action="search",
                details=json.dumps({"query": query, "results_count": len(results)}),
                ip_address=request.client.host if request else None
            )
            db.add(audit)
            db.commit()
        except Exception as db_e:
            logger.warning(f"Failed to log search audit: {db_e}")
        finally:
            db.close()
            
        return response_data
    except Exception as e:
        logger.error(f"Search query error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.post("/chat")
async def chat_with_recruiter(payload: Dict[str, Any] = Body(...), request: Request = None):
    """Context-grounded recruiter streaming chatbot with real-time PII masking."""
    query = payload.get("query", "")
    session_id = payload.get("session_id", str(uuid.uuid4()))
    
    if not query or not PIIProtector.validate_content(query):
        raise HTTPException(status_code=400, detail="Invalid chat query content detected.")

    try:
        # Core Hybrid Retrieval context gathering
        optimized_query = llm_service.optimize_query(query)
        expanded_query = llm_service.expand_query(optimized_query)
        context_docs = retrieval_service.hybrid_search(expanded_query, top_k=3)
        
        def stream_generator():
            full_response = ""
            for chunk in llm_service.stream_response(query, context_docs):
                if chunk.content:
                    full_response += chunk.content
                    safe_text = PIIProtector.mask_pii(chunk.content)
                    yield safe_text
            
            # Record interactive session transcript in Postgres
            db = SessionLocal()
            try:
                session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
                if not session:
                    session = ChatSession(session_id=session_id)
                    db.add(session)
                    db.commit()
                
                db.add(ChatMessage(session_id=session.id, role="user", content=query))
                db.add(ChatMessage(session_id=session.id, role="assistant", content=full_response))
                db.commit()
            except Exception as e:
                logger.error(f"Failed to save chat history: {e}")
            finally:
                db.close()
                
        return StreamingResponse(stream_generator(), media_type="text/plain")
    except Exception as e:
        logger.error(f"Chat stream generation error: {e}")
        raise HTTPException(status_code=500, detail="Chat service failure")


@router.get("/analytics")
async def get_analytics():
    """Aggregate dashboard metrics and skill distribution insights."""
    db = SessionLocal()
    try:
        total_docs = db.query(DocumentRecord).count()
        completed_docs = db.query(DocumentRecord).filter(DocumentRecord.processing_status == "completed").count()
        failed_docs = db.query(DocumentRecord).filter(DocumentRecord.processing_status.like("failed%")).count()
        
        doc_types = {}
        for row in db.query(DocumentRecord.document_type).all():
            dt = row[0] or "unknown"
            doc_types[dt] = doc_types.get(dt, 0) + 1
            
        total_searches = db.query(AuditRecord).filter(AuditRecord.action == "search").count()
        
        skill_counts = {}
        successful_docs = db.query(DocumentRecord.metadata_json).filter(
            DocumentRecord.processing_status == "completed",
            DocumentRecord.metadata_json.isnot(None)
        ).all()
        
        avg_exp_sum = 0
        exp_count = 0
        
        for doc in successful_docs:
            try:
                meta = json.loads(doc[0])
                if "skills" in meta and isinstance(meta["skills"], list):
                    for skill in meta["skills"]:
                        skill_clean = skill.title()
                        skill_counts[skill_clean] = skill_counts.get(skill_clean, 0) + 1
                
                if "years_of_experience" in meta and isinstance(meta["years_of_experience"], (int, float)):
                    avg_exp_sum += meta["years_of_experience"]
                    exp_count += 1
            except Exception:
                pass
                
        top_skills = dict(sorted(skill_counts.items(), key=lambda item: item[1], reverse=True)[:10])
        avg_exp = round(avg_exp_sum / exp_count, 1) if exp_count > 0 else 0
        
        return {
            "documents": {
                "total": total_docs,
                "completed": completed_docs,
                "failed": failed_docs,
                "by_type": doc_types
            },
            "activity": {
                "total_searches": total_searches
            },
            "insights": {
                "avg_experience_years": avg_exp,
                "top_skills": top_skills
            }
        }
    except Exception as e:
        logger.error(f"Analytics aggregation error: {e}")
        return {"error": "Failed to fetch analytics"}
    finally:
        db.close()
