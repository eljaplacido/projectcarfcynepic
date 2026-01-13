# LLM Agentic Strategy

## Purpose
Define when and how LLMs are used in CARF, what remains deterministic/statistical, and how to select models with guardrails for cost, latency, and safety.

## Roles by Layer
- Router (Cynefin): LLM (DeepSeek or distilled model) for domain classification; entropy heuristic + confidence gate; fallback to Disorder/Human.
- Context Assembly: LLM for query rewriting, context synthesis, retrieval summarization; deterministic filters for PII/policy.
- Planning: LLM for task decomposition and solver selection; constrained schema; budget-aware.
- Causal Analyst: Primary causal engine (DoWhy/EconML). LLM assist for hypothesis surfacing, variable suggestions, narration; outputs validated by causal engine.
- Bayesian Explorer: Primary PyMC/statistical. LLM assist for probe design, scenario narration, assumption surfacing; numeric updates stay statistical.
- Deterministic Runner: Non-LLM; LLM optional for response phrasing only.
- Circuit Breaker: Rule/runbook; LLM for incident summary/communication drafts; execution gated by policy/human.
- Guardian: Symbolic/OPA/YAML as source of truth; LLM only to explain verdicts or suggest compliant alternatives.
- Reflector: LLM for self-correction reasoning; bounded retries; may request human escalation.
- HumanLayer: LLM to craft 3-point context (what/why/risk) for approvals; never auto-approves.
- Narration/UX: LLM to explain results, generate executive/developer/user-facing summaries.

## Model Selection Strategy
- Tiers: cheap (distilled/local), balanced (DeepSeek), strong (optional premium).
- Policy: pick tier by entropy/difficulty/cost budget; fall back to local distilled for privacy/offline; log model choice.
- Caching: reuse prompts/responses where safe; prefer short context windows; chunk retrieval summaries.

## Guardrails
- Deterministic sources of truth: Guardian policies, causal/Bayesian math, circuit-breaker runbooks.
- Structured IO: Pydantic schemas; reject malformed outputs; retries with backoff.
- Safety: refuse execution without clarity; default to Disorder/Human on low confidence; redact PII; respect size limits.
- Audit: log state transitions, model used, confidence, indicators; send decisions to Kafka/Neo4j when enabled.

## When NOT to use LLMs
- Policy enforcement (Guardian), numeric inference (causal/Bayesian), deterministic runbooks, critical actuation without human/guardian approval, unvetted code execution.

## Self-Healing Hooks
- Reflection loop: bounded retries with reasoned modifications; escalate after max_reflections.
- Human feedback: incorporate override instructions and approvals into state; persist for learning.
- Memory: optionally record predictions/actions in Neo4j/Kafka for future evaluation and retraining datasets.

## Domain Adaptation
- Ship generic router; allow fine-tune per domain (DistilBERT path).
- Plug domain prompts/templates for planning/context assembly.
- Keep deterministic cores domain-agnostic; adapt surface prompts and router only.

## Cost/Latency Practices
- Prefer distilled/local for routing when accuracy acceptable.
- Batch external calls; short prompts; structured outputs.
- Use cheap tier for low-risk paths; escalate to stronger model only when entropy/uncertainty high.
