# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""PROV-AGENT JSON-LD emission for CARF audit lineage.

Emits a W3C PROV-DM bundle (JSON-LD serialization) per EpistemicState, extending
W3C PROV with the PROV-AGENT vocabulary proposed in arXiv:2508.02866 to cover
LLM invocations, tool calls, agent reasoning chains, and Guardian verdicts.

Design:
- Each session becomes one ``prov:Bundle`` written to ``CARF_PROV_DIR``
  (default ``var/prov/<session>.jsonld``).
- ``carf:AIAgent`` is a subclass of ``prov:SoftwareAgent``; specialised agent
  classes (``carf:CynefinRouter``, ``carf:CausalAnalyst``, …) are derived from
  the LangGraph node name.
- Each ``ReasoningStep`` becomes a ``prov:Activity`` and chains via
  ``prov:wasInformedBy`` to its predecessor.
- Causal / Bayesian / counterfactual / neurosymbolic evidence and the final
  response become ``prov:Entity`` records ``prov:wasGeneratedBy`` the
  appropriate activity.

Emission is opt-in (``CARF_PROV_ENABLED=true`` or explicit config). The module
has no third-party dependencies — JSON-LD here is plain JSON with a context
block, so we do not require ``pyld`` or ``rdflib``.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.core.state import EpistemicState

logger = logging.getLogger("carf.prov_agent")

CARF_NAMESPACE = "https://cisuregen.local/ns/carf#"
PROV_NAMESPACE = "http://www.w3.org/ns/prov#"
SCHEMA_ORG = "https://schema.org/"

# Node-name → specialised carf agent subclass. Anything unknown falls back to
# the generic carf:AIAgent.
NODE_AGENT_TYPE: dict[str, str] = {
    "router": "carf:CynefinRouter",
    "cynefin_router": "carf:CynefinRouter",
    "causal_analyst": "carf:CausalAnalyst",
    "causal": "carf:CausalAnalyst",
    "bayesian_analyst": "carf:BayesianAnalyst",
    "bayesian": "carf:BayesianAnalyst",
    "chimera_oracle": "carf:ChimeraOracle",
    "chimera_fast_path": "carf:ChimeraOracle",
    "neurosymbolic": "carf:NeurosymbolicAgent",
    "counterfactual": "carf:CounterfactualAgent",
    "guardian": "carf:Guardian",
    "csl_guard": "carf:CSLGuard",
    "human_layer": "carf:HumanLayerAdapter",
    "circuit_breaker": "carf:CircuitBreaker",
    "smart_reflector": "carf:SmartReflector",
    "evaluation": "carf:EvaluationService",
    "rag": "carf:RAGAgent",
    "memory": "carf:AgentMemory",
}


class PROVAgentConfig(BaseModel):
    """Configuration for the PROV emitter."""

    enabled: bool = Field(default=False)
    output_dir: Path = Field(default=Path("var/prov"))
    pretty: bool = Field(default=True, description="Indented JSON-LD output")
    include_full_response: bool = Field(
        default=False,
        description=(
            "When True, the final response text is embedded as a literal in "
            "the entity. When False (default) only a hash + length are kept "
            "to avoid leaking content into logs."
        ),
    )

    @classmethod
    def from_env(cls) -> "PROVAgentConfig":
        enabled_env = os.getenv("CARF_PROV_ENABLED")
        enabled = bool(enabled_env and enabled_env.lower() == "true")
        output_dir = Path(os.getenv("CARF_PROV_DIR", "var/prov"))
        pretty = os.getenv("CARF_PROV_PRETTY", "true").lower() == "true"
        include_full = (
            os.getenv("CARF_PROV_INCLUDE_RESPONSE", "false").lower() == "true"
        )
        return cls(
            enabled=enabled,
            output_dir=output_dir,
            pretty=pretty,
            include_full_response=include_full,
        )


def _agent_type_for_node(node_name: str) -> str:
    key = (node_name or "").strip().lower()
    return NODE_AGENT_TYPE.get(key, "carf:AIAgent")


