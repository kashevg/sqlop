# 🍜 SQLop Implementation Plan - MVP First!

**Strategy**: Get Phase 1 working end-to-end FIRST, then build Phase 2. No fancy stuff until the basics work.

---

## 📊 Progress Overview

**Overall Progress: 9/13 tasks (69%)**

- ✅ Foundation: 3/3 complete
- ✅ MVP (Phase 1): 6/6 complete (including bug fixes + observability)
- ⏳ Phase 2: 0/5 complete ← **CURRENT FOCUS**
- ⏳ Future: 0/0 complete (Langfuse moved to Phase 1!)

---

## ✅ Foundation (Already Done!)

These are complete from the previous session:

- [x] **Project Structure** - src/, data/, docs/ organized
- [x] **Streamlit UI** - Both tabs with slop theme and styling
- [x] **Database Layer** - PostgreSQL with connection pooling (psycopg3)
- [x] **Configuration** - Environment management with .env
- [x] **Docker Setup** - PostgreSQL running in container

**Total: 735 lines of foundation code** 🎉

---

## ✅ MVP: Phase 1 - Data Generation (COMPLETE!)

**Goal**: Upload a DDL → Generate synthetic data → Preview → Refine → Download CSV → Stored in DB

### Task 1: Gemini Client Wrapper ✅ (ENHANCED!)
**File**: `src/utils/gemini_client.py` (314 lines)

**Completed features**:
- ✅ Initialize Google Gemini client with Vertex AI OR API key auth
- ✅ Support streaming responses (text and JSON)
- ✅ Handle structured JSON output mode with response_schema
- ✅ Simple interface: `generate_text()` and `generate_json()`
- ✅ Schema enforcement for reliable JSON parsing
- ✅ **Langfuse 2.x observability** (commit 15ebbcc):
  - All methods decorated with `@observe(as_type="generation")`
  - Metadata tracking (model, temperature, max_tokens, stream flags)
  - Token usage extraction via `update_current_observation()`
  - Comprehensive error handling (quota exceeded, timeouts)
  - Structured logging (replaced print statements)

**Status**: Production-ready with full observability!

---

### Task 2: DDL Parser ✅
**File**: `src/tools/ddl_parser.py` (357 lines)

**Completed features**:
- ✅ Takes uploaded .sql/.ddl file content
- ✅ Parses using sqlparse library
- ✅ Extracts table names, columns, types, PKs, FKs, constraints
- ✅ Returns clean Python dict of schema
- ✅ Handles multi-table schemas with dependencies
- ✅ Topological sort for generation order

**Status**: All tests passing!

---

### Task 3: Data Generator ✅
**File**: `src/tools/data_generator.py` (526 lines)

**Completed features**:
- ✅ Takes parsed schema + user instructions
- ✅ Builds smart Gemini prompt with FK context
- ✅ Generates synthetic data respecting all constraints
- ✅ Validates foreign keys with actual values
- ✅ Supports refinement ("regenerate this table with X")
- ✅ Returns data as pandas DataFrames
- ✅ Batching for large datasets (20 rows/batch to avoid token limits)
- ✅ JSON schema enforcement for structured output

**Status**: Tested with restaurant schema - works great!

**Prompt strategy**:
```
You are generating realistic synthetic data for a database.

Schema: {table definitions}
Instructions: {user instructions}
Rows: {num_rows}

Generate data that:
- Respects all foreign key relationships
- Follows data type constraints
- Looks realistic and varied
- Maintains referential integrity

Return JSON with structure: {"table_name": [{"col": "val", ...}, ...]}
```

---

### Task 4: Wire to UI ✅
**File**: `src/app.py` (628 lines)

**Completed features**:
- ✅ Connect "Cook It Up!" button to data generator
- ✅ Show streaming progress bars
- ✅ Display preview tables with st.dataframe()
- ✅ Handle refinement prompts (Remix button)
- ✅ Generate CSV downloads
- ✅ Insert data into PostgreSQL schemas using db.execute_insert_in_schema()
- ✅ Save datasets to separate schemas (slop_*)
- ✅ List saved schemas in Chat tab

**Status**: Full Phase 1 workflow working!

---

### Task 4.5: Bug Fixes & MySQL Compatibility ✅
**Files**: `src/utils/db.py`, `src/utils/ddl_converter.py`, `src/app.py`

**Issues Fixed** (commit 6fb0219):
- ✅ **Connection pool contamination**: search_path now properly restored after DDL execution
- ✅ **Case-sensitivity**: Table/column names lowercased to match PostgreSQL behavior
- ✅ **Foreign key violations**: Generator state maintained across table generation
- ✅ **MySQL support**: Auto-detects and converts MySQL DDL to PostgreSQL
  - AUTO_INCREMENT → SERIAL
  - TINYINT(1) → BOOLEAN
  - DATETIME → TIMESTAMP
  - ENUM(...) → VARCHAR
  - Removes ENGINE, CHARSET, backticks
- ✅ **Token limits**: Batching system for large datasets (20 rows/batch)

**Status**: All bugs fixed and tested!

---

## 🎉 MVP SUCCESS! Phase 1 Complete ✅

Tested end-to-end with restaurant schema:

1. ✅ Upload `restaurant.ddl` (MySQL format)
2. ✅ Auto-converts to PostgreSQL
3. ✅ Set rows to 10
4. ✅ Click "Cook It Up!"
5. ✅ See generated data previews (Restaurants, MenuItems, Customers, Orders)
6. ✅ Remix individual table with new instructions
7. ✅ Download CSV
8. ✅ Save to database schema (slop_rest_v8)
9. ✅ All foreign keys valid
10. ✅ Data appears in PostgreSQL

