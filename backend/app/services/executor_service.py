"""
SQL Executor Service — safely executes validated SQL on the data database.
"""

import time
from typing import Optional
from sqlalchemy import text

from ..database import DataSessionLocal


async def execute_sql(
    sql: str,
    timeout_seconds: float = 30.0,
    max_rows: int = 10000,
) -> dict:
    """
    Execute a validated SQL query on the data database.
    Returns structured results.
    """
    start_time = time.time()

    try:
        async with DataSessionLocal() as session:
            # Add LIMIT if not present and query might return many rows
            execution_sql = sql.rstrip(";").strip()
            if "LIMIT" not in execution_sql.upper():
                execution_sql += f" LIMIT {max_rows}"

            result = await session.execute(text(execution_sql))
            execution_time = (time.time() - start_time) * 1000

            columns = list(result.keys())
            rows = result.fetchall()

            # Convert rows to list of dicts
            data = [dict(zip(columns, row)) for row in rows]

            # Serialize values for JSON compatibility
            serialized_data = []
            for row in data:
                clean_row = {}
                for k, v in row.items():
                    if v is None:
                        clean_row[k] = None
                    elif isinstance(v, (int, float, bool)):
                        clean_row[k] = v
                    else:
                        clean_row[k] = str(v)
                serialized_data.append(clean_row)

            return {
                "success": True,
                "columns": columns,
                "rows": serialized_data,
                "row_count": len(serialized_data),
                "execution_time_ms": round(execution_time, 2),
                "sql_executed": execution_sql,
                "error": None,
            }

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": round(execution_time, 2),
            "sql_executed": sql,
            "error": str(e),
        }


async def dry_run_sql(sql: str) -> dict:
    """
    Attempt a dry-run of SQL to verify it will execute.
    Uses LIMIT 0 trick to check without actually fetching data.
    """
    try:
        dry_sql = f"SELECT * FROM ({sql.rstrip(';')}) AS dry_run LIMIT 0"
        async with DataSessionLocal() as session:
            await session.execute(text(dry_sql))
            return {"success": True, "error": None}
    except Exception as e:
        return {"success": False, "error": str(e)}
