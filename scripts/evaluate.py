import os
import sys
import logging
import warnings
from pathlib import Path

# Enable real-time logging (unbuffered output)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

# --- Suppress all warnings and progress bars globally ---
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TQDM_DISABLE"] = "1"
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", module="google.generativeai")
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

# --- Ensure project root is on sys.path ---
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Ensure sample_movies.db is removed to pick up fresh CSV data
_db_path = _PROJECT_ROOT / "tools" / "query_data" / "sample_movies.db"
if _db_path.exists():
    try:
        _db_path.unlink()
    except Exception as e:
        print(f"Warning: could not delete {_db_path}: {e}")

# Load .env (requires python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv(_PROJECT_ROOT / ".env")
except ImportError:
    pass

from app.agent.agent import run_agent

QUESTIONS = [
    {
        "id": 1,
        "question": "What was the budget and revenue for Project Hail Mary?",
        "tools_required": "SQL / CSV tool",
        "expected_outcome": "Single numbers for budget and revenue.",
    },
    {
        "id": 2,
        "question": "What is the plot summary of Tron: Ares?",
        "tools_required": "RAG / doc search",
        "expected_outcome": "Quoted explanation/summary with citation from the text.",
    },
    {
        "id": 3,
        "question": "What is the budget for F1 The Movie, and how does its concept compare to the plot of Tron: Ares?",
        "tools_required": "SQL + RAG (multi-tool)",
        "expected_outcome": "Composed answer retrieving F1 The Movie's budget via SQL and Tron's plot via RAG.",
    },
    {
        "id": 4,
        "question": "What is the current worldwide box office gross for Dune: Part Two?",
        "tools_required": "Web search",
        "expected_outcome": "Live box office numbers with source URL.",
    },
    {
        "id": 5,
        "question": "Who is the director of the upcoming Superman (2025) movie?",
        "tools_required": "Web search or RAG",
        "expected_outcome": "Director's name (James Gunn) with source.",
    },
    {
        "id": 6,
        "question": "Which movies in the structured database have a rotten tomatoes score higher than 85?",
        "tools_required": "SQL / CSV tool",
        "expected_outcome": "List of movies with their scores.",
    },
    {
        "id": 7,
        "question": "What strategic themes or plot points are highlighted in the reviews for The Fantastic Four First Steps?",
        "tools_required": "RAG / doc search",
        "expected_outcome": "Bullet points discussing the themes with citations.",
    },
    {
        "id": 8,
        "question": "Compare the worldwide gross of Thunderbolts* (from the database) with the expected box office performance mentioned in the documents for Spider-Man No Way Home.",
        "tools_required": "SQL + RAG (multi-tool)",
        "expected_outcome": "Comparison combining the SQL gross figure and the RAG text references.",
    },
    {
        "id": 9,
        "question": "What were the major movie industry news or casting announcements from last week?",
        "tools_required": "Web search",
        "expected_outcome": "Recent news summary with web sources.",
    },
    {
        "id": 10,
        "question": "What is the airspeed velocity of an unladen swallow?",
        "tools_required": "None - refuse",
        "expected_outcome": "Polite refusal stating it lacks the information.",
    },
    {
        "id": 11,
        "question": "What is the rotten tomatoes score for Until Dawn?",
        "tools_required": "SQL / CSV tool",
        "expected_outcome": "The rotten tomatoes score for Until Dawn.",
    },
    {
        "id": 12,
        "question": "Can you summarize the plot for The Long Walk based on the local reviews?",
        "tools_required": "RAG / doc search",
        "expected_outcome": "Plot summary with citations.",
    },
    {
        "id": 13,
        "question": "Which movie has the highest worldwide gross among the local database?",
        "tools_required": "SQL / CSV tool",
        "expected_outcome": "The name of the highest grossing movie and its gross amount.",
    },
    {
        "id": 14,
        "question": "What is the budget for Jurassic World Rebirth?",
        "tools_required": "SQL / CSV tool",
        "expected_outcome": "The budget amount for Jurassic World Rebirth.",
    },
    {
        "id": 15,
        "question": "How does the plot of Coolie compare with The Drama (2026)?",
        "tools_required": "RAG / doc search",
        "expected_outcome": "Comparison of themes and plot based on documents.",
    },
    {
        "id": 16,
        "question": "What is the latest news regarding the development of Ballerina?",
        "tools_required": "Web search or RAG",
        "expected_outcome": "News summary with sources.",
    },
    {
        "id": 17,
        "question": "Is Spider-Man: No Way Home considered a financial success based on its opening weekend versus its budget?",
        "tools_required": "SQL / CSV tool",
        "expected_outcome": "Analysis of opening weekend vs budget.",
    },
    {
        "id": 18,
        "question": "What do the documents say about the visual style of Superman (2025)?",
        "tools_required": "RAG / doc search",
        "expected_outcome": "Description of the visual style with citations.",
    },
    {
        "id": 19,
        "question": "Find the total budget for F1: The Movie and Thunderbolts* combined.",
        "tools_required": "SQL / CSV tool",
        "expected_outcome": "Combined total budget of the two movies.",
    },
    {
        "id": 20,
        "question": "What are the common themes between Thunderbolts* and The Fantastic Four: First Steps based on the documents?",
        "tools_required": "RAG / doc search",
        "expected_outcome": "Shared themes and motifs with citations.",
    }
]

def main():
    report_path = _PROJECT_ROOT / "evaluation_results.md"
    
    print(f"Writing evaluation to {report_path}")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Agent Evaluation Results\n\n")
        f.write("| # | Question | Tools Required | Expected Outcome | Actual Output |\n")
        f.write("|---|---|---|---|---|\n")

    for q in QUESTIONS:
        print(f"\n[{q['id']}/20] Evaluating: {q['question']}")
        
        try:
            # We let run_agent print its trace normally so the user can watch the progress.
            actual_output = run_agent(q["question"])
            
            # Formatting to prevent breaking the markdown table
            # We replace newlines with HTML line breaks and escape pipes
            formatted_output = str(actual_output).replace("\n", "<br>").replace("|", "\\|")
            
            with open(report_path, "a", encoding="utf-8") as f:
                f.write(f"| {q['id']} | {q['question']} | {q['tools_required']} | {q['expected_outcome']} | {formatted_output} |\n")
                
        except Exception as e:
            print(f"Error evaluating Q{q['id']}: {e}")
            with open(report_path, "a", encoding="utf-8") as f:
                f.write(f"| {q['id']} | {q['question']} | {q['tools_required']} | {q['expected_outcome']} | **ERROR**: {e} |\n")

    print(f"\nEvaluation complete. Results written to {report_path}")

if __name__ == "__main__":
    main()
