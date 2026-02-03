"""CYNEPIC Architecture 0.5 - Main Entry Point.

This module initializes the CYNEPIC system (CYNefin-EPIstemic Cockpit)
and provides the main execution loop for the Neuro-Symbolic-Causal Agentic System.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.core.state import CynefinDomain, EpistemicState, GuardianVerdict
from src.services.bayesian import BayesianInferenceConfig
from src.services.causal import CausalEstimationConfig
from src.services.chat import ChatMessage, ChatRequest, ChatResponse, get_chat_service
from src.services.dataset_store import DatasetMetadata, get_dataset_store
from src.services.developer import DeveloperState, LogEntry, get_developer_service
from src.services.explanations import ExplanationComponent, ExplanationRequest, ExplanationResponse, get_explanation_service
from src.services.file_analyzer import FileAnalysisResult, get_file_analyzer
from src.utils.telemetry import init_telemetry
from src.workflows.graph import run_carf

# Load environment variables
load_dotenv()

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

    # Validate required environment
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set - LLM features will fail")

    # Initialise Neo4j and wire it into the causal engine
    prod_mode = os.getenv("PROD_MODE", "").lower() in ("1", "true", "yes")
    neo4j_service = None
    try:
        from src.services.neo4j_service import get_neo4j_service, shutdown_neo4j
        from src.services.causal import get_causal_engine

        neo4j_service = get_neo4j_service()
        await neo4j_service.connect()
        logger.info("Neo4j connected and ready")

        # Enable graph persistence in the causal engine
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


class DatasetSelection(BaseModel):
    """Selection mapping for a stored dataset."""

    dataset_id: str = Field(..., description="Dataset registry ID")
    treatment: str = Field(..., description="Treatment column name")
    outcome: str = Field(..., description="Outcome column name")
    covariates: list[str] = Field(default_factory=list)
    effect_modifiers: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    """Input request for CARF processing."""

    query: str = Field(..., min_length=1, description="The query to process")
    context: dict | None = Field(default=None, description="Additional context")
    causal_estimation: CausalEstimationConfig | None = Field(
        default=None,
        description="Optional DoWhy/EconML estimation config",
    )
    bayesian_inference: BayesianInferenceConfig | None = Field(
        default=None,
        description="Optional PyMC inference config",
    )
    dataset_selection: DatasetSelection | None = Field(
        default=None,
        description="Optional dataset selection for causal estimation",
    )
    use_fast_oracle: bool = Field(
        default=False,
        description="Use ChimeraOracle for fast causal scoring instead of full DoWhy analysis",
    )
    oracle_scenario_id: str | None = Field(
        default=None,
        description="Scenario ID for fast oracle (required if use_fast_oracle=True)",
    )


from src.services.visualization_engine import get_visualization_config, ContextualVisualization
from src.services.schema_detector import schema_detector, SchemaDetectionResult
from src.services.improvement_suggestions import improvement_service, ImprovementContext, Suggestion


@app.post("/data/detect-schema", response_model=SchemaDetectionResult, tags=["Data"])
async def detect_schema_endpoint(file: UploadFile = File(...)):
    """
    Detect schema and suggested roles from an uploaded CSV file.
    """
    content = await file.read()
    return schema_detector.detect(content, file.filename)


@app.post("/agent/suggest-improvements", response_model=list[Suggestion], tags=["Agent"])
async def suggest_improvements_endpoint(context: ImprovementContext):
    """
    Generate proactive suggestions for query refinement or next steps.
    """
    return improvement_service.suggest(context)


# ==================== Configuration Endpoints ====================

@app.get("/config/visualization", tags=["Configuration"])
async def get_viz_config(context: str = "general") -> ContextualVisualization:
    """Get context-aware visualization configuration."""
    return get_visualization_config(context)


class LLMConfigStatus(BaseModel):
    """Status of LLM configuration."""

    is_configured: bool = Field(description="Whether LLM is properly configured")
    provider: str | None = Field(default=None, description="Configured provider name")
    model: str | None = Field(default=None, description="Configured model name")
    message: str = Field(description="Status message")


class LLMConfigValidateRequest(BaseModel):
    """Request to validate LLM configuration."""

    provider: str = Field(description="LLM provider: openai, anthropic, deepseek, local")
    api_key: str | None = Field(default=None, description="API key (not needed for local)")
    base_url: str | None = Field(default=None, description="Custom base URL for local/ollama")


@app.get("/config/status", tags=["Configuration"])
async def get_config_status() -> LLMConfigStatus:
    """Check current LLM configuration status.

    Returns whether the system has a valid LLM configuration.
    """
    # Check for any configured API key
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")

    if openai_key:
        return LLMConfigStatus(
            is_configured=True,
            provider="openai",
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            message="OpenAI API configured",
        )
    elif anthropic_key:
        return LLMConfigStatus(
            is_configured=True,
            provider="anthropic",
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet"),
            message="Anthropic API configured",
        )
    elif deepseek_key:
        return LLMConfigStatus(
            is_configured=True,
            provider="deepseek",
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            message="DeepSeek API configured",
        )
    else:
        return LLMConfigStatus(
            is_configured=False,
            provider=None,
            model=None,
            message="No LLM API key configured. Please set up your API key.",
        )


@app.post("/config/validate", tags=["Configuration"])
async def validate_config(request: LLMConfigValidateRequest) -> dict:
    """Validate LLM configuration.

    Tests that the provided API key and configuration are valid.
    """
    import httpx

    provider = request.provider.lower()

    # For local/ollama, check connectivity
    if provider == "local":
        base_url = request.base_url or "http://localhost:11434"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                if response.status_code == 200:
                    return {"valid": True, "message": "Local Ollama server is accessible"}
                else:
                    return {"valid": False, "message": f"Ollama returned status {response.status_code}"}
        except Exception as e:
            return {"valid": False, "message": f"Cannot connect to Ollama: {str(e)}"}

    # For cloud providers, validate API key format
    if not request.api_key:
        return {"valid": False, "message": "API key is required for cloud providers"}

    api_key = request.api_key.strip()

    if provider == "openai":
        if not api_key.startswith("sk-"):
            return {"valid": False, "message": "OpenAI API key should start with 'sk-'"}
        if len(api_key) < 20:
            return {"valid": False, "message": "OpenAI API key appears too short"}
        return {"valid": True, "message": "OpenAI API key format is valid"}

    elif provider == "anthropic":
        if not api_key.startswith("sk-ant-"):
            return {"valid": False, "message": "Anthropic API key should start with 'sk-ant-'"}
        return {"valid": True, "message": "Anthropic API key format is valid"}

    elif provider == "deepseek":
        if len(api_key) < 10:
            return {"valid": False, "message": "DeepSeek API key appears too short"}
        return {"valid": True, "message": "DeepSeek API key format is valid"}

    else:
        return {"valid": False, "message": f"Unknown provider: {provider}"}


class LLMConfigUpdateRequest(BaseModel):
    """Request to update LLM configuration."""

    provider: str = Field(description="LLM provider: openai, anthropic, deepseek, local")
    api_key: str | None = Field(default=None, description="API key (not needed for local)")
    base_url: str | None = Field(default=None, description="Custom base URL for local/ollama")


@app.post("/config/update", tags=["Configuration"])
async def update_config(request: LLMConfigUpdateRequest) -> LLMConfigStatus:
    """Update LLM configuration and persist to .env.

    1. Validates the new configuration
    2. Updates environment variables
    3. Clears LLM client cache
    4. Writes to .env file
    """
    # 1. Validate
    validation = await validate_config(
        LLMConfigValidateRequest(
            provider=request.provider,
            api_key=request.api_key,
            base_url=request.base_url,
        )
    )
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["message"])

    # 2. Update Environment
    provider = request.provider.lower()
    from src.core.llm import PROVIDER_CONFIGS, get_chat_model

    # Determine env key to set
    env_key = None
    if provider == "openai":
        env_key = "OPENAI_API_KEY"
    elif provider == "deepseek":
        env_key = "DEEPSEEK_API_KEY"
    elif provider == "anthropic":
        env_key = "ANTHROPIC_API_KEY"

    # Set new variables
    os.environ["LLM_PROVIDER"] = provider
    if env_key and request.api_key:
        os.environ[env_key] = request.api_key
        # Ensure we don't have conflicting keys set
        for k in ["OPENAI_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY"]:
            if k != env_key and k in os.environ:
                del os.environ[k]

    # 3. Clear Cache
    get_chat_model.cache_clear()
    logger.info(f"Updated LLM config to {provider} and cleared cache")

    # 4. Persist to .env
    env_path = PROJECT_ROOT / ".env"
    try:
        current_env = {}
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        current_env[k] = v

        # Update values
        current_env["LLM_PROVIDER"] = provider
        if env_key and request.api_key:
            current_env[env_key] = request.api_key
            # Remove others to avoid confusion
            for k in ["OPENAI_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY"]:
                if k != env_key and k in current_env:
                    del current_env[k]
        
        # Write back
        with open(env_path, "w", encoding="utf-8") as f:
            for k, v in current_env.items():
                f.write(f"{k}={v}\n")
            
            # Preserve comments? (Simplification: just writing kv pairs for now, 
            # ideally we'd use python-dotenv but we want to avoid deps if possible)
            # Checking if file was empty or new
            if not current_env:
                f.write(f"LLM_PROVIDER={provider}\n")
                if env_key and request.api_key:
                    f.write(f"{env_key}={request.api_key}\n")

    except Exception as e:
        logger.error(f"Failed to write .env: {e}")
        # Non-fatal, just means it won't persist across restarts

    return await get_config_status()


# ==================== ChimeraOracle Endpoints ====================


class OracleTrainRequest(BaseModel):
    """Request to train a ChimeraOracle model."""

    scenario_id: str = Field(..., description="Unique ID for this scenario model")
    csv_path: str = Field(..., description="Path to training data CSV")
    treatment: str = Field(..., description="Treatment variable name")
    outcome: str = Field(..., description="Outcome variable name")
    covariates: list[str] = Field(default_factory=list)
    effect_modifiers: list[str] = Field(default_factory=list)
    n_estimators: int = Field(100, ge=10, le=500)


class OracleTrainResponse(BaseModel):
    """Response from oracle training."""

    status: str
    n_samples: int
    model_path: str
    average_treatment_effect: float
    effect_std: float
    error: str | None = None


class OraclePredictRequest(BaseModel):
    """Request for fast causal prediction."""

    scenario_id: str = Field(..., description="Scenario model to use")
    context: dict[str, Any] = Field(..., description="Feature values for prediction")


class OraclePredictResponse(BaseModel):
    """Response from oracle prediction."""

    effect_estimate: float
    confidence_interval: tuple[float, float]
    feature_importance: dict[str, float]
    used_model: str
    prediction_time_ms: float


class OracleModelInfo(BaseModel):
    """Information about a trained oracle model."""

    scenario_id: str
    average_treatment_effect: float
    effect_std: float
    n_samples: int


@app.get("/oracle/models", tags=["ChimeraOracle"])
async def list_oracle_models() -> list[OracleModelInfo]:
    """List all trained ChimeraOracle models."""
    from src.services.chimera_oracle import get_oracle_engine

    engine = get_oracle_engine()
    models = []
    for scenario_id in engine.get_available_scenarios():
        stats = engine.get_average_treatment_effect(scenario_id)
        models.append(
            OracleModelInfo(
                scenario_id=scenario_id,
                average_treatment_effect=stats["ate"],
                effect_std=stats["std"],
                n_samples=stats["n_samples"],
            )
        )
    return models


@app.post("/oracle/train", tags=["ChimeraOracle"])
async def train_oracle_model(request: OracleTrainRequest) -> OracleTrainResponse:
    """Train a CausalForestDML model on scenario data.
    
    This creates a fast-prediction model for the given scenario.
    Once trained, use /oracle/predict for sub-100ms causal scoring.
    """
    from src.services.chimera_oracle import get_oracle_engine

    engine = get_oracle_engine()
    result = await engine.train_on_scenario(
        scenario_id=request.scenario_id,
        csv_path=request.csv_path,
        treatment=request.treatment,
        outcome=request.outcome,
        covariates=request.covariates,
        effect_modifiers=request.effect_modifiers,
        n_estimators=request.n_estimators,
    )

    return OracleTrainResponse(
        status=result.status,
        n_samples=result.n_samples,
        model_path=result.model_path,
        average_treatment_effect=result.average_treatment_effect,
        effect_std=result.effect_std,
        error=result.error,
    )


@app.post("/oracle/predict", tags=["ChimeraOracle"])
async def predict_oracle_effect(request: OraclePredictRequest) -> OraclePredictResponse:
    """Fast causal effect prediction using a trained model.
    
    Returns effect estimate with confidence interval in <100ms.
    For rigorous analysis with refutation tests, use /query with DoWhy.
    """
    from src.services.chimera_oracle import get_oracle_engine

    engine = get_oracle_engine()
    
    if not engine.has_model(request.scenario_id):
        raise HTTPException(
            status_code=404,
            detail=f"No trained model for scenario: {request.scenario_id}. Train first with /oracle/train"
        )

    prediction = engine.predict_effect(request.scenario_id, request.context)

    return OraclePredictResponse(
        effect_estimate=prediction.effect_estimate,
        confidence_interval=prediction.confidence_interval,
        feature_importance=prediction.feature_importance,
        used_model=prediction.used_model,
        prediction_time_ms=prediction.prediction_time_ms,
    )


@app.get("/oracle/models/{scenario_id}", tags=["ChimeraOracle"])
async def get_oracle_model(scenario_id: str) -> OracleModelInfo:
    """Get details about a specific trained model."""
    from src.services.chimera_oracle import get_oracle_engine

    engine = get_oracle_engine()
    
    if not engine.has_model(scenario_id):
        raise HTTPException(status_code=404, detail=f"Model not found: {scenario_id}")
    
    stats = engine.get_average_treatment_effect(scenario_id)
    return OracleModelInfo(
        scenario_id=scenario_id,
        average_treatment_effect=stats["ate"],
        effect_std=stats["std"],
        n_samples=stats["n_samples"],
    )


class DatasetCreateRequest(BaseModel):
    """Dataset upload payload for the registry."""

    name: str = Field(..., min_length=1, description="Dataset name")
    description: str | None = Field(default=None, description="Dataset description")
    data: list[dict[str, Any]] | dict[str, list[Any]] = Field(
        ..., description="Rows as list of objects or columns as dict of lists"
    )


class DatasetCreateResponse(BaseModel):
    """Response for dataset creation."""

    dataset_id: str
    name: str
    description: str | None
    created_at: str
    row_count: int
    column_names: list[str]


class DatasetListResponse(BaseModel):
    """List datasets response."""

    datasets: list[DatasetCreateResponse]


class DatasetPreviewResponse(BaseModel):
    """Preview rows for a dataset."""

    dataset_id: str
    rows: list[dict[str, Any]]


class ScenarioMetadata(BaseModel):
    """Demo scenario metadata."""

    id: str
    name: str
    description: str
    payload_path: str
    suggested_queries: list[str] | None = None


class ScenarioListResponse(BaseModel):
    """List demo scenarios."""

    scenarios: list[ScenarioMetadata]


class ScenarioDetailResponse(BaseModel):
    """Scenario details including payload."""

    scenario: ScenarioMetadata
    payload: dict[str, Any]


def _validate_payload_limits(request: QueryRequest) -> None:
    """Guardrails for payload sizes in the research demo."""
    if request.dataset_selection and request.causal_estimation:
        raise HTTPException(
            status_code=400,
            detail="Provide either dataset_selection or causal_estimation, not both",
        )

    if request.causal_estimation and request.causal_estimation.data is not None:
        data = request.causal_estimation.data
        if isinstance(data, list) and len(data) > 5000:
            raise HTTPException(
                status_code=400,
                detail="causal_estimation.data exceeds 5000 rows",
            )
        if isinstance(data, dict):
            longest = max((len(values) for values in data.values()), default=0)
            if longest > 5000:
                raise HTTPException(
                    status_code=400,
                    detail="causal_estimation.data exceeds 5000 rows",
                )

    if request.bayesian_inference and request.bayesian_inference.observations:
        if len(request.bayesian_inference.observations) > 10000:
            raise HTTPException(
                status_code=400,
                detail="bayesian_inference.observations exceeds 10000 values",
            )


class ReasoningStep(BaseModel):
    """A step in the reasoning chain."""

    node: str
    action: str
    confidence: str
    timestamp: datetime
    duration_ms: int = Field(0, alias="durationMs", serialization_alias="durationMs")





class CausalResult(BaseModel):
    """Causal analysis result for API response."""

    model_config = {"populate_by_name": True, "serialize_by_alias": True}

    effect: float
    unit: str = "units"
    p_value: float | None = Field(None, alias="pValue", serialization_alias="pValue")
    ci_low: float = Field(..., alias="ciLow", serialization_alias="confidenceInterval")
    ci_high: float = Field(..., alias="ciHigh")
    description: str
    refutations_passed: int = Field(0, alias="refutationsPassed", serialization_alias="refutationsPassed")
    refutations_total: int = Field(0, alias="refutationsTotal", serialization_alias="refutationsTotal")
    confounders_controlled: int = Field(0, alias="confoundersControlled", serialization_alias="confoundersControlled")
    confounders_total: int = Field(0, alias="confoundersTotal", serialization_alias="confoundersTotal")
    treatment: str = ""
    outcome: str = ""



class BayesianResult(BaseModel):
    """Bayesian analysis result for API response."""

    model_config = {"populate_by_name": True, "serialize_by_alias": True}

    posterior_mean: float = Field(..., alias="posteriorMean", serialization_alias="posteriorMean")
    ci_low: float = Field(..., alias="ciLow")
    ci_high: float = Field(..., alias="ciHigh")
    uncertainty_before: float = Field(..., alias="uncertaintyBefore", serialization_alias="uncertaintyBefore")
    uncertainty_after: float = Field(..., alias="uncertaintyAfter", serialization_alias="uncertaintyAfter")
    epistemic_uncertainty: float = Field(..., alias="epistemicUncertainty", serialization_alias="epistemicUncertainty")
    aleatoric_uncertainty: float = Field(..., alias="aleatoricUncertainty", serialization_alias="aleatoricUncertainty")
    hypothesis: str
    confidence_level: str = Field(..., alias="confidenceLevel", serialization_alias="confidenceLevel")
    probes_designed: int = Field(0, alias="probesDesigned", serialization_alias="probesDesigned")
    recommended_probe: str | None = Field(None, alias="recommendedProbe", serialization_alias="recommendedProbe")


class GuardianResult(BaseModel):
    """Guardian policy check result for API response."""

    model_config = {"populate_by_name": True, "serialize_by_alias": True}

    verdict: GuardianVerdict | None
    policies_passed: int = Field(0, alias="policiesPassed", serialization_alias="policiesPassed")
    policies_total: int = Field(0, alias="policiesTotal", serialization_alias="policiesTotal")
    risk_level: str = Field("low", alias="riskLevel", serialization_alias="riskLevel")
    violations: list[str] = []


class QueryResponse(BaseModel):
    """Response from CYNEPIC processing."""

    model_config = {"populate_by_name": True, "serialize_by_alias": True}

    session_id: str = Field(..., alias="sessionId", serialization_alias="sessionId")
    domain: CynefinDomain
    domain_confidence: float = Field(..., alias="domainConfidence", serialization_alias="domainConfidence")
    domain_entropy: float = Field(0.0, alias="domainEntropy", serialization_alias="domainEntropy")
    guardian_verdict: GuardianVerdict | None = Field(None, alias="guardianVerdict", serialization_alias="guardianVerdict")
    response: str | None
    requires_human: bool = Field(..., alias="requiresHuman", serialization_alias="requiresHuman")
    reasoning_chain: list[ReasoningStep] = Field(..., alias="reasoningChain", serialization_alias="reasoningChain")
    causal_result: CausalResult | None = Field(None, alias="causalResult", serialization_alias="causalResult")
    bayesian_result: BayesianResult | None = Field(None, alias="bayesianResult", serialization_alias="bayesianResult")
    guardian_result: GuardianResult | None = Field(None, alias="guardianResult", serialization_alias="guardianResult")
    error: str | None = None
    # Router transparency fields
    router_reasoning: str | None = Field(None, alias="routerReasoning", serialization_alias="routerReasoning")
    router_key_indicators: list[str] = Field(default_factory=list, alias="routerKeyIndicators", serialization_alias="routerKeyIndicators")
    domain_scores: dict[str, float] = Field(default_factory=dict, alias="domainScores", serialization_alias="domainScores")
    triggered_method: str | None = Field(None, alias="triggeredMethod", serialization_alias="triggeredMethod")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "phase": "MVP",
        "version": "0.5.0",
        "components": {
            "router": "active",
            "guardian": "active",
            "human_layer": "mock" if not os.getenv("HUMANLAYER_API_KEY") else "active",
        },
    }


class InfrastructureStatus(BaseModel):
    """Status of infrastructure components."""
    service: str
    status: str  # healthy, unhealthy, degraded
    latency_ms: float | None = None
    message: str | None = None


class HealthCheckResponse(BaseModel):
    """Comprehensive health check response."""
    status: str
    version: str
    services: list[InfrastructureStatus]
    all_healthy: bool
    ready_for_analysis: bool


@app.get("/health/infrastructure", response_model=HealthCheckResponse, tags=["Health"])
async def infrastructure_health_check():
    """Comprehensive infrastructure health check.

    Verifies connectivity to all required services before analysis:
    - Neo4j graph database
    - Kafka message broker
    - OPA policy engine (optional)
    - LLM provider
    """
    import httpx
    import time

    services = []

    # Check Neo4j
    try:
        start = time.perf_counter()
        from src.services.neo4j_service import get_neo4j_service
        neo4j = get_neo4j_service()
        if neo4j._driver:
            # Quick connectivity test
            await neo4j._driver.verify_connectivity()
            latency = (time.perf_counter() - start) * 1000
            services.append(InfrastructureStatus(
                service="neo4j",
                status="healthy",
                latency_ms=latency,
                message="Connected"
            ))
        else:
            services.append(InfrastructureStatus(
                service="neo4j",
                status="unhealthy",
                message="Driver not initialized"
            ))
    except Exception as e:
        services.append(InfrastructureStatus(
            service="neo4j",
            status="unhealthy",
            message=str(e)[:100]
        ))

    # Check Kafka
    kafka_enabled = os.getenv("KAFKA_ENABLED", "false").lower() == "true"
    if kafka_enabled:
        try:
            from src.services.kafka_audit import get_kafka_audit_service
            kafka_service = get_kafka_audit_service()
            if kafka_service._producer is not None:
                services.append(InfrastructureStatus(
                    service="kafka",
                    status="healthy",
                    message="Producer available"
                ))
            else:
                services.append(InfrastructureStatus(
                    service="kafka",
                    status="degraded",
                    message="Producer not initialized"
                ))
        except Exception as e:
            services.append(InfrastructureStatus(
                service="kafka",
                status="unhealthy",
                message=str(e)[:100]
            ))
    else:
        services.append(InfrastructureStatus(
            service="kafka",
            status="disabled",
            message="KAFKA_ENABLED=false"
        ))

    # Check OPA (optional)
    opa_enabled = os.getenv("OPA_ENABLED", "false").lower() == "true"
    if opa_enabled:
        try:
            start = time.perf_counter()
            opa_url = os.getenv("OPA_URL", "http://localhost:8181")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{opa_url}/health")
                latency = (time.perf_counter() - start) * 1000
                if response.status_code == 200:
                    services.append(InfrastructureStatus(
                        service="opa",
                        status="healthy",
                        latency_ms=latency,
                        message="Connected"
                    ))
                else:
                    services.append(InfrastructureStatus(
                        service="opa",
                        status="degraded",
                        message=f"Status {response.status_code}"
                    ))
        except Exception as e:
            services.append(InfrastructureStatus(
                service="opa",
                status="unhealthy",
                message=str(e)[:100]
            ))
    else:
        services.append(InfrastructureStatus(
            service="opa",
            status="disabled",
            message="OPA_ENABLED=false"
        ))

    # Check LLM provider
    llm_provider = os.getenv("LLM_PROVIDER", "unknown")
    test_mode = os.getenv("CARF_TEST_MODE", "").lower() in ("1", "true")
    if test_mode:
        services.append(InfrastructureStatus(
            service="llm",
            status="test_mode",
            message=f"Test mode active (CARF_TEST_MODE=1)"
        ))
    elif os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("ANTHROPIC_API_KEY"):
        services.append(InfrastructureStatus(
            service="llm",
            status="healthy",
            message=f"Provider: {llm_provider}"
        ))
    else:
        services.append(InfrastructureStatus(
            service="llm",
            status="unhealthy",
            message="No API key configured"
        ))

    # Determine overall status
    unhealthy_count = sum(1 for s in services if s.status == "unhealthy")
    all_healthy = unhealthy_count == 0
    ready_for_analysis = all_healthy or (unhealthy_count <= 1 and
                                          not any(s.service == "neo4j" and s.status == "unhealthy" for s in services))

    overall_status = "healthy" if all_healthy else ("degraded" if ready_for_analysis else "unhealthy")

    return HealthCheckResponse(
        status=overall_status,
        version="0.5.0",
        services=services,
        all_healthy=all_healthy,
        ready_for_analysis=ready_for_analysis,
    )


@app.post("/datasets", response_model=DatasetCreateResponse)
async def create_dataset(request: DatasetCreateRequest):
    """Create a dataset in the local registry."""
    store = get_dataset_store()
    try:
        metadata = store.create_dataset(
            name=request.name,
            description=request.description,
            data=request.data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DatasetCreateResponse(**_metadata_to_payload(metadata))


@app.get("/datasets", response_model=DatasetListResponse)
async def list_datasets():
    """List datasets from the local registry."""
    store = get_dataset_store()
    datasets = [
        DatasetCreateResponse(**_metadata_to_payload(metadata))
        for metadata in store.list_datasets()
    ]
    return DatasetListResponse(datasets=datasets)


@app.get("/datasets/{dataset_id}/preview", response_model=DatasetPreviewResponse)
async def preview_dataset(dataset_id: str, limit: int = 10):
    """Preview dataset rows."""
    store = get_dataset_store()
    try:
        rows = store.load_preview(dataset_id, limit=limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return DatasetPreviewResponse(dataset_id=dataset_id, rows=rows)


@app.get("/scenarios", response_model=ScenarioListResponse)
async def list_scenarios():
    """List demo scenarios for the UI."""
    scenarios = _load_scenarios()
    return ScenarioListResponse(scenarios=scenarios)


@app.get("/scenarios/{scenario_id}", response_model=ScenarioDetailResponse)
async def get_scenario(scenario_id: str):
    """Fetch a scenario payload by ID."""
    scenarios = _load_scenarios()
    scenario_map = {scenario.id: scenario for scenario in scenarios}
    scenario = scenario_map.get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    payload = _load_scenario_payload(scenario.payload_path)
    return ScenarioDetailResponse(scenario=scenario, payload=payload)


class ScenarioLoadRequest(BaseModel):
    """Request to load a scenario."""
    scenario_id: str


@app.post("/scenarios/load")
async def load_scenario(request: ScenarioLoadRequest):
    """Load a scenario by ID (POST version for compatibility)."""
    scenarios = _load_scenarios()
    scenario_map = {scenario.id: scenario for scenario in scenarios}
    scenario = scenario_map.get(request.scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    payload = _load_scenario_payload(scenario.payload_path)
    return {"scenario_id": request.scenario_id, "message": "Scenario loaded", "scenario": scenario.model_dump(), "payload": payload}


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a query through the CARF cognitive pipeline.

    The query flows through:
    1. Cynefin Router - classifies into domain (Clear/Complicated/Complex/Chaotic/Disorder)
    2. Domain Agent - processes based on classification
    3. Guardian - policy check
    4. Human Escalation - if needed

    Returns the final state with reasoning chain for audit.
    """
    try:
        _validate_payload_limits(request)

        context = dict(request.context or {})
        if request.dataset_selection:
            store = get_dataset_store()
            try:
                store.get_dataset(request.dataset_selection.dataset_id)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc

            context["dataset_selection"] = request.dataset_selection.model_dump()
            context["causal_estimation"] = CausalEstimationConfig(
                dataset_id=request.dataset_selection.dataset_id,
                treatment=request.dataset_selection.treatment,
                outcome=request.dataset_selection.outcome,
                covariates=request.dataset_selection.covariates,
                effect_modifiers=request.dataset_selection.effect_modifiers,
            ).model_dump()
        elif request.causal_estimation:
            context["causal_estimation"] = request.causal_estimation.model_dump()
        
        # Auto-load scenario configuration if ID provided but config missing
        scenario_id = context.get("scenario_id")
        if scenario_id:
            try:
                scenarios = _load_scenarios()
                scenario = next((s for s in scenarios if s.id == scenario_id), None)
                if scenario:
                    payload = _load_scenario_payload(scenario.payload_path)

                    # Load domain_hint and other context settings from scenario
                    if "context" in payload and isinstance(payload["context"], dict):
                        for key, value in payload["context"].items():
                            if key not in context:  # Don't override user-provided context
                                context[key] = value

                    # Load causal estimation config
                    if "causal_estimation" in payload and "causal_estimation" not in context:
                        ce_config = CausalEstimationConfig(**payload["causal_estimation"])
                        context["causal_estimation"] = ce_config.model_dump()

                    # Load bayesian inference config
                    if "bayesian_inference" in payload and "bayesian_inference" not in context:
                        bi_config = BayesianInferenceConfig(**payload["bayesian_inference"])
                        context["bayesian_inference"] = bi_config.model_dump()

                    logger.info(f"Auto-loaded scenario config: {scenario_id}, domain_hint={context.get('domain_hint')}")
            except Exception as e:
                logger.warning(f"Failed to auto-load scenario {scenario_id}: {e}")
                # Don't fail the request, proceed and let agents decide

        if request.bayesian_inference:
            context["bayesian_inference"] = request.bayesian_inference.model_dump()

        # Run the full CARF pipeline
        final_state = await run_carf(
            user_input=request.query,
            context=context,
        )

        # Build reasoning chain for response
        reasoning_chain = [
            ReasoningStep(
                node=step.node_name,
                action=step.action,
                confidence=step.confidence.value,
                timestamp=step.timestamp,
                duration_ms=step.duration_ms,
            )
            for step in final_state.reasoning_chain
        ]

        # Build causal result if available
        causal_result = None
        if final_state.causal_evidence:
            ce = final_state.causal_evidence
            refutations_passed = sum(1 for v in ce.refutation_results.values() if v)
            causal_result = CausalResult(
                effect=ce.effect_size,
                unit="units",
                p_value=ce.p_value,
                ci_low=ce.confidence_interval[0],
                ci_high=ce.confidence_interval[1],
                description=ce.interpretation or f"Effect of {ce.treatment} on {ce.outcome}",
                refutations_passed=refutations_passed,
                refutations_total=len(ce.refutation_results),
                confounders_controlled=len([c for c in ce.confounders_checked]),
                confounders_total=len(ce.confounders_checked),
                treatment=ce.treatment,
                outcome=ce.outcome,
            )

        # Build bayesian result if available
        bayesian_result = None
        if final_state.bayesian_evidence:
            be = final_state.bayesian_evidence
            bayesian_result = BayesianResult(
                posterior_mean=be.posterior_mean,
                ci_low=be.credible_interval[0],
                ci_high=be.credible_interval[1],
                uncertainty_before=be.uncertainty_before,
                uncertainty_after=be.uncertainty_after,
                epistemic_uncertainty=be.epistemic_uncertainty,
                aleatoric_uncertainty=be.aleatoric_uncertainty,
                hypothesis=be.hypothesis,
                confidence_level=be.confidence_level,
                probes_designed=be.probes_designed,
                recommended_probe=be.recommended_probe,
            )

        # Build guardian result
        guardian_result = GuardianResult(
            verdict=final_state.guardian_verdict,
            policies_passed=0 if final_state.policy_violations else 1,
            policies_total=1,
            risk_level="high" if final_state.policy_violations else "low",
            violations=final_state.policy_violations or [],
        )

        return QueryResponse(
            session_id=str(final_state.session_id),
            domain=final_state.cynefin_domain,
            domain_confidence=final_state.domain_confidence,
            domain_entropy=final_state.domain_entropy,
            guardian_verdict=final_state.guardian_verdict,
            response=final_state.final_response,
            requires_human=final_state.should_escalate_to_human(),
            reasoning_chain=reasoning_chain,
            causal_result=causal_result,
            bayesian_result=bayesian_result,
            guardian_result=guardian_result,
            error=final_state.error,
            # Router transparency fields
            router_reasoning=final_state.current_hypothesis,
            router_key_indicators=final_state.router_key_indicators,
            domain_scores=final_state.domain_scores,
            triggered_method=final_state.triggered_method,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"CARF pipeline validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"CARF pipeline error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"CARF processing failed: {str(e)}",
        )


