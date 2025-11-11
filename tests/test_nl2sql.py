"""Test script for NL2SQL converter functionality.

Note: These tests require:
1. Valid GCP credentials or API key in .env
2. PostgreSQL database running with test schema
"""

import traceback
from utils.config import AppConfig
from utils.db import DatabaseManager
from utils.gemini_client import GeminiClient
from tools.nl2sql import NL2SQLConverter


def setup_test_schema(db_manager: DatabaseManager):
    """Create a simple test schema for testing."""
    print("📝 Setting up test schema...")

    # Create test schema
    schema_name = "test_nl2sql"
    try:
        db_manager.drop_schema(schema_name)
    except Exception:
        pass  # Schema might not exist

    db_manager.create_schema(schema_name)

    # Create simple test tables
    ddl = """
        CREATE TABLE customers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE orders (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER REFERENCES customers(id),
            total DECIMAL(10, 2),
            status VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            price DECIMAL(10, 2),
            category VARCHAR(50)
        );
    """

    db_manager.execute_ddl_in_schema(ddl, schema_name)
    print(f"✓ Test schema '{schema_name}' created\n")

    return schema_name


def teardown_test_schema(db_manager: DatabaseManager, schema_name: str):
    """Clean up test schema."""
    print(f"🧹 Cleaning up test schema '{schema_name}'...")
    try:
        db_manager.drop_schema(schema_name)
        print(f"✓ Test schema dropped\n")
    except Exception as e:
        print(f"⚠️  Failed to drop schema: {e}\n")


def test_simple_query(nl2sql: NL2SQLConverter, schema_name: str):
    """Test converting a simple question to SQL."""
    print("🧪 Testing simple query conversion...")

    question = "Show me all customers"
    result = nl2sql.convert_to_sql(question, schema_name)

    assert "sql_query" in result, "Result should contain sql_query"
    assert "SELECT" in result["sql_query"].upper(), "Query should be a SELECT statement"
    assert "customers" in result["sql_query"].lower(), "Query should reference customers table"

    print(f"  Question: {question}")
    print(f"  SQL: {result['sql_query']}")
    print(f"  Explanation: {result.get('explanation', 'N/A')}")
    print(f"  Confidence: {result.get('confidence', 'N/A')}\n")


def test_aggregation_query(nl2sql: NL2SQLConverter, schema_name: str):
    """Test converting aggregation question to SQL."""
    print("🧪 Testing aggregation query...")

    question = "What is the average order total?"
    result = nl2sql.convert_to_sql(question, schema_name)

    assert "sql_query" in result, "Result should contain sql_query"
    query_upper = result["sql_query"].upper()
    assert "AVG" in query_upper or "AVERAGE" in query_upper, "Query should use AVG function"
    assert "orders" in result["sql_query"].lower(), "Query should reference orders table"

    print(f"  Question: {question}")
    print(f"  SQL: {result['sql_query']}")
    print(f"  Explanation: {result.get('explanation', 'N/A')}\n")


def test_join_query(nl2sql: NL2SQLConverter, schema_name: str):
    """Test converting question requiring JOIN to SQL."""
    print("🧪 Testing JOIN query...")

    question = "Show me customers and their order totals"
    result = nl2sql.convert_to_sql(question, schema_name)

    assert "sql_query" in result, "Result should contain sql_query"
    query_upper = result["sql_query"].upper()
    assert "JOIN" in query_upper, "Query should use JOIN"
    assert "customers" in result["sql_query"].lower(), "Query should reference customers"
    assert "orders" in result["sql_query"].lower(), "Query should reference orders"

    print(f"  Question: {question}")
    print(f"  SQL: {result['sql_query']}")
    print(f"  Explanation: {result.get('explanation', 'N/A')}\n")


def test_filtered_query(nl2sql: NL2SQLConverter, schema_name: str):
    """Test converting question with filtering to SQL."""
    print("🧪 Testing filtered query...")

    question = "Show me orders with total greater than 100"
    result = nl2sql.convert_to_sql(question, schema_name)

    assert "sql_query" in result, "Result should contain sql_query"
    query_upper = result["sql_query"].upper()
    assert "WHERE" in query_upper, "Query should have WHERE clause"
    assert "orders" in result["sql_query"].lower(), "Query should reference orders table"

    print(f"  Question: {question}")
    print(f"  SQL: {result['sql_query']}")
    print(f"  Explanation: {result.get('explanation', 'N/A')}\n")


