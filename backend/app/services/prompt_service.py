"""
Prompt Engineering Service — builds structured prompts for LLMs
with schema context, conversation history, and safety constraints.
"""

from typing import List, Optional
from . import rag_service


def build_sql_generation_prompt(
    user_question: str,
    available_tables: List[dict],
    conversation_history: Optional[List[dict]] = None,
    rag_context: Optional[List[dict]] = None,
) -> str:
    """
    Build a comprehensive prompt for SQL generation.

    Args:
        user_question: Natural language question from the user
        available_tables: List of {table_name, columns: [{name, type}]}
        conversation_history: Previous Q&A exchanges for context
        rag_context: Retrieved schema context from RAG
    """

    # System instructions
    prompt = """You are an expert SQL analyst. Your task is to convert natural language questions into accurate, safe SQL queries.

## CRITICAL RULES:
1. ONLY generate SELECT statements. Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, or any data-modifying SQL.
2. Always use double-quoted identifiers for table and column names (e.g., SELECT "column_name" FROM "table_name").
3. Return ONLY the SQL query — no explanations, no markdown code fences, no extra text.
4. If you cannot answer the question with the available schema, return: UNABLE_TO_GENERATE
5. Use appropriate aggregations (SUM, COUNT, AVG, MIN, MAX) when the question implies them.
6. Use GROUP BY when aggregating, ORDER BY when sorting is implied.
7. Use LIMIT when the user asks for "top N" or "first N".
8. Handle NULL values appropriately with COALESCE or IS NOT NULL.
9. For date filtering, use standard SQL date comparisons.
10. Use aliases for readability in complex queries.

"""

    # Add schema information
    prompt += "## AVAILABLE DATABASE SCHEMA:\n\n"
    for table in available_tables:
        prompt += f"### Table: \"{table['table_name']}\"\n"
        prompt += "Columns:\n"
        for col in table.get("columns", []):
            prompt += f"  - \"{col['name']}\" ({col['type']})\n"
        if table.get("row_count"):
            prompt += f"  Row count: {table['row_count']}\n"
        prompt += "\n"

    # Add RAG context if available
    if rag_context:
        prompt += "## ADDITIONAL SCHEMA CONTEXT (from knowledge base):\n\n"
        for ctx in rag_context[:5]:
            prompt += f"- {ctx['text']}\n"
        prompt += "\n"

    # Add conversation history for contextual follow-ups
    if conversation_history:
        prompt += "## CONVERSATION HISTORY (for context):\n\n"
        for exchange in conversation_history[-5:]:  # Last 5 exchanges
            prompt += f"User: {exchange.get('question', '')}\n"
            prompt += f"SQL: {exchange.get('sql', '')}\n\n"

    # The actual question
    prompt += f"## USER QUESTION:\n{user_question}\n\n"
    prompt += "## YOUR SQL QUERY:\n"

    return prompt


def build_insight_prompt(
    user_question: str,
    sql_query: str,
    query_results: dict,
) -> str:
    """Build a prompt for generating business insights from query results."""

    prompt = """You are a business data analyst. Analyze the query results and provide clear, actionable insights.

## RULES:
1. Provide 2-4 key insights from the data.
2. Use plain language — avoid technical jargon.
3. Highlight notable patterns, trends, outliers, or anomalies.
4. If applicable, suggest follow-up questions the user might ask.
5. Format your response as a structured analysis with bullet points.
6. Keep it concise — no more than 200 words.

"""

    prompt += f"## USER QUESTION:\n{user_question}\n\n"
    prompt += f"## SQL QUERY EXECUTED:\n{sql_query}\n\n"

    # Add result summary
    columns = query_results.get("columns", [])
    rows = query_results.get("rows", [])
    total = query_results.get("total_rows", len(rows))

    prompt += f"## QUERY RESULTS ({total} total rows):\n"
    prompt += f"Columns: {', '.join(columns)}\n\n"

    # Include first 20 rows for context
    preview_rows = rows[:20]
    if preview_rows:
        prompt += "Data (first rows):\n"
        for row in preview_rows:
            prompt += f"  {row}\n"
    else:
        prompt += "No data returned.\n"

    prompt += "\n## YOUR ANALYSIS:\n"

    return prompt


def build_chart_recommendation_prompt(
    user_question: str,
    columns: List[str],
    sample_rows: List[dict],
    row_count: int,
) -> str:
    """Build a prompt for recommending chart type."""

    prompt = """You are a data visualization expert. Recommend the best chart type for displaying the given data.

## RULES:
1. Return ONLY one of these chart types: bar, pie, line, scatter, heatmap, table
2. Consider the data structure:
   - Categories + values → bar
   - Parts of a whole → pie
   - Time series → line
   - Two numeric variables → scatter
   - Matrix/correlation → heatmap
   - Too many columns or complex data → table
3. Return a JSON object with: {"chart_type": "...", "x_column": "...", "y_column": "...", "title": "..."}
4. Return ONLY the JSON — no extra text.

"""

    prompt += f"## USER QUESTION:\n{user_question}\n\n"
    prompt += f"## COLUMNS: {columns}\n"
    prompt += f"## ROW COUNT: {row_count}\n"

    if sample_rows:
        prompt += f"## SAMPLE DATA:\n"
        for row in sample_rows[:5]:
            prompt += f"  {row}\n"

    prompt += "\n## YOUR RECOMMENDATION (JSON only):\n"

    return prompt


def get_schema_context(user_question: str) -> List[dict]:
    """Retrieve relevant schema context from RAG for the user's question."""
    return rag_service.search(user_question)
