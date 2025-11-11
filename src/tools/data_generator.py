"""Synthetic data generator using Gemini LLM.

Generates realistic test data for database schemas while respecting
foreign key relationships and constraints.
"""

import json
from typing import Any, Dict, Generator, List, Optional

import pandas as pd
from langfuse.decorators import observe

from tools.ddl_parser import DDLParser, Table
from utils.gemini_client import GeminiClient


class DataGenerator:
    """Generate synthetic data for database schemas using LLM."""

    def __init__(self, gemini_client: GeminiClient):
        """Initialize data generator.

        Args:
            gemini_client: Configured Gemini client for LLM calls
        """
        self.gemini = gemini_client
        self.generated_data: Dict[str, pd.DataFrame] = {}

    @observe()
    def generate_all_tables(
        self,
        tables: Dict[str, Table],
        rows_per_table: int = 100,
        instructions: str = "",
        stream: bool = False,
    ) -> (
        Dict[str, pd.DataFrame]
        | Generator[tuple[str, str], None, Dict[str, pd.DataFrame]]
    ):
        """Generate data for all tables in correct dependency order.

        Args:
            tables: Dictionary of Table objects from DDL parser
            rows_per_table: Number of rows to generate per table
            instructions: User instructions for data generation (e.g., "diverse names, realistic prices")
            stream: If True, yields progress updates during generation

        Returns:
            Dictionary mapping table names to DataFrames (or generator if stream=True)

        Example:
            >>> generator = DataGenerator(gemini_client)
            >>> data = generator.generate_all_tables(tables, rows_per_table=500)
            >>> data['users'].head()
        """
        # Get correct generation order
        parser = DDLParser()
        parser.tables = tables
        generation_order = parser.get_generation_order()

        self.generated_data = {}

        if stream:
            return self._generate_streaming(
                tables, generation_order, rows_per_table, instructions
            )
        else:
            for table_name in generation_order:
                table = tables[table_name]
                df = self._generate_table_data(
                    table, rows_per_table, instructions, tables
                )
                self.generated_data[table_name] = df

            return self.generated_data

    def _generate_streaming(
        self,
        tables: Dict[str, Table],
        generation_order: List[str],
        rows_per_table: int,
        instructions: str,
    ) -> Generator[tuple[str, str], None, Dict[str, pd.DataFrame]]:
        """Generate data with streaming progress updates.

        Args:
            tables: Dictionary of Table objects
            generation_order: Order to generate tables
            rows_per_table: Rows per table
            instructions: User instructions

        Yields:
            Tuples of (table_name, status_message) during generation

        Returns:
            Final dictionary of generated DataFrames
        """
        for table_name in generation_order:
            yield (table_name, f"Generating {rows_per_table} rows...")

            table = tables[table_name]
            df = self._generate_table_data(table, rows_per_table, instructions, tables)
            self.generated_data[table_name] = df

            yield (table_name, f"✓ Generated {len(df)} rows")

        return self.generated_data

    def regenerate_table(
        self,
        table_name: str,
        tables: Dict[str, Table],
        rows: int,
        instructions: str = "",
    ) -> pd.DataFrame:
        """Regenerate data for a single table with new instructions.

        Preserves previously generated data for other tables to maintain
        foreign key relationships.

        Args:
            table_name: Name of table to regenerate
            tables: All table schemas
            rows: Number of rows to generate
            instructions: New instructions for this table

        Returns:
            DataFrame with regenerated data

        Example:
            >>> df = generator.regenerate_table(
            ...     'orders',
            ...     tables,
            ...     rows=1000,
            ...     instructions="More recent order dates"
            ... )
        """
        if table_name not in tables:
            raise ValueError(f"Table '{table_name}' not found in schema")

        table = tables[table_name]
        df = self._generate_table_data(table, rows, instructions, tables)
        self.generated_data[table_name] = df

        return df

    def _generate_table_data(
        self,
        table: Table,
        rows: int,
        instructions: str,
        all_tables: Dict[str, Table],
    ) -> pd.DataFrame:
        """Generate data for a single table.

        Uses batching to avoid hitting token limits for large datasets.

        Args:
            table: Table object to generate data for
            rows: Number of rows to generate
            instructions: User instructions
            all_tables: All tables in schema (for FK references)

        Returns:
            DataFrame with generated data
        """
        # Batch size to avoid hitting max_output_tokens (8192)
        # Conservative estimate: ~200-300 tokens per row for complex schemas
        # Safe batch size: 20 rows (~4000-6000 tokens with overhead, leaving buffer)
        BATCH_SIZE = 20

        if rows <= BATCH_SIZE:
            # Single batch - generate all at once
            return self._generate_batch(table, rows, instructions, all_tables)
        else:
            # Multiple batches - split and concatenate
            print(
                f"Batching {rows} rows into chunks of {BATCH_SIZE} for {table.name}..."
            )
            batches = []
            remaining = rows

            while remaining > 0:
                batch_size = min(remaining, BATCH_SIZE)
                print(f"  Generating batch of {batch_size} rows...")

                batch_df = self._generate_batch(
                    table, batch_size, instructions, all_tables
                )
                batches.append(batch_df)

                remaining -= batch_size

            # Concatenate all batches
            df = pd.concat(batches, ignore_index=True)

            # Renumber primary keys if present to be sequential
            for col in table.columns:
                if col.primary_key and col.name in df.columns:
                    df[col.name] = range(1, len(df) + 1)

            print(f"  Completed: {len(df)} total rows for {table.name}")
            return df

    def _generate_batch(
        self,
        table: Table,
        rows: int,
        instructions: str,
        all_tables: Dict[str, Table],
    ) -> pd.DataFrame:
        """Generate a single batch of data.

        Args:
            table: Table object to generate data for
            rows: Number of rows to generate in this batch
            instructions: User instructions
            all_tables: All tables in schema (for FK references)

        Returns:
            DataFrame with generated data
        """
        # Build prompt for LLM
        prompt = self._build_generation_prompt(table, rows, instructions, all_tables)

        # Build JSON schema for structured output
        schema = self._build_json_schema(table)

        # Generate data using Gemini with schema enforcement
        response = self.gemini.generate_json(prompt, schema, temperature=0.9)

        # Parse response into DataFrame
        df = self._parse_generation_response(response, table)

        return df

    def _build_json_schema(self, table: Table) -> Dict[str, Any]:
        """Build JSON schema for table data generation.

        Args:
            table: Table object with column definitions

        Returns:
            OpenAPI 3.0 schema dict for array of row objects

        Example output:
            {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "id": {"type": "INTEGER"},
                        "name": {"type": "STRING"}
                    },
                    "required": ["id", "name"]
                }
            }
        """
        properties = {}
        required = []

        for col in table.columns:
            # Map SQL types to Gemini schema types
            schema_type = self._sql_type_to_schema_type(col.data_type)
            properties[col.name] = {"type": schema_type}

            # Add to required if NOT NULL
            if col.not_null or col.primary_key:
                required.append(col.name)

        return {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": properties,
                "required": required,
            },
        }

    def _sql_type_to_schema_type(self, sql_type: str) -> str:
        """Map SQL data type to Gemini schema type.

        Args:
            sql_type: SQL data type (e.g., 'VARCHAR', 'INTEGER')

        Returns:
            Gemini schema type ('STRING', 'INTEGER', 'NUMBER', 'BOOLEAN')
        """
        sql_type_upper = sql_type.upper()

        # Integer types
        if any(
            t in sql_type_upper
            for t in ["INT", "SERIAL", "BIGINT", "SMALLINT", "TINYINT"]
        ):
            return "INTEGER"

        # Numeric/decimal types
        if any(
            t in sql_type_upper
            for t in ["DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL", "MONEY"]
        ):
            return "NUMBER"

        # Boolean types
        if "BOOL" in sql_type_upper:
            return "BOOLEAN"

        # Everything else (VARCHAR, TEXT, DATE, TIMESTAMP, etc.) as STRING
        return "STRING"

    def _build_generation_prompt(
        self,
        table: Table,
        rows: int,
        instructions: str,
        all_tables: Dict[str, Table],
    ) -> str:
        """Build prompt for LLM to generate table data.

        Args:
            table: Table to generate data for
            rows: Number of rows
            instructions: User instructions
            all_tables: All tables for FK context

        Returns:
            Formatted prompt string
        """
        # Build column descriptions
        column_specs = []
        for col in table.columns:
            spec = f"- {col.name} ({col.data_type})"

            constraints = []
            if col.primary_key:
                constraints.append("PRIMARY KEY")
            if col.not_null:
                constraints.append("NOT NULL")
            if col.unique:
                constraints.append("UNIQUE")
            if col.default:
                constraints.append(f"DEFAULT {col.default}")

            if constraints:
                spec += f" [{', '.join(constraints)}]"

            column_specs.append(spec)

        # Build foreign key information with available values
        fk_specs = []
        for fk in table.foreign_keys:
            ref_table = fk.referenced_table
            ref_col = fk.referenced_column

            # Get available values if we've already generated that table
            if ref_table in self.generated_data:
                available_values = (
                    self.generated_data[ref_table][ref_col].unique().tolist()
                )
                # Limit to first 50 values for prompt brevity
                if len(available_values) > 50:
                    available_values = available_values[:50]
                    fk_specs.append(
                        f"- {fk.column} must reference {ref_table}.{ref_col}\n"
                        f"  Available values: {available_values} (and more...)"
                    )
                else:
                    fk_specs.append(
                        f"- {fk.column} must reference {ref_table}.{ref_col}\n"
                        f"  Available values: {available_values}"
                    )
            else:
                fk_specs.append(f"- {fk.column} must reference {ref_table}.{ref_col}")

        # Build full prompt
        prompt_parts = [
            "You are generating realistic synthetic test data for a database table.",
            f"\n**Table**: {table.name}",
            f"**Rows to generate**: {rows}",
            "\n**Schema**:",
            *column_specs,
        ]

        if fk_specs:
            prompt_parts.append("\n**Foreign Key Constraints**:")
            prompt_parts.extend(fk_specs)

        if instructions:
            prompt_parts.append(f"\n**Additional Instructions**: {instructions}")

        prompt_parts.extend(
            [
                "\n**Requirements**:",
                "- Generate exactly the requested number of rows",
                "- All foreign key values MUST exist in the referenced tables",
                "- Primary keys must be unique (use sequential integers starting from 1)",
                "- NOT NULL columns must have values",
                "- UNIQUE columns must have unique values",
                "- Make data realistic, diverse, and varied",
                "- Use appropriate data formats for each type",
                "- For TIMESTAMP/DATE fields, use ISO format (YYYY-MM-DD HH:MM:SS or YYYY-MM-DD)",
                "",
                "**Output Format**:",
                "Return a JSON array of objects, where each object represents one row.",
                "Use column names as keys. Example:",
                json.dumps(
                    [
                        {
                            col.name: f"<{col.data_type.lower()} value>"
                            for col in table.columns[:3]
                        }
                    ],
                    indent=2,
                ),
                "",
                f"Generate {rows} rows now:",
            ]
        )

        return "\n".join(prompt_parts)

    def _parse_generation_response(
        self, response: Dict[str, Any], table: Table
    ) -> pd.DataFrame:
        """Parse LLM JSON response into DataFrame.

        Args:
            response: JSON response from LLM
            table: Table schema

        Returns:
            DataFrame with generated data

        Raises:
            ValueError: If response format is invalid
        """
        # Response should be an array of row objects
        if isinstance(response, list):
            data = response
        elif isinstance(response, dict) and table.name in response:
            data = response[table.name]
        elif isinstance(response, dict) and "data" in response:
            data = response["data"]
        else:
            raise ValueError(
                f"Unexpected response format. Expected list or dict with '{table.name}' key."
            )

        if not isinstance(data, list):
            raise ValueError(f"Expected list of rows, got {type(data)}")

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Validate columns match schema
        expected_cols = {col.name for col in table.columns}
        actual_cols = set(df.columns)

        missing_cols = expected_cols - actual_cols
        if missing_cols:
            print(
                f"Warning: Missing columns in generated data: {missing_cols}. Adding with NULLs."
            )
            for col in missing_cols:
                df[col] = None

        # Reorder columns to match schema
        df = df[[col.name for col in table.columns]]

        return df

    def get_data(self, table_name: str) -> Optional[pd.DataFrame]:
        """Get generated data for a specific table.

        Args:
            table_name: Name of table

        Returns:
            DataFrame or None if not generated yet
        """
        return self.generated_data.get(table_name)

    def get_all_data(self) -> Dict[str, pd.DataFrame]:
        """Get all generated data.

        Returns:
            Dictionary mapping table names to DataFrames
        """
        return self.generated_data.copy()

    def export_to_csv(self, table_name: str, file_path: str) -> None:
        """Export table data to CSV file.

        Args:
            table_name: Name of table to export
            file_path: Path to save CSV file

        Raises:
            ValueError: If table not generated yet
        """
        if table_name not in self.generated_data:
            raise ValueError(f"No data generated for table '{table_name}'")

        df = self.generated_data[table_name]
        df.to_csv(file_path, index=False)

    def export_all_to_csv(self, output_dir: str) -> List[str]:
        """Export all tables to separate CSV files.

        Args:
            output_dir: Directory to save CSV files

        Returns:
            List of file paths created
        """
        import os

        os.makedirs(output_dir, exist_ok=True)

        file_paths = []
        for table_name, df in self.generated_data.items():
            file_path = os.path.join(output_dir, f"{table_name}.csv")
            df.to_csv(file_path, index=False)
            file_paths.append(file_path)

        return file_paths
