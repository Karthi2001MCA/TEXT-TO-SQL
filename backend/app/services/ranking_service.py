"""
SQL Ranking Service — scores and ranks validated SQL queries from multiple LLMs.
Selects the best query based on multi-factor scoring.
"""

from typing import List, Optional
from dataclasses import dataclass, field

from ..llm_providers.base import LLMResponse
from .validator_service import ValidationResult


@dataclass
class RankedSQL:
    """A SQL query with its ranking score and metadata."""
    sql: str
    provider: str
    model: str
    score: float  # 0-100
    is_valid: bool
    validation_result: Optional[ValidationResult] = None
    latency_ms: float = 0.0
    agreement_count: int = 0  # How many models produced similar SQL
    breakdown: dict = field(default_factory=dict)  # Score breakdown


def rank_sql_queries(
    responses: List[LLMResponse],
    validation_results: dict,
) -> List[RankedSQL]:
    """
    Rank SQL queries from multiple LLMs based on:
    1. Validation pass (40 points)
    2. Model agreement / consensus (25 points)
    3. Response latency (10 points)
    4. Query complexity appropriateness (15 points)
    5. Provider reliability bonus (10 points)
    """
    if not responses:
        return []

    ranked_queries = []

    # Filter to only successful responses with content
    valid_responses = [
        r for r in responses
        if r.is_success and r.content and r.content.strip()
    ]

    if not valid_responses:
        return []

    # Calculate agreement: normalize and compare SQL queries
    normalized_sqls = {}
    for resp in valid_responses:
        norm = _normalize_sql(resp.content)
        if norm not in normalized_sqls:
            normalized_sqls[norm] = []
        normalized_sqls[norm].append(resp)

    # Find max agreement count for scoring
    max_agreement = max(len(group) for group in normalized_sqls.values()) if normalized_sqls else 1

    for resp in valid_responses:
        score = 0.0
        breakdown = {}

        # 1. Validation score (40 points)
        key = f"{resp.provider}:{resp.model}"
        validation = validation_results.get(key)
        if validation and validation.is_valid:
            validation_score = 40.0
            if validation.warnings:
                validation_score -= len(validation.warnings) * 5
                validation_score = max(validation_score, 20.0)
        elif validation and not validation.is_valid:
            validation_score = 0.0
        else:
            validation_score = 20.0  # No validation data = uncertain
        score += validation_score
        breakdown["validation"] = validation_score

        # 2. Agreement score (25 points)
        norm = _normalize_sql(resp.content)
        agreement_count = len(normalized_sqls.get(norm, []))
        agreement_score = (agreement_count / max_agreement) * 25.0
        score += agreement_score
        breakdown["agreement"] = agreement_score

        # 3. Latency score (10 points) — faster is better
        if resp.latency_ms > 0:
            # Scale: <1s = 10 points, >10s = 2 points
            latency_score = max(2.0, 10.0 - (resp.latency_ms / 1000.0))
            latency_score = min(10.0, latency_score)
        else:
            latency_score = 5.0
        score += latency_score
        breakdown["latency"] = latency_score

        # 4. Query complexity (15 points) — prefer appropriate complexity
        complexity_score = _score_query_complexity(resp.content)
        score += complexity_score
        breakdown["complexity"] = complexity_score

        # 5. Provider reliability bonus (10 points)
        reliability = _get_provider_reliability(resp.provider)
        score += reliability
        breakdown["reliability"] = reliability

        ranked_queries.append(RankedSQL(
            sql=resp.content,
            provider=resp.provider,
            model=resp.model,
            score=round(score, 2),
            is_valid=validation.is_valid if validation else False,
            validation_result=validation,
            latency_ms=resp.latency_ms,
            agreement_count=agreement_count,
            breakdown=breakdown,
        ))

    # Sort by score descending, preferring valid queries
    ranked_queries.sort(key=lambda x: (x.is_valid, x.score), reverse=True)

    return ranked_queries


def _normalize_sql(sql: str) -> str:
    """Normalize SQL for comparison (case, whitespace)."""
    import re
    normalized = sql.upper().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r'\s*,\s*', ', ', normalized)
    normalized = normalized.strip(';').strip()
    return normalized


def _score_query_complexity(sql: str) -> float:
    """
    Score query complexity appropriateness (15 points).
    Penalize overly simple or overly complex queries.
    """
    sql_upper = sql.upper()
    score = 10.0  # Base score

    # Bonus for appropriate keywords
    if "WHERE" in sql_upper:
        score += 1.0
    if "GROUP BY" in sql_upper:
        score += 1.0
    if "ORDER BY" in sql_upper:
        score += 1.0
    if any(agg in sql_upper for agg in ["SUM(", "COUNT(", "AVG(", "MIN(", "MAX("]):
        score += 1.0

    # Penalty for overly complex (subqueries, many JOINs)
    join_count = sql_upper.count("JOIN")
    if join_count > 3:
        score -= 2.0

    subquery_count = sql_upper.count("SELECT") - 1
    if subquery_count > 2:
        score -= 2.0

    return max(0.0, min(15.0, score))


def _get_provider_reliability(provider: str) -> float:
    """
    Static reliability scores for providers.
    Based on general known performance for SQL generation.
    """
    reliability_scores = {
        "gemini": 9.0,
        "groq": 7.5,
        "deepseek": 8.5,
        "ollama": 6.0,
        "openai": 9.5,
    }
    return reliability_scores.get(provider, 5.0)


def get_confidence_score(ranked_queries: List[RankedSQL]) -> float:
    """
    Calculate overall confidence score (0-100) based on ranked results.
    High confidence = top query has high score AND multiple models agree.
    """
    if not ranked_queries:
        return 0.0

    top = ranked_queries[0]
    base_confidence = top.score  # Already 0-100

    # Boost if multiple models agree
    if top.agreement_count > 1:
        agreement_boost = min(15.0, (top.agreement_count - 1) * 5.0)
        base_confidence = min(100.0, base_confidence + agreement_boost)

    # Reduce if no validation
    if not top.is_valid:
        base_confidence *= 0.3

    return round(base_confidence, 1)
