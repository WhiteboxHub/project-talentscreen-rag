from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.models.database import Base
from app.core.logging import logger

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    try:
        logger.info("Initializing relational database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Relational database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing relational database: {e}")
        raise

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