def test_top_n_query(nl2sql: NL2SQLConverter, schema_name: str):
    """Test converting 'top N' question to SQL."""
    print("🧪 Testing TOP N query...")

    question = "Show me the top 5 customers by number of orders"
    result = nl2sql.convert_to_sql(question, schema_name)

    assert "sql_query" in result, "Result should contain sql_query"
    query_upper = result["sql_query"].upper()
    assert "LIMIT" in query_upper or "TOP" in query_upper, "Query should limit results"
    assert "ORDER BY" in query_upper, "Query should have ORDER BY"

    print(f"  Question: {question}")
    print(f"  SQL: {result['sql_query']}")
    print(f"  Explanation: {result.get('explanation', 'N/A')}\n")


def test_conversation_history(nl2sql: NL2SQLConverter, schema_name: str):
    """Test using conversation history for follow-up questions."""
    print("🧪 Testing conversation history...")

    # First question
    question1 = "Show me all customers"
    result1 = nl2sql.convert_to_sql(question1, schema_name)

    # Build conversation history
    history = [
        {"role": "user", "content": question1},
        {"role": "assistant", "content": "Here are all customers", "sql_query": result1["sql_query"]}
    ]

    # Follow-up question
    question2 = "Now show me only the ones created this year"
    result2 = nl2sql.convert_to_sql(question2, schema_name, conversation_history=history)

    assert "sql_query" in result2, "Result should contain sql_query"
    query_upper = result2["sql_query"].upper()
    assert "WHERE" in query_upper or "EXTRACT" in query_upper, "Follow-up should add filtering"

    print(f"  Question 1: {question1}")
    print(f"  SQL 1: {result1['sql_query']}")
    print(f"  Question 2: {question2}")
    print(f"  SQL 2: {result2['sql_query']}")
    print(f"  Explanation: {result2.get('explanation', 'N/A')}\n")


def test_invalid_empty_question(nl2sql: NL2SQLConverter, schema_name: str):
    """Test that empty questions are rejected."""
    print("🧪 Testing empty question handling...")

    try:
        nl2sql.convert_to_sql("", schema_name)
        assert False, "Empty question should raise ValueError"
    except ValueError as e:
        print(f"✓ Empty question rejected: {e}\n")


def test_tables_used_metadata(nl2sql: NL2SQLConverter, schema_name: str):
    """Test that tables_used metadata is populated."""
    print("🧪 Testing tables_used metadata...")

    question = "Show me customers and their orders"
    result = nl2sql.convert_to_sql(question, schema_name)

    assert "tables_used" in result, "Result should contain tables_used"
    assert isinstance(result["tables_used"], list), "tables_used should be a list"
    assert len(result["tables_used"]) > 0, "tables_used should not be empty"

    print(f"  Question: {question}")
    print(f"  Tables used: {result['tables_used']}\n")


if __name__ == "__main__":
    print("=" * 60)
    print("🍜 SQLop - NL2SQL Converter Test Suite")
    print("=" * 60)
    print()

    try:
        # Initialize components
        print("🔧 Initializing components...")
        config = AppConfig.from_env()
        db_manager = DatabaseManager(config.database)
        db_manager.initialize()
        gemini_client = GeminiClient(config.gemini, enable_tracing=False)
        nl2sql = NL2SQLConverter(gemini_client, db_manager, enable_tracing=False)
        print("✓ Components initialized\n")

        # Setup test schema
        schema_name = setup_test_schema(db_manager)

        # Run tests
        tests = [
            (test_simple_query, nl2sql, schema_name),
            (test_aggregation_query, nl2sql, schema_name),
            (test_join_query, nl2sql, schema_name),
            (test_filtered_query, nl2sql, schema_name),
            (test_top_n_query, nl2sql, schema_name),
            (test_conversation_history, nl2sql, schema_name),
            (test_invalid_empty_question, nl2sql, schema_name),
            (test_tables_used_metadata, nl2sql, schema_name),
        ]

        passed = 0
        failed = 0

        for test_func, *args in tests:
            try:
                test_func(*args)
                passed += 1
            except AssertionError as e:
                failed += 1
                print(f"❌ Test failed: {test_func.__name__}")
                print(f"   {e}\n")
            except Exception as e:
                failed += 1
                print(f"❌ Test error: {test_func.__name__}")
                print(f"   {e}")
                traceback.print_exc()
                print()

        # Cleanup
        teardown_test_schema(db_manager, schema_name)
        db_manager.close()

        # Results
        print("=" * 60)
        print(f"✅ Tests passed: {passed}")
        print(f"❌ Tests failed: {failed}")
        print("=" * 60)

        if failed == 0:
            print("\n🎉 All tests passed!")
        else:
            print(f"\n⚠️  {failed} test(s) need attention")

    except Exception as e:
        print(f"❌ Test suite failed to initialize: {e}")
        traceback.print_exc()