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

## LLM Output Evaluation Strategy

All LLM outputs are subject to runtime quality evaluation using [DeepEval](https://github.com/confident-ai/deepeval).

### Quality Metrics by Layer

| Layer | Primary Metrics | Thresholds | Action on Failure |
|-------|-----------------|------------|-------------------|
| **Router** | Relevancy, Reasoning Depth | R>0.7, RD>0.6 | Route to Disorder |
| **Causal Analyst** | Hallucination Risk, Reasoning | H<0.3, RD>0.7 | Flag for human review |
| **Bayesian Explorer** | UIX Compliance, Reasoning | UIX>0.6 | Add uncertainty warning |
| **Narration/UX** | Relevancy, UIX Compliance | R>0.7, UIX>0.6 | Regenerate response |
| **Guardian** | Reasoning Depth | RD>0.6 | Log explanation gap |

### Quality Gates

- Responses with `hallucination_risk > 0.3` trigger reflection loop or human escalation
- Responses with `relevancy < 0.7` escalate to stronger model or human review
- `uix_compliance < 0.6` blocks presentation to end users without remediation
- All quality scores logged to Kafka audit trail for compliance

### Evaluation Integration Points

1. **Post-Router**: Evaluate classification reasoning before domain dispatch
2. **Post-Analyst**: Evaluate causal/Bayesian output before Guardian
3. **Post-Guardian**: Evaluate decision explanations for clarity
4. **Pre-Delivery**: Final UIX compliance check before user presentation

### Chimera Oracle Quality Assurance

Fast predictions from Chimera Oracle are validated:
- Compare Chimera output quality vs cached full-analysis scores
- Only cache predictions with `hallucination_risk < 0.2`
- Fall back to full DoWhy analysis if Chimera quality degrades

### Continuous Improvement

- Quality scores stored in Neo4j for regression analysis
- Weekly quality trend reports for model performance monitoring
- Human feedback incorporated to refine evaluation thresholds
- Automatic alerts on quality degradation (>10% drop in any metric)

See [Evaluation Framework](./EVALUATION_FRAMEWORK.md) for detailed implementation.

---

## Phase 17 LLM Roles (Causal World Model & NeSy)

Phase 17 introduced new LLM touchpoints within clearly bounded roles:

| Component | LLM Role | Deterministic Core | Safety Bound |
|-----------|----------|-------------------|--------------|
| **Causal World Model** | Probabilistic simulation fallback when no SCM data available | SCM evaluation, OLS learning, do-calculus | H-Neuron sentinel pre-delivery gate |
| **Counterfactual Engine** | Natural language query parsing, Pearl's 3-step reasoning when no SCM | SCM-based counterfactual when data available | Cached results validation |
| **Neurosymbolic Engine** | Fact extraction from unstructured text | Forward-chaining, shortcut detection, constraint validation | KB confidence thresholds, CSL policy rules |
| **H-Neuron Sentinel** | None (proxy mode) | Weighted signal fusion, deterministic risk scoring | Threshold-based flagging |

**Key principle:** LLMs serve as knowledge priors and natural language interfaces. All critical reasoning paths have deterministic fallbacks. The neurosymbolic engine explicitly validates LLM outputs through symbolic constraint checking before they enter the knowledge base.

## Supervised Recursive Refinement (SRR) and LLM Safety

CARF's LLM usage is governed by the SRR model (see [`CARF_RSI_ANALYSIS.md`](CARF_RSI_ANALYSIS.md)):

- **LLMs cannot modify** policies, Guardian thresholds, CSL rules, or their own prompts
- **LLMs can only repair** proposed actions within existing heuristic bounds (Reflector)
- **Memory influence** from LLM-produced analyses is capped at 0.03 weight in routing hints
- **Feedback-driven retraining** requires human triggering — LLMs cannot initiate model updates
- **Guardian verdicts are deterministic** — preventing LLM manipulation of safety evaluator

### Known SRR Gaps (Phase 18 Addresses)

1. No monitoring of whether LLM-influenced memory hints cause routing drift over time
2. No automated bias audit of LLM-produced analyses accumulated in memory
3. No convergence detection in feedback→retraining loops
4. ChimeraOracle bypasses Guardian enforcement (AP-7) — Phase 18 integrates into StateGraph

## Multi-Agent Scaling Strategy (Research-Informed)

> Source: [`research.md`](../research.md) §1.2, §4.1, §4.4

As CARF scales to enterprise deployment, multi-agent LLM systems offer solutions for:

### Collaborative Causal Discovery
- **Variable Partitioning**: Different LLM agents specialize in subsets of variables
- **Algorithm Selection**: Agent debates between PC, FCI, and score-based methods
- **Validation**: Cross-agent graph structure voting with consensus threshold
- **Integration**: Via existing LangGraph cognitive mesh — each discovery agent as a new domain node

### Scalable Policy Management
- **Policy Translation**: LLM agents convert natural language regulations to CSL rules
- **Conflict Detection**: Multi-agent analysis of policy interactions across domains
- **Dynamic Adaptation**: Agents monitor regulatory changes and propose policy updates
- **Human Gate**: All policy modifications require human approval (SRR principle)

### Enhanced Knowledge Operations
- **RAG Quality**: LLM agents curate and validate RAG corpus entries
- **Knowledge Graph Maintenance**: Automated Neo4j graph cleaning and enrichment
- **Cross-Session Learning**: Agents extract patterns from accumulated analyses
- **Bias Monitoring**: Dedicated auditor agent for memory corpus fairness (Phase 18)

### Multi-Agent Coordination Guardrails
- All inter-agent communication must pass through EpistemicState (no side channels)
- Agent outputs validated by Guardian before affecting system state
- Token budgets enforced per-agent to prevent runaway costs
- Coordination overhead tracked by Cost Intelligence Service
- Accountability: each agent decision logged with model ID and reasoning trace
