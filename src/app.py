"""Main Streamlit application for SQLOp.

TODO: Implementation Status (check STATUS.md for current progress)
--------------------------------------------------------------
PHASE 1 - Data Generation (✅ COMPLETE):
  - [x] Gemini client wrapper (src/utils/gemini_client.py)
  - [x] DDL parser (src/tools/ddl_parser.py)
  - [x] Data generator (src/tools/data_generator.py)
  - [x] Wire to show_data_generation_tab() - lines 182-418
  - Status: Ready to test with GCP authentication

PHASE 2 - Chat Interface (🚀 IN PROGRESS):
  - [x] NL2SQL converter (src/tools/nl2sql.py)
  - [x] SQL Guardrails (src/tools/sql_guardrails.py)
  - [ ] Visualizer (src/tools/visualizer.py) - Optional for later
  - [x] Wire to show_chat_tab() - lines 564-653

Current Status: Phase 1 MVP complete, awaiting GCP setup for testing.
See .claude/PLAN.md for detailed task breakdown and .claude/STATUS.md for current task.
"""

import logging
import time
import traceback
import uuid
import pandas as pd
import streamlit as st

from utils.config import AppConfig
from utils.db import DatabaseManager
from utils.gemini_client import GeminiClient
from utils.langfuse_instrumentation import initialize_langfuse, flush_langfuse
from utils.security_guard import SecurityGuard
from tools.ddl_parser import DDLParser
from tools.data_generator import DataGenerator
from tools.nl2sql import NL2SQLConverter
from tools.sql_guardrails import SQLGuardrails

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@st.cache_resource
def get_config() -> AppConfig:
    """Get application configuration (cached)."""
    return AppConfig.from_env()


@st.cache_resource
def setup_langfuse(_config: AppConfig) -> bool:
    """Initialize Langfuse tracing (cached singleton)."""
    return initialize_langfuse(_config)


@st.cache_resource
def get_db_manager(_config: AppConfig) -> DatabaseManager:
    """Get database manager (cached).

    Uses generator pattern to ensure connection pool is closed on cleanup.
    """
    db_manager = DatabaseManager(_config.database)
    db_manager.initialize()
    yield db_manager
    # Cleanup runs when cache is cleared or app exits
    db_manager.close()


@st.cache_resource
def get_gemini_client(_config: AppConfig, _langfuse_enabled: bool) -> GeminiClient:
    """Get Gemini client (cached)."""
    return GeminiClient(_config.gemini, enable_tracing=_langfuse_enabled)


@st.cache_resource
def get_security_guard(_langfuse_enabled: bool) -> SecurityGuard:
    """Get security guard (cached)."""
    return SecurityGuard(enable_tracing=_langfuse_enabled)


