"""DDL converter utilities for translating between SQL dialects.

Converts MySQL DDL syntax to PostgreSQL-compatible syntax.
"""

import re


def mysql_to_postgres(ddl: str) -> str:
    """Convert MySQL DDL syntax to PostgreSQL syntax.

    Handles common MySQL-specific syntax that doesn't work in PostgreSQL:
    - AUTO_INCREMENT → SERIAL
    - TINYINT(1) → BOOLEAN
    - DATETIME → TIMESTAMP
    - UNSIGNED → (removed)
    - Backticks → (removed)
    - ENGINE, CHARSET, COMMENT → (removed)

    Args:
        ddl: DDL string with potential MySQL syntax

    Returns:
        PostgreSQL-compatible DDL string

    Example:
        >>> mysql_ddl = '''
        ... CREATE TABLE `users` (
        ...     id INT PRIMARY KEY AUTO_INCREMENT,
        ...     name VARCHAR(100),
        ...     active TINYINT(1)
        ... ) ENGINE=InnoDB;
        ... '''
        >>> pg_ddl = mysql_to_postgres(mysql_ddl)
        >>> print(pg_ddl)
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            active BOOLEAN
        );
    """
    result = ddl

    # Remove single-line comments to avoid parsing issues
    # Must preserve line structure, so replace with empty line
    result = re.sub(r'--[^\n]*', '', result)

    # AUTO_INCREMENT → SERIAL (must handle PRIMARY KEY combination)
    # Pattern: INT PRIMARY KEY AUTO_INCREMENT → SERIAL PRIMARY KEY
    result = re.sub(
        r'\b(INT|INTEGER|BIGINT|SMALLINT)\s+PRIMARY\s+KEY\s+AUTO_INCREMENT\b',
        r'SERIAL PRIMARY KEY',
        result,
        flags=re.IGNORECASE
    )

    # Pattern: INT AUTO_INCREMENT → SERIAL (without PRIMARY KEY)
    result = re.sub(
        r'\b(INT|INTEGER|BIGINT|SMALLINT)\s+AUTO_INCREMENT\b',
        r'SERIAL',
        result,
        flags=re.IGNORECASE
    )

    # Clean up any remaining AUTO_INCREMENT keywords
    result = re.sub(r',?\s*\bAUTO_INCREMENT\b', '', result, flags=re.IGNORECASE)

    # TINYINT(1) → BOOLEAN (MySQL convention for booleans)
    result = re.sub(r'\bTINYINT\s*\(\s*1\s*\)', 'BOOLEAN', result, flags=re.IGNORECASE)

    # TINYINT (other sizes) → SMALLINT
    result = re.sub(r'\bTINYINT\b', 'SMALLINT', result, flags=re.IGNORECASE)

    # DATETIME → TIMESTAMP
    result = re.sub(r'\bDATETIME\b', 'TIMESTAMP', result, flags=re.IGNORECASE)

    # ENUM(...) → VARCHAR(100) (simplified for synthetic data)
    # MySQL: cuisine_type ENUM('Italian', 'Mexican', ...) NOT NULL
    # PostgreSQL: cuisine_type VARCHAR(100) NOT NULL
    result = re.sub(
        r'\bENUM\s*\([^)]*\)',
        'VARCHAR(100)',
        result,
        flags=re.IGNORECASE
    )

    # Remove UNSIGNED keyword (PostgreSQL doesn't have unsigned types)
    result = re.sub(r'\s+UNSIGNED\b', '', result, flags=re.IGNORECASE)

    # Remove MySQL table options: ENGINE=InnoDB, DEFAULT CHARSET=utf8, etc.
    # Pattern: ) ENGINE=... options... ;
    result = re.sub(
        r'\)\s*ENGINE\s*=\s*\w+[^;]*;',
        r');',
        result,
        flags=re.IGNORECASE
    )

    # Remove CHARACTER SET / CHARSET clauses
    result = re.sub(
        r'\s+(CHARACTER\s+SET|CHARSET)\s*=?\s*\w+',
        '',
        result,
        flags=re.IGNORECASE
    )

    # Remove COLLATE clauses
    result = re.sub(
        r'\s+COLLATE\s+\w+',
        '',
        result,
        flags=re.IGNORECASE
    )

    # Remove COMMENT clauses
    result = re.sub(
        r'\s+COMMENT\s+(["\'])[^"\']*\1',
        '',
        result,
        flags=re.IGNORECASE
    )

    # Remove backticks (MySQL identifier quotes)
    result = result.replace('`', '')

    # Clean up multiple spaces
    result = re.sub(r'\s+', ' ', result)

    # Clean up space before commas
    result = re.sub(r'\s+,', ',', result)

    return result


def detect_mysql_syntax(ddl: str) -> bool:
    """Detect if DDL contains MySQL-specific syntax.

    Args:
        ddl: DDL string to check

    Returns:
        True if MySQL syntax detected, False otherwise
    """
    mysql_indicators = [
        r'\bAUTO_INCREMENT\b',
        r'\bENGINE\s*=',
        r'\bCHARSET\s*=',
        r'`',  # Backticks
        r'\bTINYINT\s*\(\s*1\s*\)',
    ]

    for pattern in mysql_indicators:
        if re.search(pattern, ddl, re.IGNORECASE):
            return True

    return False