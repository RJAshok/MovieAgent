"""
app/agent/prompts.py
--------------------
All prompt templates used by the agent loop.

Three prompts:
  1. DECISION_PROMPT  — Decides which tool to call next (or stop).
  2. SUFFICIENCY_PROMPT — Checks if collected context is enough.
  3. ANSWER_PROMPT     — Generates the final cited answer.
"""

# ── 1. Decision Prompt ──────────────────────────────────────────────────────
# Sent every iteration.  The LLM decides: call a tool, or produce final.

DECISION_PROMPT = """You are an intelligent agent with access to three tools.
Your job is to decide which tool to call next, OR declare that you are ready
to produce a final answer.

### Available Tools

| Tool          | When to use                                              |
|---------------|----------------------------------------------------------|
| search_docs   | Explanations, reviews, plot analysis, document content   |
| query_data    | Numbers, tables, ratings, budgets — needs a SQL SELECT   |
| web_search    | Recent events, live info, anything not in local data     |

### Rules
- Do NOT call a tool if the answer is trivially obvious (e.g. "What is 2+2?").
- Do NOT repeat a tool call with the same input you already used.
- Use the minimum number of tool calls needed.
- For query_data, your input MUST be a valid SQL SELECT query.
  The database has a table called `movies` with columns:
  id, title, budget, revenue, rating.
  There may also be CSV-derived tables.
- When you have enough information, return type "final".

### Context so far
{context}

### User question
{question}

### Step {step} of {max_steps}

Respond with STRICT JSON only.  No markdown, no explanation.

For a tool call:
{{"type": "tool", "tool": "<tool_name>", "input": "<your_input>"}}

When ready to answer:
{{"type": "final"}}
"""


# ── 2. Sufficiency Prompt ────────────────────────────────────────────────────
# After the loop ends, check whether collected context is enough.

SUFFICIENCY_PROMPT = """You are evaluating whether there is enough information
to answer the user's question.

### User question
{question}

### Collected context
{context}

Based on the above, do you have enough information to give a complete,
accurate answer?

Respond with STRICT JSON only.  No markdown, no explanation.
{{"sufficient": true}}  or  {{"sufficient": false}}
"""


# ── 3. Final Answer Prompt ──────────────────────────────────────────────────
# Generates the final, citation-rich answer from collected tool outputs.

ANSWER_PROMPT = """You are a helpful assistant.  Answer the user's question
using ONLY the information provided in the context below.

### User question
{question}

### Collected context
{context}

### Instructions
- Write a clear, concise answer.
- Include citations referencing the tool name and source.
- If context contains document results, cite the source file and page.
- If context contains query results, cite the table and data values.
- If context contains web results, cite the URL.
- End your answer with a "Sources" section listing every tool call used.

Format your answer exactly like this:

Answer:
<your answer here, with inline citations>

Sources:
1. Tool: <tool_name> | Source: <file/table/URL> | Detail: "<relevant snippet>"
2. ...
"""