def check_database_connection(db_manager: DatabaseManager) -> tuple[bool, str]:
    """Check if database is connected and return status."""
    try:
        result = db_manager.execute_query("SELECT version()")
        version = result[0]["version"].split(",")[0]
        return True, version
    except Exception as e:
        return False, str(e)


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="SQLop - SQL Slop Generator",
        page_icon="🍜",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for better styling
    st.markdown(
        """
        <style>
        .main {
            background: linear-gradient(to bottom right, #fafafa 0%, #f0f0f5 100%);
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #2d3748 0%, #1a202c 100%);
        }
        [data-testid="stSidebar"] * {
            color: white !important;
        }
        .stButton button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .stButton button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        div[data-testid="stExpander"] {
            background: white;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .upload-section {
            background: white;
            padding: 20px;
            border-radius: 12px;
            border: 2px dashed #cbd5e0;
            text-align: center;
        }
        .stDataFrame {
            border-radius: 8px;
            overflow: hidden;
        }
        h1, h2, h3 {
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        /* Hide radio button circles */
        div[data-testid="stSidebar"] .stRadio > div {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        div[data-testid="stSidebar"] .stRadio label {
            background: rgba(255, 255, 255, 0.1);
            padding: 12px 16px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            border: 2px solid transparent;
        }
        div[data-testid="stSidebar"] .stRadio label:hover {
            background: rgba(255, 255, 255, 0.15);
            transform: translateX(4px);
        }
        div[data-testid="stSidebar"] .stRadio label[data-checked="true"] {
            background: rgba(99, 102, 241, 0.3);
            border-color: rgba(99, 102, 241, 0.5);
        }
        /* Hide the actual radio button */
        div[data-testid="stSidebar"] .stRadio input {
            display: none;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # Initialize config, Langfuse, and database
    try:
        config = get_config()
        langfuse_enabled = setup_langfuse(config)
        db_manager = get_db_manager(config)
        # Initialize shared resources (cached)
        get_gemini_client(config, langfuse_enabled)
        get_security_guard(langfuse_enabled)
    except Exception as e:
        st.error(f"⚠️ Configuration error: {e}")
        st.stop()

    # Initialize session ID for tracing
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    # Sidebar
    with st.sidebar:
        st.markdown("# 🍜 SQLop")
        st.caption("_Serving fresh SQL slop daily_")
        st.markdown("---")

        # Navigation with custom styling (tabs-like)
        page = st.radio(
            "Navigate",
            ["🍲 Slop Generator", "💬 Chat with Slop"],
            label_visibility="collapsed",
        )

        st.markdown("---")

        # Database status with styled box
        st.markdown("##### 🔌 Connection Status")
        db_connected, db_status = check_database_connection(db_manager)

        if db_connected:
            st.success(f"✅ {db_status[:50]}...")
        else:
            st.error(f"❌ {db_status[:50]}...")

        st.markdown("---")
        st.caption("Powered by Gemini 2.0 Flash 🚀")

    # Main content area
    if page == "🍲 Slop Generator":
        show_data_generation_tab(config, db_manager)
    else:
        show_chat_tab(config, db_manager)


def show_data_generation_tab(config: AppConfig, db_manager: DatabaseManager):
    """Display Data Generation tab."""

    # Initialize session state
    if "generated_data" not in st.session_state:
        st.session_state.generated_data = {}
    if "parsed_tables" not in st.session_state:
        st.session_state.parsed_tables = {}
    if "ddl_content" not in st.session_state:
        st.session_state.ddl_content = None

    # Hero section with slop theme
    st.markdown("# 🍲 SQL Slop Generator")
    st.markdown(
        "_Order up! Tell me what kind of data slop you're craving, and I'll cook it up fresh_"
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Prompt input with nice styling
    prompt = st.text_area(
        "🍴 Place your order",
        placeholder="E.g., 'Cook me up 1000 customer records with names, emails, and order history... make it spicy with some edge cases!'",
        height=120,
        help="Describe the data slop you want. Be specific about portions (row counts), ingredients (columns), and seasoning (constraints).",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Upload section with custom styling
    col1, col2 = st.columns([2, 3])

    with col1:
        st.markdown("### 📤 Upload Schema")
        uploaded_file = st.file_uploader(
            "Upload DDL Schema",
            type=["sql", "json", "ddl", "txt"],
            label_visibility="collapsed",
            help="Upload your database schema in SQL or JSON format",
        )
        st.caption("Supported: SQL, JSON")

    with col2:
        if uploaded_file:
            st.markdown("### 📝 Schema Preview")
            schema_content = uploaded_file.read().decode()
            st.session_state.ddl_content = schema_content
            st.code(
                schema_content[:500] + ("..." if len(schema_content) > 500 else ""),
                language="sql",
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Advanced Parameters in expandable section
    with st.expander("⚙️ Advanced Parameters", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            _temperature = st.slider(
                "🌡️ Temperature",
                min_value=0.0,
                max_value=2.0,
                value=float(config.gemini.temperature),
                step=0.1,
                help="Higher values = more creative, lower = more deterministic",
            )

        with col2:
            _max_tokens = st.number_input(
                "🎯 Max Tokens",
                min_value=100,
                max_value=100000,
                value=8000,
                step=1000,
                help="Maximum tokens for generation",
            )

        with col3:
            rows_per_table = st.number_input(
                "📊 Rows per Table",
                min_value=10,
                max_value=10000,
                value=10,
                step=100,
                help="Number of rows to generate per table",
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Generate button with nice styling
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        generate_btn = st.button(
            "👨‍🍳 Cook It Up!", type="primary", use_container_width=True
        )

    if generate_btn:
        if not st.session_state.ddl_content:
            st.error("⚠️ Please upload a DDL schema first!")
        else:
            try:
                with st.spinner("🍳 Cooking your data slop..."):
                    # Convert MySQL syntax to PostgreSQL if needed (before parsing)
                    from utils.ddl_converter import mysql_to_postgres, detect_mysql_syntax

                    ddl_to_parse = st.session_state.ddl_content
                    if detect_mysql_syntax(ddl_to_parse):
                        logger.info("MySQL syntax detected, converting to PostgreSQL before parsing")
                        ddl_to_parse = mysql_to_postgres(ddl_to_parse)
                        st.session_state.ddl_content = ddl_to_parse  # Update stored DDL

                    # Parse DDL
                    parser = DDLParser()
                    tables = parser.parse(ddl_to_parse)
                    st.session_state.parsed_tables = tables

                    if not tables:
                        st.error(
                            "❌ No tables found in DDL. Please check your schema format."
                        )
                    else:
                        st.success(
                            f"✅ Parsed {len(tables)} tables: {', '.join(tables.keys())}"
                        )

                        # Generate data
                        gemini_client = get_gemini_client(config)
                        generator = DataGenerator(gemini_client)

                        # Progress tracking
                        progress_bar = st.progress(0)
                        status_text = st.empty()

                        generation_order = parser.get_generation_order()
                        total_tables = len(generation_order)

                        for idx, table_name in enumerate(generation_order):
                            status_text.text(
                                f"🍳 Cooking {table_name}... ({idx+1}/{total_tables})"
                            )
                            table = tables[table_name]
                            df = generator._generate_table_data(
                                table,
                                int(rows_per_table),
                                prompt if prompt else "",
                                tables,
                            )
                            # Update both session state and generator's internal state
                            # Generator needs this to look up FK values for dependent tables
                            st.session_state.generated_data[table_name] = df
                            generator.generated_data[table_name] = df
                            progress_bar.progress((idx + 1) / total_tables)

                        status_text.empty()
                        progress_bar.empty()
                        st.success(
                            f"🍽️ Fresh slop ready! Generated {total_tables} tables with {int(rows_per_table)} rows each."
                        )
                        st.rerun()

            except Exception as e:
                logger.error(f"Data generation failed: {str(e)}", exc_info=True)
                st.error(f"❌ Kitchen mishap: {str(e)}")
                with st.expander("🔍 Error details"):
                    st.code(traceback.format_exc())

    st.markdown("---")

    # Data Preview section with modern design
    st.markdown("## 🍽️ Fresh from the Kitchen")

    if st.session_state.generated_data:
        # Show generated data
        available_tables = list(st.session_state.generated_data.keys())

        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"*{len(available_tables)} tables ready to serve*")
        with col3:
            selected_table = st.selectbox(
                "Table", available_tables, label_visibility="collapsed"
            )

        # Display selected table
        if selected_table and selected_table in st.session_state.generated_data:
            df = st.session_state.generated_data[selected_table]
            st.dataframe(
                df.head(100),  # Show first 100 rows
                use_container_width=True,
                hide_index=True,
            )

            st.caption(f"Showing first 100 of {len(df)} rows")

            st.markdown("<br>", unsafe_allow_html=True)

            # Quick edit section
            col1, col2 = st.columns([5, 1])
            with col1:
                edit_instructions = st.text_input(
                    "Edit",
                    placeholder=f"Refine {selected_table}? E.g., 'More diverse names', 'Higher price range'...",
                    label_visibility="collapsed",
                    key=f"edit_{selected_table}",
                )
            with col2:
                submit_edit = st.button(
                    "🔧 Remix", type="secondary", use_container_width=True
                )

            if submit_edit and edit_instructions:
                try:
                    with st.spinner(f"🍳 Remixing {selected_table}..."):
                        gemini_client = get_gemini_client(config)
                        generator = DataGenerator(gemini_client)
                        generator.generated_data = (
                            st.session_state.generated_data.copy()
                        )

                        # Regenerate just this table
                        df = generator.regenerate_table(
                            selected_table,
                            st.session_state.parsed_tables,
                            int(rows_per_table),
                            edit_instructions,
                        )
                        st.session_state.generated_data[selected_table] = df
                        st.success(f"✅ {selected_table} remixed!")
                        st.rerun()

                except Exception as e:
                    logger.error(
                        f"Table remix failed for {selected_table}: {str(e)}",
                        exc_info=True,
                    )
                    st.error(f"❌ Remix failed: {str(e)}")

            # Download section
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                st.download_button(
                    "📦 Take Out (CSV)",
                    data=df.to_csv(index=False),
                    file_name=f"{selected_table}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

        # Save Dataset section (for all tables)
        st.markdown("---")
        st.markdown("### 💾 Save Dataset to Database")

        col1, col2 = st.columns([3, 2])
        with col1:
            dataset_name = st.text_input(
                "Dataset name",
                value="",
                placeholder="e.g., restaurant_test_v1",
                help="Dataset will be stored in schema: slop_{name}",
                key="dataset_name_input",
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            save_btn = st.button(
                "💾 Save All Tables",
                type="primary",
                use_container_width=True,
                disabled=not dataset_name,
            )

        if save_btn and dataset_name:
            # Generate schema name
            schema_name = f"slop_{dataset_name}"

            try:
                with st.spinner(f"Saving dataset to schema '{schema_name}'..."):
                    # Create schema
                    db_manager.create_schema(schema_name)

                    # Get generation order
                    parser = DDLParser()
                    parser.tables = st.session_state.parsed_tables
                    generation_order = parser.get_generation_order()

                    # Create tables in schema
                    if st.session_state.ddl_content:
                        # Convert MySQL syntax to PostgreSQL if needed
                        from utils.ddl_converter import mysql_to_postgres, detect_mysql_syntax

                        ddl_to_execute = st.session_state.ddl_content
                        if detect_mysql_syntax(ddl_to_execute):
                            st.info("🔧 MySQL syntax detected - auto-converting to PostgreSQL...")
                            logger.info("MySQL syntax detected, converting to PostgreSQL")
                            ddl_to_execute = mysql_to_postgres(ddl_to_execute)

                        db_manager.execute_ddl_in_schema(
                            ddl_to_execute, schema_name
                        )

                    # Insert data for all tables
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    total_rows = 0
                    for idx, table_name in enumerate(generation_order):
                        status_text.text(
                            f"Saving {table_name}... ({idx+1}/{len(generation_order)})"
                        )
                        df = st.session_state.generated_data[table_name]
                        rows = db_manager.execute_insert_in_schema(
                            table_name, df.to_dict("records"), schema_name
                        )
                        total_rows += rows
                        progress_bar.progress((idx + 1) / len(generation_order))

                    status_text.empty()
                    progress_bar.empty()

                    st.success(
                        f"✅ Dataset saved! Schema: `{schema_name}` • {len(generation_order)} tables • {total_rows} rows"
                    )
                    st.info(
                        f"💬 Use this dataset in the 'Chat with Slop' tab by selecting `{schema_name}` from the dropdown"
                    )

            except Exception as e:
                logger.error(
                    f"Dataset save failed for schema {schema_name}: {str(e)}",
                    exc_info=True,
                )
                st.error(f"❌ Save failed: {str(e)}")
                with st.expander("🔍 Error details"):
                    st.code(traceback.format_exc())

    else:
        # No data generated yet - show placeholder
        st.info(
            "🍽️ No fresh slop yet! Upload a schema and hit 'Cook It Up!' to get started."
        )


def show_chat_tab(config: AppConfig, db_manager: DatabaseManager):
    """Display chat interface for natural language querying."""

    # Initialize session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "result_limit" not in st.session_state:
        st.session_state.result_limit = 1000

    st.markdown("# 💬 Chat with Your Slop")
    st.markdown("_Ask me anything about your data - I speak both English and SQL!_")

    st.markdown("<br>", unsafe_allow_html=True)

    # Dataset selector + Result limit slider
    try:
        schemas = db_manager.list_schemas(prefix="slop_")
        if schemas:
            schema_names = [s["schema_name"] for s in schemas]

            # Initialize session state for selected schema
            if "selected_schema" not in st.session_state:
                st.session_state.selected_schema = (
                    schema_names[0] if schema_names else None
                )

            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                selected_schema = st.selectbox(
                    "🗄️ Dataset",
                    schema_names,
                    index=(
                        schema_names.index(st.session_state.selected_schema)
                        if st.session_state.selected_schema in schema_names
                        else 0
                    ),
                    help="Select a saved dataset to query",
                )
                st.session_state.selected_schema = selected_schema

            with col2:
                if selected_schema:
                    # Show dataset info
                    schema_info = next(
                        (s for s in schemas if s["schema_name"] == selected_schema),
                        None,
                    )
                    if schema_info:
                        st.caption(f"📊 {schema_info['table_count']} tables")

            with col3:
                result_limit = st.slider(
                    "Max rows",
                    min_value=10,
                    max_value=5000,
                    value=st.session_state.result_limit,
                    step=10,
                    help="Maximum number of rows to return",
                )
                st.session_state.result_limit = result_limit

            st.markdown("---")
        else:
            st.warning(
                "⚠️ No saved datasets found. Generate and save data in the 'Slop Generator' tab first!"
            )
            st.markdown("---")
            return
    except Exception as e:
        logger.error(f"Failed to load dataset list: {str(e)}", exc_info=True)
        st.error(f"❌ Failed to load datasets: {str(e)}")
        st.markdown("---")
        return

    # Display chat history
    st.markdown("### 💭 Conversation")

    if st.session_state.chat_history:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f"**🧑 You:** {message['content']}")
            elif message["role"] == "assistant":
                st.markdown(f"**🤖 SQLop:** {message.get('explanation', '')}")

                # Show SQL query
                if "sql_query" in message:
                    st.code(message["sql_query"], language="sql")

                # Show results
                if "results" in message and message["results"] is not None:
                    df = message["results"]
                    row_count = len(df)

                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.caption(f"📊 {row_count} rows • Query took {message.get('execution_time', 0):.2f}s")

                    # Truncation warning
                    if "was_truncated" in message and message["was_truncated"]:
                        st.warning(f"⚠️ Results limited to {st.session_state.result_limit} rows")

                # Show error if any
                if "error" in message:
                    st.error(f"❌ {message['error']}")

            st.markdown("---")
    else:
        st.info("👋 Hey! Ready to dig through your data slop? Ask away!")

        # Example questions
        with st.expander("💡 Try asking me...", expanded=True):
            st.markdown(
                """
            - "Show me the top 10 customers by revenue"
            - "What's the average order value?"
            - "Which products have the most sales?"
            - "Count the number of orders per customer"
            """
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Chat input at bottom
    col1, col2 = st.columns([6, 1])
    with col1:
        user_question = st.text_input(
            "Ask a question",
            placeholder="What's cooking? e.g., 'Show me the top 5 most popular items'",
            label_visibility="collapsed",
            key="chat_input",
        )
    with col2:
        send_btn = st.button("🍴 Serve", type="primary", use_container_width=True)

    # Process user question
    if send_btn and user_question:
        selected_schema = st.session_state.selected_schema

        if not selected_schema:
            st.error("⚠️ Please select a dataset first!")
            return

        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_question
        })

        try:
            with st.spinner("🍳 Cooking up your query..."):
                # Initialize components
                gemini_client = get_gemini_client(config, setup_langfuse(config))
                nl2sql = NL2SQLConverter(gemini_client, db_manager)
                guardrails = SQLGuardrails()

                # Convert question to SQL with conversation history
                nl2sql_result = nl2sql.convert_to_sql(
                    question=user_question,
                    schema_name=selected_schema,
                    conversation_history=st.session_state.chat_history[:-1]  # Exclude current question
                )

                sql_query = nl2sql_result["sql_query"]
                explanation = nl2sql_result.get("explanation", "Here are your results:")
                confidence = nl2sql_result.get("confidence", 0.0)

                # Validate SQL with guardrails
                is_safe, reason = guardrails.validate_query(sql_query)

                if not is_safe:
                    # Query blocked by guardrails
                    logger.warning(f"Query blocked by guardrails: {reason}")
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": explanation,
                        "sql_query": sql_query,
                        "error": f"Security check failed: {reason}",
                        "results": None
                    })
                    st.rerun()
                    return

                # Add LIMIT clause
                sql_query = guardrails.add_limit_clause(
                    sql_query,
                    max_rows=st.session_state.result_limit
                )

                # Execute query
                start_time = time.time()
                results = db_manager.execute_query_in_schema(sql_query, selected_schema)
                execution_time = time.time() - start_time

                # Convert to DataFrame
                df = pd.DataFrame(results) if results else pd.DataFrame()

                # Check if results were truncated
                was_truncated = len(df) >= st.session_state.result_limit

                # Add assistant response to history
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": explanation,
                    "sql_query": sql_query,
                    "results": df,
                    "row_count": len(df),
                    "execution_time": execution_time,
                    "confidence": confidence,
                    "was_truncated": was_truncated
                })

                logger.info(f"Query executed successfully: {len(df)} rows in {execution_time:.2f}s")
                st.rerun()

        except ValueError as e:
            # NL2SQL or validation error
            logger.error(f"Query generation failed: {str(e)}", exc_info=True)
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "Sorry, I couldn't understand that question.",
                "error": str(e),
                "results": None
            })
            st.rerun()

        except Exception as e:
            # Database or other error
            logger.error(f"Query execution failed: {str(e)}", exc_info=True)
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "Oops! Something went wrong while executing your query.",
                "sql_query": sql_query if 'sql_query' in locals() else None,
                "error": str(e),
                "results": None
            })
            st.rerun()


if __name__ == "__main__":
    main()
