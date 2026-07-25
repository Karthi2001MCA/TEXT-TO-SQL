"""
QueryLog model — audit trail for every query executed through the platform.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, JSON, Boolean
from sqlalchemy.sql import func

from ..database import Base


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    natural_language_query = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=True)
    selected_model = Column(String(100), nullable=True)  # Which LLM was selected
    all_model_responses = Column(JSON, nullable=True)     # {model: sql} for all LLMs
    confidence_score = Column(Float, nullable=True)
    validation_passed = Column(Boolean, default=False)
    execution_time_ms = Column(Float, nullable=True)
    row_count_returned = Column(Integer, nullable=True)
    result_preview = Column(JSON, nullable=True)  # First few rows of result
    chart_type = Column(String(50), nullable=True)
    insight_text = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    is_successful = Column(Boolean, default=False)
    dataset_tables_used = Column(JSON, nullable=True)  # List of tables queried
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<QueryLog(id={self.id}, success={self.is_successful})>"
