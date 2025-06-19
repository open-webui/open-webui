import uuid
from sqlalchemy import Column, String, BigInteger, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID  # For PostgreSQL UUID type
from sqlalchemy.orm import relationship
from open_webui.internal.db import Base, JSONField # Removed direct JSON import
import time

class ProcessedFile(Base):
    __tablename__ = "processed_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False) # Assuming user_id is UUID
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    processing_status = Column(String(50), default="pending") # e.g., pending, processing, completed, failed
    metadata_ = Column('metadata', JSONField, nullable=True) # Renamed to avoid conflict with Base.metadata, changed to JSONField
    created_at = Column(BigInteger, default=lambda: int(time.time()))

    chunks = relationship("FileChunk", back_populates="processed_file")

class FileChunk(Base):
    __tablename__ = "file_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("processed_files.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_metadata = Column(JSONField, nullable=True) # Changed to JSONField
    # For sentence-transformers/all-MiniLM-L6-v2, dimension is 384. Storing as JSON array for now.
    # Consider specialized vector types if DB supports (e.g., pgvector)
    embedding = Column(JSONField(enforce_string=True), nullable=True) # Storing as JSON array of floats
    created_at = Column(BigInteger, default=lambda: int(time.time()))

    processed_file = relationship("ProcessedFile", back_populates="chunks")
