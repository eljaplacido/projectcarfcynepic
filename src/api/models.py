"""Pydantic request/response models for the CARF API.

Extracted from src/main.py to enable reuse across routers.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.core.state import CynefinDomain, GuardianVerdict
from src.services.bayesian import BayesianInferenceConfig
from src.services.causal import CausalEstimationConfig


# ── Dataset / Scenario models ──────────────────────────────────────────────

class DatasetSelection(BaseModel):
    """Selection mapping for a stored dataset."""

    dataset_id: str = Field(..., description="Dataset registry ID")
    treatment: str = Field(..., description="Treatment column name")
    outcome: str = Field(..., description="Outcome column name")
    covariates: list[str] = Field(default_factory=list)
    effect_modifiers: list[str] = Field(default_factory=list)


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


class ScenarioLoadRequest(BaseModel):
    """Request to load a scenario."""

    scenario_id: str


# ── Query models ───────────────────────────────────────────────────────────

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


class ProgressUpdate(BaseModel):
    """Real-time progress update during analysis."""

    step: str
    status: str  # started, completed, error
    message: str
    progress_percent: int
    timestamp: str
    details: dict[str, Any] | None = None


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


# ── Config models ──────────────────────────────────────────────────────────

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


class LLMConfigUpdateRequest(BaseModel):
    """Request to update LLM configuration."""

    provider: str = Field(description="LLM provider: openai, anthropic, deepseek, local")
    api_key: str | None = Field(default=None, description="API key (not needed for local)")
    base_url: str | None = Field(default=None, description="Custom base URL for local/ollama")


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


# ── Oracle models ──────────────────────────────────────────────────────────

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


# ── Router/Guardian config models ──────────────────────────────────────────

class RouterThresholdUpdate(BaseModel):
    """Partial update for specific router thresholds."""

    confidence_threshold: float | None = Field(None, ge=0.0, le=1.0)
    entropy_threshold_chaotic: float | None = Field(None, ge=0.0, le=1.0)
    clear_threshold: float | None = Field(None, ge=0.0, le=1.0)
    complicated_threshold: float | None = Field(None, ge=0.0, le=1.0)
    complex_threshold: float | None = Field(None, ge=0.0, le=1.0)


class GuardianThresholdUpdate(BaseModel):
    """Partial update for Guardian thresholds."""

    user_financial_limit: float | None = Field(None, description="Override financial limit")
    user_confidence_threshold: float | None = Field(None, ge=0.0, le=1.0)
    strict_mode: bool | None = Field(None, description="Enable strict mode")


# ── Analysis models ────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    """Request for text analysis (when no file uploaded)."""

    query: str = Field(..., description="Analysis query")
    text_content: str | None = Field(None, description="Text content to analyze")
    context: dict[str, Any] | None = Field(None, description="Additional context")


# ── Health models ──────────────────────────────────────────────────────────

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


# ── Escalation models ─────────────────────────────────────────────────────

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


# ── Benchmark models ──────────────────────────────────────────────────────

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
    # --- Causal-specific (existing, keep for backward compat) ---
    actual_effect: float | None = None
    expected_range: list[float] | None = None
    actual_confidence: float | None = None
    expected_confidence_min: float | None = None
    effect_direction_match: bool | None = None
    # --- Domain-generic ---
    actual_domain: str | None = None
    expected_domain: str | None = None
    domain_match: bool | None = None
    escalation_triggered: bool | None = None
    expected_escalation: bool | None = None
    action_type: str | None = None
    expected_action_type: str | None = None
    pipeline_duration_ms: float | None = None
    # --- Summary ---
    message: str
    validation_details: dict[str, Any] | None = None


# ── Simulation models ─────────────────────────────────────────────────────

class DataGenerationRequest(BaseModel):
    """Request for generating simulation data."""

    scenario_type: str = Field(..., description="Type of scenario (e.g., 'scope3_emissions')")
    n_samples: int = Field(1000, ge=100, le=10000, description="Number of samples")
    seed: int = Field(42, description="Random seed for reproducibility")


class RealismAssessmentRequest(BaseModel):
    """Request for scenario realism assessment."""

    dataset_id: str = Field(..., description="Dataset ID to assess")
    treatment_col: str = Field(..., description="Treatment column name")
    outcome_col: str = Field(..., description="Outcome column name")
    covariates: list[str] = Field(default_factory=list, description="Covariate columns")


# ── Transparency models ───────────────────────────────────────────────────

class DataQualityRequest(BaseModel):
    """Request for data quality assessment."""

    data: list[dict[str, Any]] | dict[str, list[Any]] = Field(
        ..., description="Data to assess quality"
    )
    dataset_id: str | None = Field(None, description="Optional dataset identifier")


class ReliabilityRequest(BaseModel):
    """Request for reliability assessment."""

    confidence: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence")
    refutation_passed: bool | None = Field(None, description="Did refutation tests pass")
    refutation_tests_run: int = Field(0, description="Number of refutation tests run")
    refutation_tests_passed: int = Field(0, description="Number passed")
    sample_size: int = Field(0, description="Sample size used")
    methodology: str = Field("unknown", description="Analysis methodology")
    data: list[dict[str, Any]] | None = Field(None, description="Optional data for quality assessment")


class ComplianceRequest(BaseModel):
    """Request for EU AI Act compliance assessment."""

    session_id: str | None = Field(None, description="Session to assess")
    has_explanation: bool = Field(True, description="Explanation service enabled")
    has_audit_trail: bool = Field(True, description="Kafka audit enabled")
    has_human_oversight: bool = Field(True, description="HumanLayer enabled")
    data_governance_score: float = Field(0.8, ge=0.0, le=1.0)


class WorkflowEvaluationRequest(BaseModel):
    """Request for workflow evaluation."""

    workflow_name: str = Field(..., description="Name of the workflow")
    use_case: str = Field(..., description="Business use case description")
    data_types: list[str] = Field(default_factory=list, description="Types of data used")
    models_used: list[str] = Field(default_factory=list, description="Models/algorithms used")
    has_validation: bool = Field(False, description="Includes validation tests")
    has_human_review: bool = Field(False, description="Human review enabled")
    sample_size: int = Field(0, description="Data sample size")
    domain: str = Field("Complicated", description="Cynefin domain")


class GuardianTransparencyRequest(BaseModel):
    """Request for Guardian transparency report."""

    session_id: str = Field(..., description="Session ID")
    verdict: str = Field(..., description="Guardian verdict")
    policies_passed: list[str] = Field(default_factory=list)
    policies_violated: list[str] = Field(default_factory=list)


# ── Enhanced Query Response ────────────────────────────────────────────────

class EnhancedQueryResponse(QueryResponse):
    """Extended query response with full transparency metrics."""

    reliability_assessment: Any | None = Field(
        None, alias="reliabilityAssessment", serialization_alias="reliabilityAssessment"
    )
    data_quality_assessment: Any | None = Field(
        None, alias="dataQualityAssessment", serialization_alias="dataQualityAssessment"
    )
    agents_used: list[Any] = Field(
        default_factory=list, alias="agentsUsed", serialization_alias="agentsUsed"
    )
    eu_compliance_status: str | None = Field(
        None, alias="euComplianceStatus", serialization_alias="euComplianceStatus"
    )


# ── Insights models ───────────────────────────────────────────────────────

class InsightsRequest(BaseModel):
    """Request for generating insights."""

    persona: str = Field("analyst", description="Target persona: analyst, developer, or executive")
    domain: str | None = Field(None, description="Cynefin domain")
    domain_confidence: float | None = Field(None, description="Domain classification confidence")
    domain_entropy: float | None = Field(None, description="Domain entropy")
    has_causal_result: bool = Field(False, description="Whether causal result exists")
    causal_effect: float | None = Field(None, description="Causal effect size")
    refutation_pass_rate: float | None = Field(None, description="Refutation test pass rate")
    has_bayesian_result: bool = Field(False, description="Whether Bayesian result exists")
    epistemic_uncertainty: float | None = Field(None, description="Epistemic uncertainty")
    aleatoric_uncertainty: float | None = Field(None, description="Aleatoric uncertainty")
    guardian_verdict: str | None = Field(None, description="Guardian verdict")
    policies_passed: int = Field(0, description="Number of policies passed")
    policies_total: int = Field(0, description="Total number of policies")
    sample_size: int | None = Field(None, description="Data sample size")
    processing_time_ms: int | None = Field(None, description="Processing time in ms")


class InsightsResponseModel(BaseModel):
    """Response containing generated insights."""

    persona: str
    insights: list[dict]
    total_count: int
    generated_at: str


# ── Workflow tracking models ───────────────────────────────────────────────

class StartWorkflowRequest(BaseModel):
    """Request to start workflow tracking."""

    session_id: str = Field(..., description="Session ID")
    query: str = Field(..., description="User query")
    workflow_name: str = Field("carf_analysis", description="Workflow name")


class StartWorkflowResponse(BaseModel):
    """Response with workflow trace ID."""

    trace_id: str
    session_id: str
    started_at: str


class CompleteWorkflowRequest(BaseModel):
    """Request to complete workflow tracking."""

    trace_id: str = Field(..., description="Trace ID from start_workflow")
    domain: str | None = Field(None, description="Final Cynefin domain")
    quality_score: float | None = Field(None, description="Overall quality score")


# ── Data Loader models ────────────────────────────────────────────────────

class LoadJsonRequest(BaseModel):
    """Request to load JSON data."""

    data: dict | list = Field(..., description="JSON data to load")
    source_name: str = Field("json_payload", description="Name for the data source")


class LoadedDataResponse(BaseModel):
    """Response with loaded data metadata."""

    data_id: str
    source_type: str
    source_name: str
    row_count: int
    column_count: int
    quality: str
    quality_score: float
    quality_issues: list[str]
    suggested_treatment: str | None
    suggested_outcome: str | None
    suggested_covariates: list[str]
    columns: list[dict]


class LoadCsvRequest(BaseModel):
    """Request to load CSV data."""

    content: str = Field(..., description="CSV content as string")
    source_name: str = Field("csv_file", description="Name for the data source")
