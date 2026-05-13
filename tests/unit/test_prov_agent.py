# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Tests for the PROV-AGENT JSON-LD emitter."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from src.core.state import (
    BayesianEvidence,
    CausalEvidence,
    ConfidenceLevel,
    CounterfactualEvidence,
    CynefinDomain,
    EpistemicState,
    GuardianVerdict,
    NeurosymbolicEvidence,
)
from src.services.prov_agent import (
    PROV_NAMESPACE,
    PROVAgentConfig,
    PROVAgentEmitter,
    reset_prov_emitter,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_prov_emitter()
    yield
    reset_prov_emitter()


def _populated_state() -> EpistemicState:
    state = EpistemicState(
        cynefin_domain=CynefinDomain.COMPLICATED,
        domain_confidence=0.92,
        domain_entropy=0.41,
        router_key_indicators=["multi-factor", "cause-effect-analyzable"],
        domain_scores={"Complicated": 0.92, "Complex": 0.05},
        user_input="Why did supplier costs jump 15%?",
        task_description="Causal analysis on supplier cost spike",
    )
    state.add_reasoning_step(
        node_name="router",
        action="classify-domain",
        input_summary="user query",
        output_summary="Complicated",
        confidence=ConfidenceLevel.HIGH,
        duration_ms=42,
    )
    state.add_reasoning_step(
        node_name="causal_analyst",
        action="estimate-ate",
        input_summary="cost dataset",
        output_summary="ATE=0.15 (refuted=ok)",
        confidence=ConfidenceLevel.MEDIUM,
        duration_ms=812,
    )
    state.add_reasoning_step(
        node_name="guardian",
        action="enforce-policy",
        input_summary="proposed action",
        output_summary="approved",
        confidence=ConfidenceLevel.HIGH,
        duration_ms=12,
    )
    state.causal_evidence = CausalEvidence(
        effect_size=0.15,
        confidence_interval=(0.08, 0.22),
        refutation_passed=True,
        refutation_results={"placebo_treatment_refuter": True, "random_common_cause": True},
        treatment="freight_index",
        outcome="supplier_cost",
    )
    state.bayesian_evidence = BayesianEvidence(
        posterior_mean=0.13,
        credible_interval=(0.05, 0.21),
        epistemic_uncertainty=0.18,
        aleatoric_uncertainty=0.04,
        hypothesis="freight index drives cost",
    )
    state.counterfactual_evidence = CounterfactualEvidence(
        factual_outcome="cost +15%",
        counterfactual_outcome="cost +4%",
        intervention_description="freight index held flat",
        confidence=0.71,
    )
    state.neurosymbolic_evidence = NeurosymbolicEvidence(
        conclusion="Freight index dominates supplier cost spike",
        rules_fired=["rule:freight-pass-through", "rule:fx-residual"],
        shortcut_warnings=[],
        grounding_source="rules+kg",
        confidence=0.82,
    )
    state.guardian_verdict = GuardianVerdict.APPROVED
    state.policy_violations = []
    state.final_response = "The 15% jump is mostly attributable to the freight index spike."
    state.final_action = {"type": "report", "channel": "dashboard"}
    return state


class TestPROVAgentBundle:
    def test_build_bundle_has_required_top_level(self):
        emitter = PROVAgentEmitter(PROVAgentConfig(enabled=True))
        bundle = emitter.build_bundle(_populated_state())

        assert bundle["@type"] == "prov:Bundle"
        ctx = bundle["@context"]
        assert ctx["prov"] == PROV_NAMESPACE
        assert "carf" in ctx
        assert "@graph" in bundle and isinstance(bundle["@graph"], list)
        assert bundle["carf:schemaVersion"].startswith("prov-agent/")

    def test_each_node_has_specialised_agent_type(self):
        emitter = PROVAgentEmitter(PROVAgentConfig(enabled=True))
        bundle = emitter.build_bundle(_populated_state())

        agents = [n for n in bundle["@graph"] if "carf:AIAgent" in (n.get("@type") or [])]
        # runtime + router + causal_analyst + guardian = 4 carf agents
        agent_types = {tuple(a["@type"]) for a in agents}
        assert any("carf:CynefinRouter" in t for t in agent_types)
        assert any("carf:CausalAnalyst" in t for t in agent_types)
        assert any("carf:Guardian" in t for t in agent_types)

    def test_reasoning_chain_is_linked_via_was_informed_by(self):
        emitter = PROVAgentEmitter(PROVAgentConfig(enabled=True))
        bundle = emitter.build_bundle(_populated_state())

        steps = [
            n for n in bundle["@graph"]
            if "carf:ReasoningStep" in (n.get("@type") or [])
        ]
        assert len(steps) == 3
        # First step has no wasInformedBy; subsequent steps do.
        assert "wasInformedBy" not in steps[0]
        assert steps[1]["wasInformedBy"] == steps[0]["@id"]
        assert steps[2]["wasInformedBy"] == steps[1]["@id"]

    def test_guardian_verdict_emitted_as_first_class_activity(self):
        emitter = PROVAgentEmitter(PROVAgentConfig(enabled=True))
        bundle = emitter.build_bundle(_populated_state())

        verdicts = [
            n for n in bundle["@graph"]
            if "carf:GuardianVerdictActivity" in (n.get("@type") or [])
        ]
        assert len(verdicts) == 1
        assert verdicts[0]["carf:verdict"] == "approved"
        assert verdicts[0]["wasAssociatedWith"] == "urn:carf:agent:guardian"

    def test_evidence_entities_attributed_to_specialised_agents(self):
        emitter = PROVAgentEmitter(PROVAgentConfig(enabled=True))
        bundle = emitter.build_bundle(_populated_state())

        wanted = {
            "carf:CausalEvidence": "urn:carf:agent:causal_analyst",
            "carf:BayesianEvidence": "urn:carf:agent:bayesian_analyst",
            "carf:CounterfactualEvidence": "urn:carf:agent:counterfactual",
            "carf:NeurosymbolicEvidence": "urn:carf:agent:neurosymbolic",
        }
        for evidence_type, expected_agent in wanted.items():
            ents = [
                n for n in bundle["@graph"]
                if evidence_type in (n.get("@type") or [])
            ]
            assert len(ents) == 1, f"missing {evidence_type}"
            assert ents[0]["wasAttributedTo"] == expected_agent

    def test_final_response_was_generated_by_last_activity(self):
        emitter = PROVAgentEmitter(PROVAgentConfig(enabled=True))
        bundle = emitter.build_bundle(_populated_state())

        finals = [
            n for n in bundle["@graph"]
            if "carf:FinalResponse" in (n.get("@type") or [])
        ]
        assert len(finals) == 1
        # Fingerprint instead of raw text by default — no content leak.
        assert "carf:responseText" not in finals[0]
        assert finals[0]["carf:contentFingerprint"]["sha256"] is not None
        assert "wasGeneratedBy" in finals[0]

    def test_include_full_response_opt_in(self):
        emitter = PROVAgentEmitter(
            PROVAgentConfig(enabled=True, include_full_response=True)
        )
        bundle = emitter.build_bundle(_populated_state())
        finals = [
            n for n in bundle["@graph"]
            if "carf:FinalResponse" in (n.get("@type") or [])
        ]
        assert finals[0]["carf:responseText"].startswith("The 15% jump")


class TestPROVAgentWrite:
    def test_write_disabled_returns_none(self, tmp_path: Path):
        emitter = PROVAgentEmitter(
            PROVAgentConfig(enabled=False, output_dir=tmp_path)
        )
        result = emitter.write_state(_populated_state())
        assert result is None
        assert list(tmp_path.iterdir()) == []

    def test_write_enabled_produces_jsonld_file(self, tmp_path: Path):
        emitter = PROVAgentEmitter(
            PROVAgentConfig(enabled=True, output_dir=tmp_path)
        )
        state = _populated_state()
        out = emitter.write_state(state)
        assert out is not None
        assert out.exists()
        assert out.suffix == ".jsonld"
        assert out.stem == str(state.session_id)

        loaded = json.loads(out.read_text(encoding="utf-8"))
        assert loaded["@type"] == "prov:Bundle"
        # Must round-trip JSON cleanly.
        json.dumps(loaded)

    def test_config_from_env(self, monkeypatch, tmp_path: Path):
        monkeypatch.setenv("CARF_PROV_ENABLED", "true")
        monkeypatch.setenv("CARF_PROV_DIR", str(tmp_path))
        monkeypatch.setenv("CARF_PROV_INCLUDE_RESPONSE", "false")
        cfg = PROVAgentConfig.from_env()
        assert cfg.enabled is True
        assert cfg.output_dir == tmp_path
        assert cfg.include_full_response is False

    def test_minimal_state_still_emits_valid_bundle(self, tmp_path: Path):
        emitter = PROVAgentEmitter(
            PROVAgentConfig(enabled=True, output_dir=tmp_path)
        )
        # Default-constructed state has no reasoning chain, no evidence.
        state = EpistemicState(session_id=uuid4(), user_input="hi")
        out = emitter.write_state(state)
        assert out is not None
        loaded = json.loads(out.read_text(encoding="utf-8"))
        assert loaded["@type"] == "prov:Bundle"
        # Should still have at least the runtime and user agent nodes.
        agent_ids = {
            n["@id"]
            for n in loaded["@graph"]
            if "prov:SoftwareAgent" in (n.get("@type") or [])
            or "prov:Person" in (n.get("@type") or [])
        }
        assert "urn:carf:agent:runtime" in agent_ids
        assert "urn:carf:agent:user" in agent_ids
