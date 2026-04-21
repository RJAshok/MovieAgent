"""
scripts/run_agent.py
--------------------
Demo runner for the Agentic RAG agent loop.

Usage:
    python scripts/run_agent.py
    python scripts/run_agent.py "Your custom question here"
"""

import sys
from pathlib import Path

# ── Ensure project root is on sys.path ──────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")

from app.agent.agent import run_agent


def main():
    # ── Demo questions ──────────────────────────────────────────────────
    demo_questions = [
        "Compare Inception and Interstellar ratings",
        "What is the highest grossing movie in the database?",
        "What themes are explored in the Inception review?",
        "What is 2 + 2?",
    ]

    if len(sys.argv) > 1:
        # Run a single custom question from CLI
        question = " ".join(sys.argv[1:])
        print(f"\n>>> Running agent for: \"{question}\"\n")
        answer = run_agent(question)
        print("\n" + "=" * 72)
        print("  FINAL ANSWER")
        print("=" * 72)
        print(answer)
    else:
        # Run the first demo question as the default showcase
        question = demo_questions[0]
        print(f"\n>>> Running agent for: \"{question}\"\n")
        answer = run_agent(question)
        print("\n" + "=" * 72)
        print("  FINAL ANSWER")
        print("=" * 72)
        print(answer)

        print("\n\n--- Other demo questions you can try ---")
        for i, q in enumerate(demo_questions[1:], start=2):
            print(f"  {i}. python scripts/run_agent.py \"{q}\"")


if __name__ == "__main__":
    main()
