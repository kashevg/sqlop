"""Main Streamlit application for SQLOp."""

import streamlit as st
import pandas as pd

from utils.config import AppConfig
from utils.db import DatabaseManager


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
        with st.spinner("🍳 Cooking your data slop..."):
            st.info("🚧 Kitchen still under construction!")

    st.markdown("---")

    # Data Preview section with modern design
    st.markdown("## 🍽️ Fresh from the Kitchen")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown("*Take a taste of your freshly cooked data*")
    with col3:
        table_selector = st.selectbox(
            "Table",
            ["users", "orders", "products"],
            label_visibility="collapsed"
        )

    # Sample data table with nice formatting
    sample_data = pd.DataFrame({
        "ID": ["001", "002", "003"],
        "Name": ["Alice Johnson", "Bob Smith", "Carol Williams"],
        "Email": ["alice@example.com", "bob@example.com", "carol@example.com"],
        "Category": ["Premium", "Standard", "Premium"],
        "Value": ["$245.50", "$127.80", "$389.20"]
    })

    st.dataframe(
        sample_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.TextColumn("ID", width="small"),
            "Name": st.column_config.TextColumn("Name", width="medium"),
            "Email": st.column_config.TextColumn("Email", width="medium"),
            "Category": st.column_config.TextColumn("Category", width="small"),
            "Value": st.column_config.TextColumn("Value", width="small"),
        }
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Quick edit section
    col1, col2 = st.columns([5, 1])
    with col1:
        edit_instructions = st.text_input(
            "Edit",
            placeholder="Need adjustments? 'Add more salt' (Premium → VIP) or 'More portions' (add rows)...",
            label_visibility="collapsed"
        )
    with col2:
        submit_edit = st.button("🔧 Remix", type="secondary", use_container_width=True)

    if submit_edit and edit_instructions:
        st.info(f"👨‍🍳 Remixing: {edit_instructions}")

    # Download section
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        st.download_button(
            "📦 Take Out (CSV)",
            data=sample_data.to_csv(index=False),
            file_name="sql_slop.csv",
            mime="text/csv",
            use_container_width=True
        )


def show_chat_tab(config: AppConfig, db_manager: DatabaseManager):
    """Display Talk to your data tab."""

    st.markdown("# 💬 Chat with Your Slop")
    st.markdown("_Ask me anything about your data - I speak both English and SQL!_")

    st.markdown("<br>", unsafe_allow_html=True)

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