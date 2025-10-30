"""Test DDL parser with sample schemas."""

from tools.ddl_parser import DDLParser


# Sample schema: Restaurant
RESTAURANT_SCHEMA = """
CREATE TABLE restaurants (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    cuisine VARCHAR(50),
    rating DECIMAL(3,2),
    address TEXT
);

CREATE TABLE menu_items (
    id INTEGER PRIMARY KEY,
    restaurant_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category VARCHAR(50),
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
);

CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20)
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    restaurant_id INTEGER NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total DECIMAL(10,2) NOT NULL,
    status VARCHAR(20),
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    menu_item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
);
"""

# Sample schema: Library
LIBRARY_SCHEMA = """
CREATE TABLE authors (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    birth_year INTEGER,
    country VARCHAR(50)
);

CREATE TABLE books (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    author_id INTEGER NOT NULL,
    isbn VARCHAR(13) UNIQUE,
    published_year INTEGER,
    genre VARCHAR(50),
    FOREIGN KEY (author_id) REFERENCES authors(id)
);

CREATE TABLE members (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    join_date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE loans (
    id INTEGER PRIMARY KEY,
    book_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    loan_date DATE NOT NULL,
    due_date DATE NOT NULL,
    return_date DATE,
    FOREIGN KEY (book_id) REFERENCES books(id),
    FOREIGN KEY (member_id) REFERENCES members(id)
);
"""


def test_restaurant_schema():
    """Test parsing restaurant schema."""
    print("\n=== Testing Restaurant Schema ===")
    parser = DDLParser()
    tables = parser.parse(RESTAURANT_SCHEMA)

    print(f"\nFound {len(tables)} tables:")
    for table_name, table in tables.items():
        print(f"\n{table_name}:")
        print(f"  Columns: {len(table.columns)}")
        for col in table.columns:
            flags = []
            if col.primary_key:
                flags.append("PK")
            if col.not_null:
                flags.append("NOT NULL")
            if col.unique:
                flags.append("UNIQUE")
            flags_str = f" ({', '.join(flags)})" if flags else ""
            print(f"    - {col.name}: {col.data_type}{flags_str}")

        if table.foreign_keys:
            print("  Foreign Keys:")
            for fk in table.foreign_keys:
                print(
                    f"    - {fk.column} -> {fk.referenced_table}.{fk.referenced_column}"
                )

    # Test generation order
    print("\n\nGeneration Order (respecting FK dependencies):")
    order = parser.get_generation_order()
    for i, table_name in enumerate(order, 1):
        print(f"  {i}. {table_name}")

    # Test dict export
    print("\n\nDict Export Sample (restaurants table):")
    dict_repr = parser.to_dict()
    if "restaurants" in dict_repr:
        print(f"  Columns: {len(dict_repr['restaurants']['columns'])}")
        print(f"  FKs: {len(dict_repr['restaurants']['foreign_keys'])}")

    return tables


def test_library_schema():
    """Test parsing library schema."""
    print("\n\n=== Testing Library Schema ===")
    parser = DDLParser()
    tables = parser.parse(LIBRARY_SCHEMA)

    print(f"\nFound {len(tables)} tables:")
    for table_name in tables:
        print(f"  - {table_name}")

    print("\nGeneration Order:")
    order = parser.get_generation_order()
    for i, table_name in enumerate(order, 1):
        print(f"  {i}. {table_name}")

    return tables


def test_constraints():
    """Test various constraint parsing."""
    print("\n\n=== Testing Constraint Parsing ===")

    test_schema = """
    CREATE TABLE test_table (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE,
        age INTEGER DEFAULT 18,
        parent_id INTEGER,
        FOREIGN KEY (parent_id) REFERENCES test_table(id)
    );
    """

    parser = DDLParser()
    tables = parser.parse(test_schema)

    table = tables["test_table"]
    print("\ntest_table columns:")
    for col in table.columns:
        print(
            f"  {col.name}: {col.data_type} (PK={col.primary_key}, NN={col.not_null}, "
            f"UQ={col.unique}, default={col.default})"
        )

    print("\nForeign keys:")
    for fk in table.foreign_keys:
        print(f"  {fk.column} -> {fk.referenced_table}.{fk.referenced_column}")


if __name__ == "__main__":
    print("DDL Parser Tests")
    print("=" * 60)

    try:
        test_restaurant_schema()
        test_library_schema()
        test_constraints()

        print("\n\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
