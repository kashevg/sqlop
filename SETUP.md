# 🍜 SQLop Setup Guide

Complete setup instructions to get your data slop kitchen running.

---

## Prerequisites

- **Python 3.11** installed (project uses 3.11.6)
- **Docker** installed (for PostgreSQL)
- **Google Cloud account** (free tier works!)
- **Terminal/Command Prompt** access

---

## Part 1: Google Cloud / Vertex AI Setup

SQLop uses **Gemini 2.0 Flash** via Google's Vertex AI. Here's how to set it up:

### Step 1: Create/Select GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Note your **Project ID** (you'll need this!)

### Step 2: Enable Required APIs

```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Or do it via Console:
# https://console.cloud.google.com/apis/library/aiplatform.googleapis.com
```

Click "Enable" button.

### Step 3: Set Up Authentication

**Option A: Application Default Credentials (Recommended)**

```bash
# Install gcloud CLI if you haven't
# Download from: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

**Option B: Service Account Key (Alternative)**

1. Go to [Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Create service account with "Vertex AI User" role
3. Create JSON key
4. Download and save as `gcp-key.json` in project root
5. Set environment variable:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/sqlop/gcp-key.json"
   ```

### Step 4: Verify Access

```bash
# Test that you can access Vertex AI
gcloud ai models list --region=us-central1
```

If you see a list (or "no models found" message), you're good! ✅

---

## Part 2: Project Setup

### Step 1: Clone and Navigate

```bash
git clone <your-repo-url>
cd sqlop
```

### Step 2: Create Virtual Environment

```bash
# Create venv with Python 3.11
python3.11 -m venv .venv

# Activate it
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

You should see `(.venv)` in your terminal prompt.

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- streamlit (UI)
- google-genai (Gemini SDK)
- psycopg3 (PostgreSQL)
- pandas, seaborn, matplotlib (data & viz)
- sqlparse (DDL parsing)
- langfuse (future observability)

### Step 4: Configure Environment Variables

```bash
# Copy the template
cp .env.example .env

# Edit with your values
nano .env  # or use your favorite editor
```

**Minimal required `.env` contents**:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sqlop
DB_USER=sqlop_user
DB_PASSWORD=sqlop_password

# Google Cloud / Vertex AI
GCP_PROJECT_ID=your-project-id-here
GCP_LOCATION=us-central1

# Gemini Configuration
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_TEMPERATURE=0.7

# Langfuse (optional - can skip for now)
# LANGFUSE_PUBLIC_KEY=
# LANGFUSE_SECRET_KEY=
# LANGFUSE_HOST=https://cloud.langfuse.com
```

**Important**: Replace `your-project-id-here` with your actual GCP project ID!

---

## Part 3: Database Setup

### Step 1: Start PostgreSQL with Docker

```bash
# Start the database
docker-compose up -d

# Verify it's running
docker ps
```

You should see `sqlop_postgres` container running.

### Step 2: Test Database Connection

```bash
# Run the test script
python test_db.py
```

Expected output:
```
Testing database connection...
Database version: PostgreSQL 16.x
Connection successful!
```

If you get an error, wait 10 seconds and try again (PostgreSQL takes a moment to start).

---

## Part 4: Run the Application

### Start Streamlit

```bash
streamlit run src/app.py
```

Expected output:
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

### Open in Browser

Navigate to: **http://localhost:8501**

You should see the SQLop interface with:
- 🍜 Fun slop theme
- Two tabs: "Slop Generator" and "Chat with Slop"
- Database connection status in sidebar (should show ✅ PostgreSQL 16.x)

---

## Part 5: Verify Setup

### Test 1: Check Database Connection

In the Streamlit UI sidebar, you should see:
```
✅ PostgreSQL 16.x.x
Database: sqlop
```

### Test 2: Upload a DDL File

1. Go to "Slop Generator" tab
2. Upload any .sql file
3. You should see the file content displayed

*(Generation won't work yet - that's what we're building!)*

---

## Troubleshooting

### Issue: "Database connection failed"

**Solution**:
```bash
# Stop and restart PostgreSQL
docker-compose down
docker-compose up -d

# Wait 10 seconds, then test
python test_db.py
```

### Issue: "GCP authentication failed"

**Solution**:
```bash
# Re-authenticate
gcloud auth application-default login

# Verify project
gcloud config get-value project

# Should show your project ID
```

### Issue: "Module not found"

**Solution**:
```bash
# Make sure venv is activated (you should see (.venv))
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Vertex AI quota exceeded"

**Solution**:
- You're on free tier and hit rate limits
- Wait a few minutes
- Or upgrade to paid tier (still very cheap!)

### Issue: "Port 8501 already in use"

**Solution**:
```bash
# Use different port
streamlit run src/app.py --server.port 8502
```

### Issue: "Permission denied" on Docker

**Solution**:
```bash
# On Linux/Mac, you might need:
sudo docker-compose up -d

# Or add your user to docker group:
sudo usermod -aG docker $USER
# Then logout and login
```

---

## Directory Structure After Setup

```
sqlop/
├── .venv/                    # Virtual environment (created)
├── data/                     # Data storage (empty for now)
├── src/
│   ├── app.py
│   ├── utils/
│   │   ├── config.py
│   │   └── db.py
│   └── tools/               # Will populate during development
├── .env                     # Your config (created from .env.example)
├── .env.example
├── requirements.txt
├── docker-compose.yml
├── test_db.py
├── README.md
├── PLAN.md
└── SETUP.md
```

---

## Next Steps

Now that everything is set up:

1. ✅ Environment configured
2. ✅ Database running
3. ✅ GCP auth working
4. ✅ Streamlit running

**Ready to build!** 🎉

Check [.claude/PLAN.md](.claude/PLAN.md) for the implementation roadmap.

Start with **Task 1: Create Gemini Client Wrapper** (`src/utils/gemini_client.py`)

---

## Quick Reference Commands

```bash
# Start everything
docker-compose up -d
source .venv/bin/activate  # or .venv\Scripts\activate
streamlit run src/app.py

# Stop everything
# Ctrl+C to stop Streamlit
docker-compose down

# View logs
docker-compose logs -f

# Access PostgreSQL directly
docker exec -it sqlop_postgres psql -U sqlop_user -d sqlop

# Run tests
python test_db.py
```

---

## Optional: Sample DDL Files

Create a `samples/` directory with test schemas:

```bash
mkdir samples
```

Download or create these files:
- `samples/library.ddl` - Books, authors, loans
- `samples/restaurant.ddl` - Menus, orders, customers
- `samples/company.ddl` - Employees, departments, projects

Example `library.ddl`:
```sql
CREATE TABLE authors (
    author_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    birth_year INTEGER
);

CREATE TABLE books (
    book_id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    author_id INTEGER REFERENCES authors(author_id),
    isbn VARCHAR(13) UNIQUE,
    publication_year INTEGER
);

CREATE TABLE members (
    member_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    join_date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE loans (
    loan_id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(book_id),
    member_id INTEGER REFERENCES members(member_id),
    loan_date DATE NOT NULL,
    return_date DATE
);
```

---

**Questions?** Check the troubleshooting section or review [.claude/PLAN.md](.claude/PLAN.md)!

Happy slopping! 🍜