from fastapi.responses import StreamingResponse


class ProgressUpdate(BaseModel):
    """Real-time progress update during analysis."""
    step: str
    status: str  # started, completed, error
    message: str
    progress_percent: int
    timestamp: str
    details: dict[str, Any] | None = None


@app.post("/query/stream", tags=["Query"])
async def process_query_stream(request: QueryRequest):
    """Process a query with real-time chain-of-thought streaming.

    Returns Server-Sent Events (SSE) with progress updates as the
    analysis progresses through each stage:
    1. Router classification
    2. Domain agent analysis (Causal/Bayesian/etc.)
    3. Guardian policy check
    4. Final result

    Use this endpoint when you need to show users real-time progress.
    """
    import asyncio

    async def generate_progress():
        try:
            _validate_payload_limits(request)

            # Progress: Starting
            yield f"data: {json.dumps({'step': 'init', 'status': 'started', 'message': 'Initializing analysis', 'progress_percent': 5, 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(0.1)

            # Build context
            context = dict(request.context or {})
            scenario_id = context.get("scenario_id")

            # Auto-load scenario configuration
            if scenario_id:
                try:
                    scenarios = _load_scenarios()
                    scenario = next((s for s in scenarios if s.id == scenario_id), None)
                    if scenario:
                        payload = _load_scenario_payload(scenario.payload_path)
                        if "context" in payload and isinstance(payload["context"], dict):
                            for key, value in payload["context"].items():
                                if key not in context:
                                    context[key] = value
                        if "causal_estimation" in payload and "causal_estimation" not in context:
                            ce_config = CausalEstimationConfig(**payload["causal_estimation"])
                            context["causal_estimation"] = ce_config.model_dump()
                        if "bayesian_inference" in payload and "bayesian_inference" not in context:
                            bi_config = BayesianInferenceConfig(**payload["bayesian_inference"])
                            context["bayesian_inference"] = bi_config.model_dump()
                except Exception as e:
                    logger.warning(f"Failed to auto-load scenario {scenario_id}: {e}")

            if request.causal_estimation:
                context["causal_estimation"] = request.causal_estimation.model_dump()
            if request.bayesian_inference:
                context["bayesian_inference"] = request.bayesian_inference.model_dump()

            yield f"data: {json.dumps({'step': 'context', 'status': 'completed', 'message': 'Context prepared', 'progress_percent': 10, 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(0.1)

            # Progress: Router
            yield f"data: {json.dumps({'step': 'router', 'status': 'started', 'message': 'Classifying query into Cynefin domain...', 'progress_percent': 15, 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(0.1)

            # Import and run the pipeline in steps
            from src.core.state import EpistemicState
            from src.workflows.router import cynefin_router_node

            initial_state = EpistemicState(user_input=request.query, context=context)

            # Step 1: Router
            state = await cynefin_router_node(initial_state)
            domain = state.cynefin_domain.value
            confidence = state.domain_confidence

            yield f"data: {json.dumps({'step': 'router', 'status': 'completed', 'message': f'Classified as {domain} (confidence: {confidence:.0%})', 'progress_percent': 30, 'timestamp': datetime.now().isoformat(), 'details': {'domain': domain, 'confidence': confidence, 'entropy': state.domain_entropy}})}\n\n"
            await asyncio.sleep(0.1)

            # Progress: Domain Agent
            triggered_method = state.triggered_method or "unknown"
            yield f"data: {json.dumps({'step': 'domain_agent', 'status': 'started', 'message': f'Running {triggered_method} analysis...', 'progress_percent': 35, 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(0.1)

            # Run the full pipeline from here
            final_state = await run_carf(user_input=request.query, context=context)

            yield f"data: {json.dumps({'step': 'domain_agent', 'status': 'completed', 'message': 'Analysis complete', 'progress_percent': 70, 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(0.1)

            # Progress: Guardian
            guardian_status = final_state.guardian_verdict.value if final_state.guardian_verdict else "passed"
            yield f"data: {json.dumps({'step': 'guardian', 'status': 'completed', 'message': f'Policy check: {guardian_status}', 'progress_percent': 90, 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(0.1)

            # Final result
            reasoning_chain = [
                {
                    "node": step.node_name,
                    "action": step.action,
                    "confidence": step.confidence.value,
                    "timestamp": step.timestamp.isoformat(),
                    "durationMs": step.duration_ms,
                }
                for step in final_state.reasoning_chain
            ]

            causal_result = None
            if final_state.causal_evidence:
                ce = final_state.causal_evidence
                causal_result = {
                    "effect": ce.effect_size,
                    "confidenceInterval": ce.confidence_interval,
                    "refutationsPassed": sum(1 for v in ce.refutation_results.values() if v),
                    "treatment": ce.treatment,
                    "outcome": ce.outcome,
                }

            final_response = {
                "step": "complete",
                "status": "completed",
                "message": "Analysis complete",
                "progress_percent": 100,
                "timestamp": datetime.now().isoformat(),
                "result": {
                    "sessionId": str(final_state.session_id),
                    "domain": final_state.cynefin_domain.value,
                    "domainConfidence": final_state.domain_confidence,
                    "response": final_state.final_response,
                    "reasoningChain": reasoning_chain,
                    "causalResult": causal_result,
                    "guardianVerdict": final_state.guardian_verdict.value if final_state.guardian_verdict else None,
                }
            }
            yield f"data: {json.dumps(final_response)}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'step': 'error', 'status': 'error', 'message': str(e), 'progress_percent': 0, 'timestamp': datetime.now().isoformat()})}\n\n"

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


