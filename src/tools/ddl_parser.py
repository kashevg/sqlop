"""DDL parser for extracting schema information from SQL CREATE TABLE statements.

Uses sqlparse to parse DDL and extract table structures, columns, constraints,
and relationships for synthetic data generation.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import sqlparse
from sqlparse.sql import Identifier, IdentifierList, Parenthesis, Token
from sqlparse.tokens import Keyword, Name, Punctuation


@dataclass
class Column:
    """Represents a database column with its properties."""

    name: str
    data_type: str
    not_null: bool = False
    primary_key: bool = False
    default: Optional[str] = None
    unique: bool = False


@dataclass
class ForeignKey:
    """Represents a foreign key relationship."""

    column: str
    referenced_table: str
    referenced_column: str


@dataclass
class Table:
    """Represents a database table with its columns and constraints."""

    name: str
    columns: List[Column] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: List[ForeignKey] = field(default_factory=list)


class DDLParser:
    """Parser for SQL DDL statements to extract schema information."""

    def __init__(self):
        """Initialize the DDL parser."""
        self.tables: Dict[str, Table] = {}

    def parse(self, ddl: str) -> Dict[str, Table]:
        """Parse DDL string and return dictionary of tables.

        Args:
            ddl: SQL DDL string containing CREATE TABLE statements

        Returns:
            Dictionary mapping table names to Table objects

        Example:
            >>> parser = DDLParser()
            >>> tables = parser.parse(ddl_content)
            >>> for table_name, table in tables.items():
            ...     print(f"{table_name}: {len(table.columns)} columns")
        """
        self.tables = {}

        # Parse SQL into statements
        statements = sqlparse.parse(ddl)

        for statement in statements:
            if statement.get_type() == "CREATE":
                self._parse_create_table(statement)

        # Link primary keys to columns
        for table in self.tables.values():
            for pk_col in table.primary_keys:
                for col in table.columns:
                    if col.name.lower() == pk_col.lower():
                        col.primary_key = True
                        break

        return self.tables

    def _parse_create_table(self, statement) -> None:
        """Parse a CREATE TABLE statement and extract table information.

        Args:
            statement: Parsed SQL statement from sqlparse
        """
        # Extract table name
        table_name = None
        for token in statement.tokens:
            if isinstance(token, Identifier):
                table_name = self._clean_identifier(token.get_name())
                break
            elif token.ttype is Name:
                table_name = self._clean_identifier(str(token))
                break

        if not table_name:
            return

        table = Table(name=table_name)

        # Find the parenthesis containing column definitions
        for token in statement.tokens:
            if isinstance(token, Parenthesis):
                self._parse_column_definitions(token, table)
                break

        self.tables[table_name] = table

    def _parse_column_definitions(self, parenthesis: Parenthesis, table: Table) -> None:
        """Parse column definitions and constraints inside CREATE TABLE.

        Args:
            parenthesis: Parenthesis token containing column definitions
            table: Table object to populate
        """
        # Split by commas at the top level
        definitions = self._split_by_comma(parenthesis)

        for definition in definitions:
            definition_str = definition.strip()

            if not definition_str:
                continue

            # Check if it's a constraint
            if self._is_constraint_definition(definition_str):
                self._parse_constraint(definition_str, table)
            else:
                # It's a column definition
                column = self._parse_column(definition_str)
                if column:
                    table.columns.append(column)

    def _split_by_comma(self, parenthesis: Parenthesis) -> List[str]:
        """Split parenthesis content by top-level commas.

        Args:
            parenthesis: Parenthesis token to split

        Returns:
            List of definition strings
        """
        content = str(parenthesis)[1:-1]  # Remove outer parentheses
        definitions = []
        current = []
        paren_depth = 0

        for char in content:
            if char == "(":
                paren_depth += 1
            elif char == ")":
                paren_depth -= 1
            elif char == "," and paren_depth == 0:
                definitions.append("".join(current))
                current = []
                continue

            current.append(char)

        if current:
            definitions.append("".join(current))

        return definitions

    def _is_constraint_definition(self, definition: str) -> bool:
        """Check if definition is a table constraint.

        Args:
            definition: Definition string to check

        Returns:
            True if it's a constraint, False if it's a column
        """
        definition_upper = definition.upper().strip()
        constraint_keywords = [
            "PRIMARY KEY",
            "FOREIGN KEY",
            "UNIQUE",
            "CHECK",
            "CONSTRAINT",
        ]
        return any(
            definition_upper.startswith(keyword) for keyword in constraint_keywords
        )

    def _parse_column(self, definition: str) -> Optional[Column]:
        """Parse a column definition string.

        Args:
            definition: Column definition string (e.g., "id INTEGER PRIMARY KEY")

        Returns:
            Column object or None if parsing fails
        """
        parts = definition.strip().split()

        if len(parts) < 2:
            return None

        col_name = self._clean_identifier(parts[0])
        data_type = parts[1].upper()

        # Parse inline constraints and modifiers
        definition_upper = definition.upper()
        not_null = "NOT NULL" in definition_upper
        primary_key = "PRIMARY KEY" in definition_upper
        unique = " UNIQUE" in definition_upper or definition_upper.endswith("UNIQUE")

        # Extract DEFAULT value if present
        default = None
        default_match = re.search(r"DEFAULT\s+([^\s,]+)", definition, re.IGNORECASE)
        if default_match:
            default = default_match.group(1).strip("'\"")

        return Column(
            name=col_name,
            data_type=data_type,
            not_null=not_null,
            primary_key=primary_key,
            default=default,
            unique=unique,
        )

    def _parse_constraint(self, definition: str, table: Table) -> None:
        """Parse a table-level constraint definition.

        Args:
            definition: Constraint definition string
            table: Table object to update
        """
        definition_upper = definition.upper().strip()

        # Primary key constraint
        if "PRIMARY KEY" in definition_upper:
            self._parse_primary_key_constraint(definition, table)

        # Foreign key constraint
        elif "FOREIGN KEY" in definition_upper:
            self._parse_foreign_key_constraint(definition, table)

    def _parse_primary_key_constraint(self, definition: str, table: Table) -> None:
        """Parse PRIMARY KEY constraint and extract column names.

        Args:
            definition: Constraint definition string
            table: Table object to update
        """
        # Extract column names from PRIMARY KEY (col1, col2, ...)
        match = re.search(r"PRIMARY\s+KEY\s*\(([^)]+)\)", definition, re.IGNORECASE)
        if match:
            columns_str = match.group(1)
            columns = [
                self._clean_identifier(col.strip()) for col in columns_str.split(",")
            ]
            table.primary_keys.extend(columns)

    def _parse_foreign_key_constraint(self, definition: str, table: Table) -> None:
        """Parse FOREIGN KEY constraint and extract relationship.

        Args:
            definition: Constraint definition string
            table: Table object to update
        """
        # FOREIGN KEY (column) REFERENCES table(column)
        match = re.search(
            r"FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+(\w+)\s*\(([^)]+)\)",
            definition,
            re.IGNORECASE,
        )

        if match:
            fk_column = self._clean_identifier(match.group(1).strip())
            ref_table = self._clean_identifier(match.group(2).strip())
            ref_column = self._clean_identifier(match.group(3).strip())

            foreign_key = ForeignKey(
                column=fk_column,
                referenced_table=ref_table,
                referenced_column=ref_column,
            )
            table.foreign_keys.append(foreign_key)

    def _clean_identifier(self, identifier: str) -> str:
        """Remove quotes and clean identifier name.

        Args:
            identifier: Raw identifier string

        Returns:
            Cleaned identifier
        """
        return identifier.strip().strip('"').strip("'").strip("`")

    def get_generation_order(self) -> List[str]:
        """Determine order to generate data based on foreign key dependencies.

        Returns:
            List of table names in order they should be generated

        Example:
            For schema with users → orders → order_items,
            returns: ['users', 'orders', 'order_items']
        """
        # Build dependency graph
        dependencies: Dict[str, List[str]] = {table_name: [] for table_name in self.tables}

        for table_name, table in self.tables.items():
            for fk in table.foreign_keys:
                if fk.referenced_table in self.tables:
                    dependencies[table_name].append(fk.referenced_table)

        # Topological sort
        visited = set()
        order = []

        def visit(table_name: str):
            if table_name in visited:
                return
            visited.add(table_name)

            for dep in dependencies.get(table_name, []):
                visit(dep)

            order.append(table_name)

        for table_name in self.tables:
            visit(table_name)

        return order

    def to_dict(self) -> Dict[str, dict]:
        """Convert parsed tables to dictionary format.

        Returns:
            Dictionary representation of all tables and their schemas

        Example:
            {
                "users": {
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": true, ...},
                        ...
                    ],
                    "foreign_keys": [...]
                }
            }
        """
        result = {}

        for table_name, table in self.tables.items():
            result[table_name] = {
                "columns": [
                    {
                        "name": col.name,
                        "type": col.data_type,
                        "not_null": col.not_null,
                        "primary_key": col.primary_key,
                        "default": col.default,
                        "unique": col.unique,
                    }
                    for col in table.columns
                ],
                "primary_keys": table.primary_keys,
                "foreign_keys": [
                    {
                        "column": fk.column,
                        "references": f"{fk.referenced_table}.{fk.referenced_column}",
                    }
                    for fk in table.foreign_keys
                ],
            }

        return result
