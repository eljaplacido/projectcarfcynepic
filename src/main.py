# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""CYNEPIC Architecture 0.5 - Main Entry Point.

This module initializes the CYNEPIC system (CYNefin-EPIstemic Cockpit)
and provides the main execution loop for the Neuro-Symbolic-Causal Agentic System.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.deployment_profile import get_profile
from src.utils.telemetry import init_telemetry

# Load environment variables from project root (override system env vars)
_project_root = Path(__file__).resolve().parents[1]
load_dotenv(_project_root / ".env", override=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("carf")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("CARF System Starting...")
    logger.info("Phase 1 MVP - Cognitive Spine Active")

    # Initialise observability
    init_telemetry()

    # Validate required environment - check for any supported LLM provider
    has_llm_key = (
        os.getenv("DEEPSEEK_API_KEY") or
        os.getenv("OPENAI_API_KEY") or
        os.getenv("ANTHROPIC_API_KEY")
    )
    if not has_llm_key:
        logger.warning("No LLM API key found (DEEPSEEK_API_KEY/OPENAI_API_KEY) - LLM features will fail")
    else:
        provider = os.getenv("LLM_PROVIDER", "deepseek")
        logger.info(f"LLM provider configured: {provider}")

    # Resolve deployment profile
    profile = get_profile()
    logger.info(f"Deployment profile: {profile.mode.value}")

    # Initialise Neo4j and wire it into the causal engine
    prod_mode = profile.require_neo4j
    neo4j_service = None
    try:
        from src.services.neo4j_service import get_neo4j_service, shutdown_neo4j

        neo4j_service = get_neo4j_service()
        await neo4j_service.connect()
        logger.info("Neo4j connected and ready")

        # Enable graph persistence in the causal engine
        from src.services.causal import get_causal_engine

        causal_engine = get_causal_engine()
        causal_engine.enable_neo4j(neo4j_service)
    except Exception as exc:
        if prod_mode:
            logger.error("PROD_MODE: Neo4j is required but unreachable — aborting startup")
            raise RuntimeError(
                f"Neo4j is required in PROD_MODE but failed to connect: {exc}"
            ) from exc
        logger.warning(f"Neo4j unavailable (non-production): {exc}")

    # Initialise Governance subsystem (Phase 16 — optional)
    if profile.governance_enabled:
        try:
            from src.services.federated_policy_service import get_federated_service
            from src.services.governance_graph_service import get_governance_graph_service

            fed_service = get_federated_service()
            fed_service.load_policies()
            logger.info(f"Governance: Loaded {len(fed_service.list_domains())} domains, "
                        f"{len(fed_service.list_policies())} policies")

            gov_graph = get_governance_graph_service()
            await gov_graph.connect()
            # Auto-ingest governance policies into RAG (non-blocking)
            try:
                from src.services.rag_service import get_rag_service
                rag = get_rag_service()
                count = rag.ingest_policies()
                logger.info(f"RAG: Auto-ingested {count} policy chunks")
            except Exception as rag_exc:
                logger.debug(f"RAG policy auto-ingest skipped: {rag_exc}")
        except Exception as exc:
            logger.warning(f"Governance init failed (non-critical): {exc}")
    else:
        logger.info("Governance subsystem disabled (GOVERNANCE_ENABLED != true)")

    yield

    # Shutdown Governance graph cleanly
    if profile.governance_enabled:
        try:
            from src.services.governance_graph_service import shutdown_governance_graph
            await shutdown_governance_graph()
        except Exception:
            pass

    # Shutdown Neo4j cleanly
    if neo4j_service is not None:
        try:
            from src.services.neo4j_service import shutdown_neo4j

            await shutdown_neo4j()
        except Exception:
            pass
    logger.info("CARF System Shutting Down...")


app = FastAPI(
    title="CYNEPIC API",
    description="CYNEPIC Architecture 0.5 - CYNefin-EPIstemic Cockpit: Neuro-Symbolic-Causal Agentic System",
    version="0.5.0",
    lifespan=lifespan,
)

# Security middleware — profile-aware (no-op in research mode)
# NOTE: Security middleware is registered BEFORE CORS so that CORS ends up
# as the outermost middleware (Starlette processes last-registered first).
# This ensures CORS headers are added to ALL responses, including 429s.
_profile = get_profile()
from src.api.middleware import register_security_middleware  # noqa: E402
register_security_middleware(app)

# CORS middleware — registered LAST so it wraps the entire middleware stack
app.add_middleware(
    CORSMiddleware,
    allow_origins=_profile.cors_origins or ["*"],
    allow_credentials=_profile.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Register all routers ──────────────────────────────────────────────────

from src.api.routers import (  # noqa: E402
    analysis,
    config,
    csl,
    datasets,
    developer,
    feedback,
    guardian,
    health,
    history,
    monitoring,
    oracle,
    query,
    router_config,
    simulation,
    transparency,
    world_model,
)

app.include_router(health.router)
app.include_router(config.router)
app.include_router(oracle.router)
app.include_router(router_config.router)
app.include_router(guardian.router)
app.include_router(datasets.router)
app.include_router(developer.router)
app.include_router(simulation.router)
app.include_router(analysis.router)
app.include_router(transparency.router)
app.include_router(feedback.router)
app.include_router(history.router)
app.include_router(csl.router)
app.include_router(query.router)
app.include_router(world_model.router)
app.include_router(monitoring.router)  # Phase 18: drift, bias, convergence

# Governance router (Phase 16 — conditionally registered)
if _profile.governance_enabled:
    from src.api.routers import governance  # noqa: E402
    app.include_router(governance.router)
    logger.info("Governance API router registered (/governance/*)")

    # File upload endpoint (requires UploadFile at app level)
    from fastapi import UploadFile, File as FastAPIFile

    @app.post("/governance/documents/upload-file", tags=["governance"])
    async def upload_governance_document(
        file: UploadFile = FastAPIFile(...),
        domain_id: str | None = None,
        source_name: str | None = None,
    ):
        """Upload a document for RAG ingestion and optional policy extraction."""
        from src.services.document_processor import get_document_processor
        data = await file.read()
        result = get_document_processor().process_and_ingest(
            data,
            filename=file.filename or "upload",
            domain_id=domain_id,
            source=source_name,
        )
        return result


def main():
    """Main entry point for CLI execution."""
    import uvicorn

    logger.info("Starting CARF in development mode...")
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
