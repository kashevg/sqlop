"""Test script for SQL guardrails functionality."""

import traceback
from tools.sql_guardrails import SQLGuardrails


def test_safe_select():
    """Test that safe SELECT queries pass validation."""
    print("🧪 Testing safe SELECT query...")
    guardrails = SQLGuardrails(enable_tracing=False)

    query = "SELECT * FROM customers WHERE id = 1"
    is_safe, reason = guardrails.validate_query(query)

    assert is_safe, f"Safe query was blocked: {reason}"
    print(f"✓ Query passed validation: {query}\n")


def test_dangerous_drop():
    """Test that DROP queries are blocked."""
    print("🧪 Testing dangerous DROP query...")
    guardrails = SQLGuardrails(enable_tracing=False)

    query = "DROP TABLE customers"
    is_safe, reason = guardrails.validate_query(query)

    assert not is_safe, "DROP query should be blocked"
    print(f"✓ Query blocked: {reason}\n")


def test_dangerous_delete():
    """Test that DELETE queries are blocked."""
    print("🧪 Testing dangerous DELETE query...")
    guardrails = SQLGuardrails(enable_tracing=False)

    query = "DELETE FROM customers WHERE id = 1"
    is_safe, reason = guardrails.validate_query(query)

    assert not is_safe, "DELETE query should be blocked"
    print(f"✓ Query blocked: {reason}\n")


def test_dangerous_update():
    """Test that UPDATE queries are blocked."""
    print("🧪 Testing dangerous UPDATE query...")
    guardrails = SQLGuardrails(enable_tracing=False)

    query = "UPDATE customers SET email = 'evil@example.com'"
    is_safe, reason = guardrails.validate_query(query)

    assert not is_safe, "UPDATE query should be blocked"
    print(f"✓ Query blocked: {reason}\n")


def test_sql_injection_comment():
    """Test that SQL comment injection patterns are blocked."""
    print("🧪 Testing SQL injection with comment...")
    guardrails = SQLGuardrails(enable_tracing=False)

    query = "SELECT * FROM users WHERE id = 1 -- DROP TABLE users"
    is_safe, reason = guardrails.validate_query(query)

    assert not is_safe, "SQL injection with comment should be blocked"
    print(f"✓ Injection blocked: {reason}\n")


def test_sql_injection_union():
    """Test that UNION-based injection is blocked."""
    print("🧪 Testing SQL injection with UNION...")
    guardrails = SQLGuardrails(enable_tracing=False)

    query = "SELECT * FROM users WHERE id = 1 UNION SELECT * FROM admin"
    is_safe, reason = guardrails.validate_query(query)

    assert not is_safe, "UNION injection should be blocked"
    print(f"✓ Injection blocked: {reason}\n")


def test_complex_safe_query():
    """Test that complex but safe queries pass."""
    print("🧪 Testing complex safe query with JOINs...")
    guardrails = SQLGuardrails(enable_tracing=False)

    query = """
        SELECT c.name, COUNT(o.id) as order_count, SUM(o.total) as revenue
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        WHERE o.created_at >= '2024-01-01'
        GROUP BY c.id, c.name
        ORDER BY revenue DESC
    """
    is_safe, reason = guardrails.validate_query(query)

    assert is_safe, f"Complex safe query was blocked: {reason}"
    print(f"✓ Complex query passed validation\n")


def test_add_limit_clause():
    """Test adding LIMIT clause to queries."""
    print("🧪 Testing LIMIT clause addition...")
    guardrails = SQLGuardrails(enable_tracing=False)

    # Query without LIMIT
    query = "SELECT * FROM customers"
    limited_query = guardrails.add_limit_clause(query, max_rows=100)
    assert "LIMIT 100" in limited_query
    print(f"✓ LIMIT added: {limited_query}\n")

    # Query with lower LIMIT (should keep it)
    query_with_limit = "SELECT * FROM customers LIMIT 50"
    limited_query = guardrails.add_limit_clause(query_with_limit, max_rows=100)
    assert "LIMIT 50" in limited_query
    print(f"✓ Existing lower LIMIT preserved: {limited_query}\n")

    # Query with higher LIMIT (should replace it)
    query_with_high_limit = "SELECT * FROM customers LIMIT 5000"
    limited_query = guardrails.add_limit_clause(query_with_high_limit, max_rows=100)
    assert "LIMIT 100" in limited_query
    assert "LIMIT 5000" not in limited_query
    print(f"✓ High LIMIT reduced: {limited_query}\n")


def test_table_whitelist():
    """Test table whitelist validation."""
    print("🧪 Testing table whitelist validation...")
    guardrails = SQLGuardrails(enable_tracing=False)

    # Query with allowed tables
    query = "SELECT * FROM customers"
    is_safe, reason = guardrails.validate_query(query, allowed_tables=["customers", "orders"])
    assert is_safe, f"Query with allowed table was blocked: {reason}"
    print(f"✓ Allowed table passed: {query}\n")

    # Query with disallowed table
    query_bad = "SELECT * FROM admin_users"
    is_safe, reason = guardrails.validate_query(query_bad, allowed_tables=["customers", "orders"])
    assert not is_safe, "Query with disallowed table should be blocked"
    print(f"✓ Disallowed table blocked: {reason}\n")


def test_non_select_query():
    """Test that non-SELECT queries are blocked."""
    print("🧪 Testing non-SELECT query...")
    guardrails = SQLGuardrails(enable_tracing=False)

    query = "INSERT INTO customers (name) VALUES ('test')"
    is_safe, reason = guardrails.validate_query(query)

    assert not is_safe, "Non-SELECT query should be blocked"
    print(f"✓ Non-SELECT blocked: {reason}\n")


def test_empty_query():
    """Test that empty queries are rejected."""
    print("🧪 Testing empty query...")
    guardrails = SQLGuardrails(enable_tracing=False)

    is_safe, reason = guardrails.validate_query("")
    assert not is_safe, "Empty query should be blocked"
    print(f"✓ Empty query blocked: {reason}\n")


if __name__ == "__main__":
    print("=" * 60)
    print("🍜 SQLop - SQL Guardrails Test Suite")
    print("=" * 60)
    print()

    tests = [
        test_safe_select,
        test_dangerous_drop,
        test_dangerous_delete,
        test_dangerous_update,
        test_sql_injection_comment,
        test_sql_injection_union,
        test_complex_safe_query,
        test_add_limit_clause,
        test_table_whitelist,
        test_non_select_query,
        test_empty_query,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"❌ Test failed: {test.__name__}")
            print(f"   {e}\n")
        except Exception as e:
            failed += 1
            print(f"❌ Test error: {test.__name__}")
            print(f"   {e}")
            traceback.print_exc()
            print()

    print("=" * 60)
    print(f"✅ Tests passed: {passed}")
    print(f"❌ Tests failed: {failed}")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed} test(s) need attention")