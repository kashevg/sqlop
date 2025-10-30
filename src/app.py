"""Main Streamlit application for SQLOp.

TODO: Implementation Status (check STATUS.md for current progress)
--------------------------------------------------------------
PHASE 1 - Data Generation (✅ COMPLETE):
  - [x] Gemini client wrapper (src/utils/gemini_client.py)
  - [x] DDL parser (src/tools/ddl_parser.py)
  - [x] Data generator (src/tools/data_generator.py)
  - [x] Wire to show_data_generation_tab() - lines 182-418
  - Status: Ready to test with GCP authentication

PHASE 2 - Chat Interface (Not Implemented Yet):
  - [ ] NL2SQL converter (src/tools/nl2sql.py)
  - [ ] Guardrails (src/tools/guardrails.py)
  - [ ] Visualizer (src/tools/visualizer.py)
  - [ ] Wire to show_chat_tab() - lines 421-460

Current Status: Phase 1 MVP complete, awaiting GCP setup for testing.
See .claude/PLAN.md for detailed task breakdown and .claude/STATUS.md for current task.
"""

import logging
import traceback
import streamlit as st
import pandas as pd

from utils.config import AppConfig
from utils.db import DatabaseManager
from utils.gemini_client import GeminiClient
from tools.ddl_parser import DDLParser
from tools.data_generator import DataGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@st.cache_resource
def get_config() -> AppConfig:
    """Get application configuration (cached)."""
    return AppConfig.from_env()


@st.cache_resource
def get_db_manager(_config: AppConfig) -> DatabaseManager:
    """Get database manager (cached)."""
    db_manager = DatabaseManager(_config.database)
    db_manager.initialize()
    return db_manager


@st.cache_resource
def get_gemini_client(_config: AppConfig) -> GeminiClient:
    """Get Gemini client (cached)."""
    return GeminiClient(_config.gemini)


