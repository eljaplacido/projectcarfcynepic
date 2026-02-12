"""Unit tests for the Transparency and Reliability Service.

Tests cover:
- Pydantic models (AgentInfo, AgentDecision, DataQualityMetric, etc.)
- TransparencyService agent registry
- Agent decision creation
- Data quality assessment
- Reliability assessment
- Workflow evaluation
- EU AI Act compliance models
- Guardian transparency models
"""

from datetime import datetime
from uuid import uuid4

import pandas as pd
import pytest

from src.services.transparency import (
    AgentChainTrace,
    AgentDecision,
    AgentInfo,
    ComplianceRequirement,
    ComplianceStatus,
    DataQualityAssessment,
    DataQualityLevel,
    DataQualityMetric,
    DeepEvalScores,
    EUAIActComplianceReport,
    GuardianTransparencyReport,
    PolicyDefinition,
    ReliabilityAssessment,
    ReliabilityFactor,
    ReliabilityLevel,
    TransparencyService,
    WorkflowEvaluation,
    WorkflowEvaluationCriteria,
    get_transparency_service,
)


# =============================================================================
# Enum Tests
# =============================================================================


class TestEnums:
    """Tests for transparency enums."""

    def test_reliability_levels(self):
        assert ReliabilityLevel.VERY_HIGH == "very_high"
        assert ReliabilityLevel.HIGH == "high"
        assert ReliabilityLevel.MEDIUM == "medium"
        assert ReliabilityLevel.LOW == "low"
        assert ReliabilityLevel.VERY_LOW == "very_low"
        assert ReliabilityLevel.UNKNOWN == "unknown"

    def test_compliance_status(self):
        assert ComplianceStatus.COMPLIANT == "compliant"
        assert ComplianceStatus.PARTIALLY_COMPLIANT == "partially_compliant"
        assert ComplianceStatus.NON_COMPLIANT == "non_compliant"
        assert ComplianceStatus.NOT_ASSESSED == "not_assessed"

    def test_data_quality_levels(self):
        assert DataQualityLevel.EXCELLENT == "excellent"
        assert DataQualityLevel.GOOD == "good"
        assert DataQualityLevel.FAIR == "fair"
        assert DataQualityLevel.POOR == "poor"
        assert DataQualityLevel.UNUSABLE == "unusable"


# =============================================================================
# Pydantic Model Tests
# =============================================================================


class TestAgentInfoModel:
    """Tests for AgentInfo model."""

    def test_creation(self):
        agent = AgentInfo(
            agent_id="test_agent",
            agent_name="Test Agent",
            agent_type="causal",
            role="Testing",
        )
        assert agent.agent_id == "test_agent"
        assert agent.version == "1.0"
        assert agent.capabilities == []
        assert agent.limitations == []

    def test_with_capabilities(self):
        agent = AgentInfo(
            agent_id="a1",
            agent_name="Agent 1",
            agent_type="router",
            role="Route queries",
            capabilities=["classify", "score"],
            limitations=["needs LLM"],
        )
        assert len(agent.capabilities) == 2
        assert len(agent.limitations) == 1


class TestAgentDecisionModel:
    """Tests for AgentDecision model."""

    def test_creation(self):
        agent = AgentInfo(
            agent_id="a1", agent_name="A1", agent_type="causal", role="Test"
        )
        decision = AgentDecision(
            agent=agent,
            input_summary="test input",
            output_summary="test output",
            reasoning="because test",
            confidence=0.85,
        )
        assert decision.confidence == 0.85
        assert decision.decision_id is not None
        assert decision.timestamp is not None

    def test_confidence_bounds(self):
        agent = AgentInfo(
            agent_id="a1", agent_name="A1", agent_type="causal", role="Test"
        )
        with pytest.raises(Exception):
            AgentDecision(
                agent=agent,
                input_summary="in",
                output_summary="out",
                reasoning="r",
                confidence=1.5,  # out of bounds
            )


class TestDataQualityModels:
    """Tests for data quality models."""

    def test_data_quality_metric(self):
        m = DataQualityMetric(
            name="completeness",
            score=0.95,
            status=DataQualityLevel.GOOD,
            description="95% complete",
        )
        assert m.score == 0.95
        assert m.recommendation is None

    def test_data_quality_assessment(self):
        a = DataQualityAssessment(
            overall_score=0.9,
            overall_status=DataQualityLevel.GOOD,
            sample_size=1000,
        )
        assert a.overall_score == 0.9
        assert a.completeness == 0.0  # default

    def test_deep_eval_scores(self):
        s = DeepEvalScores(
            relevancy_score=0.8,
            hallucination_risk=0.1,
            reasoning_depth=0.7,
            uix_compliance=0.9,
            task_completion=True,
        )
        assert s.task_completion is True
        assert s.evaluated_at is not None


