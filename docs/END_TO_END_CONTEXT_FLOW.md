# End-to-End Context Flow

## Purpose
Describe how data and context move through CARF: Router → Domain Agents → Guardian → Reflector → HumanLayer, with memory and audit integration.

## High-Level Flow
1. Ingest: User query + optional scenario/dataset context enters EpistemicState.
2. Router: Compute entropy; classify domain (LLM/model); set confidence, domain, hypothesis.
3. Domain Agent:
   - Clear → deterministic_runner (lookups/automation)
   - Complicated → causal_analyst (DoWhy/EconML)
   - Complex → bayesian_explorer (PyMC)
   - Chaotic → circuit_breaker (stabilize)
   - Disorder → human_escalation
4. Guardian: Policy check; verdict = approved | rejected | requires_escalation.
5. Reflector: On rejection, bounded self-correction; else escalate to HumanLayer.
6. HumanLayer: Approvals/overrides; updates state; may return to Router or end.
7. Output: Final response/action with audit trail.

## State Propagation (EpistemicState highlights)
- cynefin_domain, domain_confidence, domain_entropy
- current_hypothesis, reasoning steps
- proposed_action, guardian_verdict, policy_violations
- reflection_count/max_reflections
- human_interaction_status, human_verification, human_override_instructions
- final_response, final_action, error

## Memory & Audit Integration
- Neo4j (optional): causal graphs, analyses, history of actions (planned for model feedback).
- Kafka (optional): immutable audit events (router → agent → guardian → human).
- Logs: state transitions and reasoning steps for traceability.

## Human Feedback Loop
- Guardian rejection → Reflector → Router retry; after cap → HumanLayer.
- HumanLayer approvals/overrides persisted in state; can guide retry or finalize.

## Model/LLM Touchpoints
- Router classification (LLM/distilled).
- Optional LLM assists: context synthesis, planning, narration, reflection reasoning, human notifications.
- Core decisions (guardian, causal/Bayesian math, circuit-breaker actions) stay deterministic/statistical.

## Failure Handling & Escalation
- Low confidence or parse failure → Disorder/Human.
- Repeated rejection → human_escalation after max_reflections.
- Circuit breaker always escalates to human after stabilization attempt.

## Cost/Latency Considerations
- Prefer local/distilled model for routing when sufficient; use stronger LLM only on high entropy/uncertainty.
- Keep prompts short; structure outputs; cache safe summaries.
