"""
SQL Validator Service — validates generated SQL for safety, syntax, and schema correctness.
"""

import re
import sqlparse
from typing import List
from dataclasses import dataclass, field

from ..core.security import detect_sql_injection
from ..database import get_data_db_tables, get_table_columns


@dataclass
class ValidationResult:
    """Result of SQL validation."""
    sql: str
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    tables_used: List[str] = field(default_factory=list)
    columns_used: List[str] = field(default_factory=list)


async def validate_sql(sql: str) -> ValidationResult:
    """
    Comprehensive SQL validation pipeline.
    Checks: non-empty, safety, syntax, table existence, column existence.
    """
    result = ValidationResult(sql=sql, is_valid=True)

    # Step 1: Empty check
    if not sql or not sql.strip():
        result.is_valid = False
        result.errors.append("SQL query is empty")
        return result

    # Skip if model couldn't generate
    if sql.strip() == "UNABLE_TO_GENERATE":
        result.is_valid = False
        result.errors.append("Model was unable to generate SQL for this question")
        return result

    # Step 2: Safety check (injection detection)
    safety = detect_sql_injection(sql)
    if not safety["is_safe"]:
        result.is_valid = False
        result.errors.append(safety["reason"])
        return result

    # Step 3: Syntax check with sqlparse
    try:
        parsed = sqlparse.parse(sql)
        if not parsed:
            result.is_valid = False
            result.errors.append("Failed to parse SQL")
            return result

        # Check for multiple statements
        if len(parsed) > 1:
            result.is_valid = False
            result.errors.append("Multiple SQL statements are not allowed")
            return result

        stmt = parsed[0]
        if stmt.get_type() != "SELECT":
            result.is_valid = False
            result.errors.append(f"Only SELECT statements allowed, got: {stmt.get_type()}")
            return result
    except Exception as e:
        result.warnings.append(f"SQL parse warning: {str(e)}")

    # Step 4: Table existence check
    try:
        existing_tables = await get_data_db_tables()
        tables_in_query = _extract_table_names(sql)
        result.tables_used = tables_in_query

        for table in tables_in_query:
            if table not in existing_tables:
                result.is_valid = False
                result.errors.append(
                    f"Table '{table}' does not exist. Available tables: {existing_tables}"
                )
    except Exception as e:
        result.warnings.append(f"Could not verify tables: {str(e)}")

    # Step 5: Column existence check
    if result.is_valid and result.tables_used:
        try:
            for table in result.tables_used:
                table_cols = await get_table_columns(table)
                col_names = [c["name"] for c in table_cols]
                query_cols = _extract_column_names(sql, table)
                for col in query_cols:
                    if col != "*" and col not in col_names:
                        result.warnings.append(
                            f"Column '{col}' may not exist in table '{table}'"
                        )
        except Exception as e:
            result.warnings.append(f"Could not verify columns: {str(e)}")

    return result


# Identifier forms: "quoted", `backticked`, [bracketed], or bare
_IDENTIFIER = r'"[^"]+"|`[^`]+`|\[[^\]]+\]|[A-Za-z_][\w$]*'

# Clause keywords that terminate a FROM/JOIN target list
_CLAUSE_KEYWORDS = (
    "WHERE", "GROUP", "ORDER", "HAVING", "LIMIT", "OFFSET", "UNION", "INTERSECT",
    "EXCEPT", "ON", "USING", "JOIN", "INNER", "LEFT", "RIGHT", "FULL", "OUTER",
    "CROSS", "NATURAL", "AS", "WINDOW", "FETCH",
)

# Located separately from the target list so that nested FROMs are each scanned
# from their own keyword position — a single combined regex would let an outer
# "FROM ( SELECT ... FROM inner" match swallow the inner FROM.
_FROM_KEYWORD_RE = re.compile(r"\b(?:FROM|JOIN)\b", re.IGNORECASE)

_TARGETS_RE = re.compile(
    r"\s*(?P<targets>.+?)"
    r"(?=\s+\b(?:" + "|".join(_CLAUSE_KEYWORDS) + r")\b|\s*\)|\s*$)",
    re.IGNORECASE | re.DOTALL,
)

