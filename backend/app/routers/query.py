"""
Query router — the main natural language query endpoint.
Orchestrates the full pipeline: prompt → multi-LLM → validate → rank → execute → insight.
(No authentication — open access)
"""

import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List

from ..database import get_app_db, get_data_db_tables, get_table_columns, get_table_row_count
from ..core.exceptions import SQLGenerationError, NotFoundError
from ..models.query_log import QueryLog
from ..services.llm_service import get_llm_engine
from ..services import prompt_service, validator_service, ranking_service, executor_service

router = APIRouter(prefix="/api/query", tags=["Query"])

NO_LLM_CONFIGURED_MESSAGE = (
    "No working LLM is configured. Add a real API key to backend/.env "
    "(GEMINI_API_KEY from aistudio.google.com/apikey or GROQ_API_KEY from console.groq.com/keys) "
    "and restart the server, or run Ollama locally (ollama serve)."
)


# ============================================
# Request / Response Schemas
# ============================================

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    dataset_tables: Optional[List[str]] = None  # Specific tables to query


class ModelResponse(BaseModel):
    provider: str
    model: str
    sql: str
    score: float
    is_valid: bool
    latency_ms: float


class QueryResponse(BaseModel):
    question: str
    sql: str
    confidence: float
    results: dict
    models: List[ModelResponse]
    chart_recommendation: Optional[dict]
    insights: Optional[str]
    execution_time_ms: float


class QueryHistoryItem(BaseModel):
    id: int
    question: str
    sql: Optional[str]
    confidence: Optional[float]
    is_successful: bool
    row_count: Optional[int]
    execution_time_ms: Optional[float]
    created_at: str


# ============================================
# Endpoints
# ============================================