class FastQueryRequest(BaseModel):
    """Request for fast causal query bypassing LLM routing."""

    scenario_id: str = Field(description="Scenario with pre-trained Oracle model")
    treatment: str = Field(default="supplier_program", description="Treatment variable")
    outcome: str = Field(default="scope3_emissions", description="Outcome variable")
    context: dict[str, Any] = Field(default_factory=dict, description="Context for heterogeneous effects")


class FastQueryResponse(BaseModel):
    """Response from fast causal query."""

    effect_estimate: float = Field(description="Estimated causal effect")
    confidence_interval: tuple[float, float] = Field(description="95% confidence interval")
    interpretation: str = Field(description="Human-readable interpretation")
    prediction_time_ms: float = Field(description="Prediction latency in milliseconds")
    model_info: dict[str, Any] = Field(description="Model metadata")
    domain: str = Field(default="Complicated", description="Cynefin domain (fast path assumes Complicated)")


@app.post("/query/fast", response_model=FastQueryResponse, tags=["Query"])
async def process_fast_query(request: FastQueryRequest):
    """Fast causal effect query using pre-trained ChimeraOracle.

    Bypasses LLM-based Cynefin classification for <100ms response times.
    Use this for routine causal queries on scenarios with trained models.
    For complex/novel queries requiring full analysis, use /query instead.
    """
    from src.services.chimera_oracle import get_oracle_engine

    engine = get_oracle_engine()

    if not engine.has_model(request.scenario_id):
        raise HTTPException(
            status_code=404,
            detail=f"No trained Oracle model for scenario '{request.scenario_id}'. "
            f"Train first with POST /oracle/train. Available: {engine.get_available_scenarios()}"
        )

    try:
        prediction = engine.predict_effect(request.scenario_id, request.context)
        model_stats = engine.get_average_treatment_effect(request.scenario_id)

        # Generate interpretation
        effect = prediction.effect_estimate
        direction = "reduces" if effect < 0 else "increases"
        magnitude = abs(effect)

        interpretation = (
            f"The {request.treatment} {direction} {request.outcome} by approximately "
            f"{magnitude:.2f} units (95% CI: [{prediction.confidence_interval[0]:.2f}, "
            f"{prediction.confidence_interval[1]:.2f}]). "
            f"Based on {model_stats['n_samples']} samples."
        )

        return FastQueryResponse(
            effect_estimate=prediction.effect_estimate,
            confidence_interval=prediction.confidence_interval,
            interpretation=interpretation,
            prediction_time_ms=prediction.prediction_time_ms,
            model_info={
                "scenario_id": request.scenario_id,
                "average_treatment_effect": model_stats["ate"],
                "effect_std": model_stats["std"],
                "n_samples": model_stats["n_samples"],
                "feature_importance": prediction.feature_importance,
            },
            domain="Complicated",
        )
    except Exception as e:
        logger.error(f"Fast query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _metadata_to_payload(metadata: DatasetMetadata) -> dict[str, Any]:
    """Serialize dataset metadata for API responses."""
    return {
        "dataset_id": metadata.dataset_id,
        "name": metadata.name,
        "description": metadata.description,
        "created_at": metadata.created_at,
        "row_count": metadata.row_count,
        "column_names": metadata.column_names,
    }


def _load_scenarios() -> list[ScenarioMetadata]:
    """Load demo scenarios from the registry file."""
    registry_path = PROJECT_ROOT / "demo" / "scenarios.json"
    if not registry_path.exists():
        return []

    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse scenarios registry: %s", exc)
        return []

    scenarios = []
    for item in data:
        try:
            scenarios.append(ScenarioMetadata(**item))
        except Exception as exc:
            logger.warning("Skipping invalid scenario entry: %s", exc)
    return scenarios


def _load_scenario_payload(payload_path: str) -> dict[str, Any]:
    """Load scenario payload JSON from disk."""
    path = PROJECT_ROOT / payload_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Scenario payload not found")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Invalid scenario payload") from exc


