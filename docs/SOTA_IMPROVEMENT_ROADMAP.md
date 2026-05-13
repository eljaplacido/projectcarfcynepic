# CARF SOTA Improvement Roadmap

Living roadmap for raising CARF/CYNEPIC to current state-of-the-art for
agentic, neuro-symbolic, causal, Bayesian, RAG, governance, evaluation, and
benchmarking practice. Anchor reference is the cursor plan at
`carf_sota_improvements_eab86904.plan.md`.

The principle behind PR1 (this batch): **make every benchmark claim
reproducible, categorised, and defensible before adding more capability**.
Capability-level work (P1+) builds on top of that evidence floor.

## Status legend

- DONE — landed on `main`.
- IN PROGRESS — partial, tracked but not finished.
- PLANNED — accepted for the roadmap, no code yet.
- DEFERRED — explicitly postponed; revisit on the date noted.

---

## P0 — Benchmark Evidence Hardening

| ID | Item | Status |
|----|------|--------|
| P0.1 | Add benchmark manifest JSON Schema with evidence-grading fields | DONE — `benchmarks/reports/benchmark_manifest.schema.json` |
| P0.2 | Extend `BenchmarkRealismSpec` with `data_source`, `ground_truth_type`, `llm_provider`, `seed`, `uses_mock`, `uses_fallback`, `sample_size`, `confidence_interval`, `repro_command`, `evidence_grade` | DONE — `benchmarks/reports/realism.py` |
| P0.3 | Add `--strict-manifest` gate to `check_result_evidence.py` | DONE |
| P0.4 | Grade and enrich every entry in `realism_manifest.json` (33 sources) | DONE — initial pass; grades open to challenge |
| P0.5 | Tests for completeness gate, schema/constant parity, real-manifest grading | DONE — `tests/unit/test_benchmark_manifest_completeness.py` |
| P0.6 | Wire H40–H43 (monitoring) into `evaluate_hypotheses()` so the unified report stops silently dropping them | PLANNED |
| P0.7 | Reconcile the 32.7x vs 40.7x ChimeraOracle speedup numbers | DONE — canonical value is 40.72x from `benchmark_oracle_results.json`; all docs updated |
| P0.8 | Verify and write the *actual* seed used by each benchmark script into the manifest (currently a placeholder of `42` for entries with `seed_reproducible=true`) | PLANNED |
| P0.9 | Re-run `benchmarks/reports/generate_report.py` so `benchmark_report.json` reflects 43 hypotheses (and the realism gate state with current data) | PLANNED |

### Initial evidence-grade distribution (33 manifest entries)

| Grade | Count | Examples |
|-------|-------|----------|
| `validated` | 2 | `guardian`, `cross_llm` |
| `synthetic-only` | 11 | `causal`, `bayesian`, `counterbench`, `adversarial_causal`, `fairness`, `scope3`, `supply_chain`, `healthcare`, `finance`, `baseline`, `board_lifecycle`, `policy_roundtrip` |
| `needs-independent-replication` | 20 | `router`, `performance`, `chimera`, `governance`, `e2e`, `owasp`, `red_team`, `tau_bench`, `hallucination_scale`, `clear`, `xai`, `audit_trail`, `energy`, `sus`, `task_completion`, `wcag`, `load`, `chaos_cascade`, `soak` |
| `stubbed` | 0 | — |
| `aspirational` | 0 | — |

Read this as: today, only `guardian` and `cross_llm` are positioned as
production-strength evidence. Most other entries either rely on synthetic
ground truth or have not been replicated outside this repository. That is
**not** a regression — it makes a state previously implicit in the docs
explicit and gateable.

### Discrepancies tracked from the documentation audit

These were surfaced when reviewing CYNEPIC, BENCHMARK_RE_EVALUATION_PLAN,
README, and `benchmark_report.json` against each other:

- **39 vs 43 hypotheses.** `benchmarks/reports/generate_report.py` now lists
  H0–H43 in `HYPOTHESES`, but only H0–H39 have evaluation branches. The
  shipped `benchmark_report.json` shows `hypotheses_total: 39`. Tracked as
  P0.6 / P0.9.
- **H20 missing.** The README hypothesis table jumps from H19 to H21. The
  source `HYPOTHESES` list also has no H20 entry. Decide whether to renumber
  or document the gap.
- **ChimeraOracle speedup published as both 32.7x and 40.7x.** RESOLVED: canonical
  value is **40.72x** from `benchmarks/technical/chimera/benchmark_oracle_results.json`
  (DoWhy mean 3,154ms / Oracle mean 77ms = 40.72x). The 32.7x figure was from an
  older calculation method and has been corrected in all docs. Tracked as P0.7 (DONE).
- **Realism quality gate `false` in `benchmark_report.json`.** Once the
  manifest enrichment in this PR is consumed by a fresh report run, the gate
  reasons should be readable in `realism_validation.quality_gate_reasons`.
- **Test count drift** (CYNEPIC: 1,158; CURRENT_STATUS: 1,365+). Doc
  reconciliation lives in PR2 (see below) — out of scope for the evidence
  PR but noted here so it does not get lost.

---

## P1 — Production Observability and Trace-to-Eval Loop

PLANNED. Design deliverable for PR3.

- OpenTelemetry / OpenInference per-node spans for the LangGraph workflow
  in `src/workflows/graph.py`: `router_node`, `rag_context_node`,
  `csl_precheck_node`, the domain runners, `csl_guardian_node`,
  `reflector_node`, `human_escalation_node`, optional governance nodes.