# Names the query defines for itself: CTEs and derived-table aliases
_CTE_RE = re.compile(r"(?:\bWITH\b|,)\s*(" + _IDENTIFIER + r")\s+AS\s*\(", re.IGNORECASE)
_ALIAS_RE = re.compile(r"\)\s*(?:AS\s+)?(" + _IDENTIFIER + r")", re.IGNORECASE)


def _unquote(name: str) -> str:
    """Strip identifier quoting from a name."""
    name = name.strip()
    if len(name) >= 2 and name[0] in "\"`[" and name[-1] in "\"`]":
        return name[1:-1]
    return name


_TABLE_ALIAS_RE = re.compile(
    r"\s*(?:" + _IDENTIFIER + r")\s+(?:AS\s+)?(" + _IDENTIFIER + r")\s*$",
    re.IGNORECASE,
)


def _local_names(sql: str) -> set:
    """Names the query introduces itself (CTEs, table/derived-table aliases) — not base tables."""
    names = {_unquote(m.group(1)).lower() for m in _CTE_RE.finditer(sql)}
    names |= {_unquote(m.group(1)).lower() for m in _ALIAS_RE.finditer(sql)}

    # Table aliases: FROM sales a / JOIN sales AS a
    for keyword in _FROM_KEYWORD_RE.finditer(sql):
        match = _TARGETS_RE.match(sql, keyword.end())
        if not match:
            continue
        for target in match.group("targets").split(","):
            alias = _TABLE_ALIAS_RE.match(target)
            if alias:
                names.add(_unquote(alias.group(1)).lower())

    return {n for n in names if n and n.upper() not in _CLAUSE_KEYWORDS}


def _extract_table_names(sql: str) -> List[str]:
    """
    Extract base table names referenced by FROM/JOIN clauses.

    Handles quoted identifiers, comma-separated targets, and table aliases, and
    excludes names the query defines itself (CTEs, subquery aliases) so that
    valid SQL is not reported as referencing a missing table.
    """
    tables: List[str] = []
    local = _local_names(sql)

    for keyword in _FROM_KEYWORD_RE.finditer(sql):
        match = _TARGETS_RE.match(sql, keyword.end())
        if not match:
            continue
        targets = match.group("targets").strip()

        # A derived table — FROM ( SELECT ... ) — has no base table name here;
        # the inner SELECT's own FROM is matched separately by finditer.
        if targets.startswith("("):
            continue

        for target in targets.split(","):
            # Take the table reference, discarding any alias that follows it
            first = re.match(r"\s*(" + _IDENTIFIER + r")", target)
            if not first:
                continue
            name = _unquote(first.group(1))
            if not name or name.upper() in _CLAUSE_KEYWORDS:
                continue
            if name.lower() in local:
                continue
            if name not in tables:
                tables.append(name)

    return tables


def _extract_column_names(sql: str, table: str) -> List[str]:
    """
    Extract column identifiers referenced in the SQL.

    Skips function names, aliases introduced with AS, table qualifiers, and
    keywords, so that callers do not raise warnings for non-columns like SUM.
    """
    columns: List[str] = []
    parsed = sqlparse.parse(sql)[0]
    tokens = [t for t in parsed.flatten() if not t.is_whitespace]

    name_types = (sqlparse.tokens.Name, sqlparse.tokens.String.Symbol)
    known_tables = {t.lower() for t in _extract_table_names(sql)} | _local_names(sql)

    for i, token in enumerate(tokens):
        if token.ttype not in name_types:
            continue

        prev = tokens[i - 1] if i > 0 else None
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None

        # Function call: SUM( ... )
        if nxt is not None and nxt.ttype is sqlparse.tokens.Punctuation and nxt.value == "(":
            continue
        # Table qualifier in t.column
        if nxt is not None and nxt.ttype is sqlparse.tokens.Punctuation and nxt.value == ".":
            continue
        # Alias: ... AS total_sales
        if prev is not None and prev.ttype is sqlparse.tokens.Keyword and prev.value.upper() == "AS":
            continue

        name = _unquote(token.value)
        if not name or name.upper() in _CLAUSE_KEYWORDS:
            continue
        if name.lower() in known_tables:
            continue
        if name not in columns:
            columns.append(name)

    return columns
