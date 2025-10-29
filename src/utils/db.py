"""Database connection and query utilities using psycopg3."""

import logging
from contextlib import contextmanager
from typing import List, Optional, Tuple

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
                statements = [s.strip() for s in ddl.split(';') if s.strip()]
                for statement in statements:
                    cur.execute(statement)
                conn.commit()
                logger.info(f"Executed {len(statements)} DDL statement(s)")

    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[dict]:
        """Execute SELECT query and return results as list of dicts."""
        with self.get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                results = cur.fetchall()
                logger.info(f"Query returned {len(results)} row(s)")
                return results

    def execute_insert(self, table: str, data: List[dict]) -> int:
        """Bulk insert data into a table."""
        if not data:
            return 0

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Get column names from first record
                columns = list(data[0].keys())
                placeholders = ', '.join(['%s'] * len(columns))
                column_names = ', '.join(columns)

                insert_query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"

                # Prepare data tuples
                values = [tuple(row[col] for col in columns) for row in data]

                # Execute batch insert
                cur.executemany(insert_query, values)
                conn.commit()

                row_count = cur.rowcount
                logger.info(f"Inserted {row_count} row(s) into {table}")
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
        return result[0]['exists'] if result else False

    def drop_all_tables(self) -> None:
        """Drop all tables in the public schema (for cleanup)."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                        END LOOP;
                    END $$;
                """)
                conn.commit()
                logger.info("Dropped all tables")