def check_database_connection(db_manager: DatabaseManager) -> tuple[bool, str]:
    """Check if database is connected and return status."""
    try:
        result = db_manager.execute_query("SELECT version()")
        version = result[0]['version'].split(',')[0]
        return True, version
    except Exception as e:
        return False, str(e)


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="SQLop - SQL Slop Generator",
        page_icon="🍜",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for better styling
    st.markdown("""
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
    """, unsafe_allow_html=True)

    # Initialize config and database
    try:
        config = get_config()
        db_manager = get_db_manager(config)
    except Exception as e:
        st.error(f"⚠️ Configuration error: {e}")
        st.stop()

    # Sidebar
    with st.sidebar:
        st.markdown("# 🍜 SQLop")
        st.caption("_Serving fresh SQL slop daily_")
        st.markdown("---")

        # Navigation with custom styling (tabs-like)
        page = st.radio(
            "Navigate",
            ["🍲 Slop Generator", "💬 Chat with Slop"],
            label_visibility="collapsed"
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
    st.markdown("_Order up! Tell me what kind of data slop you're craving, and I'll cook it up fresh_")

    st.markdown("<br>", unsafe_allow_html=True)

    # Prompt input with nice styling
    prompt = st.text_area(
        "🍴 Place your order",
        placeholder="E.g., 'Cook me up 1000 customer records with names, emails, and order history... make it spicy with some edge cases!'",
        height=120,
        help="Describe the data slop you want. Be specific about portions (row counts), ingredients (columns), and seasoning (constraints)."
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
            help="Upload your database schema in SQL or JSON format"
        )
        st.caption("Supported: SQL, JSON")

    with col2:
        if uploaded_file:
            st.markdown("### 📝 Schema Preview")
            schema_content = uploaded_file.read().decode()
            st.session_state.ddl_content = schema_content
            st.code(schema_content[:500] + ("..." if len(schema_content) > 500 else ""), language="sql")

    st.markdown("<br>", unsafe_allow_html=True)

    # Advanced Parameters in expandable section
    with st.expander("⚙️ Advanced Parameters", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            temperature = st.slider(
                "🌡️ Temperature",
                min_value=0.0,
                max_value=2.0,
                value=float(config.gemini.temperature),
                step=0.1,
                help="Higher values = more creative, lower = more deterministic"
            )

        with col2:
            max_tokens = st.number_input(
                "🎯 Max Tokens",
                min_value=100,
                max_value=100000,
                value=8000,
                step=1000,
                help="Maximum tokens for generation"
            )

        with col3:
            rows_per_table = st.number_input(
                "📊 Rows per Table",
                min_value=10,
                max_value=10000,
                value=1000,
                step=100,
                help="Number of rows to generate per table"
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Generate button with nice styling
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        generate_btn = st.button("👨‍🍳 Cook It Up!", type="primary", use_container_width=True)

    if generate_btn:
        if not st.session_state.ddl_content:
            st.error("⚠️ Please upload a DDL schema first!")
        else:
            try:
                with st.spinner("🍳 Cooking your data slop..."):
                    # Parse DDL
                    parser = DDLParser()
                    tables = parser.parse(st.session_state.ddl_content)
                    st.session_state.parsed_tables = tables

                    if not tables:
                        st.error("❌ No tables found in DDL. Please check your schema format.")
                    else:
                        st.success(f"✅ Parsed {len(tables)} tables: {', '.join(tables.keys())}")

                        # Generate data
                        gemini_client = get_gemini_client(config)
                        generator = DataGenerator(gemini_client)

                        # Progress tracking
                        progress_bar = st.progress(0)
                        status_text = st.empty()

                        generation_order = parser.get_generation_order()
                        total_tables = len(generation_order)

                        for idx, table_name in enumerate(generation_order):
                            status_text.text(f"🍳 Cooking {table_name}... ({idx+1}/{total_tables})")
                            table = tables[table_name]
                            df = generator._generate_table_data(
                                table,
                                int(rows_per_table),
                                prompt if prompt else "",
                                tables
                            )
                            st.session_state.generated_data[table_name] = df
                            progress_bar.progress((idx + 1) / total_tables)

                        status_text.empty()
                        progress_bar.empty()
                        st.success(f"🍽️ Fresh slop ready! Generated {total_tables} tables with {int(rows_per_table)} rows each.")
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
                "Table",
                available_tables,
                label_visibility="collapsed"
            )

        # Display selected table
        if selected_table and selected_table in st.session_state.generated_data:
            df = st.session_state.generated_data[selected_table]
            st.dataframe(
                df.head(100),  # Show first 100 rows
                use_container_width=True,
                hide_index=True
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
                    key=f"edit_{selected_table}"
                )
            with col2:
                submit_edit = st.button("🔧 Remix", type="secondary", use_container_width=True)

            if submit_edit and edit_instructions:
                try:
                    with st.spinner(f"🍳 Remixing {selected_table}..."):
                        gemini_client = get_gemini_client(config)
                        generator = DataGenerator(gemini_client)
                        generator.generated_data = st.session_state.generated_data.copy()

                        # Regenerate just this table
                        df = generator.regenerate_table(
                            selected_table,
                            st.session_state.parsed_tables,
                            int(rows_per_table),
                            edit_instructions
                        )
                        st.session_state.generated_data[selected_table] = df
                        st.success(f"✅ {selected_table} remixed!")
                        st.rerun()

                except Exception as e:
                    logger.error(f"Table remix failed for {selected_table}: {str(e)}", exc_info=True)
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
                    use_container_width=True
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
                key="dataset_name_input"
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            save_btn = st.button("💾 Save All Tables", type="primary", use_container_width=True, disabled=not dataset_name)

        if save_btn and dataset_name:
            try:
                # Generate schema name
                schema_name = f"slop_{dataset_name}"

                with st.spinner(f"Saving dataset to schema '{schema_name}'..."):
                    # Create schema
                    db_manager.create_schema(schema_name)

                    # Get generation order
                    parser = DDLParser()
                    parser.tables = st.session_state.parsed_tables
                    generation_order = parser.get_generation_order()

                    # Create tables in schema
                    if st.session_state.ddl_content:
                        db_manager.execute_ddl_in_schema(st.session_state.ddl_content, schema_name)

                    # Insert data for all tables
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    total_rows = 0
                    for idx, table_name in enumerate(generation_order):
                        status_text.text(f"Saving {table_name}... ({idx+1}/{len(generation_order)})")
                        df = st.session_state.generated_data[table_name]
                        rows = db_manager.execute_insert_in_schema(
                            table_name,
                            df.to_dict('records'),
                            schema_name
                        )
                        total_rows += rows
                        progress_bar.progress((idx + 1) / len(generation_order))

                    status_text.empty()
                    progress_bar.empty()

                    st.success(f"✅ Dataset saved! Schema: `{schema_name}` • {len(generation_order)} tables • {total_rows} rows")
                    st.info(f"💬 Use this dataset in the 'Chat with Slop' tab by selecting `{schema_name}` from the dropdown")

            except Exception as e:
                logger.error(f"Dataset save failed for schema {schema_name}: {str(e)}", exc_info=True)
                st.error(f"❌ Save failed: {str(e)}")
                with st.expander("🔍 Error details"):
                    st.code(traceback.format_exc())

    else:
        # No data generated yet - show placeholder
        st.info("🍽️ No fresh slop yet! Upload a schema and hit 'Cook It Up!' to get started.")


def show_chat_tab(config: AppConfig, db_manager: DatabaseManager):
    """Display Talk to your data tab."""

    st.markdown("# 💬 Chat with Your Slop")
    st.markdown("_Ask me anything about your data - I speak both English and SQL!_")

    st.markdown("<br>", unsafe_allow_html=True)

    # Dataset selector
    try:
        schemas = db_manager.list_schemas(prefix="slop_")
        if schemas:
            schema_names = [s['schema_name'] for s in schemas]

            # Initialize session state for selected schema
            if "selected_schema" not in st.session_state:
                st.session_state.selected_schema = schema_names[0] if schema_names else None

            col1, col2 = st.columns([3, 2])
            with col1:
                selected_schema = st.selectbox(
                    "🗄️ Dataset",
                    schema_names,
                    index=schema_names.index(st.session_state.selected_schema) if st.session_state.selected_schema in schema_names else 0,
                    help="Select a saved dataset to query"
                )
                st.session_state.selected_schema = selected_schema

            with col2:
                if selected_schema:
                    # Show dataset info
                    schema_info = next((s for s in schemas if s['schema_name'] == selected_schema), None)
                    if schema_info:
                        st.caption(f"📊 {schema_info['table_count']} tables")

            st.markdown("---")
        else:
            st.warning("⚠️ No saved datasets found. Generate and save data in the 'Slop Generator' tab first!")
            st.markdown("---")
    except Exception as e:
        logger.error(f"Failed to load dataset list: {str(e)}", exc_info=True)
        st.error(f"❌ Failed to load datasets: {str(e)}")
        st.markdown("---")

    # Chat history placeholder
    st.markdown("### 💭 Conversation")

    chat_container = st.container()
    with chat_container:
        st.info("👋 Hey! Ready to dig through your data slop? Ask away!")

        # Example questions
        with st.expander("💡 Try asking me...", expanded=True):
            st.markdown("""
            - "Show me the juiciest customers by revenue"
            - "What's the average order value - give it to me straight"
            - "Plot the sales rollercoaster for 2024"
            - "Which products are the biggest flops?"
            """)

    st.markdown("<br>", unsafe_allow_html=True)

    # Chat input at bottom
    col1, col2 = st.columns([6, 1])
    with col1:
        user_question = st.text_input(
            "Ask a question",
            placeholder="What's cooking? e.g., 'Show me the freshest sales data by region'",
            label_visibility="collapsed"
        )
    with col2:
        send_btn = st.button("🍴 Serve", type="primary", use_container_width=True)

    if send_btn and user_question:
        st.info(f"🔍 Searching the slop: {user_question}")
        st.warning("🚧 Still training the chef!")


if __name__ == "__main__":
    main()