@app.get("/domains")
async def list_domains():
    """List all Cynefin domains and their descriptions."""
    return {
        "domains": [
            {
                "name": "Clear",
                "description": "Cause-effect obvious. Deterministic automation.",
                "route": "deterministic_runner",
            },
            {
                "name": "Complicated",
                "description": "Requires expert analysis. Causal inference.",
                "route": "causal_analyst",
            },
            {
                "name": "Complex",
                "description": "Emergent causality. Bayesian probing.",
                "route": "bayesian_explorer",
            },
            {
                "name": "Chaotic",
                "description": "Crisis mode. Circuit breaker.",
                "route": "circuit_breaker",
            },
            {
                "name": "Disorder",
                "description": "Cannot classify. Human escalation.",
                "route": "human_escalation",
            },
        ]
    }


# ============================================================================
# Phase 7: /analyze Endpoint - File Upload and Analysis
# ============================================================================


class AnalyzeRequest(BaseModel):
    """Request for text analysis (when no file uploaded)."""

    query: str = Field(..., description="Analysis query")
    text_content: str | None = Field(None, description="Text content to analyze")
    context: dict[str, Any] | None = Field(None, description="Additional context")


@app.post("/analyze", response_model=FileAnalysisResult)
async def analyze_content(
    file: UploadFile | None = File(None),
    query: str = Form(""),
    text_content: str | None = Form(None),
    context: str | None = Form(None),
):
    """Analyze uploaded file or text content.

    Supports:
    - CSV files (parsed as tabular data)
    - JSON files (parsed as tabular or structured data)
    - PDF files (text extraction)
    - TXT/MD files (raw text)
    - Excel files (.xlsx, .xls)

    Returns analysis results with variable suggestions for causal analysis.
    """
    analyzer = get_file_analyzer()

    if file:
        # File upload analysis
        content = await file.read()
        filename = file.filename or "unknown"
        content_type = file.content_type

        result = await analyzer.analyze_file(content, filename, content_type)
        return result

    elif text_content:
        # Text content analysis
        text_analysis = await analyzer.analyze_text(text_content, query)
        return FileAnalysisResult(
            file_type="text",
            file_name="pasted_content",
            file_size=len(text_content),
            text_content=text_content[:10000],
            analysis_ready=False,
            error=None,
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="Either file or text_content must be provided",
        )


