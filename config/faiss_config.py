"""
config/faiss_config.py
----------------------
Shared configuration for the FAISS document pipeline.
Single source of truth — imported by both tools and the mcp package.

STORE_DIR is resolved relative to the project root so that the
FAISS index is always written/read from the same location regardless of
the working directory the caller uses.
"""

from pathlib import Path

# ── Project root (directory containing the config folder) ────────────────────
_ROOT: Path = Path(__file__).resolve().parent.parent

# ── Paths ────────────────────────────────────────────────────────────────────
STORE_DIR:  Path = _ROOT / "faiss_store"
INDEX_PATH: Path = STORE_DIR / "index.faiss"
META_PATH:  Path = STORE_DIR / "metadata.json"   # JSON — auditable, no pickle

# ── Embedding model ──────────────────────────────────────────────────────────
EMBED_MODEL: str = "all-MiniLM-L6-v2"   # 384-dim, cosine-optimised, fast on CPU

# ── Chunking ─────────────────────────────────────────────────────────────────
CHUNK_SIZE:     int = 500     # target characters per chunk
CHUNK_OVERLAP:  int = 100     # overlap between neighbouring chunks
CHARS_PER_PAGE: int = 3000    # logical page derivation (~3 000 chars ≈ 1 page)

# ── Search defaults ──────────────────────────────────────────────────────────
DEFAULT_TOP_K: int = 3
