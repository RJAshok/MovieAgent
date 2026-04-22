"""
app/agent/agent.py
------------------
Core agent loop — the reasoning engine of the Agentic RAG system.

Architecture:
    1. Receive user question.
    2. Loop (max 8 steps):
       a. Ask LLM → tool call or final.
       b. If tool → execute, append result to context.
       c. If final → break.
    3. Sufficiency check via LLM.
    4. If sufficient → generate cited answer.
       If not → refuse gracefully.

Public API:
    run_agent(question: str) -> str
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ── Ensure project root is importable ────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.agent.llm import ask_llm
from app.agent.prompts import ANSWER_PROMPT, DECISION_PROMPT, SUFFICIENCY_PROMPT

# ── Tool imports (used as-is, never modified) ───────────────────────────────
from tools.search_docs.search_docs import search_docs as _search_docs
from tools.query_data.query_data import query_data as _query_data
from tools.web_search.web_search import web_search as _web_search
from mcp.schemas import SearchDocsInput

MAX_STEPS = 8


# ── Tool dispatcher ─────────────────────────────────────────────────────────

def _call_tool(tool_name: str, tool_input: str) -> dict | list | str:
    """
    Dispatch a tool call by name and return its output.
    Returns an error dict if the tool fails.
    """
    try:
        if tool_name == "search_docs":
            result = _search_docs(SearchDocsInput(query=tool_input))
            # Convert Pydantic model to serialisable dict
            return result.model_dump()

        elif tool_name == "query_data":
            return _query_data(tool_input)

        elif tool_name == "web_search":
            return _web_search(tool_input)

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as exc:
        return {"error": f"{tool_name} failed: {exc}"}


# ── Trace printer ────────────────────────────────────────────────────────────

def _print_trace(question: str, context: list[dict], final_answer: str) -> None:
    """Print a structured trace of the agent's reasoning to stdout."""
    print(f"\n{'='*72}")
    print(f"  AGENT TRACE")
    print(f"{'='*72}")
    print(f"\n  Question: {question}\n")

    for entry in context:
        print(f"  Step {entry['step']}:")
        print(f"    Tool  : {entry['tool']}")
        print(f"    Input : {entry['input']}")
        # Truncate long outputs for readability
        output_str = json.dumps(entry["output"], default=str)
        if len(output_str) > 300:
            output_str = output_str[:300] + "..."
        print(f"    Output: {output_str}")
        print()

    print(f"  Final Answer:\n")
    for line in final_answer.strip().split("\n"):
        print(f"    {line}")
    print(f"\n  Steps used: {len(context)}/{MAX_STEPS}")
    print(f"{'='*72}\n")


# ── Core agent loop ─────────────────────────────────────────────────────────

def run_agent(question: str) -> str:
    """
    Run the agentic reasoning loop for *question*.

    Returns the final answer string (with citations),
    or a graceful refusal if context is insufficient.
    """
    context: list[dict] = []   # accumulated tool results
    step = 0

    # ── Reasoning loop ──────────────────────────────────────────────────
    while step < MAX_STEPS:
        step += 1

        # Build the decision prompt with current context
        prompt = DECISION_PROMPT.format(
            context=json.dumps(context, indent=2, default=str) if context else "No context collected yet.",
            question=question,
            step=step,
            max_steps=MAX_STEPS,
        )

        # Ask LLM what to do next
        try:
            decision = ask_llm(prompt)
        except ValueError:
            # Invalid JSON on first try — retry once
            try:
                decision = ask_llm(prompt)
            except ValueError:
                # Still invalid — stop and refuse
                return "I encountered an error while reasoning. Please try again."

        # ── Handle decision ─────────────────────────────────────────────
        if decision.get("type") == "final":
            break

        if decision.get("type") == "tool":
            tool_name = decision.get("tool", "")
            tool_input = decision.get("input", "")

            # Execute the tool
            tool_output = _call_tool(tool_name, tool_input)

            # Append structured result to context
            context.append({
                "step": step,
                "tool": tool_name,
                "input": tool_input,
                "output": tool_output,
            })
        else:
            # Unrecognised decision type — treat as final
            break

    # ── Sufficiency check (with retry if steps remain) ────────────────────
    sufficiency_retries = 0
    max_sufficiency_retries = 2  # allow up to 2 rounds of "go back and gather more"

    while True:
        suff_prompt = SUFFICIENCY_PROMPT.format(
            question=question,
            context=json.dumps(context, indent=2, default=str) if context else "No context collected.",
        )

        try:
            suff_result = ask_llm(suff_prompt)
        except ValueError:
            suff_result = {"sufficient": False}

        if suff_result.get("sufficient", False):
            break  # enough info — proceed to answer

        # Not sufficient — can we gather more?
        if step >= MAX_STEPS or sufficiency_retries >= max_sufficiency_retries:
            # Exhausted steps or retries — refuse
            refusal = "I do not have enough information to answer this question."
            _print_trace(question, context, refusal)
            return refusal

        # Still have steps — go back and gather more context
        sufficiency_retries += 1
        context.append({
            "step": "hint",
            "tool": "system",
            "input": "sufficiency_check_failed",
            "output": "The information gathered so far is NOT enough. "
                      "Try different search queries, alternative tools, "
                      "or rephrase your approach to find the answer.",
        })

        # Resume the reasoning loop
        while step < MAX_STEPS:
            step += 1
            prompt = DECISION_PROMPT.format(
                context=json.dumps(context, indent=2, default=str),
                question=question,
                step=step,
                max_steps=MAX_STEPS,
            )
            try:
                decision = ask_llm(prompt)
            except ValueError:
                try:
                    decision = ask_llm(prompt)
                except ValueError:
                    break

            if decision.get("type") == "final":
                break

            if decision.get("type") == "tool":
                tool_name = decision.get("tool", "")
                tool_input = decision.get("input", "")
                tool_output = _call_tool(tool_name, tool_input)
                context.append({
                    "step": step,
                    "tool": tool_name,
                    "input": tool_input,
                    "output": tool_output,
                })
            else:
                break

    # ── Generate final answer ───────────────────────────────────────────
    answer_prompt = ANSWER_PROMPT.format(
        question=question,
        context=json.dumps(context, indent=2, default=str),
    )

    try:
        answer_response = ask_llm(answer_prompt)
        # The answer prompt asks for structured text, but the LLM may
        # return it as JSON with an "answer" key or as raw text.
        if isinstance(answer_response, dict):
            final_answer = answer_response.get("answer", json.dumps(answer_response, indent=2))
        else:
            final_answer = str(answer_response)
    except ValueError:
        # LLM returned non-JSON — use the raw text directly
        from app.agent.llm import _model
        raw = _model.generate_content(answer_prompt)
        final_answer = raw.text.strip()

    _print_trace(question, context, final_answer)
    return final_answer


# ── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.agent.agent \"<your question>\"")
        sys.exit(1)

    user_question = " ".join(sys.argv[1:])
    answer = run_agent(user_question)
    print("\n" + answer)
