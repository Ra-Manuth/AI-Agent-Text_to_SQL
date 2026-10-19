import os
import re
import pyodbc
from dotenv import load_dotenv
from google import genai

# Load API Key from .env file
load_dotenv()
client = genai.Client()

# ==========================================
# 1. SSMS DATABASE CONFIGURATION
# ==========================================
# ==========================================
# 1. SSMS DATABASE CONFIGURATION
# ==========================================
SERVER_NAME = r'.\SQLEXPRESS'
DATABASE_NAME = 'SalesDB'

# Automatically pick the installed SQL Server ODBC driver (Driver 18 or 17)
available_drivers = [d for d in pyodbc.drivers() if 'SQL Server' in d]
DRIVER_NAME = available_drivers[-1] if available_drivers else 'ODBC Driver 17 for SQL Server'

# Windows Authentication Connection String matching your SSMS settings
CONN_STR = (
    f"Driver={{{DRIVER_NAME}}};"
    f"Server={SERVER_NAME};"
    f"Database={DATABASE_NAME};"
    f"Trusted_Connection=yes;"
    f"TrustServerCertificate=yes;"
)

# ==========================================
# 2. DYNAMIC SCHEMA AUTO-DETECTION
# ==========================================
def get_database_schema():
    """Automatically extracts tables, columns, data types, and IDENTITY properties from SSMS."""
    schema_query = """
    SELECT 
        t.TABLE_SCHEMA,
        t.TABLE_NAME,
        c.COLUMN_NAME,
        c.DATA_TYPE,
        c.IS_NULLABLE,
        COLUMNPROPERTY(OBJECT_ID(t.TABLE_SCHEMA + '.' + t.TABLE_NAME), c.COLUMN_NAME, 'IsIdentity') AS IS_IDENTITY
    FROM INFORMATION_SCHEMA.TABLES t
    INNER JOIN INFORMATION_SCHEMA.COLUMNS c 
        ON t.TABLE_NAME = c.TABLE_NAME AND t.TABLE_SCHEMA = c.TABLE_SCHEMA
    WHERE t.TABLE_TYPE = 'BASE TABLE' 
      AND t.TABLE_NAME != 'sysdiagrams'
    ORDER BY t.TABLE_NAME, c.ORDINAL_POSITION;
    """
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute(schema_query)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "No tables found in the database yet."

        schema_dict = {}
        for row in rows:
            table_full_name = f"{row.TABLE_SCHEMA}.{row.TABLE_NAME}"
            if table_full_name not in schema_dict:
                schema_dict[table_full_name] = []
            
            col_info = f"{row.COLUMN_NAME} ({row.DATA_TYPE}"
            if row.IS_IDENTITY == 1:
                col_info += ", PRIMARY KEY IDENTITY - DO NOT INSERT"
            elif row.IS_NULLABLE == 'NO':
                col_info += ", NOT NULL"
            col_info += ")"
            
            schema_dict[table_full_name].append(col_info)

        schema_text = ""
        for table, cols in schema_dict.items():
            schema_text += f"- Table {table}: " + ", ".join(cols) + "\n"
        
        return schema_text.strip()

    except Exception as e:
        return f"Error fetching schema: {str(e)}"

