"""TalentScreen FastAPI Application Entrypoint (PDF Part 14.1).

Defines the FastAPI application instance, registers middleware, includes 
the modular api router, and manages application startup/shutdown lifecycles.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.services import retrieval_service
from app.db.session import init_db
from app.api import router as api_router

# Setup Production Logging
logger = setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-Grade Enterprise AI Recruitment Assistant"
)

# CORS Security (restrict origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints router
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    """Application startup event to initialize database and reload search indices."""
    logger.info("TalentScreen API Starting Up...")
    try:
        # 1. Initialize PostgreSQL database tables
        init_db()
        # 2. Pre-load BM25 sparse index from existing documents (PDF Part 7.2)
        retrieval_service.reload_bm25()
        logger.info("Startup initialization completed successfully.")
    except Exception as e:
        logger.error(f"Startup initialization failed: {e}")

@app.get("/health")
async def health_check():
    """Basic health check status endpoint."""
    return {
        "status": "healthy", 
        "service": "talent-screen", 
        "version": settings.VERSION
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False, workers=4)