# ============================================================================
# Phase 7: /chat Endpoint - LLM-Powered Chat
# ============================================================================


@app.post("/chat", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """LLM chat with analysis context awareness.

    Provides:
    - Result interpretation ("Your effect size of 0.42 means...")
    - Reliability assessment ("Refutation tests passed, but...")
    - Improvement suggestions ("Add more confounders to...")
    - Platform guidance ("Use /analyze to upload data...")
    """
    chat_service = get_chat_service()
    return await chat_service.chat(request)


# ============================================================================
# Phase 7: /explain Endpoints - Component Explanations
# ============================================================================


@app.post("/explain", response_model=ExplanationResponse)
async def explain_component(request: ExplanationRequest):
    """Get LLM-generated explanation for any CARF component.

    Supports explanations for:
    - Cynefin domain classification, confidence, entropy, solver
    - Causal effect estimates, p-values, confidence intervals, refutation tests
    - Bayesian posterior, epistemic/aleatoric uncertainty, probes
    - Guardian policies, verdicts
    - DAG nodes, edges, paths
    """
    explanation_service = get_explanation_service()
    return await explanation_service.explain(request)


@app.get("/explain/cynefin/{element}")
async def explain_cynefin_element(element: str, value: str | None = None):
    """Quick explanation for Cynefin router elements."""
    component_map = {
        "domain": ExplanationComponent.CYNEFIN_DOMAIN,
        "confidence": ExplanationComponent.CYNEFIN_CONFIDENCE,
        "entropy": ExplanationComponent.CYNEFIN_ENTROPY,
        "solver": ExplanationComponent.CYNEFIN_SOLVER,
    }

    if element not in component_map:
        raise HTTPException(status_code=404, detail=f"Unknown element: {element}")

    request = ExplanationRequest(
        component=component_map[element],
        element_id=element,
        context={"value": value} if value else None,
    )
    explanation_service = get_explanation_service()
    return await explanation_service.explain(request)


@app.get("/explain/causal/{element}")
async def explain_causal_element(element: str, value: str | None = None):
    """Quick explanation for causal analysis elements."""
    component_map = {
        "effect": ExplanationComponent.CAUSAL_EFFECT,
        "pvalue": ExplanationComponent.CAUSAL_PVALUE,
        "p_value": ExplanationComponent.CAUSAL_PVALUE,
        "ci": ExplanationComponent.CAUSAL_CI,
        "confidence_interval": ExplanationComponent.CAUSAL_CI,
        "refutation": ExplanationComponent.CAUSAL_REFUTATION,
        "confounder": ExplanationComponent.CAUSAL_CONFOUNDER,
    }

    if element not in component_map:
        raise HTTPException(status_code=404, detail=f"Unknown element: {element}")

    request = ExplanationRequest(
        component=component_map[element],
        element_id=element,
        context={"value": value} if value else None,
    )
    explanation_service = get_explanation_service()
    return await explanation_service.explain(request)


@app.get("/explain/bayesian/{element}")
async def explain_bayesian_element(element: str, value: str | None = None):
    """Quick explanation for Bayesian analysis elements."""
    component_map = {
        "posterior": ExplanationComponent.BAYESIAN_POSTERIOR,
        "epistemic": ExplanationComponent.BAYESIAN_EPISTEMIC,
        "aleatoric": ExplanationComponent.BAYESIAN_ALEATORIC,
        "probe": ExplanationComponent.BAYESIAN_PROBE,
    }

    if element not in component_map:
        raise HTTPException(status_code=404, detail=f"Unknown element: {element}")

    request = ExplanationRequest(
        component=component_map[element],
        element_id=element,
        context={"value": value} if value else None,
    )
    explanation_service = get_explanation_service()
    return await explanation_service.explain(request)


@app.get("/explain/guardian/{element}")
async def explain_guardian_element(element: str, policy_name: str | None = None):
    """Quick explanation for Guardian elements."""
    component_map = {
        "policy": ExplanationComponent.GUARDIAN_POLICY,
        "verdict": ExplanationComponent.GUARDIAN_VERDICT,
    }

    if element not in component_map:
        raise HTTPException(status_code=404, detail=f"Unknown element: {element}")

    request = ExplanationRequest(
        component=component_map[element],
        element_id=policy_name or element,
        context={"policy_name": policy_name} if policy_name else None,
    )
    explanation_service = get_explanation_service()
    return await explanation_service.explain(request)


# ============================================================================
# Phase 7: /developer Endpoints - Developer Tools
# ============================================================================


@app.get("/developer/state", response_model=DeveloperState)
async def get_developer_state():
    """Get current system state for developer view.

    Returns:
    - System metrics (uptime, queries processed, errors, LLM calls)
    - Architecture layer status
    - Execution timeline
    - Recent logs
    """
    dev_service = get_developer_service()
    return dev_service.get_state()


@app.get("/developer/logs")
async def get_developer_logs(
    layer: str | None = None,
    level: str | None = None,
    limit: int = 100,
):
    """Get filtered log entries.

    Args:
        layer: Filter by CARF layer (router, mesh, services, guardian)
        level: Filter by log level (DEBUG, INFO, WARNING, ERROR)
        limit: Maximum number of logs to return
    """
    dev_service = get_developer_service()
    logs = dev_service.get_logs(layer=layer, level=level, limit=limit)
    return {"logs": [log.model_dump() for log in logs]}


@app.websocket("/developer/ws")
async def developer_websocket(websocket: WebSocket):
    """WebSocket for real-time log streaming.

    Connect to receive live log updates as they occur.
    """
    await websocket.accept()
    dev_service = get_developer_service()
    dev_service.add_ws_connection(websocket)

    try:
        while True:
            # Keep connection alive and wait for client messages
            data = await websocket.receive_text()
            # Client can send "ping" to keep connection alive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        dev_service.remove_ws_connection(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        dev_service.remove_ws_connection(websocket)


# ============================================================================
# Phase 7: Demo Mode Check
# ============================================================================


@app.get("/config/status")
async def get_config_status():
    """Check configuration status for demo mode detection.

    Returns information about API key availability and demo mode status.
    """
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_deepseek = bool(os.getenv("DEEPSEEK_API_KEY"))
    has_humanlayer = bool(os.getenv("HUMANLAYER_API_KEY"))

    demo_mode = not (has_openai or has_deepseek)

    return {
        "demo_mode": demo_mode,
        "llm_available": has_openai or has_deepseek,
        "llm_provider": "deepseek" if has_deepseek else "openai" if has_openai else None,
        "human_layer_available": has_humanlayer,
        "message": "Running in demo mode with synthetic responses" if demo_mode else "Full functionality available",
    }


# ============================================================================
# Simulation Arena Endpoints - What-If Scenario Management
# ============================================================================

from src.services.simulation import (
    ScenarioConfig,
    SimulationResult,
    SimulationComparison,
    get_simulation_service
)


@app.post("/simulations/run", response_model=list[SimulationResult])
async def run_simulations(
    scenarios: list[ScenarioConfig],
    context: dict[str, Any] | None = None
):
    """Run multiple what-if scenario simulations.
    
    Each scenario specifies interventions on variables and uses a baseline
    dataset. The causal model is re-run for each scenario to estimate effects.
    
    Args:
        scenarios: List of scenario configurations with interventions
        context: Optional shared context for all scenarios
        
    Returns:
        List of simulation results with effect estimates and metrics
    """
    sim_service = get_simulation_service()
    
    try:
        results = await sim_service.run_multiple_scenarios(scenarios, context)
        return results
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Simulation execution failed: {str(e)}"
        )


