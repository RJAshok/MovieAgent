import sqlite3
import os
import re
from typing import Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "sample_movies.db")

def _init_db():
    if os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE movies (
            id INTEGER PRIMARY KEY,
            title TEXT,
            budget REAL,
            revenue REAL,
            rating REAL
        )
    ''')
    sample_data = [
        (1, 'Inception', 160000000, 825532764, 8.8),
        (2, 'The Dark Knight', 185000000, 1004558444, 9.0),
        (3, 'Avatar', 237000000, 2787965087, 7.8),
        (4, 'Pulp Fiction', 8000000, 213928762, 8.9),
        (5, 'The Matrix', 63000000, 463517383, 8.7)
    ]
    cursor.executemany('INSERT INTO movies VALUES (?, ?, ?, ?, ?)', sample_data)
    conn.commit()
    conn.close()

# Initialize DB on module import
_init_db()

def query_data(query: str) -> Dict[str, Any]:
    """
    Query the structured movies dataset.
    
    WHEN TO USE:
    - Use this tool when you need numerical or tabular information about movies (e.g., budget, revenue, ratings).
    - Use this tool when the user asks analytical questions (e.g., "What is the highest grossing movie?").
    
    WHEN NOT TO USE:
    - Do NOT use this tool for semantic search, finding plot summaries, or reading movie reviews. Use search_docs instead.
    
    The database is a SQLite database with a single table named `movies`.
    Schema:
    - id (INTEGER)
    - title (TEXT)
    - budget (REAL)
    - revenue (REAL)
    - rating (REAL)
    
    If you provide natural language, the tool will return an error reminding you to provide a valid SQL query.
    For best results, pass a valid SQL query string directly.
    """
    query = query.strip()
    
    # Very basic natural language detection (if it doesn't look like SQL)
    if not re.match(r'^(SELECT|WITH)\b', query, re.IGNORECASE):
        return {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "error": (
                "Input appears to be natural language. "
                "Please provide a valid SQL query. "
                "Schema for 'movies' table: id(INTEGER), title(TEXT), budget(REAL), revenue(REAL), rating(REAL)."
            )
        }

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
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
    finally:
        if 'conn' in locals():
            conn.close()
