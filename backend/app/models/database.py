from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class DocumentRecord(Base):
    """Tracks all documents ingested into the platform (PDF Part 10.3).
    
    Supports multiple document types: resumes, job descriptions,
    interview guidelines, hiring policies, recruitment SOPs, and
    internal recruitment knowledge documents.
    """
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(100), unique=True, index=True)  # UUID
    filename = Column(String(500), index=True)
    document_type = Column(String(50), index=True)  # resume, job_description, interview_guide, hiring_policy, sop, knowledge_doc
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    storage_reference = Column(String(1000))  # S3 URI or local path
    chunk_count = Column(Integer, default=0)
    parsed_text = Column(Text)
    metadata_json = Column(Text)  # JSON blob for extracted metadata
    file_size_bytes = Column(Integer, default=0)


class ResumeRecord(Base):
    """Legacy resume tracking table — kept for backwards compatibility."""
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, index=True)
    upload_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50))  # Processed, Pending, Failed
    parsed_text = Column(Text)
    metadata_json = Column(Text)  # JSON blob for skills, experience, etc.


class ChatSession(Base):
    """Recruiter chat sessions for conversational interactions (PDF Part 10.4)."""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    messages = relationship("ChatMessage", back_populates="session")


class ChatMessage(Base):
    """Individual chat messages within a session (PDF Part 10.4)."""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String(20))  # user, assistant
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("ChatSession", back_populates="messages")


class AuditRecord(Base):
    """Audit trail for platform activities (PDF Part 10.5).
    
    Captures: user login, document upload, document processing,
    candidate search, administrative actions.
    """
    __tablename__ = "audit_records"
    
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(100), index=True)  # upload, search, chat, login, admin
    details = Column(Text)  # JSON details of the action
    user_id = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(50), nullable=True)
