"""
mcp/schemas.py
--------------
Pydantic models and MCP-compatible tool definitions for the FAISS document
search pipeline.  Any MCP governance layer can import ``TOOL_REGISTRY`` to
discover tools and validate inputs / outputs at runtime.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  search_docs — schemas                                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class SearchDocsInput(BaseModel):
    """Input schema for the search_docs tool."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language query string for semantic search.",
        examples=["How is the cinematography described?"],
    )

    @model_validator(mode="after")
    def _strip_query(self) -> "SearchDocsInput":
        self.query = self.query.strip()
        return self


class TextChunk(BaseModel):
    """A single search result chunk."""

    source: str = Field(
        ...,
        description="Source filename from which this chunk was extracted.",
        examples=["oppenheimer_review.txt"],
    )
    page: int = Field(
        ...,
        ge=1,
        description="Logical page number (1-indexed, ~3 000 chars per page).",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Cosine similarity score (0–1, higher = more relevant).",
    )
    text: str = Field(
        ...,
        description="The matching text chunk.",
    )


class SearchDocsOutput(BaseModel):
    """Output schema for the search_docs tool."""

    query: str = Field(
        ...,
        description="The original query string that was searched.",
    )
    total_results: int = Field(
        ...,
        ge=0,
        description="Number of results returned.",
    )
    results: list[TextChunk] = Field(
        ...,
        max_length=10,
        description="Top-K relevant text chunks, ordered by descending similarity.",
    )


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  ingest_docs — schemas                                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class IngestDocsInput(BaseModel):
    """Input schema for the ingest_docs tool."""

    file_paths: list[str] = Field(
        ...,
        min_length=1,
        description="List of absolute or relative paths to .txt or .pdf files to ingest.",
        examples=[["blade_runner_2049_review.txt", "oppenheimer_review.pdf"]],
    )


class IngestedFileInfo(BaseModel):
    """Summary of a single file's ingestion."""

    source: str = Field(..., description="Filename that was ingested.")
    chunks_added: int = Field(..., ge=0, description="Number of new chunks indexed.")
    skipped: bool = Field(
        False,
        description="True if the file was already present and skipped.",
    )


class IngestDocsOutput(BaseModel):
    """Output schema for the ingest_docs tool."""

    files: list[IngestedFileInfo] = Field(
        ...,
        description="Per-file ingestion summary.",
    )
    total_chunks: int = Field(
        ...,
        ge=0,
        description="Total chunks now in the vector store.",
    )
    total_vectors: int = Field(
        ...,
        ge=0,
        description="Total vectors now in the FAISS index.",
    )


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  MCP Tool Registry                                                      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def _mcp_tool_def(
    name: str,
    description: str,
    input_model: type[BaseModel],
    output_model: type[BaseModel],
) -> dict[str, Any]:
    """Build an MCP-compatible tool definition dict from Pydantic models."""
    return {
        "name": name,
        "description": description,
        "inputSchema":  input_model.model_json_schema(),
        "outputSchema": output_model.model_json_schema(),
    }


TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "search_docs": _mcp_tool_def(
        name="search_docs",
        description=(
            "Semantic search over unstructured movie-review documents. "
            "Accepts a natural language query string and returns the top-3 "
            "most relevant text chunks with source filename, page number, "
            "and cosine similarity score."
        ),
        input_model=SearchDocsInput,
        output_model=SearchDocsOutput,
    ),
    "ingest_docs": _mcp_tool_def(
        name="ingest_docs",
        description=(
            "Ingest one or more plain-text (.txt) or PDF (.pdf) movie-review files into the FAISS "
            "vector store. Files are chunked, embedded, and indexed for later "
            "semantic search via the search_docs tool."
        ),
        input_model=IngestDocsInput,
        output_model=IngestDocsOutput,
    ),
}


def get_tool_definition(tool_name: str) -> dict[str, Any]:
    """Return the MCP tool definition for *tool_name*, or raise KeyError."""
    return TOOL_REGISTRY[tool_name]


def list_tools() -> list[dict[str, Any]]:
    """Return all registered MCP tool definitions."""
    return list(TOOL_REGISTRY.values())
