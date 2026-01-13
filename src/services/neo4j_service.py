"""Neo4j Service for CARF - Persistent Causal Graph Storage.

Provides persistent storage for causal graphs, enabling:
- Historical analysis retrieval
- Cross-session knowledge accumulation
- Graph-based querying of causal relationships

The Neo4j schema uses:
- (:CausalVariable) nodes with properties: name, description, type, role
- [:CAUSES] relationships with properties: effect_size, confidence, session_id
- (:CausalAnalysis) nodes linking variables to analysis sessions
"""

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncGenerator
import os

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, AuthError

from src.services.causal import CausalGraph, CausalVariable, CausalAnalysisResult, CausalHypothesis

logger = logging.getLogger("carf.neo4j")


@dataclass
class Neo4jConfig:
    """Neo4j connection configuration."""
    uri: str
    username: str
    password: str
    database: str = "neo4j"

    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        """Load configuration from environment variables."""
        return cls(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
            database=os.getenv("NEO4J_DATABASE", "neo4j"),
        )


class Neo4jService:
    """Service for persisting and querying causal graphs in Neo4j.

    Cypher Schema:

    (:CausalVariable {
        name: string,
        description: string,
        variable_type: string,
        role: string,
        created_at: datetime,
        updated_at: datetime
    })

    (:CausalAnalysis {
        session_id: string,
        query: string,
        treatment: string,
        outcome: string,
        effect_size: float,
        confidence_lower: float,
        confidence_upper: float,
        passed_refutation: boolean,
        interpretation: string,
        created_at: datetime
    })

    (:CausalVariable)-[:CAUSES {
        effect_size: float,
        session_id: string,
        created_at: datetime
    }]->(:CausalVariable)

    (:CausalAnalysis)-[:INCLUDES]->(:CausalVariable)
    (:CausalAnalysis)-[:TREATMENT]->(:CausalVariable)
    (:CausalAnalysis)-[:OUTCOME]->(:CausalVariable)
    """

    def __init__(self, config: Neo4jConfig | None = None):
        """Initialize the Neo4j service.

        Args:
            config: Neo4j connection configuration. If None, loads from environment.
        """
        self.config = config or Neo4jConfig.from_env()
        self._driver: AsyncDriver | None = None
        self._initialized = False

    async def connect(self) -> None:
        """Establish connection to Neo4j database."""
        if self._driver is not None:
            return

        logger.info(f"Connecting to Neo4j at {self.config.uri}")
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.config.uri,
                auth=(self.config.username, self.config.password),
            )
            # Verify connectivity
            await self._driver.verify_connectivity()
            logger.info("Neo4j connection established")

            # Initialize schema constraints
            await self._initialize_schema()
            self._initialized = True

        except AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            raise
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            raise

    async def disconnect(self) -> None:
        """Close the Neo4j connection."""
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            self._initialized = False
            logger.info("Neo4j connection closed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a Neo4j session context manager."""
        if self._driver is None:
            await self.connect()

        async with self._driver.session(database=self.config.database) as session:
            yield session

    async def _initialize_schema(self) -> None:
        """Create indexes and constraints for optimal performance."""
        async with self.session() as session:
            # Unique constraint on CausalVariable name
            await session.run("""
                CREATE CONSTRAINT causal_variable_name IF NOT EXISTS
                FOR (v:CausalVariable) REQUIRE v.name IS UNIQUE
            """)

            # Index on CausalAnalysis session_id
            await session.run("""
                CREATE INDEX analysis_session IF NOT EXISTS
                FOR (a:CausalAnalysis) ON (a.session_id)
            """)

            # Index on CausalAnalysis created_at for temporal queries
            await session.run("""
                CREATE INDEX analysis_created IF NOT EXISTS
                FOR (a:CausalAnalysis) ON (a.created_at)
            """)

            logger.info("Neo4j schema initialized")

    async def save_causal_graph(
        self,
        graph: CausalGraph,
        session_id: str,
        effect_size: float | None = None,
    ) -> None:
        """Persist a causal graph to Neo4j.

        Args:
            graph: The CausalGraph to persist
            session_id: Session identifier for tracking
            effect_size: Optional effect size for edges
        """
        if not graph.nodes:
            logger.warning("Attempted to save empty causal graph")
            return

        async with self.session() as session:
            # Create/update nodes
            for variable in graph.nodes:
                await session.run("""
                    MERGE (v:CausalVariable {name: $name})
                    ON CREATE SET
                        v.description = $description,
                        v.variable_type = $variable_type,
                        v.role = $role,
                        v.created_at = datetime(),
                        v.updated_at = datetime()
                    ON MATCH SET
                        v.description = COALESCE($description, v.description),
                        v.variable_type = COALESCE($variable_type, v.variable_type),
                        v.role = COALESCE($role, v.role),
                        v.updated_at = datetime()
                """, {
                    "name": variable.name,
                    "description": variable.description,
                    "variable_type": variable.variable_type,
                    "role": variable.role,
                })

            # Create edges
            for cause, effect in graph.edges:
                await session.run("""
                    MATCH (c:CausalVariable {name: $cause})
                    MATCH (e:CausalVariable {name: $effect})
                    MERGE (c)-[r:CAUSES]->(e)
                    ON CREATE SET
                        r.effect_size = $effect_size,
                        r.session_id = $session_id,
                        r.created_at = datetime()
                    ON MATCH SET
                        r.effect_size = COALESCE($effect_size, r.effect_size),
                        r.last_session_id = $session_id,
                        r.updated_at = datetime()
                """, {
                    "cause": cause,
                    "effect": effect,
                    "effect_size": effect_size,
                    "session_id": session_id,
                })

            logger.info(f"Saved causal graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    async def save_analysis_result(
        self,
        result: CausalAnalysisResult,
        graph: CausalGraph,
        session_id: str,
        query: str,
    ) -> str:
        """Persist a complete causal analysis result.

        Args:
            result: The CausalAnalysisResult to persist
            graph: The associated CausalGraph
            session_id: Session identifier
            query: The original user query

        Returns:
            The Neo4j node ID of the created CausalAnalysis
        """
        # First save the graph
        await self.save_causal_graph(graph, session_id, result.effect_estimate)

        async with self.session() as session:
            # Create analysis node
            record = await session.run("""
                CREATE (a:CausalAnalysis {
                    session_id: $session_id,
                    query: $query,
                    treatment: $treatment,
                    outcome: $outcome,
                    mechanism: $mechanism,
                    effect_size: $effect_size,
                    confidence_lower: $conf_lower,
                    confidence_upper: $conf_upper,
                    passed_refutation: $passed_refutation,
                    interpretation: $interpretation,
                    created_at: datetime()
                })
                RETURN elementId(a) as analysis_id
            """, {
                "session_id": session_id,
                "query": query,
                "treatment": result.hypothesis.treatment,
                "outcome": result.hypothesis.outcome,
                "mechanism": result.hypothesis.mechanism,
                "effect_size": result.effect_estimate,
                "conf_lower": result.confidence_interval[0],
                "conf_upper": result.confidence_interval[1],
                "passed_refutation": result.passed_refutation,
                "interpretation": result.interpretation,
            })

            data = await record.single()
            analysis_id = data["analysis_id"]

            # Link analysis to treatment and outcome variables
            await session.run("""
                MATCH (a:CausalAnalysis) WHERE elementId(a) = $analysis_id
                MATCH (t:CausalVariable {name: $treatment})
                MATCH (o:CausalVariable {name: $outcome})
                MERGE (a)-[:TREATMENT]->(t)
                MERGE (a)-[:OUTCOME]->(o)
            """, {
                "analysis_id": analysis_id,
                "treatment": result.hypothesis.treatment,
                "outcome": result.hypothesis.outcome,
            })

            # Link to all variables in the graph
            for variable in graph.nodes:
                await session.run("""
                    MATCH (a:CausalAnalysis) WHERE elementId(a) = $analysis_id
                    MATCH (v:CausalVariable {name: $var_name})
                    MERGE (a)-[:INCLUDES]->(v)
                """, {
                    "analysis_id": analysis_id,
                    "var_name": variable.name,
                })

            logger.info(f"Saved analysis result: {analysis_id}")
            return analysis_id

    async def get_causal_graph(self, session_id: str | None = None) -> CausalGraph:
        """Retrieve a causal graph from Neo4j.

        Args:
            session_id: Optional session ID to filter by. If None, returns full graph.

        Returns:
            CausalGraph reconstructed from Neo4j
        """
        graph = CausalGraph()

        async with self.session() as session:
            # Get all variables
            if session_id:
                # Get variables from specific session
                result = await session.run("""
                    MATCH (a:CausalAnalysis {session_id: $session_id})-[:INCLUDES]->(v:CausalVariable)
                    RETURN DISTINCT v.name as name, v.description as description,
                           v.variable_type as variable_type, v.role as role
                """, {"session_id": session_id})
            else:
                # Get all variables
                result = await session.run("""
                    MATCH (v:CausalVariable)
                    RETURN v.name as name, v.description as description,
                           v.variable_type as variable_type, v.role as role
                """)

            async for record in result:
                graph.add_node(CausalVariable(
                    name=record["name"],
                    description=record["description"] or "",
                    variable_type=record["variable_type"] or "continuous",
                    role=record["role"] or "covariate",
                ))

            # Get edges
            if session_id:
                edge_result = await session.run("""
                    MATCH (c:CausalVariable)-[r:CAUSES]->(e:CausalVariable)
                    WHERE r.session_id = $session_id OR r.last_session_id = $session_id
                    RETURN c.name as cause, e.name as effect
                """, {"session_id": session_id})
            else:
                edge_result = await session.run("""
                    MATCH (c:CausalVariable)-[:CAUSES]->(e:CausalVariable)
                    RETURN c.name as cause, e.name as effect
                """)

            async for record in edge_result:
                graph.add_edge(record["cause"], record["effect"])

        logger.info(f"Retrieved causal graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
        return graph

    async def find_similar_analyses(
        self,
        treatment: str,
        outcome: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find historical analyses with similar treatment/outcome pairs.

        Args:
            treatment: Treatment variable name (or partial match)
            outcome: Outcome variable name (or partial match)
            limit: Maximum number of results

        Returns:
            List of analysis records with similarity information
        """
        async with self.session() as session:
            result = await session.run("""
                MATCH (a:CausalAnalysis)
                WHERE toLower(a.treatment) CONTAINS toLower($treatment)
                   OR toLower(a.outcome) CONTAINS toLower($outcome)
                RETURN a.session_id as session_id,
                       a.query as query,
                       a.treatment as treatment,
                       a.outcome as outcome,
                       a.effect_size as effect_size,
                       a.passed_refutation as passed_refutation,
                       a.created_at as created_at
                ORDER BY a.created_at DESC
                LIMIT $limit
            """, {
                "treatment": treatment,
                "outcome": outcome,
                "limit": limit,
            })

            analyses = []
            async for record in result:
                analyses.append({
                    "session_id": record["session_id"],
                    "query": record["query"],
                    "treatment": record["treatment"],
                    "outcome": record["outcome"],
                    "effect_size": record["effect_size"],
                    "passed_refutation": record["passed_refutation"],
                    "created_at": record["created_at"],
                })

            return analyses

    async def get_causal_path(
        self,
        source: str,
        target: str,
        max_depth: int = 5,
    ) -> list[list[str]]:
        """Find all causal paths between two variables.

        Args:
            source: Source variable name
            target: Target variable name
            max_depth: Maximum path length

        Returns:
            List of paths, where each path is a list of variable names
        """
        async with self.session() as session:
            result = await session.run("""
                MATCH path = (s:CausalVariable {name: $source})-[:CAUSES*1..$max_depth]->(t:CausalVariable {name: $target})
                RETURN [node in nodes(path) | node.name] as path
                ORDER BY length(path)
            """, {
                "source": source,
                "target": target,
                "max_depth": max_depth,
            })

            paths = []
            async for record in result:
                paths.append(record["path"])

            return paths

    async def get_variable_neighbors(
        self,
        variable_name: str,
        direction: str = "both",
    ) -> dict[str, list[str]]:
        """Get the causal neighbors of a variable (Markov blanket approximation).

        Args:
            variable_name: The variable to query
            direction: "causes", "effects", or "both"

        Returns:
            Dict with "causes" and "effects" lists
        """
        neighbors = {"causes": [], "effects": []}

        async with self.session() as session:
            if direction in ("causes", "both"):
                # What causes this variable
                result = await session.run("""
                    MATCH (c:CausalVariable)-[:CAUSES]->(v:CausalVariable {name: $name})
                    RETURN c.name as cause
                """, {"name": variable_name})
                async for record in result:
                    neighbors["causes"].append(record["cause"])

            if direction in ("effects", "both"):
                # What this variable causes
                result = await session.run("""
                    MATCH (v:CausalVariable {name: $name})-[:CAUSES]->(e:CausalVariable)
                    RETURN e.name as effect
                """, {"name": variable_name})
                async for record in result:
                    neighbors["effects"].append(record["effect"])

        return neighbors

    async def health_check(self) -> dict[str, Any]:
        """Check Neo4j connection health and return statistics."""
        try:
            if self._driver is None:
                await self.connect()

            async with self.session() as session:
                result = await session.run("""
                    MATCH (v:CausalVariable)
                    WITH count(v) as variables
                    MATCH ()-[r:CAUSES]->()
                    WITH variables, count(r) as relationships
                    MATCH (a:CausalAnalysis)
                    RETURN variables, relationships, count(a) as analyses
                """)

                data = await result.single()

                return {
                    "status": "healthy",
                    "connected": True,
                    "uri": self.config.uri,
                    "database": self.config.database,
                    "statistics": {
                        "variables": data["variables"] if data else 0,
                        "relationships": data["relationships"] if data else 0,
                        "analyses": data["analyses"] if data else 0,
                    }
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
            }


# Singleton instance
_neo4j_instance: Neo4jService | None = None


def get_neo4j_service() -> Neo4jService:
    """Get or create the Neo4j service singleton."""
    global _neo4j_instance
    if _neo4j_instance is None:
        _neo4j_instance = Neo4jService()
    return _neo4j_instance


async def shutdown_neo4j() -> None:
    """Shutdown the Neo4j connection (call on app shutdown)."""
    global _neo4j_instance
    if _neo4j_instance is not None:
        await _neo4j_instance.disconnect()
        _neo4j_instance = None
