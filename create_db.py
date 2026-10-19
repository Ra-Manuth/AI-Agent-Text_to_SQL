import os
from dotenv import load_dotenv
from google import genai
import re
import sqlite3


load_dotenv()
client = genai.Client()


def generate_sql(question):
    prompt = f"""
    You are an expert SQL assistant.
    Return only raw SQL. Do not use markdown. Do not wrap in quotes.
    Use table: customers
    Columns: id, name, country, revenue

    Question: {question}
    """
    
    response = client.models.generate_content(
        model='gemini-3.8-flash', 
        contents=prompt
    )
    return response.text.strip()

def clean_sql(sql):
    sql = re.sub(r'```sql', '', sql, flags=re.IGNORECASE)
    sql = re.sub(r'```', '', sql)
    return sql.strip()


def run_query(sql):
    conn = sqlite3.connect("sales.db")
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        

        if sql.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            conn.commit()
            results = "ប្រតិបត្តិការបានជោគជ័យ! ទិន្នន័យត្រូវបានបញ្ចូលទៅក្នុង Database រួចរាល់។"
        else:
            results = cursor.fetchall()
            
    except Exception as e:
        results = str(e)
    conn.close()
    return results


def ask_database(question):
    sql = generate_sql(question)
    sql = clean_sql(sql)
    print("\nGenerated SQL:\n", sql)
    result = run_query(sql)
    return result

if __name__ == "__main__":
    while True:
        question = input("\nPlease enter your question: ")
        if question.lower() in ['exit', 'quit', 'stop']:
            break
        result = ask_database(question)
        print("Result:", result)