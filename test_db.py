"""Simple test script to verify database connectivity."""

import logging

from src.utils.config import AppConfig
from src.utils.db import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Test database connection."""
    logger.info("Starting database connection test...")

    # Load configuration
    try:
        config = AppConfig.from_env()
        logger.info(f"Configuration loaded successfully")
        logger.info(f"Database: {config.database.host}:{config.database.port}/{config.database.name}")
        logger.info(f"Gemini model: {config.gemini.model}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return

    # Initialize database manager
    db_manager = DatabaseManager(config.database)

    try:
        # Test connection
        logger.info("Initializing connection pool...")
        db_manager.initialize()
        logger.info("✓ Connection pool initialized")

        # Test simple query
        logger.info("Testing query execution...")
        result = db_manager.execute_query("SELECT version()")
        logger.info(f"✓ PostgreSQL version: {result[0]['version']}")

        # Test schema query
        logger.info("Testing schema query...")
        tables = db_manager.execute_query("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        logger.info(f"✓ Found {len(tables)} tables in public schema")

        logger.info("\n=== All tests passed! ===")

    except Exception as e:
        logger.error(f"Database test failed: {e}")
        raise
    finally:
        # Clean up
        logger.info("Closing connection pool...")
        db_manager.close()
        logger.info("✓ Connection pool closed")


if __name__ == "__main__":
    main()