@router.post("", response_model=QueryResponse)
async def submit_query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_app_db),
):
    """
    Submit a natural language question and get SQL query + results.
    Full pipeline: Prompt → Multi-LLM → Validate → Rank → Execute → Insight.
    """
    engine = get_llm_engine()

    # Step 1: Get available tables and schema
    all_tables = await get_data_db_tables()
    if not all_tables:
        raise NotFoundError("No datasets uploaded yet. Please upload an Excel file first.")

    # Filter to requested tables or use all
    target_tables = request.dataset_tables or all_tables
    target_tables = [t for t in target_tables if t in all_tables]

    if not target_tables:
        raise NotFoundError("Specified tables not found")

    # Build table schema info
    tables_info = []
    for table_name in target_tables:
        columns = await get_table_columns(table_name)
        row_count = await get_table_row_count(table_name)
        tables_info.append({
            "table_name": table_name,
            "columns": [{"name": c["name"], "type": str(c["type"])} for c in columns],
            "row_count": row_count,
        })

    # Step 2: Get RAG context
    rag_context = prompt_service.get_schema_context(request.question)

    # Step 3: Build prompt
    prompt = prompt_service.build_sql_generation_prompt(
        user_question=request.question,
        available_tables=tables_info,
        rag_context=rag_context,
    )

    # Step 4: Send to all LLMs in parallel
    llm_responses = await engine.generate_sql_from_all(prompt)

    if not llm_responses:
        raise SQLGenerationError(NO_LLM_CONFIGURED_MESSAGE)

    successful_responses = [r for r in llm_responses if r.is_success and r.content]
    if not successful_responses:
        error_msgs = [f"{r.provider}: {r.error}" for r in llm_responses if r.error]
        raise SQLGenerationError(
            f"{NO_LLM_CONFIGURED_MESSAGE} Provider errors: {'; '.join(error_msgs)}"
        )

    # Step 5: Validate all SQL responses
    validation_results = {}
    for resp in successful_responses:
        key = f"{resp.provider}:{resp.model}"
        validation = await validator_service.validate_sql(resp.content)
        validation_results[key] = validation

    # Step 6: Rank SQL queries
    ranked = ranking_service.rank_sql_queries(successful_responses, validation_results)

    if not ranked:
        raise SQLGenerationError("No valid SQL queries were generated")

    # Select the best valid query
    best = None
    for r in ranked:
        if r.is_valid:
            best = r
            break

    # If no valid queries, use the highest scored one anyway
    if not best:
        best = ranked[0]

    # Step 7: Execute the best SQL
    exec_result = await executor_service.execute_sql(best.sql)

    # If execution failed and we have alternatives, try the next one
    if not exec_result["success"] and len(ranked) > 1:
        for alt in ranked[1:]:
            if alt.is_valid:
                exec_result = await executor_service.execute_sql(alt.sql)
                if exec_result["success"]:
                    best = alt
                    break

    # Step 8: Calculate confidence
    confidence = ranking_service.get_confidence_score(ranked)

    # Step 9: Generate insights (async, best-effort)
    insights = None
    chart_recommendation = None

    if exec_result["success"] and exec_result["rows"]:
        try:
            insight_prompt = prompt_service.build_insight_prompt(
                user_question=request.question,
                sql_query=best.sql,
                query_results=exec_result,
            )
            insights = await engine.generate_insight(insight_prompt)
        except Exception:
            insights = None

        try:
            chart_prompt = prompt_service.build_chart_recommendation_prompt(
                user_question=request.question,
                columns=exec_result["columns"],
                sample_rows=exec_result["rows"][:5],
                row_count=exec_result["row_count"],
            )
            chart_raw = await engine.generate_chart_recommendation(chart_prompt)
            chart_recommendation = json.loads(chart_raw)
        except (json.JSONDecodeError, Exception):
            chart_recommendation = {"chart_type": "table", "title": "Query Results"}

    # Step 10: Log the query
    all_model_responses = {
        f"{r.provider}:{r.model}": r.content
        for r in successful_responses
    }

    query_log = QueryLog(
        natural_language_query=request.question,
        generated_sql=best.sql,
        selected_model=f"{best.provider}:{best.model}",
        all_model_responses=all_model_responses,
        confidence_score=confidence,
        validation_passed=best.is_valid,
        execution_time_ms=exec_result["execution_time_ms"],
        row_count_returned=exec_result["row_count"],
        result_preview=exec_result["rows"][:10] if exec_result["rows"] else None,
        chart_type=chart_recommendation.get("chart_type") if chart_recommendation else None,
        insight_text=insights,
        error_message=exec_result.get("error"),
        is_successful=exec_result["success"],
        dataset_tables_used=target_tables,
    )
    db.add(query_log)
    await db.commit()

    # Build model responses for the API
    model_responses = [
        ModelResponse(
            provider=r.provider,
            model=r.model,
            sql=r.sql,
            score=r.score,
            is_valid=r.is_valid,
            latency_ms=r.latency_ms,
        )
        for r in ranked
    ]

    return QueryResponse(
        question=request.question,
        sql=best.sql,
        confidence=confidence,
        results=exec_result,
        models=model_responses,
        chart_recommendation=chart_recommendation,
        insights=insights,
        execution_time_ms=exec_result["execution_time_ms"],
    )


@router.get("/history", response_model=List[QueryHistoryItem])
async def get_query_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_app_db),
):
    """Get query history."""
    from sqlalchemy import select

    result = await db.execute(
        select(QueryLog)
        .order_by(QueryLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()

    return [
        QueryHistoryItem(
            id=log.id,
            question=log.natural_language_query,
            sql=log.generated_sql,
            confidence=log.confidence_score,
            is_successful=log.is_successful,
            row_count=log.row_count_returned,
            execution_time_ms=log.execution_time_ms,
            created_at=str(log.created_at),
        )
        for log in logs
    ]


@router.get("/tables")
async def get_available_tables():
    """Get list of all available data tables."""
    tables = await get_data_db_tables()
    result = []
    for table in tables:
        columns = await get_table_columns(table)
        row_count = await get_table_row_count(table)
        result.append({
            "table_name": table,
            "columns": [{"name": c["name"], "type": str(c["type"])} for c in columns],
            "row_count": row_count,
        })
    return {"tables": result}


@router.get("/providers")
async def get_llm_providers():
    """Get status of all configured LLM providers."""
    engine = get_llm_engine()
    return {"providers": engine.get_available_providers()}
