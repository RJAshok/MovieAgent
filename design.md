# Agent Design Document

This document outlines the architecture, tooling, and logic of the Prodapt Movie Agent.

## Agent Loop Architecture

The agent follows an iterative **ReAct (Reason + Act)** pattern combined with a strict sufficiency check to ensure high-quality, cited answers. 

### Step-by-Step Execution
1. **Receive Query:** The user inputs a natural language question.
2. **Context Initialization:** An empty list `context` is initialized to store the trace of all tool calls, inputs, and outputs.
3. **Reasoning Loop (Max 8 Steps):**
   - The agent receives the `DECISION_PROMPT`, which contains the user's query and the current `context`.
   - The LLM decides whether it needs to use a tool (`type: tool`) or if it has enough information to stop (`type: final`).
   - If a tool is selected, the system parses the JSON, executes the local tool, and appends the result to the `context`.
   - If the LLM returns `type: final`, the reasoning loop breaks.
4. **Sufficiency Check:** 
   - A secondary prompt (`SUFFICIENCY_PROMPT`) evaluates the gathered `context` against the original query to determine if the information is genuinely sufficient to answer the question.
   - If the LLM determines the information is insufficient, it triggers a **Retry Mechanism**. The agent is fed a "hint" telling it that its previous search failed, and it is pushed back into the reasoning loop to try alternative search terms or different tools (up to 2 retries).
5. **Final Generation:** 
   - Once the context is deemed sufficient (or retries are exhausted), the `ANSWER_PROMPT` is invoked.
   - The LLM drafts the final response, strictly appending citations mapped to the exact tool and source file used.
   - If the context is still insufficient after all retries, the agent gracefully refuses rather than hallucinating.

---

## Tool Schemas

The agent has access to three primary tools.

### 1. `search_docs` (RAG / Semantic Search)
- **Description:** Performs semantic search over unstructured movie reviews and plot summaries stored in a local FAISS vector database.
- **Input Schema:** `SearchDocsInput` (Pydantic)
  - `query` (str): The natural language search query.
- **Output Schema:** `SearchDocsOutput` (Pydantic)
  - Returns the `query`, `total_results`, and a list of `TextChunk` objects containing the `source` filename, `page` number, similarity `score` (0-1), and the raw `text` snippet.

### 2. `query_data` (Structured SQLite/CSV Query)
- **Description:** Executes read-only SQL queries against an in-memory SQLite database populated with CSV box office data.
- **Input Schema:** `query` (str) - A valid SQL SELECT statement.
- **Output Schema:** 
  - Returns a dictionary containing `columns` (list of column names), `rows` (list of data arrays), and `row_count` (int). 
  - If the query is invalid or attempts a write operation, it returns an `error` string.

### 3. `web_search` (Live Web Search)
- **Description:** Uses the Tavily API to fetch real-time news, cast updates, and live box office numbers not present in the local database.
- **Input Schema:** `query` (str) - The search engine query.
- **Output Schema:**
  - Returns a list of up to 3 dictionaries, each containing the `title`, `url`, `content` snippet, and `published_date` of the search result.

---

## Infinite Loop Prevention

To guarantee the agent never gets stuck in an infinite loop, the system implements hard limits at two different layers of the architecture:

1. **Maximum Step Budget (`MAX_STEPS = 8`):** 
   The primary reasoning loop increments a `step` counter every time the LLM is queried for a decision. If `step` reaches 8, the `while step < MAX_STEPS:` loop terminates forcefully, preventing the agent from infinitely chaining tool calls.
   
2. **Maximum Sufficiency Retries (`max_sufficiency_retries = 2`):** 
   If the agent breaks out of the reasoning loop prematurely but the sufficiency checker determines the context is lacking, the agent is forced back into the reasoning loop. To prevent it from bouncing between the reasoning loop and the sufficiency checker infinitely, a `sufficiency_retries` counter is strictly capped at 2. If it fails 3 times, the agent immediately issues a fallback refusal.
