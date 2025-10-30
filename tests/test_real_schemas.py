"""Test DDL parser with real course material schemas."""

from tools.ddl_parser import DDLParser


def test_schema(schema_name: str, file_path: str):
    """Test parsing a schema file."""
    print(f"\n{'='*70}")
    print(f"Testing: {schema_name}")
    print("=" * 70)

    with open(file_path, "r") as f:
        ddl_content = f.read()

    parser = DDLParser()
    try:
        tables = parser.parse(ddl_content)

        print("\n✅ Parsed successfully!")
        print(f"Found {len(tables)} tables: {', '.join(tables.keys())}")

        # Show generation order
        order = parser.get_generation_order()
        print("\nGeneration order (respecting FK dependencies):")
        for i, table_name in enumerate(order, 1):
            table = tables[table_name]
            fk_info = (
                f" (depends on: {', '.join([fk.referenced_table for fk in table.foreign_keys])})"
                if table.foreign_keys
                else ""
            )
            print(f"  {i}. {table_name}{fk_info}")

        # Show detailed info for first table
        if tables:
            first_table = tables[order[0]]
            print(f"\nFirst table details: {first_table.name}")
            print(f"  Columns: {len(first_table.columns)}")
            for col in first_table.columns[:5]:  # Show first 5 columns
                flags = []
                if col.primary_key:
                    flags.append("PK")
                if col.not_null:
                    flags.append("NOT NULL")
                if col.unique:
                    flags.append("UNIQUE")
                flags_str = f" [{', '.join(flags)}]" if flags else ""
                print(f"    - {col.name}: {col.data_type}{flags_str}")
            if len(first_table.columns) > 5:
                print(f"    ... and {len(first_table.columns) - 5} more columns")

        return True

    except Exception as e:
        print(f"\n❌ Failed to parse: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    schemas = [
        ("Company Employee Schema", "tests/fixtures/company_employee_schema.ddl"),
        ("Library Management Schema", "tests/fixtures/library_mgm_schema.ddl"),
        ("Restaurant Schema", "tests/fixtures/restrurants_schema.ddl"),
    ]

    print("🧪 Testing DDL Parser with Real Course Material Schemas")
    print("=" * 70)

    results = []
    for name, path in schemas:
        success = test_schema(name, path)
        results.append((name, success))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")

    all_passed = all(success for _, success in results)
    if all_passed:
        print("\n🎉 All schemas parsed successfully!")
    else:
        print("\n⚠️  Some schemas failed to parse")
