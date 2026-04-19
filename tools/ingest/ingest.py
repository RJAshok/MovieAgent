"""
tools/ingest/ingest.py
----------------------
Ingest plain-text movie-review files into a FAISS vector store.

Optimisations
~~~~~~~~~~~~~
- Cosine similarity via IndexFlatIP + L2-normalised embeddings (scores 0–1).
- Sentence-aware chunking: snaps split points to sentence boundaries.
- JSON metadata (human-auditable, MCP-friendly, no pickle).
- Deduplication: skips source filenames already present in the index.
- Pydantic-validated I/O conforming to MCP governance schemas.

CLI:
    python tools/ingest/ingest.py <review.txt> [more.txt …]

Programmatic / MCP:
    from tools.ingest.ingest import ingest_docs
    from mcp.schemas import IngestDocsInput
    result = ingest_docs(IngestDocsInput(file_paths=["review.txt"]))
"""

from __future__ import annotations

import argparse
import json
import re
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

from config.faiss_config import (
    CHARS_PER_PAGE,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBED_MODEL,
    INDEX_PATH,
    META_PATH,
    STORE_DIR,
)
from mcp.schemas import IngestDocsInput, IngestDocsOutput, IngestedFileInfo

# Pre-compiled sentence-boundary pattern
_SENT_RE = re.compile(r"(?<=[.!?])\s+")


# ── Sentence-aware chunking ──────────────────────────────────────────────────

def _chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[tuple[str, int]]:
    """
    Split *text* into overlapping character windows, snapping end boundaries
    to the nearest sentence break within the last 20 % of each window.

    Returns list of (chunk_text, start_char_offset).
    """
    length = len(text)
    if length == 0:
        return []

    chunks: list[tuple[str, int]] = []
    start = 0

    while start < length:
        end = min(start + chunk_size, length)

        if end < length:
            look_back = max(int(chunk_size * 0.2), 1)
            region = text[end - look_back : end]
            matches = list(_SENT_RE.finditer(region))
            if matches:
                end = (end - look_back) + matches[-1].end()

        chunk = text[start:end].strip()
        if chunk:
            chunks.append((chunk, start))

        if end >= length:
            break
        start = max(start + 1, end - overlap)

    return chunks


# ── FAISS index helpers ──────────────────────────────────────────────────────

def _load_or_create_index(dim: int) -> tuple[faiss.Index, list[dict]]:
    """Return (index, metadata_list). Creates fresh assets if none exist."""
    STORE_DIR.mkdir(parents=True, exist_ok=True)

    if INDEX_PATH.exists() and META_PATH.exists():
        index = faiss.read_index(str(INDEX_PATH))
        with open(META_PATH, "r", encoding="utf-8") as f:
            metadata: list[dict] = json.load(f)
    else:
        # IndexFlatIP + L2-normalised vectors → inner product = cosine similarity
        index = faiss.IndexFlatIP(dim)
        metadata = []

    return index, metadata


def _save_index(index: faiss.Index, metadata: list[dict]) -> None:
    faiss.write_index(index, str(INDEX_PATH))
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=1)


# ── Core tool ────────────────────────────────────────────────────────────────

def ingest_docs(params: IngestDocsInput) -> IngestDocsOutput:
    """
    MCP-compatible ingest tool.

    Validates input via ``IngestDocsInput``, returns ``IngestDocsOutput``.
    Raises ``FileNotFoundError`` for missing files.
    """
    paths = [Path(p) for p in params.file_paths]

    for p in paths:
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")

    model = SentenceTransformer(EMBED_MODEL)
    dim = model.get_sentence_embedding_dimension()
    index, metadata = _load_or_create_index(dim)

    existing_sources: set[str] = {m["source"] for m in metadata}

    file_reports: list[IngestedFileInfo] = []
    new_chunks:   list[dict]             = []
    new_texts:    list[str]              = []

    for p in paths:
        name = p.name

        if name in existing_sources:
            file_reports.append(IngestedFileInfo(source=name, chunks_added=0, skipped=True))
            continue

        raw = p.read_text(encoding="utf-8", errors="replace")
        count = 0

        for chunk_text, offset in _chunk_text(raw):
            page = offset // CHARS_PER_PAGE + 1
            new_chunks.append({"source": name, "page": page, "text": chunk_text})
            new_texts.append(chunk_text)
            count += 1

        file_reports.append(IngestedFileInfo(source=name, chunks_added=count, skipped=False))
        existing_sources.add(name)

    if new_texts:
        embeddings = model.encode(
            new_texts,
            batch_size=128,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,   # L2-normalise → cosine sim via dot product
        ).astype("float32")

        index.add(embeddings)
        metadata.extend(new_chunks)
        _save_index(index, metadata)

    return IngestDocsOutput(
        files=file_reports,
        total_chunks=len(metadata),
        total_vectors=index.ntotal,
    )


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest plain-text movie-review files into the FAISS vector store."
    )
    parser.add_argument("files", nargs="+", help="One or more .txt files to ingest.")
    args = parser.parse_args()

    try:
        validated = IngestDocsInput(file_paths=args.files)
    except Exception as exc:
        sys.exit(f"Input validation error: {exc}")

    result = ingest_docs(validated)

    print()
    for f in result.files:
        tag = "SKIPPED (already indexed)" if f.skipped else f"{f.chunks_added} chunks added"
        icon = "⊘" if f.skipped else "✓"
        print(f"  {icon}  {f.source}  →  {tag}")

    print(f"\n  Total vectors in store : {result.total_vectors}")
    print(f"  Store location         : {STORE_DIR.resolve()}\n")


if __name__ == "__main__":
    main()
