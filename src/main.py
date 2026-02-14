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

    # Initialise Neo4j and wire it into the causal engine
    prod_mode = os.getenv("PROD_MODE", "").lower() in ("1", "true", "yes")
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

    yield

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

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=False,  # Cannot use credentials with wildcard origin
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Register all routers ──────────────────────────────────────────────────

from src.api.routers import (  # noqa: E402
    analysis,
    config,
    datasets,
    developer,
    guardian,
    health,
    oracle,
    query,
    router_config,
    simulation,
    transparency,
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
app.include_router(query.router)


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
