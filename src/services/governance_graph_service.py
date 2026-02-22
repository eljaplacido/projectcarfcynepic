"""Neo4j Governance Graph Service for CARF OG subsystem.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

Separate from neo4j_service.py to maintain data layer integrity.
Uses new node labels (:GovernanceDomain, :ContextTriple, :FederatedPolicy)
that do not touch existing (:CausalVariable, :CausalAnalysis) schema.

Graceful degradation: every method checks self.is_available and returns
empty/no-op when Neo4j is unavailable.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from src.core.governance_models import (
    ContextTriple,
    GovernanceDomain,
    FederatedPolicy,
)

logger = logging.getLogger("carf.governance.graph")


class GovernanceGraphService:
    """Persistent governance triple store using Neo4j.

    Schema:
        (:GovernanceDomain {domain_id, display_name, owner_email, ...})
        (:ContextTriple {triple_id, subject, predicate, object, confidence, ...})
        (:FederatedPolicy {policy_id, name, namespace, priority, ...})

        (:GovernanceDomain)-[:OWNS_POLICY]->(:FederatedPolicy)
        (:ContextTriple)-[:FROM_DOMAIN]->(:GovernanceDomain)
        (:ContextTriple)-[:IMPACTS_DOMAIN]->(:GovernanceDomain)
    """

    def __init__(self) -> None:
        self._driver = None
        self._available = False
        self._initialized = False

    async def connect(self) -> None:
        """Attempt to connect to Neo4j for governance graph operations."""
        try:
            from neo4j import AsyncGraphDatabase
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            username = os.getenv("NEO4J_USERNAME", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "password")

            self._driver = AsyncGraphDatabase.driver(uri, auth=(username, password))
            await self._driver.verify_connectivity()
            await self._initialize_schema()
            self._available = True
            logger.info("Governance graph service connected to Neo4j")
        except Exception as exc:
            logger.warning(f"Governance graph Neo4j unavailable (degrading to in-memory): {exc}")
            self._available = False

    async def disconnect(self) -> None:
        """Close the Neo4j connection."""
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    async def _initialize_schema(self) -> None:
        """Create governance-specific indexes and constraints."""
        if not self._available or self._driver is None:
            return
        try:
            database = os.getenv("NEO4J_DATABASE", "neo4j")
            async with self._driver.session(database=database) as session:
                await session.run("""
                    CREATE CONSTRAINT gov_domain_id IF NOT EXISTS
                    FOR (d:GovernanceDomain) REQUIRE d.domain_id IS UNIQUE
                """)
                await session.run("""
                    CREATE INDEX gov_triple_session IF NOT EXISTS
                    FOR (t:ContextTriple) ON (t.session_id)
                """)
                await session.run("""
                    CREATE INDEX gov_policy_namespace IF NOT EXISTS
                    FOR (p:FederatedPolicy) ON (p.namespace)
                """)
            self._initialized = True
            logger.info("Governance graph schema initialized")
        except Exception as exc:
            logger.warning(f"Governance schema init failed: {exc}")

    async def save_triple(self, triple: ContextTriple) -> None:
        """Persist a single context triple to Neo4j."""
        if not self._available or self._driver is None:
            return
        try:
            database = os.getenv("NEO4J_DATABASE", "neo4j")
            async with self._driver.session(database=database) as session:
                await session.run("""
                    MERGE (t:ContextTriple {triple_id: $triple_id})
                    ON CREATE SET
                        t.subject = $subject,
                        t.predicate = $predicate,
                        t.object = $object,
                        t.domain_source = $domain_source,
                        t.domain_target = $domain_target,
                        t.confidence = $confidence,
                        t.evidence_type = $evidence_type,
                        t.session_id = $session_id,
                        t.created_at = datetime()
                    ON MATCH SET
                        t.confidence = $confidence,
                        t.updated_at = datetime()
                """, {
                    "triple_id": str(triple.triple_id),
                    "subject": triple.subject,
                    "predicate": triple.predicate,
                    "object": triple.object,
                    "domain_source": triple.domain_source,
                    "domain_target": triple.domain_target,
                    "confidence": triple.confidence,
                    "evidence_type": triple.evidence_type.value,
                    "session_id": triple.session_id,
                })

                # Link to domain nodes
                await session.run("""
                    MATCH (t:ContextTriple {triple_id: $triple_id})
                    MERGE (ds:GovernanceDomain {domain_id: $source})
                    MERGE (dt:GovernanceDomain {domain_id: $target})
                    MERGE (t)-[:FROM_DOMAIN]->(ds)
                    MERGE (t)-[:IMPACTS_DOMAIN]->(dt)
                """, {
                    "triple_id": str(triple.triple_id),
                    "source": triple.domain_source,
                    "target": triple.domain_target,
                })
        except Exception as exc:
            logger.warning(f"Failed to save triple: {exc}")

    async def save_triples_batch(self, triples: list[ContextTriple]) -> int:
        """Persist multiple triples. Returns count saved."""
        if not self._available or not triples:
            return 0
        saved = 0
        for triple in triples:
            try:
                await self.save_triple(triple)
                saved += 1
            except Exception as exc:
                logger.warning(f"Batch triple save failed for {triple.triple_id}: {exc}")
        return saved

    async def find_cross_domain_impacts(
        self, domain_id: str, max_depth: int = 3
    ) -> list[dict[str, Any]]:
        """Find all domains impacted by the given domain via triple chains."""
        if not self._available or self._driver is None:
            return []
        try:
            database = os.getenv("NEO4J_DATABASE", "neo4j")
            async with self._driver.session(database=database) as session:
                result = await session.run("""
                    MATCH (source:GovernanceDomain {domain_id: $domain_id})
                    MATCH (t:ContextTriple)-[:FROM_DOMAIN]->(source)
                    MATCH (t)-[:IMPACTS_DOMAIN]->(target:GovernanceDomain)
                    WHERE target.domain_id <> $domain_id
                    RETURN DISTINCT target.domain_id as domain_id,
                           target.display_name as display_name,
                           collect(DISTINCT {
                               subject: t.subject,
                               predicate: t.predicate,
                               object: t.object,
                               confidence: t.confidence
                           }) as triples
                """, {"domain_id": domain_id})

                impacts = []
                async for record in result:
                    impacts.append({
                        "domain_id": record["domain_id"],
                        "display_name": record["display_name"],
                        "triples": record["triples"],
                    })
                return impacts
        except Exception as exc:
            logger.warning(f"Cross-domain impact query failed: {exc}")
            return []

    async def get_impact_path(
        self, source: str, target: str, max_depth: int = 5
    ) -> list[dict[str, Any]]:
        """Find shortest impact path between two domains."""
        if not self._available or self._driver is None:
            return []
        try:
            database = os.getenv("NEO4J_DATABASE", "neo4j")
            async with self._driver.session(database=database) as session:
                result = await session.run("""
                    MATCH path = shortestPath(
                        (s:GovernanceDomain {domain_id: $source})-
                        [:FROM_DOMAIN|IMPACTS_DOMAIN*1..$max_depth]-
                        (t:GovernanceDomain {domain_id: $target})
                    )
                    RETURN [node in nodes(path) |
                        CASE WHEN node:GovernanceDomain THEN {type: 'domain', id: node.domain_id}
                             WHEN node:ContextTriple THEN {type: 'triple', subject: node.subject, predicate: node.predicate, object: node.object}
                             ELSE {type: 'unknown'}
                        END
                    ] as path_nodes
                """, {"source": source, "target": target, "max_depth": max_depth})

                paths = []
                async for record in result:
                    paths.append(record["path_nodes"])
                return paths
        except Exception as exc:
            logger.warning(f"Impact path query failed: {exc}")
            return []

    async def sync_session_triples(
        self, session_id: str, triples: list[ContextTriple]
    ) -> int:
        """Persist all session triples at session end."""
        return await self.save_triples_batch(
            [t for t in triples if t.session_id == session_id or t.session_id is None]
        )

    async def get_all_triples(
        self, session_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Retrieve stored triples, optionally filtered by session."""
        if not self._available or self._driver is None:
            return []
        try:
            database = os.getenv("NEO4J_DATABASE", "neo4j")
            async with self._driver.session(database=database) as session:
                if session_id:
                    result = await session.run("""
                        MATCH (t:ContextTriple {session_id: $session_id})
                        RETURN t ORDER BY t.created_at DESC LIMIT $limit
                    """, {"session_id": session_id, "limit": limit})
                else:
                    result = await session.run("""
                        MATCH (t:ContextTriple)
                        RETURN t ORDER BY t.created_at DESC LIMIT $limit
                    """, {"limit": limit})

                triples = []
                async for record in result:
                    node = record["t"]
                    triples.append(dict(node))
                return triples
        except Exception as exc:
            logger.warning(f"Get triples failed: {exc}")
            return []

    async def health_check(self) -> dict[str, Any]:
        """Check governance graph health."""
        if not self._available:
            return {"status": "unavailable", "neo4j_connected": False}
        try:
            database = os.getenv("NEO4J_DATABASE", "neo4j")
            async with self._driver.session(database=database) as session:
                result = await session.run("""
                    OPTIONAL MATCH (t:ContextTriple) WITH count(t) as triples
                    OPTIONAL MATCH (d:GovernanceDomain) WITH triples, count(d) as domains
                    OPTIONAL MATCH (p:FederatedPolicy) RETURN triples, domains, count(p) as policies
                """)
                data = await result.single()
                return {
                    "status": "healthy",
                    "neo4j_connected": True,
                    "triples": data["triples"] if data else 0,
                    "domains": data["domains"] if data else 0,
                    "policies": data["policies"] if data else 0,
                }
        except Exception as exc:
            return {"status": "degraded", "neo4j_connected": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_governance_graph_instance: GovernanceGraphService | None = None


def get_governance_graph_service() -> GovernanceGraphService:
    """Get or create the governance graph service singleton."""
    global _governance_graph_instance
    if _governance_graph_instance is None:
        _governance_graph_instance = GovernanceGraphService()
    return _governance_graph_instance


async def shutdown_governance_graph() -> None:
    """Shutdown the governance graph connection."""
    global _governance_graph_instance
    if _governance_graph_instance is not None:
        await _governance_graph_instance.disconnect()
        _governance_graph_instance = None