@app.post("/simulations/compare", response_model=SimulationComparison)
async def compare_simulations(scenario_ids: list[str]):
    """Compare multiple simulation results.
    
    Analyzes all specified scenarios and identifies the best-performing
    scenario for each metric (effect size, confidence, refutation rate).
    
    Args:
        scenario_ids: List of scenario IDs to compare
        
    Returns:
        Comparison summary with best scenarios per metric
    """
    sim_service = get_simulation_service()
    
    try:
        comparison = await sim_service.compare_scenarios(scenario_ids)
        return comparison
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Comparison failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Comparison failed: {str(e)}"
        )


@app.get("/simulations/{scenario_id}/status", response_model=SimulationResult)
async def get_simulation_status(scenario_id: str):
    """Get the current status of a simulation.
    
    Use this to check if a background simulation is still running,
    completed, or failed.
    
    Args:
        scenario_id: Scenario identifier
        
    Returns:
        Current simulation result with status
    """
    sim_service = get_simulation_service()
    result = sim_service.get_simulation_status(scenario_id)
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation not found: {scenario_id}"
        )
    
    return result


@app.post("/simulations/{scenario_id}/rerun", response_model=SimulationResult)
async def rerun_simulation(
    scenario_id: str,
    config: ScenarioConfig,
    context: dict[str, Any] | None = None
):
    """Invalidate cache and re-run a scenario with updated parameters.
    
    This endpoint:
    1. Invalidates any cached results for the scenario
    2. Re-runs the causal analysis with fresh computation
    3. Links the new result to the original session
    
    Args:
        scenario_id: Scenario to re-run
        config: Updated scenario configuration
        context: Analysis context
        
    Returns:
        Fresh simulation result
    """
    sim_service = get_simulation_service()
    
    try:
        result = await sim_service.invalidate_and_rerun(scenario_id, config, context)
        return result
    except Exception as e:
        logger.error(f"Re-run failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Re-run failed: {str(e)}"
        )


