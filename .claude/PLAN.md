# 🍜 SQLop Implementation Plan - MVP First!

**Strategy**: Get Phase 1 working end-to-end FIRST, then build Phase 2. No fancy stuff until the basics work.

---

## 📊 Progress Overview

**Overall Progress: 3/13 tasks (23%)**

- ✅ Foundation: 3/3 complete
- 🚧 MVP (Phase 1): 0/4 complete
- ⏳ Phase 2: 0/5 complete
- ⏳ Future: 0/1 complete

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

## 🎯 MVP: Phase 1 - Data Generation (Get This Working First!)

**Goal**: Upload a DDL → Generate synthetic data → Preview → Refine → Download CSV → Stored in DB

### Task 1: Gemini Client Wrapper
**File**: `src/utils/gemini_client.py`

**What it does**:
- Initialize Google Gemini client with Vertex AI auth
- Support streaming responses
- Handle structured JSON output mode
- Simple interface: `generate_text()` and `generate_json()`

**Acceptance criteria**:
- Can send prompt and get response
- Can get structured JSON back
- Streaming works for UI updates

---

### Task 2: DDL Parser
**File**: `src/tools/ddl_parser.py`

**What it does**:
- Takes uploaded .sql/.ddl file content
- Parses using sqlparse library
- Extracts:
  - Table names
  - Column names and types
  - Primary keys
  - Foreign keys
  - NOT NULL constraints
- Returns clean Python dict of schema

**Acceptance criteria**:
- Parse all 3 sample schemas correctly
- Identify foreign key relationships
- Handle multi-table schemas

---

### Task 3: Data Generator
**File**: `src/tools/data_generator.py`

**What it does**:
- Takes parsed schema + user instructions
- Builds smart Gemini prompt with examples
- Generates synthetic data respecting all constraints
- Validates foreign keys
- Supports refinement ("regenerate this table with X")
- Returns data as pandas DataFrames (one per table)

**Acceptance criteria**:
- Generate 1000 rows in reasonable time
- All foreign keys valid
- Data looks realistic
- Can regenerate individual tables

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

### Task 4: Wire to UI
**File**: `src/app.py` (update existing)

**What it does**:
- Connect "Cook It Up!" button to data generator
- Show streaming progress
- Display preview tables with st.dataframe()
- Handle refinement prompts
- Generate CSV downloads (existing code works)
- Insert data into PostgreSQL using db.execute_insert()

**Acceptance criteria**:
- Click Generate → see progress → see previews
- Refine specific table → regenerates that table only
- Download CSV works
- Data appears in database (verify with test_db.py)

**UI Flow**:
```
1. User uploads restaurant.ddl
2. Clicks "Cook It Up!"
3. Progress: "Parsing schema..." → "Generating restaurants table..." → "Generating menu_items..."
4. Shows preview of each table
5. User types "regenerate restaurants with more Italian names"
6. Only restaurants table regenerates
7. Click Download → gets CSV/ZIP
8. Data is in PostgreSQL
```

---

## 🎉 MVP Success Criteria

Can you do this end-to-end?

1. Upload `library.ddl` (or paste DDL)
2. Add instruction: "Make it realistic with diverse names"
3. Set rows to 500
4. Click "Cook It Up!"
5. See generated data previews
6. Refine books table: "add more sci-fi titles"
7. Download all as CSV
8. Verify data in PostgreSQL

**If YES → MVP complete! 🎊**

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

## 🔮 Future Enhancements (Post-MVP & Phase 2)

### Task 10: Langfuse Observability
- Add tracing to all Gemini calls
- Track token usage and costs
- Monitor for jailbreak attempts
- Set up alerts

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

**Last Updated**: 2025-10-29
**Current Focus**: Documentation complete, ready to build MVP!