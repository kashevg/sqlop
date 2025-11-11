"""SQL query validation and security guardrails.

This module provides SQL-specific security checks to prevent dangerous
operations and SQL injection attacks. Works alongside SecurityGuard
(prompt-level checks) for defense-in-depth.
"""

import logging
import re
from typing import List, Optional, Tuple

from langfuse.decorators import langfuse_context, observe

logger = logging.getLogger(__name__)


class SQLGuardrails:
    """SQL query validator for security and safety checks.

    Provides multiple layers of protection:
    - Dangerous keyword blocking (DROP, DELETE, UPDATE, etc.)
    - SQL injection pattern detection
    - SELECT-only enforcement
    - Optional table whitelist validation
    - Automatic LIMIT clause enforcement
    """

    # Dangerous SQL keywords that should be blocked
    DANGEROUS_KEYWORDS = [
        r'\bDROP\b',
        r'\bDELETE\b',
        r'\bUPDATE\b',
        r'\bALTER\b',
        r'\bTRUNCATE\b',
        r'\bINSERT\b',
        r'\bREPLACE\b',
        r'\bCREATE\b',
        r'\bEXEC\b',
        r'\bEXECUTE\b',
        r'\bGRANT\b',
        r'\bREVOKE\b',
    ]

    # SQL injection patterns
    INJECTION_PATTERNS = [
        r'--',  # SQL line comment
        r'/\*.*?\*/',  # Block comment
        r';\s*\w+',  # Multiple statements
        r'\bOR\b.*?=.*?',  # Common injection: OR 1=1
        r'\bUNION\b.*?\bSELECT\b',  # Union-based injection
        r'xp_',  # SQL Server extended procedures
        r'sp_',  # SQL Server system procedures
    ]

    def __init__(self, enable_tracing: bool = True):
        """Initialize SQL guardrails.

        Args:
            enable_tracing: Enable Langfuse tracing
        """
        self.enable_tracing = enable_tracing
        logger.info("SQLGuardrails initialized")

    @observe()
    def validate_query(
        self,
        sql_query: str,
        allowed_tables: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """Validate SQL query for safety.

        Performs multiple security checks:
        - Dangerous keyword detection (DROP, DELETE, etc.)
        - SQL injection pattern detection
        - SELECT-only enforcement
        - Optional table whitelist validation

        Args:
            sql_query: SQL query to validate
            allowed_tables: Optional list of allowed table names

        Returns:
            Tuple of (is_safe, reason):
                - is_safe: True if query is safe to execute
                - reason: Explanation of why query was blocked (empty if safe)

        Raises:
            ValueError: If sql_query is empty or None
        """
        if not sql_query or not sql_query.strip():
            logger.warning("Empty SQL query provided to validate_query")
            return (False, "Empty query provided")

        # Track validation in Langfuse
        if self.enable_tracing:
            langfuse_context.update_current_observation(
                metadata={
                    "query_length": len(sql_query),
                    "has_table_whitelist": allowed_tables is not None,
                }
            )

        try:
            # Normalize query for analysis
            normalized = sql_query.strip().upper()

            # Check 1: SELECT-only enforcement
            if not normalized.startswith('SELECT'):
                reason = "Only SELECT queries are allowed"
                logger.warning(f"Query blocked: {reason}")
                if self.enable_tracing:
                    langfuse_context.update_current_observation(
                        metadata={"blocked_reason": reason, "is_safe": False}
                    )
                return (False, reason)

            # Check 2: Dangerous keywords
            for pattern in self.DANGEROUS_KEYWORDS:
                if re.search(pattern, normalized, re.IGNORECASE):
                    keyword = pattern.strip(r'\b\\')
                    reason = f"Dangerous SQL keyword detected: {keyword}"
                    logger.warning(f"Query blocked: {reason}")
                    if self.enable_tracing:
                        langfuse_context.update_current_observation(
                            metadata={
                                "blocked_reason": reason,
                                "blocked_keyword": keyword,
                                "is_safe": False
                            }
                        )
                    return (False, reason)

            # Check 3: SQL injection patterns
            for pattern in self.INJECTION_PATTERNS:
                if re.search(pattern, sql_query, re.IGNORECASE | re.DOTALL):
                    reason = f"Potential SQL injection pattern detected: {pattern}"
                    logger.warning(f"Query blocked: {reason}")
                    if self.enable_tracing:
                        langfuse_context.update_current_observation(
                            metadata={
                                "blocked_reason": reason,
                                "blocked_pattern": pattern,
                                "is_safe": False
                            }
                        )
                    return (False, reason)

            # Check 4: Table whitelist (if provided)
            if allowed_tables:
                # Extract table names from query (simple pattern matching)
                # This is basic - a proper parser would be more robust
                table_pattern = r'\bFROM\s+(\w+)|JOIN\s+(\w+)'
                matches = re.findall(table_pattern, normalized, re.IGNORECASE)

                # Flatten matches (regex groups)
                found_tables = set()
                for match in matches:
                    for table in match:
                        if table:
                            found_tables.add(table.lower())

                # Check if all found tables are in whitelist
                allowed_lower = [t.lower() for t in allowed_tables]
                for table in found_tables:
                    if table not in allowed_lower:
                        reason = f"Table '{table}' not in allowed list: {allowed_tables}"
                        logger.warning(f"Query blocked: {reason}")
                        if self.enable_tracing:
                            langfuse_context.update_current_observation(
                                metadata={
                                    "blocked_reason": reason,
                                    "blocked_table": table,
                                    "allowed_tables": allowed_tables,
                                    "is_safe": False
                                }
                            )
                        return (False, reason)

            # All checks passed
            logger.info("Query validated successfully")
            if self.enable_tracing:
                langfuse_context.update_current_observation(
                    metadata={"is_safe": True}
                )
            return (True, "")

        except Exception as e:
            error_msg = f"Error during query validation: {e}"
            logger.error(error_msg, exc_info=True)
            if self.enable_tracing:
                langfuse_context.update_current_observation(
                    metadata={"error": str(e), "is_safe": False}
                )
            # Fail closed - block query on error
            return (False, f"Validation error: {str(e)}")

    def add_limit_clause(
        self,
        sql_query: str,
        max_rows: int = 1000
    ) -> str:
        """Add or enforce LIMIT clause on query.

        If query already has LIMIT, enforces max_rows if existing limit is higher.
        Otherwise adds LIMIT clause to the end.

        Args:
            sql_query: SQL query (assumed to be validated SELECT)
            max_rows: Maximum number of rows to return

        Returns:
            Query with LIMIT clause added/enforced
        """
        if not sql_query or not sql_query.strip():
            return sql_query

        normalized = sql_query.strip().upper()

        # Check if LIMIT already exists
        if 'LIMIT' in normalized:
            # Extract existing limit value
            match = re.search(r'LIMIT\s+(\d+)', normalized, re.IGNORECASE)
            if match:
                existing_limit = int(match.group(1))
                # If existing limit is higher than max, replace it
                if existing_limit > max_rows:
                    logger.info(f"Reducing LIMIT from {existing_limit} to {max_rows}")
                    return re.sub(
                        r'LIMIT\s+\d+',
                        f'LIMIT {max_rows}',
                        sql_query,
                        flags=re.IGNORECASE
                    )
                else:
                    # Keep existing lower limit
                    return sql_query

        # Add LIMIT clause
        logger.info(f"Adding LIMIT {max_rows} to query")
        return f"{sql_query.rstrip(';')} LIMIT {max_rows}"