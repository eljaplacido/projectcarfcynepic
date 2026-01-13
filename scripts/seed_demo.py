"""Seed Neo4j with a demo causal analysis."""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from src.services import get_causal_engine, get_neo4j_service


async def main() -> None:
    load_dotenv()
    os.environ["CARF_TEST_MODE"] = "1"

    neo4j = get_neo4j_service()
    await neo4j.connect()

    engine = get_causal_engine()
    engine.enable_neo4j(neo4j)

    csv_path = Path("demo/data/causal_sample.csv")
    context = {
        "causal_estimation": {
            "treatment": "discount",
            "outcome": "churn",
            "covariates": ["region", "tenure"],
            "csv_path": str(csv_path),
        }
    }

    result, graph = await engine.analyze(
        query="Estimate impact of discount on churn",
        context=context,
        session_id="demo-session",
        persist=True,
    )

    print("Seeded Neo4j with demo analysis.")
    print(f"Effect estimate: {result.effect_estimate:.3f}")
    print(f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")

    await neo4j.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
