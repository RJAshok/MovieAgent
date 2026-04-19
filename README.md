# Prodapt Agent

## Tech Stack
- **Language**: Python 3.12+
- **Vector Database**: FAISS (`faiss-cpu`) for fast, local in-memory semantic similarity search.
- **Embeddings**: `sentence-transformers` utilizing the lightweight `all-MiniLM-L6-v2` model.
- **Data Validation**: `pydantic` for MCP-compliant schema validation and I/O governance.
- **Math Ops**: `numpy` for float32 array processing.

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
