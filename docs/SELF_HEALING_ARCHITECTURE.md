# Self-Healing Architecture

## Purpose
Explain how CARF detects failures, retries safely, involves humans, and learns from outcomes.

## Current Mechanisms
- Reflector node (`src/workflows/graph.py`): triggered on Guardian rejection; increments `reflection_count`, clears proposed action, prepares retry.
- Routing logic: Guardian verdict → end | reflector | human_escalation with `max_reflections` guard.
- EpistemicState fields (`src/core/state.py`): `reflection_count`, `max_reflections`, `policy_violations`, `human_interaction_status`, `human_verification`, `human_override_instructions`.
- Guardian: policy gate; rejects/approves/escalates.
- HumanLayer: escalation path for Disorder or blocked actions.

## Self-Healing Loop (MVP)
1. Router → domain agent → Guardian.
2. If Guardian rejects: go to Reflector (unless max_reflections reached).
3. Reflector logs attempt, clears action, returns to Router for reroute/retry.
4. After limit or escalation: HumanLayer handles approval/override.

## Future Enhancements
- LLM-guided reflection: propose modified actions respecting violations; keep bounded attempts.
- Feedback incorporation: store violations, human overrides, and outcomes in Neo4j/Kafka; surface as features for router/solvers.
- Adaptive retry policy: adjust `max_reflections` and model tier based on risk/entropy.
- Postmortem summaries: LLM-generated retrospectives; human-approved before action changes.

## Safety and Guardrails
- Hard cap on reflections (`max_reflections`).
- No auto-override of Guardian; human approval required for exceptions.
- Structured reasoning steps logged for audit; send to Kafka when enabled.
- On low confidence or repeated failures: default to human escalation.

## Observability
- Log each transition: node, action, confidence, verdict, violations.
- Trace IDs/session IDs preserved through Router → Guardian → Reflector → HumanLayer.
- Optionally persist reflection attempts and verdicts for evaluation sets.

## Integration Points
- Router: may downgrade to Disorder on repeated failures.
- Guardian: can include recommendations to guide reflection.
- HumanLayer: returns override instructions stored in EpistemicState, used on retry.
