import os
import sys
import time
import glob
import traceback
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

# Import tools
from tools.search_docs.search_docs import search_docs
from mcp.schemas import SearchDocsInput, IngestDocsInput
from tools.ingest.ingest import ingest_docs
from tools.query_data.query_data import query_data
from tools.web_search.web_search import web_search

# Globals for stats
TOTAL_TESTS = 0
PASSED_TESTS = 0
FAILED_TESTS = 0
LATENCIES = {"search_docs": [], "query_data": [], "web_search": []}

def print_header(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def run_test(tool_name, test_name, query, test_fn):
    global TOTAL_TESTS, PASSED_TESTS, FAILED_TESTS
    TOTAL_TESTS += 1
    print(f"[{tool_name}] TEST: {test_name}")
    print(f"Query: {query}")
    
    start_time = time.time()
    try:
        passed, result_snippet = test_fn()
        latency = time.time() - start_time
        LATENCIES[tool_name].append(latency)
        
        print(f"Result (shortened): {result_snippet}")
        if passed:
            print(f"Status: PASS ({latency:.4f}s)\n")
            PASSED_TESTS += 1
        else:
            print(f"Status: FAIL ({latency:.4f}s)\n")
            FAILED_TESTS += 1
    except Exception as e:
        latency = time.time() - start_time
        LATENCIES[tool_name].append(latency)
        print(f"Result: EXCEPTION -> {str(e)}")
        # traceback.print_exc()
        print(f"Status: FAIL ({latency:.4f}s)\n")
        FAILED_TESTS += 1

# --- PREPARATION ---

def load_data():
    print_header("PREPARATION: Loading Data")
    
    # 1. Unstructured Data
    unstructured_dir = _PROJECT_ROOT / "dataset" / "unstructured"
    txt_files = glob.glob(str(unstructured_dir / "*.txt"))
    if not txt_files:
        print("Warning: No .txt files found in dataset/unstructured/")
    else:
        print(f"Ingesting {len(txt_files)} files into FAISS...")
        try:
            inp = IngestDocsInput(file_paths=txt_files)
            res = ingest_docs(inp)
            print(f"Ingested chunks: {res.total_chunks}")
        except Exception as e:
            print(f"Error during ingestion: {e}")
            
    # Structured data is automatically loaded by query_data module initialization.
    print("Structured data loaded via query_data._init_db().")

# --- TESTS ---

def test_search_docs():
    print_header("TESTING search_docs")
    
    def validate_search(query_str, expect_empty=False):
        try:
            inp = SearchDocsInput(query=query_str)
        except Exception as e:
            # Pydantic validation error for empty query might happen
            if expect_empty:
                return True, f"Input validation caught empty query: {e}"
            raise e
            
        out = search_docs(inp)
        
        if expect_empty:
            return len(out.results) == 0, f"Found {len(out.results)} results, expected 0"
            
        for r in out.results:
            if not hasattr(r, 'source') or not hasattr(r, 'page') or not hasattr(r, 'text'):
                return False, "Missing required schema fields (source, page, text)"
            if not r.source or not str(r.page).isdigit():
                return False, "Invalid source or page value"
                
        snippet = f"{len(out.results)} results found."
        if out.results:
             snippet += f" Top match source: {out.results[0].source}"
        return True, snippet

    run_test("search_docs", "Semantic query", "What themes are explored in Inception?", lambda: validate_search("What themes are explored in Inception?"))
    run_test("search_docs", "Specific query", "Who is the main character in Interstellar?", lambda: validate_search("Who is the main character in Interstellar?"))
    run_test("search_docs", "Cross-topic query", "What storytelling techniques are mentioned?", lambda: validate_search("What storytelling techniques are mentioned?"))
    run_test("search_docs", "Irrelevant query", "banana economics supply chain", lambda: validate_search("banana economics supply chain"))
    run_test("search_docs", "Empty query", "", lambda: validate_search("", expect_empty=True))

def test_query_data():
    print_header("TESTING query_data")
    
    def validate_query(q, expect_error=False, require_columns=None):
        out = query_data(q)
        if expect_error:
            if "error" not in out or not out["error"]:
                return False, "Expected error but got success"
            return True, f"Caught expected error: {out['error']}"
        else:
            if "error" in out and out["error"]:
                return False, f"Unexpected error: {out['error']}"
            if "columns" not in out or "rows" not in out or "row_count" not in out:
                return False, "Missing required schema keys (columns, rows, row_count)"
            if require_columns and not all(c in out["columns"] for c in require_columns):
                 return False, f"Missing required columns {require_columns}"
                 
            return True, f"Returned {out['row_count']} rows, columns: {out['columns']}"

    run_test("query_data", "Basic select", "SELECT title, rating FROM movies LIMIT 5", lambda: validate_query("SELECT title, rating FROM movies LIMIT 5", require_columns=["title", "rating"]))
    run_test("query_data", "Aggregation", "SELECT AVG(rating) FROM movies", lambda: validate_query("SELECT AVG(rating) FROM movies"))
    run_test("query_data", "Filter", "SELECT title FROM movies WHERE rating > 8", lambda: validate_query("SELECT title FROM movies WHERE rating > 8", require_columns=["title"]))
    run_test("query_data", "CSV table query", "SELECT * FROM movie LIMIT 3", lambda: validate_query("SELECT * FROM movie LIMIT 3"))
    run_test("query_data", "Invalid query", "SELECT * FROM unknown_table", lambda: validate_query("SELECT * FROM unknown_table", expect_error=True))
    run_test("query_data", "Unsafe query", "DROP TABLE movies", lambda: validate_query("DROP TABLE movies", expect_error=True))

def test_web_search():
    print_header("TESTING web_search")
    
    def validate_web(q, expect_empty=False):
        out = web_search(q)
        
        # Check if error returned as dict
        if out and isinstance(out[0], dict) and "error" in out[0]:
            if expect_empty:
                return True, f"Caught expected error/empty: {out[0]['error']}"
            return False, f"API Error: {out[0]['error']}"
            
        if expect_empty:
            return len(out) == 0, f"Found {len(out)} results, expected 0"
            
        if not out:
            return False, "No results returned for valid query"
            
        for r in out:
            if "snippet" not in r or "url" not in r or "date" not in r:
                return False, "Missing required keys (snippet, url, date)"
                
        return True, f"Returned {len(out)} results. Top URL: {out[0].get('url')}"

    run_test("web_search", "General", "latest Christopher Nolan movie", lambda: validate_web("latest Christopher Nolan movie"))
    run_test("web_search", "Factual", "Best Picture Oscar 2025 winner", lambda: validate_web("Best Picture Oscar 2025 winner"))
    run_test("web_search", "Current", "AI news today", lambda: validate_web("AI news today"))
    run_test("web_search", "Empty", "", lambda: validate_web("", expect_empty=True))

def print_summary():
    print_header("TEST SUMMARY")
    print(f"TOTAL TESTS: {TOTAL_TESTS}")
    print(f"PASSED     : {PASSED_TESTS}")
    print(f"FAILED     : {FAILED_TESTS}")
    
    print("\n--- AVERAGE LATENCY ---")
    for tool, lats in LATENCIES.items():
        if lats:
            avg = sum(lats) / len(lats)
            print(f"{tool:<15}: {avg:.4f}s")
        else:
            print(f"{tool:<15}: N/A")

if __name__ == "__main__":
    load_data()
    test_search_docs()
    test_query_data()
    test_web_search()
    print_summary()