def _hash_text(text: str | None) -> dict[str, Any]:
    """Stable lightweight content fingerprint without leaking content."""
    if not text:
        return {"length": 0, "sha256": None}
    import hashlib

    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {"length": len(text), "sha256": h}


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


class PROVAgentEmitter:
    """Build PROV-AGENT JSON-LD bundles from EpistemicState."""

    def __init__(self, config: PROVAgentConfig | None = None) -> None:
        self.config = config or PROVAgentConfig.from_env()

    # ------------------------------------------------------------------ build

    def build_bundle(self, state: EpistemicState) -> dict[str, Any]:
        """Produce the full JSON-LD bundle dict for a state."""
        session_iri = self._session_iri(state.session_id)
        bundle_iri = f"{session_iri}/prov-bundle"
        agents = self._build_agents(state)
        activities, last_activity_iri = self._build_activities(state, session_iri)
        entities = self._build_entities(state, session_iri, last_activity_iri)

        graph: list[dict[str, Any]] = []
        graph.extend(agents)
        graph.extend(activities)
        graph.extend(entities)

        return {
            "@context": self._context(),
            "@id": bundle_iri,
            "@type": "prov:Bundle",
            "carf:schemaVersion": "prov-agent/1.0",
            "carf:carfVersion": os.getenv("CARF_VERSION", "0.5"),
            "prov:generatedAtTime": _iso(datetime.now(timezone.utc)),
            "carf:session": session_iri,
            "@graph": graph,
        }

    def write_state(self, state: EpistemicState) -> Path | None:
        """Serialize the bundle to ``output_dir/<session>.jsonld``."""
        if not self.config.enabled:
            return None
        bundle = self.build_bundle(state)
        try:
            self.config.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("PROV output_dir %s not writable: %s", self.config.output_dir, exc)
            return None

        path = self.config.output_dir / f"{state.session_id}.jsonld"
        indent = 2 if self.config.pretty else None
        try:
            path.write_text(
                json.dumps(bundle, indent=indent, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("PROV write failed for %s: %s", path, exc)
            return None
        logger.debug("PROV bundle written: %s", path)
        return path

    # ------------------------------------------------------------ subgraph builders

    def _context(self) -> dict[str, Any]:
        return {
            "prov": PROV_NAMESPACE,
            "carf": CARF_NAMESPACE,
            "schema": SCHEMA_ORG,
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "wasGeneratedBy": {"@id": "prov:wasGeneratedBy", "@type": "@id"},
            "wasAssociatedWith": {"@id": "prov:wasAssociatedWith", "@type": "@id"},
            "wasAttributedTo": {"@id": "prov:wasAttributedTo", "@type": "@id"},
            "actedOnBehalfOf": {"@id": "prov:actedOnBehalfOf", "@type": "@id"},
            "wasInformedBy": {"@id": "prov:wasInformedBy", "@type": "@id"},
            "used": {"@id": "prov:used", "@type": "@id"},
            "startedAtTime": {"@id": "prov:startedAtTime", "@type": "xsd:dateTime"},
            "endedAtTime": {"@id": "prov:endedAtTime", "@type": "xsd:dateTime"},
            "generatedAtTime": {
                "@id": "prov:generatedAtTime",
                "@type": "xsd:dateTime",
            },
        }

    def _session_iri(self, session_id: UUID) -> str:
        return f"urn:carf:session:{session_id}"

    def _build_agents(self, state: EpistemicState) -> list[dict[str, Any]]:
        """One generic carf:CARFRuntime + one specialised agent per distinct node."""
        runtime_iri = "urn:carf:agent:runtime"
        agents: list[dict[str, Any]] = [
            {
                "@id": runtime_iri,
                "@type": ["prov:SoftwareAgent", "carf:AIAgent", "carf:CARFRuntime"],
                "schema:name": "CARF Cognitive Mesh Runtime",
                "carf:role": "orchestrator",
            }
        ]
        seen: set[str] = set()
        for step in state.reasoning_chain:
            agent_type = _agent_type_for_node(step.node_name)
            agent_iri = f"urn:carf:agent:{step.node_name or 'unknown'}"
            if agent_iri in seen:
                continue
            seen.add(agent_iri)
            agents.append(
                {
                    "@id": agent_iri,
                    "@type": [
                        "prov:SoftwareAgent",
                        "carf:AIAgent",
                        agent_type,
                    ],
                    "schema:name": step.node_name,
                    "actedOnBehalfOf": runtime_iri,
                }
            )
        # The user is always represented as an external prov:Agent; downstream
        # delegation receipts (Tier-1 task #5) will populate provenance for who
        # initiated the session.
        agents.append(
            {
                "@id": "urn:carf:agent:user",
                "@type": ["prov:Person", "carf:HumanPrincipal"],
                "schema:name": "Session Originator",
            }
        )
        return agents

    def _build_activities(
        self, state: EpistemicState, session_iri: str
    ) -> tuple[list[dict[str, Any]], str | None]:
        activities: list[dict[str, Any]] = []
        previous_iri: str | None = None
        last_iri: str | None = None
        for step in state.reasoning_chain:
            activity_iri = f"{session_iri}/activity/{step.step_id}"
            agent_iri = f"urn:carf:agent:{step.node_name or 'unknown'}"
            entry: dict[str, Any] = {
                "@id": activity_iri,
                "@type": ["prov:Activity", "carf:ReasoningStep"],
                "carf:nodeName": step.node_name,
                "carf:action": step.action,
                "carf:inputSummary": step.input_summary,
                "carf:outputSummary": step.output_summary,
                "carf:confidence": step.confidence.value,
                "carf:durationMs": step.duration_ms,
                "startedAtTime": _iso(step.timestamp),
                "wasAssociatedWith": agent_iri,
            }
            if previous_iri is not None:
                entry["wasInformedBy"] = previous_iri
            activities.append(entry)
            previous_iri = activity_iri
            last_iri = activity_iri

        # Guardian verdict gets its own first-class activity if present, even
        # if it was already represented as a reasoning step (so consumers can
        # filter on @type == carf:GuardianVerdictActivity directly).
        if state.guardian_verdict is not None:
            verdict_iri = f"{session_iri}/activity/guardian-verdict"
            verdict_entry: dict[str, Any] = {
                "@id": verdict_iri,
                "@type": [
                    "prov:Activity",
                    "carf:GuardianVerdictActivity",
                ],
                "carf:verdict": state.guardian_verdict.value,
                "carf:policyViolations": list(state.policy_violations),
                "wasAssociatedWith": "urn:carf:agent:guardian",
            }
            if last_iri is not None:
                verdict_entry["wasInformedBy"] = last_iri
            activities.append(verdict_entry)
            last_iri = verdict_iri

        return activities, last_iri

    def _build_entities(
        self,
        state: EpistemicState,
        session_iri: str,
        last_activity_iri: str | None,
    ) -> list[dict[str, Any]]:
        entities: list[dict[str, Any]] = []

        # User input is an entity attributed to the user agent.
        if state.user_input:
            entities.append(
                {
                    "@id": f"{session_iri}/entity/user-input",
                    "@type": ["prov:Entity", "carf:UserPrompt"],
                    "carf:contentFingerprint": _hash_text(state.user_input),
                    "wasAttributedTo": "urn:carf:agent:user",
                    "generatedAtTime": _iso(state.created_at),
                }
            )

        # Cynefin classification entity.
        entities.append(
            {
                "@id": f"{session_iri}/entity/cynefin-classification",
                "@type": ["prov:Entity", "carf:CynefinClassification"],
                "carf:domain": state.cynefin_domain.value,
                "carf:domainConfidence": state.domain_confidence,
                "carf:domainEntropy": state.domain_entropy,
                "carf:keyIndicators": list(state.router_key_indicators),
                "carf:domainScores": dict(state.domain_scores),
                "wasAttributedTo": "urn:carf:agent:router",
            }
        )

        if state.causal_evidence is not None:
            ev = state.causal_evidence
            entities.append(
                {
                    "@id": f"{session_iri}/entity/causal-evidence",
                    "@type": ["prov:Entity", "carf:CausalEvidence"],
                    "carf:effectSize": ev.effect_size,
                    "carf:confidenceInterval": list(ev.confidence_interval),
                    "carf:refutationPassed": ev.refutation_passed,
                    "carf:refutationResults": dict(ev.refutation_results),
                    "carf:treatment": ev.treatment,
                    "carf:outcome": ev.outcome,
                    "wasAttributedTo": "urn:carf:agent:causal_analyst",
                }
            )

        if state.bayesian_evidence is not None:
            ev = state.bayesian_evidence
            entities.append(
                {
                    "@id": f"{session_iri}/entity/bayesian-evidence",
                    "@type": ["prov:Entity", "carf:BayesianEvidence"],
                    "carf:posteriorMean": ev.posterior_mean,
                    "carf:credibleInterval": list(ev.credible_interval),
                    "carf:epistemicUncertainty": ev.epistemic_uncertainty,
                    "carf:aleatoricUncertainty": ev.aleatoric_uncertainty,
                    "wasAttributedTo": "urn:carf:agent:bayesian_analyst",
                }
            )

        if state.counterfactual_evidence is not None:
            ev = state.counterfactual_evidence
            entities.append(
                {
                    "@id": f"{session_iri}/entity/counterfactual-evidence",
                    "@type": ["prov:Entity", "carf:CounterfactualEvidence"],
                    "carf:factualOutcome": ev.factual_outcome,
                    "carf:counterfactualOutcome": ev.counterfactual_outcome,
                    "carf:confidence": ev.confidence,
                    "wasAttributedTo": "urn:carf:agent:counterfactual",
                }
            )

        if state.neurosymbolic_evidence is not None:
            ev = state.neurosymbolic_evidence
            entities.append(
                {
                    "@id": f"{session_iri}/entity/neurosymbolic-evidence",
                    "@type": ["prov:Entity", "carf:NeurosymbolicEvidence"],
                    "carf:conclusion": ev.conclusion,
                    "carf:rulesFired": list(ev.rules_fired),
                    "carf:shortcutWarnings": list(ev.shortcut_warnings),
                    "carf:groundingSource": ev.grounding_source,
                    "carf:confidence": ev.confidence,
                    "wasAttributedTo": "urn:carf:agent:neurosymbolic",
                }
            )

        # Final response entity wasGeneratedBy the last activity.
        if state.final_response is not None or state.final_action is not None:
            final_entity: dict[str, Any] = {
                "@id": f"{session_iri}/entity/final-response",
                "@type": ["prov:Entity", "carf:FinalResponse"],
                "carf:contentFingerprint": _hash_text(state.final_response),
                "wasAttributedTo": "urn:carf:agent:runtime",
                "generatedAtTime": _iso(state.updated_at),
            }
            if state.final_action is not None:
                final_entity["carf:action"] = dict(state.final_action)
            if self.config.include_full_response and state.final_response:
                final_entity["carf:responseText"] = state.final_response
            if last_activity_iri is not None:
                final_entity["wasGeneratedBy"] = last_activity_iri
            entities.append(final_entity)

        return entities


_emitter_singleton: PROVAgentEmitter | None = None


def get_prov_emitter() -> PROVAgentEmitter:
    global _emitter_singleton
    if _emitter_singleton is None:
        _emitter_singleton = PROVAgentEmitter()
    return _emitter_singleton


def reset_prov_emitter() -> None:
    """Reset the singleton (test helper)."""
    global _emitter_singleton
    _emitter_singleton = None


def emit_prov_for_state(state: EpistemicState) -> Path | None:
    """Convenience wrapper: emit + write a PROV bundle for one state."""
    return get_prov_emitter().write_state(state)
