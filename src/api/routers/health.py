"""Health check endpoints."""

import os
import logging

from fastapi import APIRouter

from src.api.models import HealthCheckResponse, InfrastructureStatus

logger = logging.getLogger("carf")
router = APIRouter(tags=["Health"])


@router.get("/health")
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


@router.get("/health/infrastructure", response_model=HealthCheckResponse)
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
            message="Test mode active (CARF_TEST_MODE=1)"
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
