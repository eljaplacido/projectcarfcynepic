"""Experience buffer tools for MCP.

Exposes the CARF Experience Buffer's similarity search and pattern
aggregation capabilities to MCP-connected AI agents.
"""

from __future__ import annotations

from typing import Any

from src.mcp.server import mcp
from src.services.experience_buffer import get_experience_buffer


@mcp.tool()
async def query_experience_buffer(
    query: str,
    top_k: int = 3,
) -> dict[str, Any]:
    """Find similar past CARF analyses using semantic memory.

    Searches the experience buffer for past queries similar to the given query,
    returning matches ranked by TF-IDF cosine similarity.

    Args:
        query: The query to search for similar past analyses
        top_k: Number of results to return (default: 3)
    """
    buffer = get_experience_buffer()
    similar = buffer.find_similar(query, top_k=top_k)

    return {
        "matches": [
            {
                "query": entry.query,
                "domain": entry.domain,
                "domain_confidence": entry.domain_confidence,
                "response_summary": entry.response_summary,
                "causal_effect": entry.causal_effect,
                "guardian_verdict": entry.guardian_verdict,
                "timestamp": entry.timestamp.isoformat(),
                "similarity": round(score, 4),
            }
            for entry, score in similar
        ],
        "buffer_size": buffer.size,
        "query": query,
    }


@mcp.tool()
async def experience_buffer_patterns() -> dict[str, Any]:
    """Get aggregated domain-level patterns from the experience buffer.

    Returns per-domain statistics including count, average confidence,
    average causal effect, and guardian verdict distribution.
    """
    buffer = get_experience_buffer()
    patterns = buffer.get_domain_patterns()

    return {
        "patterns": patterns,
        "buffer_size": buffer.size,
    }
