"""
Admin router — system stats, dataset oversight, and audit logs.
(No authentication — open access)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..database import get_app_db
from ..models.dataset import Dataset
from ..models.query_log import QueryLog
from ..services.llm_service import get_llm_engine
from ..services import rag_service

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/datasets")
async def list_all_datasets(
    db: AsyncSession = Depends(get_app_db),
):
    """List all datasets."""
    result = await db.execute(select(Dataset).order_by(Dataset.created_at.desc()))
    datasets = result.scalars().all()
    return {
        "datasets": [
            {
                "id": d.id,
                "name": d.name,
                "table_name": d.table_name,
                "row_count": d.row_count,
                "column_count": d.column_count,
                "file_size_bytes": d.file_size_bytes,
                "created_at": str(d.created_at),
            }
            for d in datasets
        ],
        "total": len(datasets),
    }


@router.get("/logs")
async def get_audit_logs(
    limit: int = 100,
    db: AsyncSession = Depends(get_app_db),
):
    """Get query audit logs."""
    result = await db.execute(
        select(QueryLog).order_by(QueryLog.created_at.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return {
        "logs": [
            {
                "id": l.id,
                "question": l.natural_language_query,
                "sql": l.generated_sql,
                "model": l.selected_model,
                "confidence": l.confidence_score,
                "is_successful": l.is_successful,
                "execution_time_ms": l.execution_time_ms,
                "row_count": l.row_count_returned,
                "error": l.error_message,
                "created_at": str(l.created_at),
            }
            for l in logs
        ],
        "total": len(logs),
    }


@router.get("/stats")
async def get_system_stats(
    db: AsyncSession = Depends(get_app_db),
):
    """Get system-wide statistics."""
    # Dataset count
    dataset_count = await db.execute(select(func.count(Dataset.id)))
    total_datasets = dataset_count.scalar()

    # Query count
    query_count = await db.execute(select(func.count(QueryLog.id)))
    total_queries = query_count.scalar()

    # Success rate
    success_count = await db.execute(
        select(func.count(QueryLog.id)).where(QueryLog.is_successful == True)
    )
    successful_queries = success_count.scalar()
    success_rate = (successful_queries / total_queries * 100) if total_queries > 0 else 0

    # Average confidence
    avg_confidence = await db.execute(
        select(func.avg(QueryLog.confidence_score)).where(QueryLog.confidence_score.isnot(None))
    )
    avg_conf = avg_confidence.scalar() or 0

    # LLM providers
    engine = get_llm_engine()
    providers = engine.get_available_providers()

    # RAG index stats
    rag_stats = rag_service.get_index_stats()

    return {
        "total_datasets": total_datasets,
        "total_queries": total_queries,
        "success_rate": round(success_rate, 1),
        "average_confidence": round(avg_conf, 1),
        "llm_providers": providers,
        "rag_index": rag_stats,
    }
