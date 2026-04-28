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
import time
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
TELEMETRY_PATH = _PROJECT_ROOT / "telemetry.json"

# ── Telemetry Helpers ───────────────────────────────────────────────────────

def load_telemetry() -> dict:
    if TELEMETRY_PATH.exists():
        try:
            with open(TELEMETRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "queries": 0,
        "llm": {"count": 0, "latency": 0.0, "tokens": 0},
        "tools": {}
    }

def save_telemetry(data: dict) -> None:
    with open(TELEMETRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


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


# ── Core agent loop ─────────────────────────────────────────────────────────

def run_agent(question: str) -> str:
    """
    Run the agentic reasoning loop for *question*.

    Returns the final answer string (with citations),
    or a graceful refusal if context is insufficient.
    """
    context: list[dict] = []   # accumulated tool results
    step = 0

    current_llm_stats = {"count": 0, "latency": 0.0, "tokens": 0}
    current_tool_stats = {}
    total_start_time = time.time()

    # ── ANSI Colors ──
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

    print(f"\n{BOLD}{'='*72}{RESET}")
    print(f"  {BOLD}AGENT TRACE{RESET}")
    print(f"{BOLD}{'='*72}{RESET}")
    print(f"\n  {BOLD}Question:{RESET} {question}\n")

    def _print_live_step(st: int | str, t_name: str, t_input: str, t_output: dict | list | str):
        print(f"  {BOLD}Step {st}:{RESET}")
        print(f"    Tool  : {CYAN}{t_name}{RESET}")
        print(f"    Input : {YELLOW}{t_input}{RESET}")
        output_str = json.dumps(t_output, default=str)
        if len(output_str) > 300:
            output_str = output_str[:300] + "..."
        print(f"    Output: {output_str}\n")

    def _track_llm(latency: float, prompt_str: str, response: dict | str):
        current_llm_stats["count"] += 1
        current_llm_stats["latency"] += latency
        tokens = len(prompt_str) // 4
        if isinstance(response, dict):
            tokens += len(json.dumps(response)) // 4
        elif isinstance(response, str):
            tokens += len(response) // 4
        current_llm_stats["tokens"] += tokens

    def _track_tool(t_name: str, latency: float, t_input: str, t_output: dict | list | str):
        if t_name not in current_tool_stats:
            current_tool_stats[t_name] = {"count": 0, "latency": 0.0, "tokens": 0}
        current_tool_stats[t_name]["count"] += 1
        current_tool_stats[t_name]["latency"] += latency
        t_tokens = (len(str(t_input)) + len(json.dumps(t_output, default=str))) // 4
        current_tool_stats[t_name]["tokens"] += t_tokens

    # ── Reasoning loop ──────────────────────────────────────────────────
    while step < MAX_STEPS:
        step += 1

        prompt = DECISION_PROMPT.format(
            context=json.dumps(context, indent=2, default=str) if context else "No context collected yet.",
            question=question,
            step=step,
            max_steps=MAX_STEPS,
        )

        llm_start = time.time()
        try:
            decision = ask_llm(prompt)
        except ValueError:
            try:
                decision = ask_llm(prompt)
            except ValueError:
                _track_llm(time.time() - llm_start, prompt, "")
                return "I encountered an error while reasoning. Please try again."
        
        _track_llm(time.time() - llm_start, prompt, decision)

        if decision.get("type") == "final":
            break

        if decision.get("type") == "tool":
            tool_name = decision.get("tool", "")
            tool_input = decision.get("input", "")

            tool_start = time.time()
            tool_output = _call_tool(tool_name, tool_input)
            
            _track_tool(tool_name, time.time() - tool_start, tool_input, tool_output)
            _print_live_step(step, tool_name, tool_input, tool_output)

            context.append({
                "step": step,
                "tool": tool_name,
                "input": tool_input,
                "output": tool_output,
            })
        else:
            break

    # ── Sufficiency check (with retry if steps remain) ────────────────────
    sufficiency_retries = 0
    max_sufficiency_retries = 2

    while True:
        suff_prompt = SUFFICIENCY_PROMPT.format(
            question=question,
            context=json.dumps(context, indent=2, default=str) if context else "No context collected.",
        )

        llm_start = time.time()
        try:
            suff_result = ask_llm(suff_prompt)
        except ValueError:
            suff_result = {"sufficient": False}
            
        _track_llm(time.time() - llm_start, suff_prompt, suff_result)

        if suff_result.get("sufficient", False):
            break

        if step >= MAX_STEPS or sufficiency_retries >= max_sufficiency_retries:
            final_answer = "I do not have enough information to answer this question."
            break

        sufficiency_retries += 1
        hint_tool = "system"
        hint_input = "sufficiency_check_failed"
        hint_output = ("The information gathered so far is NOT enough. "
                       "Try different search queries, alternative tools, "
                       "or rephrase your approach to find the answer.")
        
        _print_live_step("hint", hint_tool, hint_input, hint_output)
        
        context.append({
            "step": "hint",
            "tool": hint_tool,
            "input": hint_input,
            "output": hint_output,
        })

        while step < MAX_STEPS:
            step += 1
            prompt = DECISION_PROMPT.format(
                context=json.dumps(context, indent=2, default=str),
                question=question,
                step=step,
                max_steps=MAX_STEPS,
            )
            llm_start = time.time()
            try:
                decision = ask_llm(prompt)
            except ValueError:
                try:
                    decision = ask_llm(prompt)
                except ValueError:
                    _track_llm(time.time() - llm_start, prompt, "")
                    break
            
            _track_llm(time.time() - llm_start, prompt, decision)

            if decision.get("type") == "final":
                break

            if decision.get("type") == "tool":
                tool_name = decision.get("tool", "")
                tool_input = decision.get("input", "")
                
                tool_start = time.time()
                tool_output = _call_tool(tool_name, tool_input)
                
                _track_tool(tool_name, time.time() - tool_start, tool_input, tool_output)
                _print_live_step(step, tool_name, tool_input, tool_output)

                context.append({
                    "step": step,
                    "tool": tool_name,
                    "input": tool_input,
                    "output": tool_output,
                })
            else:
                break
        
        if step >= MAX_STEPS:
            break

    # ── Generate final answer ───────────────────────────────────────────
    if 'final_answer' not in locals():
        answer_prompt = ANSWER_PROMPT.format(
            question=question,
            context=json.dumps(context, indent=2, default=str),
        )

        llm_start = time.time()
        try:
            answer_response = ask_llm(answer_prompt)
            if isinstance(answer_response, dict):
                final_answer = answer_response.get("answer", json.dumps(answer_response, indent=2))
            else:
                final_answer = str(answer_response)
        except ValueError:
            from app.agent.llm import _model
            raw = _model.generate_content(answer_prompt)
            final_answer = raw.text.strip()
            answer_response = final_answer
            
        _track_llm(time.time() - llm_start, answer_prompt, answer_response)

    total_time = time.time() - total_start_time

    # ── Update Cumulative Telemetry ──
    tel = load_telemetry()
    tel["queries"] += 1
    tel["llm"]["count"] += current_llm_stats["count"]
    tel["llm"]["latency"] += current_llm_stats["latency"]
    tel["llm"]["tokens"] += current_llm_stats["tokens"]
    
    for tn, stats in current_tool_stats.items():
        if tn not in tel["tools"]:
            tel["tools"][tn] = {"count": 0, "latency": 0.0, "tokens": 0}
        tel["tools"][tn]["count"] += stats["count"]
        tel["tools"][tn]["latency"] += stats["latency"]
        tel["tools"][tn]["tokens"] += stats["tokens"]
        
    save_telemetry(tel)

    # ── Print Final Answer and Stats ──
    print(f"  {BOLD}Final Answer:{RESET}\n")
    for line in final_answer.strip().split("\n"):
        print(f"    {line}")
    print(f"\n  Steps used: {len([c for c in context if c['tool'] != 'system'])}/{MAX_STEPS}")
    
    # ── Print Table ──
    print(f"\n  {BOLD}{CYAN}[Telemetry & Statistics]{RESET}")
    print(f"  Total Execution Time: {total_time:.2f}s")
    print(f"  {'-'*95}")
    print(f"  | {CYAN}{'Component':<13}{RESET} | {CYAN}{'Calls (Cur/Cum)':<15}{RESET} | {CYAN}{'Avg Latency (Cur/Cum)':<21}{RESET} | {CYAN}{'Est. Tokens (Cur/Cum Avg)':<25}{RESET} |")
    print(f"  |---------------|-----------------|-----------------------|---------------------------|")
    
    cum_queries = tel["queries"]
    
    # LLM Stats
    cum_llm_avg_lat = tel["llm"]["latency"] / tel["llm"]["count"] if tel["llm"]["count"] else 0
    cur_llm_avg_lat = current_llm_stats["latency"] / current_llm_stats["count"] if current_llm_stats["count"] else 0
    cum_llm_avg_tok = tel["llm"]["tokens"] / cum_queries if cum_queries else 0
    print(f"  | {BOLD}LLM{RESET}           | {current_llm_stats['count']:<2} / {tel['llm']['count']:<8} | {cur_llm_avg_lat:5.2f}s / {cum_llm_avg_lat:5.2f}s     | {current_llm_stats['tokens']:<6} / {cum_llm_avg_tok:<10.0f} |")
    
    # Tool Stats
    for tn in current_tool_stats.keys() | tel["tools"].keys():
        if tn == "system": continue
        c_stats = current_tool_stats.get(tn, {"count": 0, "latency": 0.0, "tokens": 0})
        cum_stats = tel["tools"].get(tn, {"count": 0, "latency": 0.0, "tokens": 0})
        
        c_avg_lat = c_stats["latency"] / c_stats["count"] if c_stats["count"] else 0.0
        cum_avg_lat = cum_stats["latency"] / cum_stats["count"] if cum_stats["count"] else 0.0
        cum_avg_tok = cum_stats["tokens"] / cum_queries if cum_queries else 0.0
        
        tn_display = tn[:13]
        print(f"  | {GREEN}{tn_display:<13}{RESET} | {c_stats['count']:<2} / {cum_stats['count']:<8} | {c_avg_lat:5.2f}s / {cum_avg_lat:5.2f}s     | {c_stats['tokens']:<6} / {cum_avg_tok:<10.0f} |")
        
    print(f"  {'-'*95}\n")

    return final_answer


# ── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.agent.agent \"<your question>\"")
        sys.exit(1)

    user_question = " ".join(sys.argv[1:])
    answer = run_agent(user_question)