# ==========================================
# 3. AI SQL GENERATOR (9-YEAR DBA PROMPT)
# ==========================================
def generate_sql(question, schema_context):
    prompt = f"""
    ### ROLE:
    You are a Senior Microsoft SQL Server Database Administrator (DBA) and Architect with over 9 years of enterprise experience. You specialize in high-performance T-SQL query optimization, database security, data integrity, and automated database administration within SQL Server Management Studio (SSMS).

    ### TASKS & CAPABILITIES:
    1. CRUD Operations: Write optimized SELECT (using CTEs, Window Functions, JOINs, TOP), INSERT, UPDATE, and DELETE statements.
    2. Database Objects: Create and manage Tables, Views, Stored Procedures, Functions, Indexes, and Triggers (FOR/AFTER/INSTEAD OF) for auditing and automation.
    3. Security & Governance: Enforce data protection, prevent SQL Injection, manage role-based permissions, and avoid destructive unverified commands.
    4. Performance Tuning: Write SARGable queries and avoid unnecessary cursors.

    ### CONTEXT (LIVE SSMS DATABASE SCHEMA):
    Target DBMS: Microsoft SQL Server (T-SQL Dialect)
    Active Schema Details:
    {schema_context}
    *CRITICAL RULE: Never include columns marked as 'IDENTITY' in your INSERT statements.*

    ### STRICT OUTPUT CONSTRAINTS:
    - Return ONLY valid, raw executable T-SQL code.
    - Do NOT include markdown formatting (no ```sql or ``` tags).
    - Do NOT include explanations, conversational text, or comments.
    - Do NOT include the 'GO' batch separator, as pyodbc cannot execute 'GO'.
    - SAFETY GUARDRAIL: If the user requests to DROP a table/database, TRUNCATE data, or execute an UPDATE/DELETE without a WHERE clause, return EXACTLY: "ERROR: Unsafe operation blocked by AI DBA Policy. Please specify a WHERE clause or confirm administrative override."

    ### USER REQUEST:
    {question}
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash', 
        contents=prompt
    )
    return response.text.strip()

# ==========================================
# 4. CLEAN & EXECUTE T-SQL IN SSMS
# ==========================================
def clean_sql(sql):
    sql = re.sub(r'```sql', '', sql, flags=re.IGNORECASE)
    sql = re.sub(r'```', '', sql)
    return sql.strip()

def run_query(sql):
    
    if sql.startswith("ERROR:"):
        return f"🛡️ [AI SECURITY BLOCK] {sql}"

    
    forbidden_keywords = ["DROP TABLE", "DROP DATABASE", "TRUNCATE TABLE"]
    upper_sql = sql.upper()
    if any(keyword in upper_sql for keyword in forbidden_keywords):
        return "🛑 [SYSTEM BLOCK] The system doesn't alloow to DROP or TRUNCATE!"
        
    if "DELETE FROM" in upper_sql and "WHERE" not in upper_sql:
         return "🛑 [SYSTEM BLOCK] មិនអាចលុបទិន្នន័យ (DELETE) ដោយគ្មានលក្ខខណ្ឌ (WHERE) បានទេ!"

    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        
        cursor.execute(sql)
        
        if cursor.description is not None:
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            results = {
                "columns": columns,
                "data": [tuple(row) for row in rows]
            }
        else:
            conn.commit()
            results = f"Transaction Successfully!"
                
    except Exception as e:
        results = f"SQL Server Error: {str(e)}"
    finally:
        if 'conn' in locals():
            conn.close()
            
    return results
# ==========================================
# 5. MAIN APPLICATION LOOP
# ==========================================
if __name__ == "__main__":
    print("====================================================")
    print(" Initializing Enterprise AI DBA Assistant (SSMS)...")
    print("====================================================")
    
    current_schema = get_database_schema()
    print("\n📊 Connected! Detected Database Schema:")
    print(current_schema)
    print("\n💡 Tip: Type 'reload' after creating new tables to refresh the schema, or 'exit' to quit.")

    while True:
        question = input("\nAsk AI DBA: ").strip()
        
        if not question:
            continue
        if question.lower() in ['exit', 'quit', 'stop']:
            print("Closing AI DBA Assistant. Goodbye!")
            break
        if question.lower() == 'reload':
            current_schema = get_database_schema()
            print("\n🔄 Schema Refreshed:\n", current_schema)
            continue
            
        sql = generate_sql(question, current_schema)
        sql = clean_sql(sql)
        print("\nGenerated T-SQL:\n", sql)
        
        result = run_query(sql)
        
        # Pretty print table results if it's a SELECT query
        if isinstance(result, dict):
            print("\nResult Table:")
            print(" | ".join(result["columns"]))
            print("-" * 50)
            for row in result["data"]:
                print(" | ".join(str(val) for val in row))
        else:
            print("\nResult:", result)
            
        # Automatically refresh schema if a new table was created or altered
        if sql.upper().startswith(("CREATE TABLE", "ALTER TABLE")):
            current_schema = get_database_schema()
            print("🔄 (Schema automatically updated with your new table changes!)")