class TestReliabilityModels:
    """Tests for reliability models."""

    def test_reliability_factor(self):
        f = ReliabilityFactor(
            name="confidence",
            weight=0.3,
            score=0.85,
            weighted_score=0.255,
            status="good",
            explanation="High confidence",
        )
        assert f.weighted_score == 0.255

    def test_reliability_assessment(self):
        a = ReliabilityAssessment(
            overall_score=0.8,
            overall_level=ReliabilityLevel.HIGH,
            data_quality_score=0.9,
            model_confidence_score=0.85,
        )
        assert a.overall_level == ReliabilityLevel.HIGH
        assert a.assessment_id is not None


class TestComplianceModels:
    """Tests for EU AI Act compliance models."""

    def test_compliance_requirement(self):
        req = ComplianceRequirement(
            requirement_id="R1",
            article="Article 13",
            title="Transparency",
            description="System must be transparent",
            status=ComplianceStatus.COMPLIANT,
            evidence=["Agent trace logging"],
        )
        assert req.status == ComplianceStatus.COMPLIANT
        assert len(req.evidence) == 1

    def test_compliance_report(self):
        report = EUAIActComplianceReport(
            overall_status=ComplianceStatus.PARTIALLY_COMPLIANT,
            compliance_score=0.75,
            transparency_score=0.9,
            human_oversight_score=0.8,
        )
        assert report.compliance_score == 0.75
        assert report.ai_system_name == "CARF - Complex-Adaptive Reasoning Fabric"


class TestGuardianTransparencyModels:
    """Tests for Guardian transparency models."""

    def test_policy_definition(self):
        p = PolicyDefinition(
            policy_id="pol-1",
            name="Financial Limit",
            category="financial",
            description="Max auto-approval amount",
            rationale="Prevent unauthorized large transactions",
            threshold_value=100000,
            threshold_unit="USD",
        )
        assert p.severity == "medium"  # default

    def test_guardian_transparency_report(self):
        report = GuardianTransparencyReport(
            session_id=uuid4(),
            verdict="approved",
            policies_passed=["financial", "operational"],
            policies_violated=[],
        )
        assert report.verdict == "approved"
        assert len(report.policies_passed) == 2


class TestWorkflowEvaluationModels:
    """Tests for workflow evaluation models."""

    def test_workflow_evaluation_criteria(self):
        c = WorkflowEvaluationCriteria(
            criterion="data_availability",
            weight=0.3,
            score=0.9,
            explanation="Sufficient data available",
        )
        assert c.score == 0.9

    def test_workflow_evaluation(self):
        e = WorkflowEvaluation(
            workflow_name="causal_analysis",
            use_case="churn_prediction",
            feasibility_score=0.85,
            reliability_score=0.8,
            transparency_score=0.9,
            overall_score=0.85,
        )
        assert e.overall_score == 0.85
        assert e.eu_ai_act_alignment == 0.0  # default


class TestAgentChainTrace:
    """Tests for AgentChainTrace model."""

    def test_creation(self):
        trace = AgentChainTrace(
            session_id=uuid4(),
            query="test query",
            total_agents_invoked=3,
            execution_path=["router", "causal_analyst", "guardian"],
        )
        assert trace.total_agents_invoked == 3
        assert len(trace.execution_path) == 3


# =============================================================================
# TransparencyService Tests
# =============================================================================


class TestTransparencyService:
    """Tests for the TransparencyService class."""

    def test_initialization(self):
        service = TransparencyService()
        assert service._agent_registry is not None
        assert len(service._agent_registry) > 0

    def test_agent_registry_has_core_agents(self):
        service = TransparencyService()
        assert "cynefin_router" in service._agent_registry
        assert "causal_analyst" in service._agent_registry
        assert "bayesian_explorer" in service._agent_registry
        assert "guardian" in service._agent_registry
        assert "chimera_oracle" in service._agent_registry

    def test_get_agent_info(self):
        service = TransparencyService()
        agent = service.get_agent_info("cynefin_router")
        assert agent is not None
        assert agent.agent_name == "Cynefin Router"
        assert agent.agent_type == "router"

    def test_get_agent_info_not_found(self):
        service = TransparencyService()
        assert service.get_agent_info("nonexistent") is None

    def test_get_all_agents(self):
        service = TransparencyService()
        agents = service.get_all_agents()
        assert len(agents) >= 5
        names = [a.agent_id for a in agents]
        assert "cynefin_router" in names

    def test_create_agent_decision_known_agent(self):
        service = TransparencyService()
        decision = service.create_agent_decision(
            agent_id="cynefin_router",
            input_summary="What causes churn?",
            output_summary="Classified as Complicated",
            reasoning="Causal keywords detected",
            confidence=0.88,
        )
        assert decision.agent.agent_name == "Cynefin Router"
        assert decision.confidence == 0.88

    def test_create_agent_decision_unknown_agent(self):
        service = TransparencyService()
        decision = service.create_agent_decision(
            agent_id="custom_agent",
            input_summary="input",
            output_summary="output",
            reasoning="reason",
            confidence=0.5,
        )
        assert decision.agent.agent_type == "unknown"

    def test_create_agent_decision_with_extras(self):
        service = TransparencyService()
        decision = service.create_agent_decision(
            agent_id="causal_analyst",
            input_summary="in",
            output_summary="out",
            reasoning="r",
            confidence=0.9,
            confidence_breakdown={"model": 0.9, "data": 0.85},
            alternatives=["bayesian_explorer"],
            data_sources=["scope3.csv"],
            assumptions=["no confounders"],
        )
        assert decision.confidence_breakdown["model"] == 0.9
        assert len(decision.alternatives_considered) == 1
        assert len(decision.data_sources_used) == 1
        assert len(decision.assumptions) == 1


