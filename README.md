# Prodapt Agent

## Tech Stack
- **Language**: Python 3.12+
- **Vector Database**: FAISS (`faiss-cpu`) for fast, local in-memory semantic similarity search.
- **Embeddings**: `sentence-transformers` utilizing the lightweight `all-MiniLM-L6-v2` model.
- **Data Validation**: `pydantic` for MCP-compliant schema validation and I/O governance.
- **Math Ops**: `numpy` for float32 array processing.

## Quickstart

1. **Setup**: Run the setup script to initialize a local virtual environment (`venv`), install Python dependencies, generate a template `.env` file, download the embedding model, and automatically ingest any unstructured text from `dataset/unstructured/` into the FAISS vector database.
   ```bash
   python setup.py
   ```
2. **Configure Environment**: Update the newly created `.env` file with your valid `TAVILY_API_KEY` and `GEMINI_API_KEY`.
3. **Run the Agent**: Activate the virtual environment and start the interactive agent interface. `run.py` will automatically prompt you to upload structured CSV data if the SQLite database is empty.
   ```bash
   # Windows
   venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   
   python run.py
   ```

## Selected Corpus
```text
Option C - Movies Corpus 
• A small corpus of 10–15 long-form film reviews from reputable publications. 
• Unstructured: The review texts as PDFs or plain text files. 
• Structured: A CSV of box-office data (budget, opening weekend, worldwide gross, Rotten Tomatoes score) from Box 
Office Mojo or similar. 
• Web: Live web search for recent awards news and director updates.
```

## Tools

Our agent has access to multiple strictly governed semantic search tools located in the `tools/` directory.

### 1. `ingest_docs` (Document Ingestion)
Located at `tools/ingest/ingest.py`.
- **Purpose**: Parses raw unstructured text files and embeds them into a FAISS vector database.
- **Features**:
  - Uses sentence-aware text chunking matching sentence boundaries rather than hard cut-offs.
  - Normalizes embeddings to leverage mathematical Cosine Similarity through FAISS' inner product searches.
  - Outputs Pydantic-validated MCP tracking information detailing the chunk counts added for auditing.
  - Deduplicates incoming filenames.

### 2. `search_docs` (Semantic Document Search)
Located at `tools/search_docs/search_docs.py`.
- **Purpose**: Queries the vector database using natural language queries to retrieve the highest relevance sub-sections of text.
- **Features**:
  - Pydantic models validate input queries to ensure standardized inputs.
  - Pydantic models structure outputs returning `source` filename, logical `page` number, similarity `score`, and raw `text`.
  - Implements global lazy-loading to cache the embedding model and FAISS vector indices on first call for extremely rapid subsequent queries.

### 3. `query_data` (Structured Data Query)
Located at `tools/query_data/query_data.py`.
- **Purpose**: Executes SQL queries against a structured SQLite database and CSV files loaded into memory.
- **Features**:
  - Handles numerical, tabular, and analytical queries (e.g., box office revenue, budgets).
  - Automatically loads and integrates data from `.csv` files inside the dataset folder into an in-memory database.
  - Built-in safety mechanisms to detect natural language and block write operations (INSERT, UPDATE, DELETE).

### 4. `web_search` (Live Web Search)
Located at `tools/web_search/web_search.py`.
- **Purpose**: Uses the Tavily API to search the web for current events and information not present in the local datasets.
- **Features**:
  - Requires a `TAVILY_API_KEY` environment variable.
  - Returns a structured list containing text snippets, URLs, and publication dates for the top search results.

## Testing

### `test_all_tools.py`
Located at `scripts/test_all_tools.py`.
- **Purpose**: A comprehensive testing suite for all agent tools.
- **Features**:
  - Prepares the environment by automatically loading unstructured text into FAISS and structured data into the database.
  - Runs a variety of scenarios (e.g., semantic queries, SQL aggregations, live API checks, invalid/unsafe inputs) to ensure each tool behaves as expected.
  - Outputs a summary of passed/failed tests along with average tool latencies.
