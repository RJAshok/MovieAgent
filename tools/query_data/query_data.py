import sqlite3
import os
import re
import glob
import pandas as pd
from typing import Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "sample_movies.db")
CSV_FOLDER = os.environ.get("CSV_FOLDER", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dataset", "structured")))

_MEM_CONN = None

def _init_db():
    global _MEM_CONN
    
    # 1. Ensure sample_movies.db exists (original functionality)
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE movies (
                id INTEGER PRIMARY KEY,
                movie_name TEXT,
                budget INTEGER,
                opening_weekend INTEGER,
                worldwide_gross INTEGER,
                rotten_tomatoes_score INTEGER
            )
        ''')
        conn.commit()
        conn.close()

    # 2. Initialize in-memory database to hold everything
    _MEM_CONN = sqlite3.connect(':memory:', check_same_thread=False)
    _MEM_CONN.row_factory = sqlite3.Row
    
    # 3. Load tables from disk SQLite db into in-memory db
    _MEM_CONN.execute(f"ATTACH DATABASE '{DB_PATH}' AS disk")
    cursor = _MEM_CONN.cursor()
    cursor.execute("SELECT name FROM disk.sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for row in tables:
        table_name = row['name']
        _MEM_CONN.execute(f"CREATE TABLE {table_name} AS SELECT * FROM disk.{table_name}")
        
    _MEM_CONN.execute("DETACH DATABASE disk")

    # 4. Load CSV files into the in-memory db
    if os.path.exists(CSV_FOLDER):
        csv_files = glob.glob(os.path.join(CSV_FOLDER, "*.csv"))
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                # Clean up column names for SQL (e.g., remove spaces or special characters if needed)
                df.columns = [str(col).strip().replace(' ', '_').replace('-', '_') for col in df.columns]
                
                table_name = os.path.splitext(os.path.basename(csv_file))[0]
                if table_name.lower() == 'movie':
                    table_name = 'movies'
                
                # If table already exists, append to combine disk data and CSV data
                df.to_sql(table_name, _MEM_CONN, if_exists='append', index=False)
            except Exception as e:
                print(f"Error loading CSV {csv_file}: {e}")

# Initialize DB on module import
_init_db()

def query_data(query: str) -> Dict[str, Any]:
    """
    Query the structured datasets (both movies SQLite db and CSV files).
    
    WHEN TO USE:
    - Use this tool when you need numerical or tabular information about movies (e.g., budget, worldwide gross, opening weekend, rotten tomatoes score).
    - Use this tool when the user asks analytical questions (e.g., "What is the highest grossing movie?").
    
    WHEN NOT TO USE:
    - Do NOT use this tool for semantic search, finding plot summaries, or reading movie reviews. Use search_docs instead.
    
    The database contains tables like `movies` (from SQLite) and others derived from CSV files in the structured dataset.
    
    If you provide natural language, the tool will return an error reminding you to provide a valid SQL query.
    For best results, pass a valid SQL query string directly.
    """
    query = query.strip()
    
    # Natural language detection (if it doesn't look like SQL)
    if not re.match(r'^(SELECT|WITH)\b', query, re.IGNORECASE):
        return {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "error": "Input appears to be natural language. Please provide a valid SQL query (e.g., starts with SELECT)."
        }

    # Safety: Block write operations
    if re.search(r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|GRANT|REVOKE)\b|\bREPLACE\s+INTO\b', query, re.IGNORECASE):
        return {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "error": "Write operations are not permitted. Only read operations (SELECT) are allowed."
        }

    try:
        cursor = _MEM_CONN.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if not rows:
            return {
                "columns": [],
                "rows": [],
                "row_count": 0
            }
            
        columns = list(rows[0].keys())
        data = [list(row) for row in rows]
        
        return {
            "columns": columns,
            "rows": data,
            "row_count": len(data)
        }
    except Exception as e:
        return {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "error": str(e)
        }
