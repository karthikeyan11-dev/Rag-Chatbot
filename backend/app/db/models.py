from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship, DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("DocumentMetadata", back_populates="user", cascade="all, delete-orphan")

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)  # JSON string of sources
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")

class DocumentMetadata(Base):
    """New model to track uploaded documents in RDS."""
    __tablename__ = "document_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    document_id = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    ingestion_status = Column(String, default="pending")  # pending, completed, error
    
    # Phase 2: Document Intelligence
    summary = Column(Text, nullable=True)
    key_topics = Column(Text, nullable=True)  # Comma-separated or JSON
    document_type = Column(String, nullable=True)

    user = relationship("User", back_populates="documents")