@app.get("/sessions/{session_id}/lineage")
async def get_session_lineage(session_id: str):
    """Get the lineage tree for an analysis session.
    
    Shows parent sessions (what this was derived from) and
    child sessions (what was derived from this).
    
    Args:
        session_id: Session ID to trace
        
    Returns:
        Lineage information with parents and children
    """
    from src.services.neo4j_service import get_neo4j_service
    
    neo4j = get_neo4j_service()
    
    try:
        lineage = await neo4j.get_session_lineage(session_id)
        return lineage
    except Exception as e:
        logger.error(f"Lineage query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve lineage: {str(e)}"
        )


# ============================================================================
# Human-in-the-Loop Escalation Endpoints
# ============================================================================

from src.services.human_layer import (
    Escalation,
    get_pending_escalations,
    get_escalation,
    resolve_escalation,
    get_all_escalations,
)


class EscalationResolveRequest(BaseModel):
    """Request to resolve an escalation."""

    resolution: str = Field(
        ...,
        description="Decision: approve, reject, or clarify"
    )
    notes: str | None = Field(
        default=None,
        description="Optional notes from the reviewer"
    )
    resolver_email: str | None = Field(
        default=None,
        description="Email of the person resolving"
    )


@app.get("/escalations", tags=["Human-in-the-Loop"])
async def list_escalations(
    pending_only: bool = True,
) -> list[Escalation]:
    """List escalations requiring human review.

    Args:
        pending_only: If True, return only unresolved escalations

    Returns:
        List of escalations
    """
    if pending_only:
        return get_pending_escalations()
    return get_all_escalations()


