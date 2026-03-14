# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Integration tests for Phase 17 cross-service interconnections.

Tests the cohesion between:
- RAG ↔ NeSy (neurosymbolic-augmented retrieval)
- RAG ↔ Causal World Model (causal context enrichment)
- H-Neuron Sentinel (proxy mode signal fusion)
- NeSy ↔ Causal World Model (symbolic grounding of structural equations)
- End-to-end retrieval pipelines
"""

import pytest

from src.services.rag_service import (
    RAGService,
    RAGResult,
    RAGQueryResponse,
    _merge_vector_and_graph,
    _boost_with_graph_context,
)
from src.services.neurosymbolic_engine import (
    KnowledgeBase,
    NeSyReasoningResult,
    SymbolicFact,
    SymbolicRule,
    RuleCondition,
)
from src.services.causal_world_model import (
    CausalWorldModel,
    CausalWorldModelService,
    StructuralEquation,
    CounterfactualResult as WMCounterfactualResult,
)
from src.services.counterfactual_engine import (
    CounterfactualResult,
    CounterfactualQuery,
    CausalAttributionItem,
)
from src.services.h_neuron_interceptor import (
    HNeuronSentinel,
    HNeuronConfig,
    HallucinationAssessment,
)
from src.core.state import (
    EpistemicState,
    CynefinDomain,
    CounterfactualEvidence,
    NeurosymbolicEvidence,
)


# =============================================================================
# 1. H-Neuron Sentinel Tests (Proxy Mode)
# =============================================================================


class TestHNeuronSentinelProxyMode:
    """Tests for H-Neuron proxy mode signal fusion."""

    def test_sentinel_disabled_by_default(self):
        config = HNeuronConfig(enabled=False)
        sentinel = HNeuronSentinel(config=config)
        assert sentinel.is_enabled is False
        assert sentinel.mode == "proxy"

    def test_sentinel_enabled(self):
        config = HNeuronConfig(enabled=True)
        sentinel = HNeuronSentinel(config=config)
        assert sentinel.is_enabled is True

    def test_domain_activation(self):
        config = HNeuronConfig(
            enabled=True, active_domains=["Complicated", "Complex"]
        )
        sentinel = HNeuronSentinel(config=config)
        assert sentinel.is_active_for("Complicated") is True
        assert sentinel.is_active_for("Complex") is True
        assert sentinel.is_active_for("Clear") is False
        assert sentinel.is_active_for("Chaotic") is False

    def test_domain_inactive_when_disabled(self):
        config = HNeuronConfig(enabled=False)
        sentinel = HNeuronSentinel(config=config)
        assert sentinel.is_active_for("Complicated") is False

    def test_low_risk_assessment(self):
        config = HNeuronConfig(enabled=True, hallucination_threshold=0.3)
        sentinel = HNeuronSentinel(config=config)
        result = sentinel.assess_hallucination_risk(
            deepeval_hallucination_risk=0.1,
            domain_confidence=0.95,
            epistemic_uncertainty=0.1,
        )
        assert isinstance(result, HallucinationAssessment)
        assert result.score < 0.3
        assert result.flagged is False
        assert result.intervention_recommended is False

    def test_high_risk_assessment(self):
        config = HNeuronConfig(enabled=True, hallucination_threshold=0.3)
        sentinel = HNeuronSentinel(config=config)
        result = sentinel.assess_hallucination_risk(
            deepeval_hallucination_risk=0.8,
            domain_confidence=0.3,
            epistemic_uncertainty=0.9,
            reflection_count=3,
        )
        assert result.score >= 0.3
        assert result.flagged is True

    def test_intervention_threshold(self):
        config = HNeuronConfig(
            enabled=True,
            hallucination_threshold=0.3,
            intervention_threshold=0.7,
        )
        sentinel = HNeuronSentinel(config=config)
        result = sentinel.assess_hallucination_risk(
            deepeval_hallucination_risk=0.95,
            domain_confidence=0.1,
            epistemic_uncertainty=0.95,
            reflection_count=5,
        )
        assert result.flagged is True
        assert result.intervention_recommended is True

    def test_no_signals_zero_score(self):
        config = HNeuronConfig(enabled=True)
        sentinel = HNeuronSentinel(config=config)
        result = sentinel.assess_hallucination_risk()
        assert result.score == 0.0
        assert result.flagged is False

    def test_signal_components_tracked(self):
        config = HNeuronConfig(enabled=True)
        sentinel = HNeuronSentinel(config=config)
        result = sentinel.assess_hallucination_risk(
            deepeval_hallucination_risk=0.5,
            domain_confidence=0.7,
            epistemic_uncertainty=0.3,
        )
        assert "deepeval_hallucination_risk" in result.signal_components
        assert "confidence_risk" in result.signal_components
        assert "epistemic_uncertainty" in result.signal_components

    def test_brevity_risk_signal(self):
        config = HNeuronConfig(enabled=True)
        sentinel = HNeuronSentinel(config=config)
        result = sentinel.assess_hallucination_risk(
            response_text="Yes.",
            deepeval_hallucination_risk=0.2,
        )
        assert "brevity_risk" in result.signal_components

    def test_verbosity_risk_signal(self):
        config = HNeuronConfig(enabled=True)
        sentinel = HNeuronSentinel(config=config)
        long_text = " ".join(["word"] * 3000)
        result = sentinel.assess_hallucination_risk(
            response_text=long_text,
            deepeval_hallucination_risk=0.2,
        )
        assert "verbosity_risk" in result.signal_components

    def test_quality_scores_integration(self):
        config = HNeuronConfig(enabled=True)
        sentinel = HNeuronSentinel(config=config)
        result = sentinel.assess_hallucination_risk(
            quality_scores={"relevancy": 0.3, "reasoning_depth": 0.2},
        )
        assert "irrelevancy_risk" in result.signal_components
        assert "shallow_reasoning_risk" in result.signal_components

    def test_latency_tracked(self):
        config = HNeuronConfig(enabled=True)
        sentinel = HNeuronSentinel(config=config)
        result = sentinel.assess_hallucination_risk(
            deepeval_hallucination_risk=0.5,
        )
        assert result.latency_ms >= 0
        assert result.mode == "proxy"

    def test_explanation_generated_when_flagged(self):
        config = HNeuronConfig(enabled=True, hallucination_threshold=0.2)
        sentinel = HNeuronSentinel(config=config)
        result = sentinel.assess_hallucination_risk(
            deepeval_hallucination_risk=0.9,
            domain_confidence=0.2,
        )
        assert result.flagged is True
        assert len(result.explanation) > 0

    def test_status_report(self):
        config = HNeuronConfig(
            enabled=True,
            hallucination_threshold=0.4,
            active_domains=["Complex"],
        )
        sentinel = HNeuronSentinel(config=config)
        status = sentinel.get_status()
        assert status["enabled"] is True
        assert status["hallucination_threshold"] == 0.4
        assert "Complex" in status["active_domains"]
        assert "mechanistic_available" in status


# =============================================================================
# 2. H-Neuron + EpistemicState Integration
# =============================================================================


class TestHNeuronStateIntegration:
    """Tests for H-Neuron sentinel integration with EpistemicState."""

    def test_sentinel_reads_state_signals(self):
        state = EpistemicState(
            cynefin_domain=CynefinDomain.COMPLICATED,
            domain_confidence=0.6,
            epistemic_uncertainty=0.7,
            reflection_count=2,
            evaluation_scores={
                "analysis": {"hallucination_risk": 0.4, "relevancy": 0.7}
            },
        )

        config = HNeuronConfig(enabled=True, hallucination_threshold=0.3)
        sentinel = HNeuronSentinel(config=config)

        deepeval_risk = None
        for scores in state.evaluation_scores.values():
            if "hallucination_risk" in scores:
                deepeval_risk = scores["hallucination_risk"]
                break

        result = sentinel.assess_hallucination_risk(
            deepeval_hallucination_risk=deepeval_risk,
            domain_confidence=state.domain_confidence,
            epistemic_uncertainty=state.epistemic_uncertainty,
            reflection_count=state.reflection_count,
        )
        assert isinstance(result, HallucinationAssessment)
        assert result.score > 0.0

    def test_sentinel_result_storable_in_context(self):
        state = EpistemicState()
        config = HNeuronConfig(enabled=True)
        sentinel = HNeuronSentinel(config=config)
        assessment = sentinel.assess_hallucination_risk(
            deepeval_hallucination_risk=0.5,
        )
        state.context["h_neuron_risk_score"] = assessment.score
        state.context["h_neuron_flagged"] = assessment.flagged
        state.context["h_neuron_mode"] = assessment.mode
        assert "h_neuron_risk_score" in state.context
        assert state.context["h_neuron_mode"] == "proxy"


# =============================================================================
# 3. RAG ↔ NeSy Interconnection Tests
# =============================================================================


class TestRAGNeSyInterconnection:
    """Tests for RAG service integration with neurosymbolic engine."""

    def test_rag_ingests_and_retrieves(self):
        rag = RAGService()
        rag.ingest_text(
            "Carbon dioxide causes global warming through greenhouse effect.",
            source="climate_science",
        )
        assert rag.document_count > 0
        result = rag.retrieve("greenhouse gas warming")
        assert isinstance(result, RAGQueryResponse)

    def test_rag_domain_boost(self):
        results = [
            RAGResult(
                doc_id="1", content="test", score=0.5,
                metadata={"domain_id": "energy"},
            ),
            RAGResult(
                doc_id="2", content="test2", score=0.5,
                metadata={"domain_id": "finance"},
            ),
        ]
        boosted = _boost_with_graph_context(results, "energy")
        energy_result = next(r for r in boosted if r.doc_id == "1")
        finance_result = next(r for r in boosted if r.doc_id == "2")
        assert energy_result.score > finance_result.score

    def test_rrf_merge_vector_and_graph(self):
        vector_results = [
            RAGResult(doc_id="v1", content="vector 1", score=0.9),
            RAGResult(doc_id="v2", content="vector 2", score=0.7),
        ]
        graph_results = [
            RAGResult(doc_id="v1", content="vector 1", score=0.8),
            RAGResult(doc_id="g1", content="graph 1", score=0.6),
        ]
        merged = _merge_vector_and_graph(vector_results, graph_results, top_k=3)
        assert len(merged) == 3
        assert merged[0].doc_id == "v1"
        assert merged[0].retrieval_mode == "hybrid"

    def test_nesy_kb_facts_searchable(self):
        kb = KnowledgeBase()
        kb.add_fact(SymbolicFact(
            entity="CO2", attribute="effect", value="warming",
            confidence=0.9, source="ipcc",
        ))
        kb.add_fact(SymbolicFact(
            entity="methane", attribute="effect", value="warming",
            confidence=0.85, source="ipcc",
        ))
        facts = kb.get_facts_about("CO2")
        assert len(facts) == 1
        assert facts[0].value == "warming"


# =============================================================================
# 4. Causal World Model ↔ NeSy Integration
# =============================================================================


class TestCausalNeSyIntegration:
    """Tests for causal world model and neurosymbolic engine working together."""

    def test_scm_equations_as_symbolic_facts(self):
        model = CausalWorldModel(model_id="integration-test")
        model.add_equation(StructuralEquation(
            variable="Y", parents=["X"],
            coefficients={"X": 2.0}, intercept=1.0,
        ))

        kb = KnowledgeBase()
        for var, eq in model.equations.items():
            kb.add_fact(SymbolicFact(
                entity=var, attribute="equation_type",
                value=eq.equation_type, confidence=0.9,
                source="causal_world_model",
            ))
            for parent in eq.parents:
                kb.add_fact(SymbolicFact(
                    entity=var, attribute="caused_by", value=parent,
                    confidence=0.9, source="causal_world_model",
                ))

        assert kb.size == 2
        y_facts = kb.get_facts_about("Y")
        assert len(y_facts) == 2

    def test_counterfactual_with_symbolic_validation(self):
        model = CausalWorldModel()
        model.add_equation(StructuralEquation(
            variable="budget", parents=[], intercept=100.0,
        ))
        model.add_equation(StructuralEquation(
            variable="sales", parents=["budget"],
            coefficients={"budget": 1.5}, intercept=50.0,
        ))

        factual = {"budget": 100.0, "sales": 200.0}
        cf = model.counterfactual(factual, intervention={"budget": 200.0})

        kb = KnowledgeBase()
        kb.add_fact(SymbolicFact(
            entity="budget", attribute="max_allowed", value="500",
            confidence=1.0, source="policy",
        ))
        kb.add_rule(SymbolicRule(
            rule_id="budget_limit", name="budget-cap",
            conditions=[
                RuleCondition(attribute="max_allowed", operator=">=", value="200")
            ],
            conclusion_attribute="budget_valid",
            conclusion_value="yes",
        ))
        derived = kb.forward_chain()
        assert any(f.attribute == "budget_valid" for f in derived)

    def test_simulation_trajectory_consistency(self):
        model = CausalWorldModel()
        model.add_equation(StructuralEquation(
            variable="X", parents=[], intercept=1.0, noise_std=0.0,
        ))
        model.add_equation(StructuralEquation(
            variable="Y", parents=["X"], coefficients={"X": 2.0},
            intercept=0.0, noise_std=0.0,
        ))
        result = model.simulate(steps=3, seed=0)
        for entry in result.trajectory:
            assert entry["Y"] == pytest.approx(entry["X"] * 2.0, abs=0.1)


# =============================================================================
# 5. End-to-End Pipeline Coherence
# =============================================================================


class TestEndToEndPipelineCoherence:
    """Tests for end-to-end workflow coherence across Phase 17 services."""

    def test_epistemic_state_carries_all_evidence_types(self):
        state = EpistemicState(
            user_input="What if we doubled the marketing budget?",
            cynefin_domain=CynefinDomain.COMPLICATED,
            domain_confidence=0.85,
            counterfactual_evidence=CounterfactualEvidence(
                factual_outcome="Sales were $10M",
                counterfactual_outcome="Sales would be $15M",
                confidence=0.7,
            ),
            neurosymbolic_evidence=NeurosymbolicEvidence(
                conclusion="Marketing has a strong causal effect on sales",
                derived_facts_count=5,
                rules_fired=["marketing-effect-rule"],
                confidence=0.8,
            ),
        )
        assert state.counterfactual_evidence is not None
        assert state.neurosymbolic_evidence is not None
        assert state.counterfactual_evidence.confidence == 0.7
        assert state.neurosymbolic_evidence.derived_facts_count == 5

    def test_h_neuron_assessment_from_full_state(self):
        state = EpistemicState(
            domain_confidence=0.4,
            epistemic_uncertainty=0.8,
            reflection_count=1,
            evaluation_scores={
                "causal_analyst": {
                    "hallucination_risk": 0.6,
                    "relevancy": 0.5,
                    "reasoning_depth": 0.4,
                }
            },
        )

        config = HNeuronConfig(enabled=True, hallucination_threshold=0.3)
        sentinel = HNeuronSentinel(config=config)

        best_risk = max(
            (scores.get("hallucination_risk", 0.0)
             for scores in state.evaluation_scores.values()),
            default=0.0,
        )
        quality_scores = {}
        for scores in state.evaluation_scores.values():
            quality_scores.update(scores)

        result = sentinel.assess_hallucination_risk(
            deepeval_hallucination_risk=best_risk,
            domain_confidence=state.domain_confidence,
            epistemic_uncertainty=state.epistemic_uncertainty,
            reflection_count=state.reflection_count,
            quality_scores=quality_scores,
        )
        assert result.flagged is True
        assert len(result.signal_components) >= 4

    def test_causal_world_model_service_stores_models(self):
        service = CausalWorldModelService()
        model = CausalWorldModel(model_id="test-model")
        model.add_equation(StructuralEquation(
            variable="X", parents=[], intercept=5.0,
        ))
        service._models["test-model"] = model
        retrieved = service.get_model("test-model")
        assert retrieved is not None
        assert retrieved.model_id == "test-model"
        assert "X" in retrieved.equations

    def test_counterfactual_result_serialization(self):
        result = CounterfactualResult(
            factual_outcome="Revenue was $1M",
            counterfactual_outcome="Revenue would be $1.5M",
            confidence=0.75,
            narrative="Increasing marketing would boost revenue.",
            reasoning_steps=["Parsed query", "Built SCM", "Computed counterfactual"],
            attributions=[
                CausalAttributionItem(
                    cause="marketing", importance=0.9,
                    but_for_result=True, description="Primary driver",
                )
            ],
            method="scm",
        )
        data = result.model_dump()
        assert data["method"] == "scm"
        assert len(data["attributions"]) == 1
        assert data["attributions"][0]["cause"] == "marketing"

    def test_nesy_reasoning_result_serialization(self):
        result = NeSyReasoningResult(
            conclusion="CO2 causes warming",
            derived_facts=[
                SymbolicFact(entity="CO2", attribute="effect", value="warming"),
            ],
            rule_chain=["Grounded 3 facts", "Derived 1 new fact"],
            shortcut_warnings=[],
            iterations=2,
            confidence=0.85,
        )
        assert result.confidence == 0.85
        assert len(result.derived_facts) == 1


# =============================================================================
# 6. Knowledge Base ↔ RAG Coherence
# =============================================================================


class TestKBRAGCoherence:
    """Tests for knowledge base and RAG working together."""

    def test_rag_ingest_from_kb_facts(self):
        kb = KnowledgeBase()
        kb.add_fact(SymbolicFact(
            entity="temperature", attribute="causes", value="ice_melt",
        ))
        kb.add_fact(SymbolicFact(
            entity="ice_melt", attribute="causes", value="sea_level_rise",
        ))

        rag = RAGService()
        for fact in kb.facts.values():
            text = f"{fact.entity} {fact.attribute} {fact.value}"
            rag.ingest_text(text, source="kb_export")
        assert rag.document_count >= 2
        result = rag.retrieve("temperature ice melt")
        assert isinstance(result, RAGQueryResponse)

    def test_forward_chain_results_ingestable(self):
        kb = KnowledgeBase()
        kb.add_fact(SymbolicFact(
            entity="system", attribute="pressure", value="high",
        ))
        kb.add_rule(SymbolicRule(
            rule_id="r1", name="pressure-alert",
            conditions=[
                RuleCondition(attribute="pressure", operator="==", value="high")
            ],
            conclusion_attribute="alert_status",
            conclusion_value="critical",
        ))
        derived = kb.forward_chain()
        assert len(derived) >= 1

        rag = RAGService()
        for fact in derived:
            text = f"Derived: {fact.entity}.{fact.attribute} = {fact.value} (from {fact.source})"
            rag.ingest_text(text, source="derived_facts")
        assert rag.document_count >= 1


# =============================================================================
# 7. Multi-Layer Retrieval Modes
# =============================================================================


class TestRetrievalModes:
    """Tests for different retrieval mode labeling."""

    def test_vector_only_mode(self):
        rag = RAGService()
        rag.ingest_text("Test document for retrieval.", source="test")
        result = rag.retrieve("test document")
        assert result.retrieval_mode in ("local", "hybrid")

    def test_hybrid_mode_with_domain(self):
        rag = RAGService()
        rag.ingest_text("Energy policy document.", source="policy", domain_id="energy")
        result = rag.retrieve("energy policy", domain_id="energy")
        assert result.retrieval_mode == "hybrid"

    def test_merge_preserves_hybrid_tag(self):
        v = [RAGResult(doc_id="shared", content="x", score=0.9)]
        g = [RAGResult(doc_id="shared", content="x", score=0.8)]
        merged = _merge_vector_and_graph(v, g, top_k=1)
        assert merged[0].retrieval_mode == "hybrid"


# =============================================================================
# 8. H-Neuron Config Model Validation
# =============================================================================


class TestHNeuronConfigValidation:
    """Tests for HNeuronConfig Pydantic model."""

    def test_default_config(self):
        config = HNeuronConfig()
        assert config.enabled is False
        assert config.mode == "proxy"
        assert config.hallucination_threshold == 0.3
        assert config.intervention_threshold == 0.85
        assert "Complicated" in config.active_domains
        assert "Complex" in config.active_domains

    def test_custom_config(self):
        config = HNeuronConfig(
            enabled=True,
            mode="mechanistic",
            hallucination_threshold=0.5,
            active_domains=["Chaotic"],
        )
        assert config.enabled is True
        assert config.mode == "mechanistic"
        assert config.hallucination_threshold == 0.5
        assert config.active_domains == ["Chaotic"]

    def test_halllucination_assessment_model(self):
        assessment = HallucinationAssessment(
            score=0.75,
            flagged=True,
            intervention_recommended=False,
            mode="proxy",
            latency_ms=3,
            signal_components={"deepeval_hallucination_risk": 0.8},
            explanation="High risk detected.",
        )
        data = assessment.model_dump()
        assert data["score"] == 0.75
        assert data["flagged"] is True
        assert "deepeval_hallucination_risk" in data["signal_components"]
