"""
Dataset model — metadata for uploaded Excel files converted to SQL tables.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    original_filename = Column(String(500), nullable=False)
    table_name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    columns_info = Column(JSON, nullable=True)  # [{name, type, nullable, sample_values}]
    sheet_name = Column(String(255), nullable=True)
    upload_path = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    schema_metadata = relationship(
        "SchemaMetadata", back_populates="dataset", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Dataset(id={self.id}, name='{self.name}', table='{self.table_name}')>"
