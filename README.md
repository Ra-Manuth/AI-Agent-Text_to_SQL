# Text-to-SQL AI Agent

Ask questions about your database in plain English and get answers back. The agent uses Google Gemini to turn your question into SQL, runs it against your database, and prints the result.

The project includes **two versions**:

| | SQL Server version | SQLite version |
| --- | --- | --- |
| Script | `sql_assistant.py` | `sqlite_assistant.py` |
| Database | Microsoft SQL Server (SSMS) with Windows Authentication | Local SQLite file (`sales.db`) |
| Schema | Auto-detected from the live database | Fixed table: `customers(id, name, country, revenue)` |
| SQL dialect | T-SQL | SQLite |
| Safety checks | Prompt guardrails plus code-level blocks | None (for learning and demos only) |

## Features

- **Natural language to SQL**: type a question, get a query and its result
- **Live schema detection** (SQL Server): reads tables, columns, data types, and `IDENTITY` columns, so generated `INSERT` statements skip auto-generated IDs
- **Automatic ODBC driver selection**: picks the installed SQL Server driver (17 or 18)
- **Safety guardrails**: blocks dangerous operations before they run
- **Schema refresh**: type `reload`, or let the app refresh automatically after `CREATE TABLE` or `ALTER TABLE`
- **Readable output**: query results are printed as a simple table

## How it works

```
Your question
     │
     ▼
Gemini (with your live database schema)
     │
     ▼
Generated SQL ──► Clean markdown ──► Safety checks ──► Execute ──► Results
```

1. `get_database_schema()` reads the schema from SQL Server and formats it for the prompt.
2. `generate_sql()` sends your question and the schema to Gemini and asks for raw T-SQL only.
3. `clean_sql()` strips any markdown code fences from the response.
4. `run_query()` checks the SQL against the safety rules, executes it, and returns the rows or a success message.

## Tech stack

- Python 3.9+
- [Google Gemini API](https://ai.google.dev/) via the `google-genai` SDK
- [pyodbc](https://github.com/mkleehammer/pyodbc) for SQL Server
- `sqlite3` (built into Python) for the SQLite version
- [python-dotenv](https://pypi.org/project/python-dotenv/) for loading the API key

## Project structure

```
AI-Agent-Text-to-SQL/
├── sql_assistant.py        # SQL Server (SSMS) version
├── sqlite_assistant.py     # SQLite version
├── create_db.py            # Creates the sample SQLite database
├── sales.db                # Sample SQLite database
├── requirements.txt        # Python dependencies
├── .env                    # Your API key (never commit this file)
├── .gitignore
└── README.md
```

## Getting started

### Prerequisites

- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
- For the SQL Server version:
  - Windows with SQL Server (Express works) and a database named `SalesDB`
  - [ODBC Driver 17 or 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

### 1. Clone the repository

```bash
git clone https://github.com/Ra-Manuth/AI-Agent-Text-to-SQL.git
cd AI-Agent-Text-to-SQL
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` should contain:

```
google-genai
python-dotenv
pyodbc
```

### 4. Add your API key

Create a file named `.env` in the project folder:

```
GEMINI_API_KEY=your_api_key_here
```

> **Warning:** Never upload your `.env` file to GitHub. Make sure `.env` is listed in `.gitignore`.

### 5. Run

**SQL Server version**

```bash
python sql_assistant.py
```

**SQLite version**

```bash
python create_db.py
python sqlite_assistant.py
```

## Usage

Type a question and press Enter. The app shows the generated SQL first, then the result.

Example session (illustrative):

```
Ask AI DBA: Show the top 3 customers by revenue

Generated T-SQL:
 SELECT TOP 3 * FROM dbo.Customers ORDER BY Revenue DESC;

Result Table:
...
```

Commands in the SQL Server version:

| Command | Action |
| --- | --- |
| `reload` | Refresh the database schema |
| `exit`, `quit`, `stop` | Close the assistant |

## Safety guardrails (SQL Server version)

Two layers protect your data:

1. **Prompt policy**: the model is told to refuse `DROP`, `TRUNCATE`, and `UPDATE`/`DELETE` without a `WHERE` clause.
2. **Code checks**: `run_query()` blocks SQL containing `DROP TABLE`, `DROP DATABASE`, or `TRUNCATE TABLE`, and blocks `DELETE FROM` statements without `WHERE`.

> **Important:** These are basic keyword checks, not complete protection. Generated SQL is executed directly, and statements that change data are committed automatically. Always read the generated SQL, use a test database, and prefer a least-privilege or read-only account. The SQLite version has no safety checks at all.

## Configuration

| Setting | Where | Default |
| --- | --- | --- |
| `SERVER_NAME` | top of `sql_assistant.py` | `.\SQLEXPRESS` |
| `DATABASE_NAME` | top of `sql_assistant.py` | `SalesDB` |
| Gemini model | `generate_sql()` | set in the script |

Gemini model names change over time. If you get a "model not found" error, check Google's current model list and update the model name in `generate_sql()`.

## Limitations

- The SQL Server version uses Windows Authentication and a local instance by default.
- Generated SQL can be wrong. Review it before relying on the results.
- The SQLite version only knows the `customers` table.

## Roadmap

- [ ] Ask for confirmation before running statements that change data
- [ ] Read-only mode
- [ ] Load server, database, and model name from `.env`
- [ ] Support SQL Server logins, not only Windows Authentication
- [ ] Simple web interface with Streamlit

## License

Add a license of your choice (for example, MIT) by creating a `LICENSE` file.

## Author

Built by **Nuth**, a Bachelor of FinTech student at ACLEDA University of Business, as a hands-on project combining databases and AI.
