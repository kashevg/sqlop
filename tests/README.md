# Test Suite

All test files use a common configuration setup via `conftest.py`.

## Running Tests

```bash
# Run individual test suites
python tests/test_ddl_parser.py         # Basic DDL parser tests
python tests/test_real_schemas.py       # Tests with real course schemas
python tests/test_db.py                 # Database connectivity (requires PostgreSQL)
python tests/test_gemini.py             # Gemini API tests (requires GCP auth)
```

## Test Fixtures

`fixtures/` contains real DDL schemas from course materials:
- `company_employee_schema.ddl` - 7 tables, complex relationships
- `library_mgm_schema.ddl` - 9 tables, circular dependencies
- `restrurants_schema.ddl` - 7 tables, restaurant management

## Current Test Status

✅ **DDL Parser Tests** - All passing
✅ **Real Schema Tests** - All 3 schemas parse correctly (23 tables total)
⚠️  **Database Tests** - Requires PostgreSQL running
⚠️  **Gemini Tests** - Requires GCP authentication

## Configuration

`conftest.py` automatically sets up the Python path for all tests, so you can import directly:

```python
import conftest  # Sets up sys.path
from tools.ddl_parser import DDLParser
```