**Phase 1 COMPLETE! 🎊 Ready for Phase 2!**

---

## 🚀 Phase 2 - Chat with Your Data (Build After MVP)

**Goal**: Ask questions in English → Get SQL + Results + Charts

### Task 5: NL2SQL Converter
**File**: `src/tools/nl2sql.py`

**What it does**:
- Takes natural language question
- Gets current database schema from db.get_table_schema()
- Builds Gemini prompt with schema context
- Returns SQL query (SELECT only)

**Prompt strategy**:
```
Database schema:
{schema from information_schema}

User question: "{question}"

Generate a PostgreSQL SELECT query to answer this question.
- Use proper JOINs where needed
- Include aggregations if appropriate
- Return only the SQL query, no explanations
```

---

### Task 6: Guardrails
**File**: `src/tools/guardrails.py`

**What it does**:
- Check for SQL injection patterns
- Block DROP, DELETE, UPDATE, ALTER, TRUNCATE
- Detect prompt injection attempts
- Verify query stays on-topic (data analysis only)
- Return: `{"safe": bool, "reason": str}`

**Simple regex patterns**:
```python
BLOCKED_PATTERNS = [
    r'\bDROP\b',
    r'\bDELETE\b',
    r'\bUPDATE\b',
    r'\bALTER\b',
    r'--\s*$',  # SQL comments
    r'/\*.*\*/',  # Block comments
]
```

---

### Task 7: Chart Visualizer
**File**: `src/tools/visualizer.py`

**What it does**:
- Analyzes query results (pandas DataFrame)
- Determines best chart type:
  - Time series → line chart
  - Categories + numbers → bar chart
  - Two numeric columns → scatter plot
  - Single numeric → histogram
- Generates Seaborn/Matplotlib chart
- Returns streamlit-compatible figure

**Simple heuristics**:
```python
if has_datetime_column and has_numeric:
    return line_chart()
elif has_category_column and has_numeric:
    return bar_chart()
elif two_numeric_columns:
    return scatter_plot()
```

---

### Task 8: Wire Chat to UI
**File**: `src/app.py` (update chat tab)

**What it does**:
- Connect chat input to NL2SQL
- Apply guardrails before execution
- Execute SQL with db.execute_query()
- Display results table
- Auto-generate chart if appropriate
- Store chat history in st.session_state
- Stream responses

**Chat Flow**:
```
User: "What are the top 5 most borrowed books?"
↓
Guardrails check → ✓ safe
↓
NL2SQL → "SELECT b.title, COUNT(*) as loans FROM books b JOIN loans l ON..."
↓
Show SQL in code block
↓
Execute query → results
↓
Show table
↓
Analyze → bar chart makes sense
↓
Show chart
```

---

### Task 9: Test Phase 2
- Ask diverse questions (simple, complex, joins, aggregations)
- Try malicious queries → blocked
- Verify charts auto-generate correctly
- Test conversation history

---

### Task 4.6: Langfuse Observability ✅
**Files**: `src/utils/gemini_client.py`, `requirements.txt`, `tests/test_gemini.py`

**Completed features** (commit 15ebbcc):
- ✅ **Enhanced all LLM methods** with Langfuse 2.x best practices
  - `@observe(as_type="generation")` decorators on all methods
  - Metadata tracking: model, temperature, max_tokens, stream flags, schema enforcement
  - Token usage extraction via `langfuse_context.update_current_observation()`
- ✅ **Comprehensive error handling**
  - Google API exceptions (ResourceExhausted, DeadlineExceeded)
  - Structured logging (replaced print statements)
- ✅ **Missing dependencies added**
  - `openinference-instrumentation-google-genai>=0.1.0`
  - `google-api-core==2.28.1`
- ✅ **All tests passing**
  - Updated test_gemini.py to use schema parameter
  - Added markdown fence stripping for JSON streaming

**Status**: Production-ready observability complete!

---

## 🔮 Future Enhancements (Post-MVP & Phase 2)

No remaining items - Langfuse observability completed in Phase 1!

---

## 📋 Daily Checklist Format

Use this to track daily progress:

```
Today's Goal: [Get X working]

[ ] Task name
    [ ] Sub-task 1
    [ ] Sub-task 2
    [ ] Test it works

Blockers: None / [describe]
Next session: [what to tackle next]
```

---

## 🎯 Time Estimates

**Realistic timeline**:
- Task 1 (Gemini client): 1 hour
- Task 2 (DDL parser): 2 hours
- Task 3 (Data generator): 3 hours
- Task 4 (Wire to UI): 2 hours
- **MVP Total: ~8 hours**

- Task 5 (NL2SQL): 2 hours
- Task 6 (Guardrails): 1 hour
- Task 7 (Visualizer): 2 hours
- Task 8 (Wire chat): 2 hours
- Task 9 (Test Phase 2): 1 hour
- **Phase 2 Total: ~8 hours**

**Grand Total: ~16 hours to complete both phases**

---

## 🐛 Known Issues / TODO

Track issues here as you find them:

- [ ] TBD

---

## 🎓 Learning Notes

Document things you learned:

- TBD

---

**Last Updated**: 2025-11-11
**Current Focus**: Phase 1 complete with observability! Now building Phase 2 - Natural Language Querying