- Per-span attributes: router score, RAG retrieval IDs, model/provider,
  token cost, tool call list, Guardian rule IDs, fallback path used
  (`method=mock|llm_fallback|statistical|oracle`), final evidence grade.
- Trace-to-dataset loop: failures, low-confidence cases, human overrides,
  and Guardian rejections become regression cases under `tests/eval/`.
- Surface the trace identifiers in the developer/governance React panels.

---

## P1 — Explicit Inference Modes

PLANNED. Implements Phase 18E from `CURRENT_STATUS.md`.

- `research`: full DoWhy/PyMC, refutations, verbose diagnostics.
- `staging`: approximate inference, cached posterior reuse, stricter
  fallback warnings.
- `production`: ChimeraOracle for eligible recurring scenarios, cached
  Bayesian summaries, full analysis only for high-risk decisions.
- New benchmarks H44/H45 covering approximate-vs-full fidelity and
  high-dimensional causal discovery; both will be added to the manifest
  with the new evidence-grade fields from PR1.

---

## P1 — SOTA Hybrid RAG

PLANNED.

- Resource-aware routing in `src/services/rag_service.py`: vector / graph /
  symbolic, fused with Reciprocal Rank Fusion or weighted fusion.
- RAGAS-style metrics: context precision, context recall, faithfulness,
  citation accuracy, answer relevance.
- LightRAG dual-level retrieval treated as an optional backend, not a hard
  dependency (matches today's code path).

---

## P2 — Active Neuro-Symbolic Reasoning

PLANNED.

- `SymbolicHypothesisConstrainer` runs **before** causal estimation and
  rejects impossible edges using domain ontology constraints stored in
  Neo4j / governance graph.
- Logic-generated refutation tests on top of DoWhy's standard placebo /
  random-common-cause tests.
- Shortcut / spurious-correlation defence: invariance tests, conditional
  independence checks, mechanism plausibility checks.

---

## P2 — Causal World Model and Temporal Counterfactuals

PLANNED.

- Version SCMs over time in Neo4j.
- Add transition dynamics and rollout simulation (not only static
  do-operator effects).
- CausalARC-style evaluation: observational, interventional, counterfactual
  prompts derived from known SCMs.
- React cockpit: divergent timelines, causal attribution deltas.

---

## P2 — Security and Agent Red-Team CI

PLANNED.

- Promptfoo or DeepTeam red-team CI against `/query`, `/query/stream`,
  MCP tools, RAG ingestion, governance document upload.
- OWASP LLM Top 10 2025 explicit coverage: prompt injection, sensitive
  info disclosure, excessive agency, system prompt leakage, vector /
  embedding weaknesses, misinformation, unbounded consumption.
- MITRE ATLAS mapping for agent-specific attacks.
- Every failed security test becomes a permanent regression case.

---

## P3 — Multi-Agent Causal Discovery

PLANNED.

- Roles: variable selector, graph proposer, algorithm selector, refutation
  designer, domain ontology critic, Guardian risk reviewer.
- LangGraph remains the deterministic top-level controller; no free-form
  multi-agent chat at the orchestration layer.
- Consensus / voting only for high-dimensional causal discovery or
  ambiguous domain cases.

---

## Companion documentation work (PR2 candidate)

The audit captured in PR1 surfaced stale or contradictory documentation.
These are separate from the evidence-hardening change to keep PR1
reviewable, but they belong on the same roadmap.

- `docs/CYNEPIC_CAPABILITY_ANALYSIS.md` — reconcile "RAG Not Implemented" /
  "15 cognitive tools" / "Phase 16" against the current Phase 17–18 stack
  (NeSy-augmented RAG, 18 MCP tools, monitoring services).
- `docs/RFC_UIX_002_DATA_ONBOARDING.md`, `docs/CARF_UIX_INTERACTION_GUIDELINES.md`,
  `HANDOFF.md`, `.agent/skills/dev_server/SKILL.md` — drop residual
  Streamlit assumptions; the cockpit is React under `carf-cockpit/`.
- `docs/archive/UIX_EVALUATION_REPORT.md`, `docs/archive/UI_UIX_VISION_REACT.md` —
  mark archive status explicitly so they are not read as current state.
- `docs/PRD.md` — note that the canonical layer count is 6 (per
  `SOLUTION_VISION.md` and `AGENTS.md`), not the 4 still implied by the
  PRD, or refresh the PRD itself.
- React cockpit: the guidelines name `ConfidenceDecomposition` and
  `DataProvenanceLink` components that do not exist in `carf-cockpit/`.
  Either implement them or remove from the spec. Same for Markov-blanket
  highlighting in `CausalDAG.tsx`.

---

## Sequencing summary

1. **PR1 (this change)** — evidence schema, manifest grading, completeness
   gate, roadmap doc.
2. **PR2** — documentation reconciliation (CYNEPIC, archive UIX reports,
   Streamlit references, PRD layer count, missing UI components).
3. **PR3** — OpenTelemetry / OpenInference trace contract design and
   per-node span instrumentation in `src/workflows/graph.py`.
4. **PR4+** — inference modes, hybrid RAG, symbolic constrainer, causal
   world model evaluation, red-team CI, multi-agent discovery.

Anything that adds a new benchmark from PR2 onwards must ship its
manifest entry with all required fields and an explicit `evidence_grade`,
or `python benchmarks/reports/check_result_evidence.py --strict-manifest`
will fail.
