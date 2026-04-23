import os
import sys
import json
import shutil
from pathlib import Path

# Ensure the root directory is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

def check_venv():
    """Verify the script is running inside a virtual environment."""
    if sys.prefix == sys.base_prefix:
        print("Error: You are not running in a virtual environment.")
        print("Please activate your virtual environment (e.g., 'source venv/bin/activate' or 'venv\\Scripts\\activate') and try again.")
        sys.exit(1)

def check_env_keys():
    """Verify API keys are present in .env file."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Warning: python-dotenv not installed. Skipping .env loading.")

    tavily = os.environ.get("TAVILY_API_KEY")
    gemini = os.environ.get("GEMINI_API_KEY")
    
    if not tavily or "your_tavily_api_key_here" in tavily:
        print("Error: TAVILY_API_KEY is missing or invalid in the .env file.")
        sys.exit(1)
    if not gemini or "your_gemini_api_key_here" in gemini:
        print("Error: GEMINI_API_KEY is missing or invalid in the .env file.")
        sys.exit(1)

def load_embedding_model():
    """Load the embedding model to ensure it is downloaded."""
    print("Loading embedding model, please wait...")
    try:
        from sentence_transformers import SentenceTransformer
        SentenceTransformer('all-MiniLM-L6-v2')
        print("Embedding model loaded successfully.")
    except Exception as e:
        print(f"Error loading embedding model: {e}")
        sys.exit(1)

def check_and_ingest_unstructured():
    """Check if FAISS vector store is empty and prompt for data ingestion."""
    from config.faiss_config import META_PATH
    from mcp.schemas import IngestDocsInput
    from tools.ingest.ingest import ingest_docs

    is_empty = True
    if META_PATH.exists():
        try:
            with open(META_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    is_empty = False
        except Exception:
            pass

    while True:
        if is_empty:
            print("\nUnstructured data (Vector store) is empty.")
            ans = "y"
        else:
            ans = input("\nDo you want to store some more unstructured data? (y/n): ").strip().lower()
            if ans != 'y':
                break
                
        if ans == 'y':
            dir_path = input("Please point to the directory with only the .txt data files: ").strip()
            dp = Path(dir_path)
            if not dp.is_dir():
                print("Error: The path provided is not a valid directory. Try again.")
                continue
                
            files = list(dp.iterdir())
            if not files:
                print("Error: The directory is empty. Try again.")
                continue
                
            non_txt = [f.name for f in files if f.is_file() and f.suffix.lower() != '.txt']
            if non_txt:
                print(f"Error: The directory contains files other than .txt: {', '.join(non_txt)}")
                print("Please provide a directory containing ONLY .txt files.")
                continue
                
            txt_files = [str(f.resolve()) for f in files if f.is_file() and f.suffix.lower() == '.txt']
            print(f"Ingesting {len(txt_files)} text files...")
            try:
                result = ingest_docs(IngestDocsInput(file_paths=txt_files))
                print(f"Successfully ingested {result.total_chunks} chunks into FAISS.")
                is_empty = False
            except Exception as e:
                print(f"Error during ingestion: {e}")

def check_and_ingest_structured():
    """Check if SQLite database is empty and prompt for CSV data."""
    db_path = _PROJECT_ROOT / "tools" / "query_data" / "sample_movies.db"
    csv_folder = _PROJECT_ROOT / "dataset" / "structured"
    
    is_empty = not db_path.exists()
    csv_folder.mkdir(parents=True, exist_ok=True)
    
    while True:
        if is_empty:
            print("\nStructured data (SQLite store) is empty.")
            ans = "y"
        else:
            ans = input("\nDo you want to store some more structured data? (y/n): ").strip().lower()
            if ans != 'y':
                break
                
        if ans == 'y':
            file_path = input("Please point to the .csv file: ").strip()
            fp = Path(file_path)
            if not fp.is_file() or fp.suffix.lower() != '.csv':
                print("Error: The path provided is not a valid .csv file. Try again.")
                continue
            
            # Verify schema
            try:
                import pandas as pd
                df = pd.read_csv(fp)
                expected_cols = {'id', 'title', 'budget', 'revenue', 'rating'}
                actual_cols = {str(c).strip().lower() for c in df.columns}
                if not expected_cols.issubset(actual_cols):
                    print(f"Error: The .csv file schema does not match the database.")
                    print(f"Expected columns to include (case-insensitive): {expected_cols}")
                    print(f"Found columns: {actual_cols}")
                    print("Please fix your CSV and try again.")
                    continue
            except Exception as e:
                print(f"Error reading the CSV file: {e}")
                continue
                
            dest = csv_folder / fp.name
            shutil.copy2(fp, dest)
            print(f"Copied {fp.name} to {dest}.")
            
            try:
                from tools.query_data import query_data
                query_data._init_db()
                print("Structured data loaded into SQLite successfully.")
                is_empty = False
            except Exception as e:
                print(f"Error initializing SQLite database with your CSV: {e}")
                print("Please fix your CSV file and try again.")
                if dest.exists():
                    dest.unlink()

def interactive_loop():
    """Run the interactive agent loop."""
    print("\n" + "="*50)
    print(" Agent Interface Ready")
    print(" Type 'exit' to quit")
    print("="*50)
    
    # Import agent here to avoid circular imports and ensure all configs are set
    from app.agent.agent import run_agent
    
    while True:
        try:
            query = input("\nQuery: ").strip()
            if not query:
                continue
            if query.lower() == 'exit':
                print("Exiting...")
                break
                
            run_agent(query)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")

def main():
    check_venv()
    check_env_keys()
    load_embedding_model()
    check_and_ingest_unstructured()
    check_and_ingest_structured()
    interactive_loop()

if __name__ == "__main__":
    main()
