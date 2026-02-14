"""Analysis, data, chat, explain, and agent endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.api.models import (
    LoadCsvRequest,
    LoadedDataResponse,
    LoadJsonRequest,
)
from src.services.chat import ChatRequest, ChatResponse, get_chat_service
from src.services.explanations import (
    ExplanationComponent,
    ExplanationRequest,
    ExplanationResponse,
    get_explanation_service,
)
from src.services.file_analyzer import FileAnalysisResult, get_file_analyzer
from src.services.schema_detector import schema_detector, SchemaDetectionResult
from src.services.improvement_suggestions import (
    improvement_service,
    ImprovementContext,
    Suggestion,
)
from src.services.data_loader import (
    get_data_loader,
    DataQuality,
    DataSourceType,
)

logger = logging.getLogger("carf")
router = APIRouter()


# ── Data detection / suggestions ───────────────────────────────────────────

@router.post("/data/detect-schema", response_model=SchemaDetectionResult, tags=["Data"])
async def detect_schema_endpoint(file: UploadFile = File(...)):
    """Detect schema and suggested roles from an uploaded CSV file."""
    content = await file.read()
    return schema_detector.detect(content, file.filename)


@router.post("/agent/suggest-improvements", response_model=list[Suggestion], tags=["Agent"])
async def suggest_improvements_endpoint(context: ImprovementContext):
    """Generate proactive suggestions for query refinement or next steps."""
    return improvement_service.suggest(context)


# ── File / text analysis ──────────────────────────────────────────────────

@router.post("/analyze", response_model=FileAnalysisResult, tags=["Analysis"])
async def analyze_content(
    file: UploadFile | None = File(None),
    query: str = Form(""),
    text_content: str | None = Form(None),
    context: str | None = Form(None),
):
    """Analyze uploaded file or text content."""
    analyzer = get_file_analyzer()

    if file:
        content = await file.read()
        filename = file.filename or "unknown"
        content_type = file.content_type
        result = await analyzer.analyze_file(content, filename, content_type)
        return result
    elif text_content:
        await analyzer.analyze_text(text_content, query)
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


# ── Chat ──────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_completion(request: ChatRequest):
    """LLM chat with analysis context awareness."""
    chat_service = get_chat_service()
    return await chat_service.chat(request)


# ── Explain ───────────────────────────────────────────────────────────────

@router.post("/explain", response_model=ExplanationResponse, tags=["Explain"])
async def explain_component(request: ExplanationRequest):
    """Get LLM-generated explanation for any CARF component."""
    explanation_service = get_explanation_service()
    return await explanation_service.explain(request)


@router.get("/explain/cynefin/{element}", tags=["Explain"])
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


@router.get("/explain/causal/{element}", tags=["Explain"])
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


@router.get("/explain/bayesian/{element}", tags=["Explain"])
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


@router.get("/explain/guardian/{element}", tags=["Explain"])
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


# ── Data Loader ───────────────────────────────────────────────────────────

@router.post("/data/load/json", response_model=LoadedDataResponse, tags=["Data Loader"])
async def load_json_data(request: LoadJsonRequest):
    """Load data from a JSON payload."""
    loader = get_data_loader()
    result = await loader.load_json(request.data, request.source_name)

    return LoadedDataResponse(
        data_id=result.data_id,
        source_type=result.source_type.value,
        source_name=result.source_name,
        row_count=result.row_count,
        column_count=result.column_count,
        quality=result.quality.value,
        quality_score=result.quality_score,
        quality_issues=result.quality_issues,
        suggested_treatment=result.suggested_treatment,
        suggested_outcome=result.suggested_outcome,
        suggested_covariates=result.suggested_covariates,
        columns=[
            {
                "name": c.name,
                "dtype": c.dtype,
                "null_count": c.null_count,
                "null_percentage": c.null_percentage,
                "unique_count": c.unique_count,
                "sample_values": c.sample_values[:3],
                "suggested_role": c.suggested_role,
            }
            for c in result.columns
        ],
    )


@router.post("/data/load/csv", response_model=LoadedDataResponse, tags=["Data Loader"])
async def load_csv_data(request: LoadCsvRequest):
    """Load data from CSV content."""
    loader = get_data_loader()
    result = await loader.load_csv(request.content, request.source_name)

    return LoadedDataResponse(
        data_id=result.data_id,
        source_type=result.source_type.value,
        source_name=result.source_name,
        row_count=result.row_count,
        column_count=result.column_count,
        quality=result.quality.value,
        quality_score=result.quality_score,
        quality_issues=result.quality_issues,
        suggested_treatment=result.suggested_treatment,
        suggested_outcome=result.suggested_outcome,
        suggested_covariates=result.suggested_covariates,
        columns=[
            {
                "name": c.name,
                "dtype": c.dtype,
                "null_count": c.null_count,
                "null_percentage": c.null_percentage,
                "unique_count": c.unique_count,
                "sample_values": c.sample_values[:3],
                "suggested_role": c.suggested_role,
            }
            for c in result.columns
        ],
    )


@router.get("/data/{data_id}", tags=["Data Loader"])
async def get_loaded_data(data_id: str, include_records: bool = False):
    """Retrieve previously loaded data by ID."""
    loader = get_data_loader()
    data = loader.get_cached_data(data_id)

    if not data:
        raise HTTPException(status_code=404, detail="Data not found")

    response = {
        "data_id": data.data_id,
        "source_type": data.source_type.value,
        "source_name": data.source_name,
        "loaded_at": data.loaded_at.isoformat(),
        "row_count": data.row_count,
        "column_count": data.column_count,
        "quality": data.quality.value,
        "quality_score": data.quality_score,
        "suggested_treatment": data.suggested_treatment,
        "suggested_outcome": data.suggested_outcome,
        "suggested_covariates": data.suggested_covariates,
    }

    if include_records:
        response["records"] = data.data_records[:100]

    return response


@router.get("/data/quality/levels", tags=["Data Loader"])
async def get_quality_levels():
    """Get available data quality levels."""
    return {
        "levels": [q.value for q in DataQuality],
        "source_types": [s.value for s in DataSourceType],
    }


@router.delete("/data/cache", tags=["Data Loader"])
async def clear_data_cache():
    """Clear the data loader cache."""
    loader = get_data_loader()
    loader.clear_cache()
    return {"status": "cache_cleared"}
