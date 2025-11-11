"""Database connection and query utilities using psycopg3."""

import logging
from contextlib import contextmanager
from typing import List, Optional, Sequence

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages PostgreSQL connections and queries."""

    def __init__(self, db_config: DatabaseConfig):
        """Initialize with database configuration."""
        self.db_config = db_config
        self.pool: Optional[ConnectionPool] = None

    def initialize(self):
        """Create connection pool."""
        if self.pool is None:
            # Use dictionary for connection params to avoid special character issues
            conn_params = {
                "host": self.db_config.host,
                "port": self.db_config.port,
                "dbname": self.db_config.name,
                "user": self.db_config.user,
                "password": self.db_config.password,
            }

            self.pool = ConnectionPool(
                kwargs=conn_params,
                min_size=2,
                max_size=10,
                timeout=30,
            )
            logger.info("Database connection pool initialized")

    def close(self):
        """Close connection pool."""
        if self.pool:
            self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool."""
        if not self.pool:
            self.initialize()

        with self.pool.connection() as conn:
            yield conn

    def execute_ddl(self, ddl: str) -> None:
        """Execute DDL statements (CREATE TABLE, etc.)."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Split by semicolon and execute each statement
                statements = [s.strip() for s in ddl.split(";") if s.strip()]
                for statement in statements:
                    cur.execute(statement)
                logger.info(f"Executed {len(statements)} DDL statement(s)")

    def execute_query(self, query: str, params: Optional[Sequence] = None) -> List[dict]:
        """Execute SELECT query and return results as list of dicts."""
        with self.get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                results = cur.fetchall()
                logger.debug(f"Query returned {len(results)} row(s)")
                return results

    def execute_insert(self, table: str, data: List[dict]) -> int:
        """Bulk insert data into a table in the public schema.

        Note: PostgreSQL lowercases unquoted identifiers, so we lowercase
        table and column names when using quoted identifiers to match the
        actual names in the database.
        """
        if not data:
            return 0

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Get column names from first record
                columns = list(data[0].keys())
                placeholders = ", ".join(["%s"] * len(columns))

                # Lowercase identifiers to match PostgreSQL's behavior
                table_lower = table.lower()
                columns_lower = [col.lower() for col in columns]
                column_names = ", ".join([f'"{col}"' for col in columns_lower])

                insert_query = (
                    f'INSERT INTO "{table_lower}" ({column_names}) VALUES ({placeholders})'
                )

                # Prepare data tuples (use original column names from data dict)
                values = [tuple(row[col] for col in columns) for row in data]

                # Execute batch insert
                cur.executemany(insert_query, values)

                row_count = cur.rowcount
                logger.info(f"Inserted {row_count} row(s) into {table_lower}")
                return row_count

    def get_table_schema(self, table_name: Optional[str] = None) -> List[dict]:
        """Get schema information for tables."""
        query = """
            SELECT
                table_name,
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
        """

        if table_name:
            query += " AND table_name = %s"
            params = (table_name,)
        else:
            params = None

        query += " ORDER BY table_name, ordinal_position"

        return self.execute_query(query, params)

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """
        result = self.execute_query(query, (table_name,))
        return result[0]["exists"] if result else False

    def drop_all_tables(self) -> None:
        """Drop all tables in the public schema (for cleanup)."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                        END LOOP;
                    END $$;
                """
                )
                logger.info("Dropped all tables")

    def get_foreign_keys(self, schema_name: str = "public") -> List[dict]:
        """Get foreign key relationships for a schema.

        Args:
            schema_name: Schema to get foreign keys from (default: 'public')

        Returns:
            List of dicts with foreign key info:
            - table_name: Source table
            - column_name: Source column
            - foreign_table_name: Referenced table
            - foreign_column_name: Referenced column
            - constraint_name: Foreign key constraint name
        """
        query = """
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                tc.constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = %s
            ORDER BY tc.table_name, kcu.ordinal_position
        """
        return self.execute_query(query, (schema_name,))

    def health_check(self) -> bool:
        """Check if database connection is healthy.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            self.execute_query("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    # Schema management methods for dataset storage

    def create_schema(self, schema_name: str) -> None:
        """Create a new PostgreSQL schema for storing generated datasets.

        Args:
            schema_name: Name of the schema to create (e.g., 'slop_restaurant_v1')
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Sanitize schema name using SQL composition
                cur.execute(
                    psycopg.sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                        psycopg.sql.Identifier(schema_name)
                    )
                )
                logger.info(f"Created schema: {schema_name}")

    def schema_exists(self, schema_name: str) -> bool:
        """Check if a schema exists.

        Args:
            schema_name: Name of the schema to check

        Returns:
            True if schema exists, False otherwise
        """
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.schemata
                WHERE schema_name = %s
            )
        """
        result = self.execute_query(query, (schema_name,))
        return result[0]["exists"] if result else False

    def list_schemas(self, prefix: str = "slop_") -> List[dict]:
        """List all schemas with a given prefix (SQLop datasets).

        Args:
            prefix: Schema name prefix to filter by (default: 'slop_')

        Returns:
            List of dicts with schema info: name, table_count, created_date
        """
        query = """
            SELECT
                s.schema_name,
                COUNT(t.table_name) as table_count
            FROM information_schema.schemata s
            LEFT JOIN information_schema.tables t
                ON s.schema_name = t.table_schema
            WHERE s.schema_name LIKE %s
            GROUP BY s.schema_name
            ORDER BY s.schema_name DESC
        """
        return self.execute_query(query, (f"{prefix}%",))

    def drop_schema(self, schema_name: str) -> None:
        """Drop a schema and all its contents.

        Args:
            schema_name: Name of the schema to drop
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    psycopg.sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                        psycopg.sql.Identifier(schema_name)
                    )
                )
                logger.info(f"Dropped schema: {schema_name}")

    def get_schema_tables(self, schema_name: str) -> List[str]:
        """Get list of table names in a schema.

        Args:
            schema_name: Name of the schema

        Returns:
            List of table names
        """
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name
        """
        results = self.execute_query(query, (schema_name,))
        return [r["table_name"] for r in results]

    def execute_ddl_in_schema(self, ddl: str, schema_name: str) -> None:
        """Execute DDL statements in a specific schema.

        Note: DDL must be valid PostgreSQL syntax with tables defined in
        dependency order (parent tables before child tables). Circular
        foreign key dependencies should be handled with ALTER TABLE statements.

        Args:
            ddl: DDL statements to execute (valid PostgreSQL syntax)
            schema_name: Schema to create tables in

        Raises:
            psycopg.Error: If DDL execution fails (e.g., syntax errors,
                          missing table references, circular dependencies)
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Set search_path to target schema (include public for system references)
                # Store original search_path to restore later
                cur.execute("SHOW search_path")
                original_search_path = cur.fetchone()[0]

                cur.execute(
                    psycopg.sql.SQL("SET search_path TO {}, public").format(
                        psycopg.sql.Identifier(schema_name)
                    )
                )

                try:
                    # Split by semicolon and execute each statement
                    statements = [s.strip() for s in ddl.split(";") if s.strip()]
                    for idx, statement in enumerate(statements, 1):
                        try:
                            cur.execute(statement)
                        except Exception as stmt_error:
                            # Include the failing statement in error context
                            logger.error(
                                f"Statement {idx}/{len(statements)} failed in schema {schema_name}: {stmt_error}\n"
                                f"Failing SQL:\n{statement[:500]}"  # Limit to 500 chars
                            )
                            raise

                    logger.info(
                        f"Executed {len(statements)} DDL statement(s) in schema {schema_name}"
                    )
                finally:
                    # Restore original search_path to avoid pool contamination
                    cur.execute(f"SET search_path TO {original_search_path}")

    def execute_insert_in_schema(
        self, table: str, data: List[dict], schema_name: str
    ) -> int:
        """Bulk insert data into a table in a specific schema.

        Args:
            table: Table name
            data: List of dicts with row data
            schema_name: Schema containing the table

        Returns:
            Number of rows inserted
        """
        if not data:
            return 0

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Get column names from first record
                columns = list(data[0].keys())
                placeholders = ", ".join(["%s"] * len(columns))

                # PostgreSQL lowercases unquoted identifiers during CREATE TABLE
                # So we need to lowercase both table and column names when using quoted identifiers
                # to ensure they match the actual names in the database
                table_lower = table.lower()
                columns_lower = [col.lower() for col in columns]
                column_names = ", ".join([f'"{col}"' for col in columns_lower])

                # Use schema-qualified table name with quoted identifiers
                qualified_table = f'"{schema_name}"."{table_lower}"'
                insert_query = f"INSERT INTO {qualified_table} ({column_names}) VALUES ({placeholders})"

                # Prepare data tuples (use original column names from data dict)
                values = [tuple(row[col] for col in columns) for row in data]

                # Execute batch insert
                cur.executemany(insert_query, values)

                row_count = cur.rowcount
                logger.info(f"Inserted {row_count} row(s) into {qualified_table}")
                return row_count
