# 🍜 SQLop - Your AI-Powered Data Slop Kitchen

> "Because sometimes you just need a big bowl of synthetic data slop!"

Welcome to **SQLop** - where we cook up synthetic data and serve it with a side of natural language queries. No Michelin stars here, just good honest data slop that gets the job done.

## What's Cooking?

SQLop is your friendly neighborhood AI chef that:
1. **Generates Data Slop** 🥘 - Feed it a SQL schema, get back mountains of realistic synthetic data
2. **Serves Data on Demand** 🍲 - Ask questions in plain English, get answers with pretty charts

Perfect for when you need test data but don't want to spend hours writing INSERT statements. We're talking 1000+ rows of data faster than you can say "connection pooling".

## The Menu

### 🥘 Slop Generator (Phase 1)
The data generation kitchen where the magic happens:
- **Upload your schema** - Drop in a .sql, .ddl, or .txt file with your table definitions
- **Tell us what you want** - "Make it realistic", "More variety", "Heavy on the Italian names"
- **Tweak the recipe** - Adjust temperature, rows per table, and other nerdy parameters
- **Preview your slop** - Check out what we cooked before you commit
- **Refine it** - Not spicy enough? Tell us to regenerate with different vibes
- **Take it to go** - Download as CSV or ZIP, automatically stored in PostgreSQL

**Respects all your constraints:**
- Primary keys? ✅ Unique every time
- Foreign keys? ✅ All relationships intact
- Data types? ✅ Dates look like dates, numbers like numbers
- NOT NULL? ✅ No nulls where you don't want 'em

### 🍲 Chat with Slop (Phase 2)
Your conversational data server:
- **Ask in plain English** - "How many orders last month?" → SQL magic happens
- **See the recipe** - We show you the SQL we generated
- **Pretty pictures** - Auto-generated charts when it makes sense
- **Safe and sound** - Guardrails prevent SQL injection and other nastiness
- **Keep chatting** - We remember the conversation so you can ask follow-ups

## Tech Stack (aka Our Kitchen Equipment)

- **Chef AI**: Gemini 2.0 Flash (via Google Vertex AI)
- **Front of House**: Streamlit
- **The Pantry**: PostgreSQL
- **Plating**: Seaborn + Matplotlib + Pandas
- **Kitchen Tools**: Docker
- **Future**: Langfuse for keeping an eye on the kitchen

## Quick Start (Get Cooking!)

### 1. Set Up Your Kitchen

```bash
# Clone the repo
cd sqlop

# Fire up the stove (virtual environment)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Get your ingredients
pip install -r requirements.txt
```

### 2. Configure Your Recipe Book

```bash
# Copy the template
cp .env.example .env

# Edit with your Google Cloud credentials
# See SETUP.md for detailed instructions
```

### 3. Start the Database (Our Pantry)

```bash
docker-compose up -d
```

### 4. Open the Kitchen

```bash
streamlit run src/app.py
```

**Boom!** 💥 Head to http://localhost:8501 and start slopping!

## Sample Schemas

Try these out:
- 📚 **Library Management** - Books, authors, members, loans
- 🍕 **Restaurant System** - Menus, orders, customers, reservations
- 🏢 **Company Database** - Employees, departments, projects, salaries

## Project Structure (The Floor Plan)

```
sqlop/
├── src/
│   ├── app.py                 # Main kitchen (Streamlit UI)
│   ├── utils/
│   │   ├── config.py          # Recipe configurations
│   │   ├── db.py              # Pantry management (PostgreSQL)
│   │   └── gemini_client.py   # The AI chef interface
│   └── tools/
│       ├── ddl_parser.py      # Menu reader (DDL parser)
│       ├── data_generator.py  # Slop maker
│       ├── nl2sql.py          # Translation service
│       ├── guardrails.py      # Health inspector
│       └── visualizer.py      # Food photographer
├── data/                      # Takeout containers
├── docker-compose.yml         # Pantry setup
├── requirements.txt           # Shopping list
└── SETUP.md                   # Detailed recipes
```

## How to Use

### Making Some Slop (Data Generation)

1. Click on **"Slop Generator"** tab
2. Upload a DDL file or paste your schema
3. (Optional) Add instructions like "make it more realistic" or "lots of variety"
4. Adjust the sliders if you're feeling fancy
5. Hit **"Cook It Up!"** and watch the magic
6. Preview your data - looking good?
7. Want changes? Use the refine box: "regenerate customers with more diverse names"
8. Download your slop as CSV or grab it all as a ZIP

### Chatting with Your Slop (Queries)

1. Switch to **"Chat with Slop"** tab
2. Ask away: "Show me top 10 customers by order value"
3. We'll show you the SQL we generated
4. See your results in a nice table
5. If it's chart-worthy, we'll throw in a visualization
6. Keep asking questions - we remember what you're talking about

## Development Roadmap

See [.claude/PLAN.md](.claude/PLAN.md) for the full implementation checklist and [.claude/STATUS.md](.claude/STATUS.md) for current progress.

**Current Status**: 🚧 Building MVP (Phase 1)

- ✅ UI Framework & Styling
- ✅ Database Layer
- ✅ Docker Setup
- 🚧 Data Generation Engine
- ⏳ Chat Interface
- ⏳ Observability (Langfuse)

## The Philosophy

We believe in:
- **Keep It Simple** - No over-engineering, just working code
- **Get It Done** - MVP first, fancy features later
- **Have Fun** - Life's too short for boring READMEs
- **Learn by Doing** - This is a practice project, mistakes are features

## Why "Slop"?

Because not every dataset needs to be a five-star meal. Sometimes you just need a heaping bowl of functional test data, and that's okay. Embrace the slop. Love the slop. Be the slop.

## License

Educational project. Made with 🍜 and ☕.

---

**Ready to start slopping?** Check out [SETUP.md](SETUP.md) for detailed setup instructions!