# =============================================================================
# Data Quality Assessment Tests
# =============================================================================


class TestDataQualityAssessment:
    """Tests for TransparencyService.assess_data_quality."""

    def test_clean_dataframe(self):
        service = TransparencyService()
        df = pd.DataFrame({
            "a": range(1000),
            "b": range(1000),
            "c": range(1000),
        })
        assessment = service.assess_data_quality(df)
        assert assessment.overall_score > 0.9
        assert assessment.overall_status in (DataQualityLevel.EXCELLENT, DataQualityLevel.GOOD)

    def test_small_dataset(self):
        service = TransparencyService()
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        assessment = service.assess_data_quality(df, dataset_id="tiny")
        assert assessment.dataset_id == "tiny"
        assert assessment.sample_size == 3
        # Should flag small sample size
        assert any(m.name == "sample_size" and m.score < 1.0 for m in assessment.metrics)

    def test_missing_values(self):
        service = TransparencyService()
        df = pd.DataFrame({"a": [1, None, 3, None, 5], "b": [1, 2, 3, 4, 5]})
        assessment = service.assess_data_quality(df)
        assert assessment.completeness < 1.0
        assert assessment.missing_values_percentage > 0

    def test_duplicate_rows(self):
        service = TransparencyService()
        df = pd.DataFrame({"a": [1, 1, 1, 2, 3], "b": [10, 10, 10, 20, 30]})
        assessment = service.assess_data_quality(df)
        assert assessment.duplicate_percentage > 0

    def test_dict_input(self):
        service = TransparencyService()
        data = {"a": [1, 2, 3], "b": [4, 5, 6]}
        assessment = service.assess_data_quality(data)
        assert assessment.sample_size == 3

    def test_list_input(self):
        service = TransparencyService()
        data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        assessment = service.assess_data_quality(data)
        assert assessment.sample_size == 2

    def test_invalid_input(self):
        service = TransparencyService()
        assessment = service.assess_data_quality("not a dataframe")
        assert assessment.overall_score == 0.0
        assert assessment.overall_status == DataQualityLevel.UNUSABLE


# =============================================================================
# Reliability Assessment Tests
# =============================================================================


class TestReliabilityAssessment:
    """Tests for TransparencyService.assess_reliability."""

    def test_high_confidence_assessment(self):
        service = TransparencyService()
        assessment = service.assess_reliability(
            confidence=0.95,
            sample_size=2000,
            methodology="causal_inference",
        )
        assert assessment.overall_score > 0.5
        assert assessment.overall_level in (
            ReliabilityLevel.VERY_HIGH, ReliabilityLevel.HIGH, ReliabilityLevel.MEDIUM,
        )

    def test_low_confidence_assessment(self):
        service = TransparencyService()
        assessment = service.assess_reliability(
            confidence=0.3,
            sample_size=50,
            methodology="unknown",
        )
        assert assessment.overall_score < 0.7
        assert len(assessment.factors) > 0

    def test_with_data_quality(self):
        service = TransparencyService()
        dq = DataQualityAssessment(
            overall_score=0.9,
            overall_status=DataQualityLevel.GOOD,
        )
        assessment = service.assess_reliability(
            confidence=0.85,
            data_quality=dq,
            sample_size=500,
        )
        assert assessment.data_quality_score > 0

    def test_with_refutation(self):
        service = TransparencyService()
        assessment = service.assess_reliability(
            confidence=0.85,
            refutation_passed=True,
            refutation_tests_run=3,
            refutation_tests_passed=3,
        )
        assert assessment.refutation_score > 0

    def test_factors_are_populated(self):
        service = TransparencyService()
        assessment = service.assess_reliability(confidence=0.75)
        assert len(assessment.factors) > 0
        for factor in assessment.factors:
            assert 0.0 <= factor.weight <= 1.0
            assert 0.0 <= factor.score <= 1.0


# =============================================================================
# Singleton Tests
# =============================================================================


class TestGetTransparencyService:
    """Tests for the service singleton."""

    def test_returns_service(self):
        service = get_transparency_service()
        assert isinstance(service, TransparencyService)

    def test_singleton(self):
        s1 = get_transparency_service()
        s2 = get_transparency_service()
        assert s1 is s2