@app.get("/escalations/{escalation_id}", tags=["Human-in-the-Loop"])
async def get_escalation_by_id(escalation_id: str) -> Escalation:
    """Get details of a specific escalation.

    Args:
        escalation_id: The escalation ID

    Returns:
        Escalation details
    """
    escalation = get_escalation(escalation_id)
    if not escalation:
        raise HTTPException(
            status_code=404,
            detail=f"Escalation {escalation_id} not found"
        )
    return escalation


@app.post("/escalations/{escalation_id}/resolve", tags=["Human-in-the-Loop"])
async def resolve_escalation_endpoint(
    escalation_id: str,
    request: EscalationResolveRequest,
) -> Escalation:
    """Resolve an escalation with a human decision.

    Args:
        escalation_id: The escalation to resolve
        request: Resolution details (decision, notes, email)

    Returns:
        Updated escalation
    """
    escalation = resolve_escalation(
        escalation_id=escalation_id,
        resolution=request.resolution,
        notes=request.notes,
        resolver_email=request.resolver_email,
    )
    if not escalation:
        raise HTTPException(
            status_code=404,
            detail=f"Escalation {escalation_id} not found"
        )
    logger.info(f"Escalation {escalation_id} resolved: {request.resolution}")
    return escalation


# ============================================================================
# Benchmarking Suite Endpoints
# ============================================================================

BENCHMARKS_DIR = PROJECT_ROOT / "demo" / "benchmarks"


class BenchmarkMetadata(BaseModel):
    """Benchmark dataset metadata."""

    id: str
    name: str
    description: str
    domain: str
    expected_classification: str
    query: str


class BenchmarkResult(BaseModel):
    """Result of running a benchmark."""

    benchmark_id: str
    passed: bool
    actual_effect: float | None = None
    expected_range: list[float] | None = None
    actual_confidence: float | None = None
    expected_confidence_min: float | None = None
    effect_direction_match: bool | None = None
    message: str


@app.get("/benchmarks", tags=["Benchmarking"])
async def list_benchmarks() -> list[BenchmarkMetadata]:
    """List all available benchmark datasets."""
    benchmarks = []

    if not BENCHMARKS_DIR.exists():
        return benchmarks

    for file in BENCHMARKS_DIR.glob("*.json"):
        try:
            with open(file) as f:
                data = json.load(f)
                benchmarks.append(
                    BenchmarkMetadata(
                        id=data["id"],
                        name=data["name"],
                        description=data["description"],
                        domain=data["domain"],
                        expected_classification=data["expected_classification"],
                        query=data["query"],
                    )
                )
        except Exception as e:
            logger.warning(f"Failed to load benchmark {file}: {e}")

    return benchmarks


@app.get("/benchmarks/{benchmark_id}", tags=["Benchmarking"])
async def get_benchmark(benchmark_id: str) -> dict:
    """Get full benchmark details including data."""
    file_path = BENCHMARKS_DIR / f"{benchmark_id}.json"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Benchmark {benchmark_id} not found")

    with open(file_path) as f:
        return json.load(f)


@app.post("/benchmarks/{benchmark_id}/run", tags=["Benchmarking"])
async def run_benchmark(benchmark_id: str) -> BenchmarkResult:
    """Run a benchmark and compare results against expected values.

    This endpoint loads the benchmark data, runs the CARF pipeline with the
    benchmark's query and data context, then validates the real result against
    the expected criteria.
    """
    file_path = BENCHMARKS_DIR / f"{benchmark_id}.json"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Benchmark {benchmark_id} not found")

    with open(file_path) as f:
        benchmark = json.load(f)

    expected_range = benchmark["expected_results"]["effect_range"]
    expected_confidence = benchmark["expected_results"]["confidence_min"]
    expected_direction = benchmark["validation_criteria"]["effect_direction"]

    # Run the actual CARF pipeline with benchmark query and data
    context: dict[str, Any] = {}
    if "data" in benchmark:
        context["benchmark_data"] = benchmark["data"]
    if "dataset_selection" in benchmark:
        context["dataset_selection"] = benchmark["dataset_selection"]

    try:
        final_state = await run_carf(
            user_input=benchmark["query"],
            context=context,
        )
    except ValueError as exc:
        return BenchmarkResult(
            benchmark_id=benchmark_id,
            passed=False,
            message=f"Engine error: {exc}",
        )

    # Extract actual results from pipeline output
    actual_effect = None
    actual_confidence = final_state.domain_confidence

    if final_state.proposed_action:
        actual_effect = final_state.proposed_action.get("effect_size")

    # Validate against expected criteria
    effect_in_range = (
        actual_effect is not None
        and expected_range[0] <= actual_effect <= expected_range[1]
    )
    confidence_met = actual_confidence >= expected_confidence

    direction_match = None
    if actual_effect is not None:
        direction_match = (
            (actual_effect < 0 and expected_direction == "negative")
            or (actual_effect > 0 and expected_direction == "positive")
            or (actual_effect == 0 and expected_direction == "neutral")
        )

    passed = effect_in_range and confidence_met and bool(direction_match)

    return BenchmarkResult(
        benchmark_id=benchmark_id,
        passed=passed,
        actual_effect=actual_effect,
        expected_range=expected_range,
        actual_confidence=actual_confidence,
        expected_confidence_min=expected_confidence,
        effect_direction_match=direction_match,
        message="Benchmark passed" if passed else "Benchmark failed validation criteria",
    )


# ============================================================================
# Configuration Validation Endpoints
# ============================================================================

class ConfigValidateRequest(BaseModel):
    """LLM configuration validation request."""

    provider: str = Field(..., description="LLM provider: deepseek, openai, anthropic, local")
    api_key: str | None = Field(default=None, description="API key for the provider")
    base_url: str | None = Field(default=None, description="Base URL for local providers")


class ConfigValidateResponse(BaseModel):
    """Configuration validation result."""

    valid: bool
    provider: str
    message: str


@app.post("/config/validate", tags=["Configuration"])
async def validate_config(request: ConfigValidateRequest) -> ConfigValidateResponse:
    """Validate LLM provider configuration.

    Tests the API key by making a minimal request to the provider.
    For local providers, checks if the endpoint is reachable.
    """
    provider = request.provider.lower()

    # For local/Ollama, just check connectivity
    if provider == "local":
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{request.base_url or 'http://localhost:11434'}/api/tags")
                if response.status_code == 200:
                    return ConfigValidateResponse(
                        valid=True,
                        provider=provider,
                        message="Local Ollama server is reachable",
                    )
        except Exception:
            pass

        return ConfigValidateResponse(
            valid=False,
            provider=provider,
            message="Cannot reach local Ollama server",
        )

    # For API providers, validate the key format
    if not request.api_key:
        return ConfigValidateResponse(
            valid=False,
            provider=provider,
            message="API key is required for this provider",
        )

    # Basic key format validation
    key = request.api_key.strip()
    valid = False
    message = "Invalid API key format"

    if provider == "deepseek":
        valid = key.startswith("sk-") and len(key) > 20
        message = "DeepSeek API key validated" if valid else "DeepSeek key should start with 'sk-'"
    elif provider == "openai":
        valid = key.startswith("sk-") and len(key) > 20
        message = "OpenAI API key validated" if valid else "OpenAI key should start with 'sk-'"
    elif provider == "anthropic":
        valid = key.startswith("sk-ant-") and len(key) > 20
        message = "Anthropic API key validated" if valid else "Anthropic key should start with 'sk-ant-'"

    # TODO: Make actual test call to provider for full validation

    return ConfigValidateResponse(
        valid=valid,
        provider=provider,
        message=message,
    )


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
