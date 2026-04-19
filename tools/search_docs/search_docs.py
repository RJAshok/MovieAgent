"""
tools/search_docs/search_docs.py
---------------------------------
search_docs: semantic search tool over ingested movie-review documents.

Purpose
~~~~~~~
Semantic search over unstructured documents (long-form movie reviews).

Input
~~~~~
Natural language query string, validated via ``SearchDocsInput``.

Expected Output
~~~~~~~~~~~~~~~
Top-3 relevant text chunks with source filename, page number (1-indexed),
and cosine similarity score (0–1).  Validated via ``SearchDocsOutput``.

CLI:
    python tools/search_docs/search_docs.py "How is the pacing in the second act?"
    python tools/search_docs/search_docs.py "Is the villain well-written?" --top-k 5

Programmatic / MCP:
    from tools.search_docs.search_docs import search_docs
    from mcp.schemas import SearchDocsInput
    output = search_docs(SearchDocsInput(query="What did critics say about the score?"))
    for chunk in output.results:
        print(chunk.source, chunk.page, chunk.score)
        print(chunk.text)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ── Ensure project root is on sys.path so 'config' and 'mcp' are importable
# regardless of the working directory from which this script is invoked.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from config.faiss_config import DEFAULT_TOP_K, EMBED_MODEL, INDEX_PATH, META_PATH, STORE_DIR
from mcp.schemas import SearchDocsInput, SearchDocsOutput, TextChunk

# ── Lazy singleton cache (reused across repeated calls in the same process) ──
_model:    SentenceTransformer | None = None
_index:    faiss.Index          | None = None
_metadata: list[dict]           | None = None


def _ensure_loaded() -> tuple[faiss.Index, list[dict], SentenceTransformer]:
    """
    Load assets on first call; return cached references on subsequent calls.
    Raises ``FileNotFoundError`` if the store has not been built yet.
    """
    global _model, _index, _metadata

    if _model is not None and _index is not None and _metadata is not None:
        return _index, _metadata, _model

    if not INDEX_PATH.exists() or not META_PATH.exists():
        raise FileNotFoundError(
            f"FAISS store not found at '{STORE_DIR.resolve()}'.\n"
            "Run  python tools/ingest/ingest.py <file.txt>  first."
        )

    _index = faiss.read_index(str(INDEX_PATH))

    with open(META_PATH, "r", encoding="utf-8") as f:
        _metadata = json.load(f)

    _model = SentenceTransformer(EMBED_MODEL)

    return _index, _metadata, _model


# ── Core tool ────────────────────────────────────────────────────────────────

def search_docs(params: SearchDocsInput, top_k: int = DEFAULT_TOP_K) -> SearchDocsOutput:
    """
    MCP-compatible semantic search tool.

    Parameters
    ----------
    params : SearchDocsInput
        Validated input.  ``params.query`` is the natural-language question.
    top_k : int
        How many results to return (default 3, clamped to index size).

    Returns
    -------
    SearchDocsOutput
        Validated output: query echo, result count, and list of TextChunk.
    """
    index, metadata, model = _ensure_loaded()

    if index.ntotal == 0:
        raise RuntimeError("The FAISS index is empty.  Ingest documents first.")

    actual_k = min(top_k, index.ntotal)

    query_vec = model.encode(
        [params.query],
        convert_to_numpy=True,
        normalize_embeddings=True,   # must match ingest normalisation
    ).astype("float32")

    # Inner-product on L2-normalised vectors = cosine similarity
    scores, indices = index.search(query_vec, actual_k)

    results: list[TextChunk] = []
    for sim, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        meta = metadata[idx]
        results.append(
            TextChunk(
                source=meta["source"],
                page=meta["page"],
                score=round(float(max(0.0, min(sim, 1.0))), 4),
                text=meta["text"],
            )
        )

    return SearchDocsOutput(
        query=params.query,
        total_results=len(results),
        results=results,
    )


# ── Pretty terminal output ───────────────────────────────────────────────────

def _pretty_print(output: SearchDocsOutput) -> None:
    bar = "-" * 72

    print(f"\n{'=' * 72}")
    print(f"  Query   : {output.query}")
    print(f"  Results : {output.total_results}")
    print(f"{'=' * 72}\n")

    for rank, r in enumerate(output.results, start=1):
        print(f"  #{rank}  [{r.source}  |  page {r.page}  |  similarity {r.score:.4f}]")
        print(f"  {bar}")
        # Word-wrap at 70 columns
        words, line, col = r.text.split(), [], 0
        for w in words:
            if col + len(w) + 1 > 70:
                print("  " + " ".join(line))
                line, col = [w], len(w)
            else:
                line.append(w)
                col += len(w) + 1
        if line:
            print("  " + " ".join(line))
        print()


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Semantic search over ingested movie-review documents."
    )
    parser.add_argument(
        "query",
        type=str,
        help="Natural language query, e.g. 'How is the cinematography?'",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"Number of results to return (default: {DEFAULT_TOP_K}).",
    )
    args = parser.parse_args()

    try:
        validated_input = SearchDocsInput(query=args.query)
    except Exception as exc:
        sys.exit(f"Input validation error: {exc}")

    try:
        output = search_docs(validated_input, top_k=args.top_k)
    except (FileNotFoundError, RuntimeError) as exc:
        sys.exit(f"Error: {exc}")

    if output.total_results == 0:
        print("No results found.")
        return

    _pretty_print(output)

    # Machine-readable JSON (useful for MCP governance inspection / piping)
    print("--- JSON (MCP output) ---")
    print(output.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
