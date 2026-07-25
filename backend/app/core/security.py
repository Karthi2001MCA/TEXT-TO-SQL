"""
Security utilities — SQL injection detection and read-only query enforcement.
(No authentication — the platform is open access.)
"""

# ============================================
# SQL Injection Detection
# ============================================

DANGEROUS_SQL_PATTERNS = [
    "DROP ",
    "DELETE ",
    "UPDATE ",
    "INSERT ",
    "TRUNCATE ",
    "ALTER ",
    "CREATE ",
    "EXEC ",
    "EXECUTE ",
    "GRANT ",
    "REVOKE ",
    "UNION ALL SELECT",  # Common injection pattern
]

DANGEROUS_SQL_CHARS = [
    ";",   # Multiple statements
    "--",  # SQL comment (used to bypass)
]


def detect_sql_injection(sql: str) -> dict:
    """
    Analyze a SQL string for potential injection or destructive operations.
    Returns: {is_safe: bool, reason: str}
    """
    sql_upper = sql.upper().strip()

    # Must start with SELECT
    if not sql_upper.startswith("SELECT"):
        return {
            "is_safe": False,
            "reason": "Only SELECT statements are allowed",
        }

    # Check for dangerous patterns
    for pattern in DANGEROUS_SQL_PATTERNS:
        if pattern in sql_upper:
            return {
                "is_safe": False,
                "reason": f"Blocked: contains dangerous pattern '{pattern.strip()}'",
            }

    # Check for dangerous characters (multiple statements)
    if ";" in sql.strip().rstrip(";"):
        return {
            "is_safe": False,
            "reason": "Multiple SQL statements are not allowed",
        }

    return {"is_safe": True, "reason": "Query passed safety checks"}
