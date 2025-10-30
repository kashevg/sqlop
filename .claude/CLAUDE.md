# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SQLop is a Streamlit application that generates synthetic data from SQL schemas and provides natural language querying capabilities. Built as a practice/educational project with a playful "slop" theme.

**Tech Stack:**
- Gemini 2.0 Flash via Vertex AI (LLM)
- Streamlit (UI)
- PostgreSQL + psycopg3 (database)
- pandas, seaborn, matplotlib (data/viz)
- Python 3.11.6

## Development Commands

```bash
# Start database
docker-compose up -d

# Activate virtual environment
source .venv/bin/activate

# Run application
streamlit run src/app.py

# Test database connection
python test_db.py

# Stop database
docker-compose down
```

## Architecture

### Two-Phase Implementation (MVP-First Strategy)

**Phase 1 (Current Focus):** Synthetic data generation
- Upload DDL schema → Parse → Generate realistic data via Gemini → Preview → Refine → Export CSV/store in DB

**Phase 2:** Natural language querying
- Ask question → Convert to SQL via Gemini → Apply guardrails → Execute → Visualize results

### Core Components

**Configuration Layer (`src/utils/config.py`)**
- `AppConfig.from_env()` - Loads all configuration from environment variables
- `DatabaseConfig` - PostgreSQL connection parameters
- `GeminiConfig` - Supports both Vertex AI (GCP_PROJECT_ID) and API key (GOOGLE_API_KEY) auth
- `GeminiConfig.is_vertex_ai()` - Determines authentication method

**Database Layer (`src/utils/db.py`)**
- `DatabaseManager` - Manages psycopg3 connection pool (2-10 connections, 30s timeout)
- Key methods:
  - `execute_ddl(ddl)` - Executes CREATE TABLE statements (splits by semicolon)
  - `execute_query(query, params)` - SELECT queries, returns list of dicts
  - `execute_insert(table, data)` - Bulk inserts using executemany
  - `get_table_schema(table_name)` - Introspects schema from information_schema
  - `table_exists(table_name)` - Checks table existence
  - `drop_all_tables()` - Clean slate (use with caution)

**UI Layer (`src/app.py`)**
- Streamlit app with two main tabs:
  - "Slop Generator" (lines 173-321) - Data generation interface
  - "Chat with Slop" (lines 324-363) - Query interface
- Uses `@st.cache_resource` for config and DB manager (singleton pattern)
- Custom CSS for "slop" themed styling
- Currently displays UI mockups; backend wiring is pending

### Key Design Patterns

**No Global State**
- Configuration and database connections passed explicitly through function parameters
- Streamlit cached resources used for singletons (`get_config()`, `get_db_manager()`)

**Connection Pooling**
- Database uses psycopg_pool for efficient connection management
- Context managers ensure proper cleanup (`with db_manager.get_connection()`)

**Dictionary-based Rows**
- All query results use `dict_row` factory for easy data manipulation
- Enables seamless conversion to pandas DataFrames

## Implementation Status & Workflow

**Check these files for current state:**
- `.claude/STATUS.md` - Current progress and next task
- `.claude/PLAN.md` - Full task breakdown with acceptance criteria
- `src/app.py` header - Quick TODO checklist

**Current Status:** Foundation complete (UI, DB layer, config, Docker). MVP Phase 1 implementation pending.

**Next Tasks (in order):**
1. Create `src/utils/gemini_client.py` - Vertex AI wrapper with streaming support
2. Create `src/tools/ddl_parser.py` - Parse DDL with sqlparse, extract schema
3. Create `src/tools/data_generator.py` - Generate synthetic data via Gemini
4. Wire Phase 1 to UI in `src/app.py` - Connect "Cook It Up!" button

## Environment Configuration

Required in `.env`:
```bash
# Database (matches docker-compose.yml)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sqlop
DB_USER=sqlop_user
DB_PASSWORD=sqlop_password

# Gemini (choose ONE auth method)
GCP_PROJECT_ID=your-project-id        # For Vertex AI
GCP_LOCATION=us-central1
# OR
GOOGLE_API_KEY=your-api-key           # For API key auth

GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_TEMPERATURE=0.7
```

## Key Implementation Guidelines

**Gemini Integration:**
- Use structured JSON output for data generation (schema enforcement)
- Stream responses for UI feedback during long operations
- Leverage Vertex AI for production (not API key)

**Data Generation Strategy:**
- Parse DDL to identify foreign key dependencies (generation order matters)
- Generate parent tables before child tables to maintain referential integrity
- Use Gemini with clear constraint instructions in prompt
- Return data as pandas DataFrames for easy CSV export and DB insertion

**Database Operations:**
- Always use parameterized queries (prevent SQL injection)
- Execute DDL statements individually (split by semicolon)
- Use bulk inserts (`executemany`) for large datasets
- Check table existence before operations to avoid errors

**UI Integration:**
- Store generated data in `st.session_state` for refinement workflow
- Use `st.spinner()` with streaming updates for long operations
- Preview data with `st.dataframe()` before allowing download/storage
- Enable per-table refinement (regenerate individual tables without losing others)

## Langfuse Integration (Future)

Currently skipped for MVP. When implementing:
- Add tracing decorators to all Gemini calls
- Track token usage and costs
- Monitor for jailbreak attempts
- Set up alerts for security events

## Project Structure Notes

```
src/
├── app.py              # Streamlit UI (both tabs defined here)
├── utils/              # Core utilities (config, db, gemini client)
└── tools/              # Business logic (parsers, generators, converters)

.claude/                # Claude Code session management
├── STATUS.md           # Current progress tracker (read first after /clear)
├── PLAN.md             # Full implementation plan
└── CLAUDE.md           # This file - architecture guidance

data/                   # Generated CSV files and exports
```

## Testing Workflow

**Phase 1 MVP Success:**
1. Upload sample DDL (library/restaurant/company schema)
2. Add generation instruction (e.g., "realistic diverse names")
3. Set rows per table (e.g., 500)
4. Generate → see streaming progress → preview tables
5. Refine specific table → regenerate with new instructions
6. Download CSV → verify data in PostgreSQL

**Phase 2 Success:**
1. Ask natural language question
2. See generated SQL query
3. View results table
4. Verify appropriate chart auto-generates
5. Test guardrails block malicious queries (DROP, DELETE, etc.)
6. Verify conversation history maintained

## Common Pitfalls

- Don't forget to respect foreign key order during data generation
- Always validate DDL parsing output before generating data
- Remember to split multi-statement DDL by semicolon before execution
- Cache Streamlit resources to avoid re-initialization on each interaction
- Use dict_row factory for all queries to enable easy DataFrame conversion