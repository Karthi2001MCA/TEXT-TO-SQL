"""
SchemaMetadata model — stores enriched schema intelligence for RAG retrieval.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class SchemaMetadata(Base):
    __tablename__ = "schema_metadata"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    table_name = Column(String(255), nullable=False, index=True)
    column_name = Column(String(255), nullable=True)
    data_type = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)       # AI-generated description
    business_context = Column(Text, nullable=True)   # Business meaning
    sample_values = Column(JSON, nullable=True)      # Example values
    relationships = Column(JSON, nullable=True)      # Detected FK relationships
    is_primary_key = Column(Boolean, default=False)
    is_nullable = Column(Boolean, default=True)
    unique_count = Column(Integer, nullable=True)
    min_value = Column(String(255), nullable=True)
    max_value = Column(String(255), nullable=True)
    embedding_text = Column(Text, nullable=True)     # Text used for vector embedding
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    dataset = relationship("Dataset", back_populates="schema_metadata")

    def __repr__(self):
        return f"<SchemaMetadata(table='{self.table_name}', column='{self.column_name}')>"
