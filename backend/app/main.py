from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import os
import shutil
import uuid
import json

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.guardrails import PIIProtector
from app.services.worker import worker
from app.services.retrieval_service import HybridRetrievalService
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService
from app.db.vector_db import VectorDB

# Setup Production Logging
logger = setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-Grade Enterprise AI Recruitment Assistant"
)

# CORS Security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Services
vector_db = VectorDB()
embedding_service = EmbeddingService()
retrieval_service = HybridRetrievalService(vector_db, embedding_service)
llm_service = LLMService()

@app.on_event("startup")
async def startup_event():
    logger.info("Talent Screen API Starting Up...")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "talent-screen"}

@app.post("/upload")
async def upload_resume(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload and process resumes asynchronously."""
    if not file.filename.lower().endswith(('.pdf', '.docx')):
        raise HTTPException(status_code=400, detail="Unsupported file format. Use PDF or DOCX.")

    file_id = str(uuid.uuid4())
    temp_dir = "data/resumes"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{file_id}_{file.filename}")
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File saved: {temp_path}. Queueing background task.")
        
        # PRODUCTION: Move processing to background to prevent timeout
        background_tasks.add_task(worker.process_resume_task, temp_path, file.filename)
        
        return {
            "message": "Upload successful. Processing in background.",
            "file_id": file_id,
            "filename": file.filename
        }
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/search")
async def search_candidates(query: str, top_k: int = 5):
    """Semantic search with AI intent expansion and guardrails."""
    if not PIIProtector.validate_content(query):
        raise HTTPException(status_code=400, detail="Invalid search query content detected.")
    
    try:
        # AI Intent Expansion (Human-like understanding)
        expanded_query = llm_service.expand_query(query)
        logger.info(f"Original: {query} | Expanded: {expanded_query}")
        
        results = retrieval_service.hybrid_search(expanded_query, top_k=top_k)
        return {
            "query": query,
            "expanded_query": expanded_query,
            "results": results
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@app.post("/chat")
async def chat_with_recruiter(query: str):
    """Secure, streaming recruiter chat assistant."""
    if not PIIProtector.validate_content(query):
        raise HTTPException(status_code=400, detail="Invalid chat query content detected.")

    try:
        context_docs = retrieval_service.hybrid_search(query, top_k=3)
        
        def stream_generator():
            for chunk in llm_service.stream_response(query, context_docs):
                if chunk.content:
                    # Mask PII in response before sending
                    safe_text = PIIProtector.mask_pii(chunk.content)
                    yield safe_text
        
        return StreamingResponse(stream_generator(), media_type="text/plain")
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat service failure")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False, workers=4)
