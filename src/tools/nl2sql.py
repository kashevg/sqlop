"""Natural language to SQL converter using Gemini LLM.

Converts user questions in natural language to PostgreSQL SELECT queries.
"""

import logging
from typing import Any, Dict, List, Optional

from langfuse.decorators import langfuse_context, observe

from utils.db import DatabaseManager
from utils.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class NL2SQLConverter:
    """Converts natural language questions to SQL queries.

    Uses Gemini LLM with structured output to generate accurate PostgreSQL
    SELECT queries based on database schema context and conversation history.
    """

    # JSON schema for structured output
    RESPONSE_SCHEMA = {
        "type": "OBJECT",
        "properties": {
            "sql_query": {
                "type": "STRING",
                "description": "The PostgreSQL SELECT query to answer the question"
            },
            "explanation": {
                "type": "STRING",
                "description": "Brief explanation of what the query does and why"
            },
            "tables_used": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "List of table names used in the query"
            },
            "confidence": {
                "type": "NUMBER",
                "description": "Confidence score 0.0-1.0 for the query accuracy"
            }
        },
        "required": ["sql_query", "explanation", "tables_used"]
    }

    def __init__(
        self,
        gemini_client: GeminiClient,
        db_manager: DatabaseManager,
        enable_tracing: bool = True
    ):
        """Initialize NL2SQL converter.

        Args:
            gemini_client: Gemini client for LLM calls
            db_manager: Database manager for schema introspection
            enable_tracing: Enable Langfuse tracing
        """
        self.gemini = gemini_client
        self.db_manager = db_manager
        self.enable_tracing = enable_tracing
        logger.info("NL2SQLConverter initialized")

    @observe()
    def convert_to_sql(
        self,
        question: str,
        schema_name: str = "public",
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Convert natural language question to SQL query.

        Args:
            question: Natural language question
            schema_name: Database schema to query (default: "public")
            conversation_history: Previous conversation messages for context

        Returns:
            Dict with keys:
                - sql_query: PostgreSQL SELECT query
                - explanation: What the query does
                - tables_used: List of table names
                - confidence: 0.0-1.0 confidence score (optional)

        Raises:
            ValueError: If question is empty or schema doesn't exist
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        logger.info(f"Converting question to SQL: '{question[:50]}...'")

        # Track in Langfuse
        if self.enable_tracing:
            langfuse_context.update_current_observation(
                metadata={
                    "question": question,
                    "schema_name": schema_name,
                    "has_conversation_history": conversation_history is not None,
                    "history_length": len(conversation_history) if conversation_history else 0,
                }
            )

        try:
            # Step 1: Build schema context
            schema_context = self._build_schema_context(schema_name)

            if not schema_context:
                raise ValueError(f"Schema '{schema_name}' is empty or doesn't exist")

            # Step 2: Build conversion prompt
            prompt = self._build_conversion_prompt(
                question,
                schema_context,
                conversation_history
            )

            # Step 3: Generate SQL using Gemini with structured output
            logger.info("Calling Gemini to generate SQL...")
            result = self.gemini.generate_json(
                prompt=prompt,
                response_schema=self.RESPONSE_SCHEMA,
                temperature=0.3  # Lower temperature for more deterministic SQL
            )

            # Validate result
            if not result or "sql_query" not in result:
                raise ValueError("Gemini returned invalid response format")

            logger.info(f"SQL generated successfully: {result['sql_query'][:100]}...")

            # Track successful conversion
            if self.enable_tracing:
                langfuse_context.update_current_observation(
                    metadata={
                        "sql_query": result["sql_query"],
                        "tables_used": result.get("tables_used", []),
                        "confidence": result.get("confidence", 0.0),
                    }
                )

            return result

        except Exception as e:
            error_msg = f"Error converting question to SQL: {e}"
            logger.error(error_msg, exc_info=True)
            if self.enable_tracing:
                langfuse_context.update_current_observation(
                    metadata={"error": str(e)}
                )
            raise

    def _build_schema_context(self, schema_name: str) -> str:
        """Build comprehensive schema context for the prompt.

        Args:
            schema_name: Database schema name

        Returns:
            Formatted string with schema information
        """
        try:
            # Get all tables in schema
            tables = self.db_manager.get_schema_tables(schema_name)

            if not tables:
                logger.warning(f"No tables found in schema '{schema_name}'")
                return ""

            schema_parts = []
            schema_parts.append(f"# Database Schema: {schema_name}\n")

            # Get schema details for each table
            for table in tables:
                schema_parts.append(f"\n## Table: {table}")

                # Get columns
                columns = self.db_manager.get_table_schema(table, schema_name)

                if columns:
                    schema_parts.append("Columns:")
                    for col in columns:
                        nullable = "" if col['is_nullable'] == 'YES' else " NOT NULL"
                        default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                        schema_parts.append(
                            f"  - {col['column_name']}: {col['data_type']}{nullable}{default}"
                        )

            # Get foreign key relationships
            foreign_keys = self.db_manager.get_foreign_keys(schema_name)

            if foreign_keys:
                schema_parts.append("\n## Foreign Key Relationships:")
                for fk in foreign_keys:
                    schema_parts.append(
                        f"  - {fk['table_name']}.{fk['column_name']} → "
                        f"{fk['foreign_table_name']}.{fk['foreign_column_name']}"
                    )

            return "\n".join(schema_parts)

        except Exception as e:
            logger.error(f"Error building schema context: {e}", exc_info=True)
            return ""

    def _build_conversion_prompt(
        self,
        question: str,
        schema_context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Build the prompt for NL2SQL conversion.

        Args:
            question: User's natural language question
            schema_context: Formatted database schema
            conversation_history: Previous conversation for context

        Returns:
            Complete prompt for Gemini
        """
        prompt_parts = []

        # System instructions
        prompt_parts.extend([
            "You are an expert PostgreSQL query generator.",
            "Your task is to convert natural language questions into accurate SQL SELECT queries.",
            "",
            "**Instructions:**",
            "- Generate ONLY SELECT queries (no INSERT, UPDATE, DELETE, DROP, etc.)",
            "- ALWAYS use table aliases (e.g., FROM restaurants r, JOIN reviews rv)",
            "- ALWAYS qualify ALL column references with table aliases (e.g., r.name, rv.rating)",
            "- This prevents ambiguous column errors when multiple tables have same column names",
            "- Use proper JOIN syntax when querying multiple tables",
            "- Use appropriate aggregation functions (COUNT, SUM, AVG, etc.) when needed",
            "- Include proper WHERE clauses for filtering",
            "- Use GROUP BY when using aggregation functions with non-aggregated columns",
            "- Use ORDER BY to sort results when asked for 'top', 'best', 'most', etc.",
            "- Use LIMIT to restrict results when appropriate",
            "- Always use lowercase table and column names",
            "- Follow PostgreSQL syntax and functions",
            "",
        ])

        # Add schema context
        prompt_parts.append(schema_context)
        prompt_parts.append("")

        # Add conversation history if provided
        if conversation_history and len(conversation_history) > 0:
            prompt_parts.append("## Previous Conversation:")
            for msg in conversation_history[-3:]:  # Last 3 messages for context
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role == "user":
                    prompt_parts.append(f"User: {content}")
                elif role == "assistant":
                    sql = msg.get("sql_query", "")
                    if sql:
                        prompt_parts.append(f"Assistant: Generated SQL: {sql}")
            prompt_parts.append("")

        # Add current question
        prompt_parts.extend([
            "## Current Question:",
            f"User: {question}",
            "",
            "## Your Response:",
            "Generate a SQL query to answer this question.",
            "Provide:",
            "1. The SQL query (PostgreSQL syntax)",
            "2. A brief explanation of what the query does",
            "3. List of tables used",
            "4. Your confidence level (0.0-1.0)",
        ])

        return "\n".join(prompt_parts)