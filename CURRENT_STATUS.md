# CYNEPIC Architecture 0.5 - Current Status

**Last Updated**: 2026-03-16
**Phase**: Phase 18 — Supervised Recursive Refinement, Scaling Hardening & Operational Intelligence
**Overall Status**: Phase 18A-D Implemented — Drift detection, bias auditing, plateau detection, ChimeraOracle StateGraph integration. 4 RSI gaps closed. 4 new benchmarks (H40-H43). MonitoringPanel in all 4 views. 18E-18F designed (pending implementation).

---

## Phase 18 Design — Derived from Architecture Review & Research Analysis

> Sources: [`research.md`](research.md) (neurosymbolic scaling research, 33 academic references), [`docs/CARF_RSI_ANALYSIS.md`](docs/CARF_RSI_ANALYSIS.md) (RSI deep architecture analysis)

### Phase 18 Concept: Supervised Recursive Refinement (SRR) Hardening

CARF occupies the "bounded self-correction → supervised self-modification" range on the RSI spectrum. Phase 18 closes the 4 gaps identified by the RSI analysis and implements scaling recommendations from the neurosymbolic research evaluation.

### 18A: Drift Detection Service (RSI Gap #1)

**Problem:** No mechanism monitors whether the memory→router feedback loop is gradually shifting routing patterns in unintended directions. The 0.03 weight limit on memory hints mitigates but does not eliminate drift risk.

**Design:**
- Track domain routing distribution over rolling windows (hourly/daily/weekly)
- Compute KL-divergence between current and baseline routing distributions
- Alert on statistically significant shifts (configurable threshold, default p<0.05)
- Expose via `/monitoring/drift` API endpoint and Developer View panel
- Store drift metrics in agent memory for cross-session tracking

**Benchmark Impact:** New hypothesis H40 (drift detection sensitivity) — system must detect >5% routing shift within 100 queries. No impact on existing H0-H39.

**Data Layer Impact:** Reads from `experience_buffer.py` domain patterns and `agent_memory.py` JSONL store. Additive — no schema changes to EpistemicState.

**Integration Impact:** New MCP tool `monitor_drift` for agentic monitoring. New frontend panel in Developer View.

### 18B: Automated Bias Auditing (RSI Gap #2)

**Problem:** No system-level bias audit across accumulated agent memory. If memory accumulates biased past analyses, memory hints could gradually bias routing.

**Design:**
- Periodic scan of agent memory corpus for domain distribution skew
- Cross-reference memory quality scores against domain to detect systematic quality differences
- Statistical tests for representation bias (chi-squared test on domain frequencies vs expected)
- Extend existing H36 fairness benchmark with memory-level bias metrics
- Report via `/monitoring/bias-audit` endpoint and Governance View

**Benchmark Impact:** Extends H36 (fairness). New hypothesis H41 (memory bias detection). No regression on existing benchmarks.

**Data Layer Impact:** Reads from `agent_memory.py` store. Additive analysis layer.

**Persona Alignment:** Executive View gets bias audit KPI cards. Developer View gets statistical breakdowns. Analyst View gets per-query bias context.

### 18C: Plateau Detection in Retraining (RSI Gap #3)

**Problem:** Router retraining pipeline lacks convergence monitoring. No mechanism to detect when successive retraining cycles produce diminishing returns or overfit to feedback.

**Design:**
- Track accuracy delta between successive retraining epochs
- Implement early stopping when improvement < configurable epsilon (default 0.5%)
- Log retraining history with accuracy curves
- Alert when plateau detected (diminishing returns) or regression detected (accuracy drop)
- Expose via `/feedback/retraining-convergence` endpoint

**Benchmark Impact:** New hypothesis H42 (plateau detection sensitivity). No regression on existing H0-H39.

**Data Layer Impact:** Extends `router_retraining_service.py` with convergence tracking. Additive.

### 18D: ChimeraOracle StateGraph Integration (RSI Gap #4 / AP-7)

**Problem:** ChimeraOracle accessible only via standalone `/oracle/predict` endpoint, bypassing Guardian enforcement, audit trail, and evaluation. This is antipattern AP-7 (Isolated Services in Cognitive Mesh).

**Design:**
- Add `chimera_fast_path` node to LangGraph StateGraph
- Router conditional edge: if Complicated domain + pre-trained model available + confidence > 0.9 → fast path
- Guardian evaluation on ChimeraOracle output (same as causal analyst)
- EvaluationService scoring at chimera node (hallucination, relevancy)
- Fallback to full causal analyst if ChimeraOracle confidence < threshold

**Benchmark Impact:** H8 (ChimeraOracle speed) now measured within workflow context. New hypothesis H43 (fast-path Guardian enforcement). May slightly increase H8 latency due to Guardian overhead but ensures safety compliance.

**Data Layer Impact:** Modifies `graph.py` StateGraph wiring. ChimeraOracle output flows through existing Guardian and Governance nodes.

**E2E Flow Impact:**
```
Router → [if fast-path eligible] → ChimeraOracle → Guardian → Governance → END
       → [else]                  → Causal Analyst → Guardian → Governance → END
```

### 18E: Scalable Inference Strategy (Research Recommendation)

**Problem:** Bayesian inference via MCMC is computationally intensive for real-time enterprise use. Causal DAG discovery is NP-hard and scales super-exponentially.

**Design:**
- Implement configurable inference mode: `full` (MCMC), `approximate` (variational), `cached` (pre-computed)
- Add inference mode selection to deployment profiles (research=full, staging=approximate, production=cached)
- Cache posterior distributions for repeated query patterns
- Document BCD Nets integration path for future variational DAG learning

**Benchmark Impact:** New hypothesis H44 (approximate inference fidelity vs full MCMC). Existing H2 (Bayesian calibration) must pass in all inference modes.

**Data Layer Impact:** Extends `bayesian.py` with mode parameter. Cache layer for posterior distributions.

### 18F: Multi-Agent Collaborative Discovery (Research Recommendation)

**Problem:** Single-agent causal discovery struggles with high-dimensional variable spaces (combinatorial explosion).

**Design:**
- Architect agent specialization: variable subset agents, algorithm selection agents, validation agents
- Collaborative graph structure voting via consensus mechanism
- Distributed hypothesis testing across agent pool
- Integration via existing LangGraph cognitive mesh extension

**Benchmark Impact:** New hypothesis H45 (multi-agent discovery accuracy vs single-agent on >20 variables). Long-term research track.

**Persona Alignment:** Developer View shows agent collaboration trace. Executive View shows discovery efficiency metrics.

### Phase 18 Implementation Priority

| Component | Priority | Effort | Safety Impact | Scaling Impact |
|-----------|----------|--------|---------------|----------------|
| 18D ChimeraOracle Integration | P0 | Medium | High (closes AP-7) | Medium |
| 18A Drift Detection | P1 | Low | High (RSI safety) | Low |
| 18C Plateau Detection | P1 | Low | Medium | Low |
| 18B Bias Auditing | P2 | Medium | High (fairness) | Low |
| 18E Scalable Inference | P2 | High | Low | High |
| 18F Multi-Agent Discovery | P3 | Very High | Low | Very High |

---

## Test Coverage

```
Total Tests: 1,130+ backend + 235+ frontend = 1,365+ passing
Overall Coverage: 68%+
Python Lines: 12,000+ lines
React Components: 59 components (+MonitoringPanel, AuthGuard, LoginPage)
Backend Unit Tests: 58+ test files (Phase 18: test_phase18_improvements, test_monitoring_api)
Frontend Tests: 240+ tests (23+ test files, all passing)
E2E Tests: 20 tests (Data Quality: 6/6 pass, API: varies by network)
Benchmark Scripts: 13 technical + 1 e2e + 1 baseline + 1 report generator (45 hypotheses)
TLA+ Specs: 2 (StateGraph, EscalationProtocol)
```

## Feature Completion Matrix

### Core Infrastructure

| Feature | Status | Coverage | Notes |
|---------|--------|----------|-------|
| FastAPI Backend | Complete | 44% | 45+ endpoints, full CRUD |
| LangGraph Orchestration | Complete | 56% | StateGraph with conditional routing |
| Cynefin Router | Complete | 59% | DistilBERT + Shannon entropy |
| Causal Engine | Complete | 26% | DoWhy integration, LLM fallback |
| Bayesian Engine | Complete | 30% | PyMC integration, LLM fallback |
| Guardian Layer | Complete | 63% | OPA + policy enforcement |
| Human Layer | Complete | 28% | HumanLayer SDK integration |
| **ChimeraOracle** | **NEW** | 89% | Fast CausalForestDML predictions |
| **Governance Service** | **NEW** | 96% | MAP-PRICE-RESOLVE orchestrator |
| **Federated Policy Service** | **NEW** | 95% | Domain-owner policy management, conflict detection |
| **Cost Intelligence Service** | **NEW** | 96% | LLM token pricing, ROI, cost breakdown |
| **Governance Graph Service** | **NEW** | 32% | Neo4j triple store (graceful degradation) |
| **Governance API Router** | **NEW** | — | 18 endpoints under `/governance/*` |
| **Causal World Model** | **NEW (P17)** | — | SCMs with do-calculus, forward simulation, OLS learning from data |
| **Counterfactual Engine** | **NEW (P17)** | — | Level-3 Pearl reasoning, scenario comparison, but-for attribution |
| **Neurosymbolic Engine** | **NEW (P17)** | — | Neural-symbolic loop: LLM fact extraction + forward-chaining + shortcut detection |
| **H-Neuron Sentinel** | **NEW (P17)** | — | Hallucination detection via weighted signal fusion (proxy mode) |
| **Cloud SQL Database** | **NEW (P17)** | — | SQLite/PostgreSQL factory, Cloud Run ADC support |
| **Firebase Auth** | **NEW (P17)** | — | JWT middleware, lazy Firebase Admin SDK init |
| **Drift Detector** | **NEW (P18)** | — | KL-divergence monitoring, rolling windows, alert thresholds |
| **Bias Auditor** | **NEW (P18)** | — | Chi-squared tests, quality disparity, verdict disparity |
| **Plateau Detection** | **NEW (P18)** | — | Convergence monitoring, regression alerts, early stopping |
| **ChimeraOracle Fast-Path** | **NEW (P18)** | — | StateGraph integration, Guardian enforcement, fallback |
| **Monitoring API** | **NEW (P18)** | — | 7 endpoints under `/monitoring/*` |

### React Frontend (carf-cockpit)

| Component | Status | Notes |
|-----------|--------|-------|
| DashboardLayout | **ENHANCED** | Three-view architecture, renamed section headers, simulation access, export |
| CynefinRouter | Complete | Full transparency on classification + method impact |
| CausalDAG | Complete | React Flow visualization |
| BayesianPanel | Complete | Uncertainty quantification display |
| GuardianPanel | **ENHANCED** | Informative empty state, policy context, audit trail link |
| SimulationArena | Complete | Enhanced with method toggles and benchmarks |
| ExecutiveKPIPanel | **ENHANCED** | Adaptive charts (Cards/Bar/Pie), action items, roadmap, export |
| EscalationModal | Complete | Channel config, trigger explanation, manual review |
| DataOnboardingWizard | Complete | Sample data, auto-suggestions, guided flow |
| DeveloperView | **ENHANCED** | Real telemetry, DeepEval drill-downs, agent flow chart, improvement modal |
| IntelligentChatTab | **ENHANCED** | Markdown rendering, panel links via MarkdownRenderer |
| SetupWizard | Complete | LLM provider configuration |
| **MarkdownRenderer** | **NEW** | Shared markdown rendering (react-markdown + remark-gfm) |
| **AgentFlowChart** | **NEW** | ReactFlow agent activation visualization for Developer view |
| StrategyComparisonPanel | Complete | Fast Oracle vs DoWhy comparison |
| ExperienceBufferPanel | Complete | Learning buffer for Developer view |
| DomainVisualization | Complete | All 5 Cynefin domain views (Clear/Complicated/Complex/Chaotic/Disorder) |
| PlotlyChart | Complete | Unified Plotly.js wrapper (waterfall, radar, sankey, gauge) |
| **TransparencyPanel** | **ENHANCED** | Data modal with dataset info, flowchart lineage, quality drill-downs with baselines |
| **ConversationalResponse** | **ENHANCED** | Markdown rendering via MarkdownRenderer |
| **ExecutionTrace** | **ENHANCED** | Fixed 0ms bug, confidence tooltips |
| **SensitivityPlot** | **ENHANCED** | Dejargonized, recharts, expandable modal, robustness interpretation |
| **InterventionSimulator** | **ENHANCED** | Multi-parameter What-If with confounders, save scenario |
| **CausalAnalysisCard** | **ENHANCED** | Follow-up question generation |
| **WalkthroughManager** | **ENHANCED** | 3 new tracks (Causal Deep Dive, Simulations, Developer Debugging) |
| **AnalysisHistoryPanel** | **ENHANCED** | OOM crash fix, capped at 50, lazy-load, cloud-backed history |
| **AuthGuard** | **NEW (P17)** | Firebase auth gatekeeper, skips in local dev |
| **LoginPage** | **NEW (P17)** | Google sign-in UI with branded gradient |
| **MonitoringPanel** | **NEW (P18)** | 3-tab panel: Drift Monitor, Bias Audit, Convergence — integrated into Developer + Governance views |
| InsightsPanel | Complete | Action items, effort badges, roadmap stepper |
| **GovernanceView** | **NEW** | 4-tab layout: Spec Map, Cost, Policy, Compliance |
| **SpecMapTab** | **NEW** | ReactFlow domain node visualization |
| **CostIntelligenceTab** | **NEW** | KPI cards + recharts cost breakdown |
| **PolicyFederationTab** | **NEW** | Domain sidebar, policy cards, conflict panel |
| **ComplianceAuditTab** | **NEW** | Framework selector, score gauge, article accordion |

### React Hooks

| Hook | Status | Notes |
|------|--------|-------|
| useCarfApi | Complete | Main API hook |
| useTheme | Complete | Dark mode toggle |
| useProactiveHighlight | Complete | Auto-highlight relevant panels |
| useVisualizationConfig | Complete | Cynefin viz config with caching |
| **useAuth** | **NEW (P17)** | Firebase auth state, sign-in/out, JWT token retrieval |
| **useMonitoring** | **NEW (P18)** | Drift/bias/convergence status with polling and auto-refresh |

### New Services (Phase 13)

| Service | Status | Notes |
|---------|--------|-------|
| **SmartReflectorService** | **NEW** | Hybrid heuristic + LLM repair for policy violations |
| **ExperienceBuffer** | **UPGRADED** | Sentence-transformer embeddings with TF-IDF fallback |
| **Library API** | **NEW** | Notebook-friendly wrappers for all CARF services |
| **Router Retraining** | **NEW** | Extract domain overrides for DistilBERT fine-tuning |
| **Reflector Benchmark** | **NEW** | 5-scenario self-correction benchmark |
| **Resiliency Benchmark** | **NEW** | 6-test circuit breaker & chaos benchmark |

### API Endpoints

| Category | Endpoints | Status |
|----------|-----------|--------|
| Health & Config | 5 | Complete |
| Query Processing | 2 | Complete |
| Dataset Management | 5 | Complete (+detect-schema) |
| Scenario Management | 4 | Complete (+POST /scenarios/load) |
| Simulation | 2 | Complete |
| Chat & Explanations | 7 | Complete |
| Developer Tools | 3 | Complete |
| Human-in-the-Loop | 3 | Complete |
| Benchmarking | 3 | Complete |
| Oracle | 3 | Complete - train, predict, list models |
| **Agent** | **1** | **NEW** - suggest-improvements |
| **Visualization Config** | **2** | **NEW** - `/api/visualization-config`, `/config/visualization` |
| **Feedback** | **5** | `/feedback`, `/feedback/summary`, `/feedback/domain-overrides`, `/feedback/export`, `/feedback/retraining-readiness` |
| **Enhanced Insights** | **1** | **NEW** - `/insights/enhanced` (action items + roadmap) |
| **Experience Buffer** | **2** | **NEW** - `/experience/similar`, `/experience/patterns` |
| **Governance** | **18** | `/governance/domains`, `/governance/policies`, `/governance/conflicts`, `/governance/compliance/{framework}`, `/governance/cost/*`, `/governance/audit`, `/governance/health` |
| **World Model** | **10** | **NEW (P17)** — `/world-model/counterfactual`, `/counterfactual/compare`, `/counterfactual/attribute`, `/simulate`, `/neurosymbolic/reason`, `/neurosymbolic/validate`, `/h-neuron/status`, `/h-neuron/assess`, `/retrieve/neurosymbolic`, `/analyze-deep` |
| **History** | **3** | **NEW (P17)** — `POST /history`, `GET /history`, `DELETE /history/{id}` (per-user, cloud-backed) |
| **Monitoring** | **7** | **NEW (P18)** — `/monitoring/drift`, `/monitoring/drift/history`, `/monitoring/drift/reset`, `/monitoring/bias-audit`, `/monitoring/convergence`, `/monitoring/convergence/record`, `/monitoring/status` |

---

## Recent Improvements

### Phase 18: SRR Hardening & Operational Intelligence (2026-03-16)

Closes all 4 RSI safety gaps identified by architecture review. Implements operational monitoring across all platform views.

**Drift Detection (18A):**
1. **DriftDetector** (`src/services/drift_detector.py`) — KL-divergence monitoring of routing distribution over rolling windows. Baseline established from first 100 observations. Alerts on distributional shift > configurable threshold. Bounded deque for snapshot history.
2. Wired into `run_carf()` pipeline — every query records routing decision automatically.

**Bias Auditing (18B):**
3. **BiasAuditor** (`src/services/bias_auditor.py`) — Chi-squared test on domain representation, quality score disparity analysis, Guardian verdict approval rate disparity. Three-dimensional fairness audit of accumulated agent memory.

**Plateau Detection (18C):**
4. **RouterRetrainingService.check_convergence()** — Detects convergence plateau (<0.5% improvement over 3+ epochs), regression (accuracy drop), and productive improvement. Records accuracy history with timestamps.

**ChimeraOracle StateGraph Integration (18D):**
5. **chimera_fast_path_node** (`src/workflows/graph.py`) — Conditional fast-path in LangGraph StateGraph. Routes Complicated queries with high confidence to ChimeraOracle, with Guardian enforcement on output. Falls back to full causal_analyst on low reliability or drift warning. Closes AP-7 and AP-10.

**Monitoring API (18E):**
6. **Monitoring Router** (`src/api/routers/monitoring.py`) — 7 endpoints under `/monitoring/*` for drift, bias, convergence, and unified status. Registered in `main.py`.

**Frontend Integration (18F):**
7. **MonitoringPanel** (`carf-cockpit/src/components/carf/MonitoringPanel.tsx`) — 3-tab component (Drift, Bias, Convergence) with Recharts visualizations. Integrated into Developer View (Monitoring tab) and Governance View (Monitoring tab).
8. **ExecutiveKPIPanel** — 3 new KPI cards: Routing Drift, Memory Bias, Retraining Health.
9. **TypeScript types** — DriftStatus, BiasReport, ConvergenceStatus, MonitoringStatus interfaces.
10. **apiService.ts** — 6 new monitoring API functions with retry and auth.

**Benchmarks (18G):**
11. **H40** (`benchmarks/technical/monitoring/benchmark_drift_detection.py`) — 5 realistic enterprise scenarios, sensitivity/specificity metrics.
12. **H41** (`benchmarks/technical/monitoring/benchmark_bias_audit.py`) — 5 realistic memory corpus scenarios.
13. **H42** (`benchmarks/technical/monitoring/benchmark_plateau_detection.py`) — 5 real DistilBERT training curve scenarios.
14. **H43** (`benchmarks/technical/monitoring/benchmark_fast_path_guardian.py`) — Guardian enforcement rate validation.

**Testing:**
15. 50+ new backend tests across `test_phase18_improvements.py` and `test_monitoring_api.py`.
16. 8+ new frontend tests for MonitoringPanel.
17. All 1,130+ existing backend tests continue passing — zero regressions.

### Phase 17: Causal World Model, NeSy Engine, Auth & Cloud Deployment (2026-03-14)

Full causal-neurosymbolic reasoning stack, hallucination detection, Firebase authentication, and Cloud SQL deployment layer.

**Causal World Model (17A):**
1. **CausalWorldModelService** (`src/services/causal_world_model.py`) — Structural Causal Models with forward simulation, do-calculus interventions, and Pearl's three-step counterfactual (Abduction → Action → Prediction). Learns structural equations via OLS from data + causal graph. LLM-assisted probabilistic simulation fallback when no data available.
2. **CounterfactualEngine** (`src/services/counterfactual_engine.py`) — Level-3 counterfactual reasoning (Pearl's Ladder). SCM-based reasoning with LLM fallback. But-for causation tests. Multi-scenario comparison with result caching.

**Neurosymbolic Engine (17B):**
3. **NeuralSymbolicReasoner** (`src/services/neurosymbolic_engine.py`) — Tight neural-symbolic integration loop: LLM fact extraction → symbolic forward-chaining → rule validation → shortcut detection. CSL policy rule import, Neo4j graph grounding, violation correction. Confidence computation based on derivation quality.

**H-Neuron Hallucination Sentinel (17C):**
4. **HNeuronSentinel** (`src/services/h_neuron_interceptor.py`) — Mechanistic hallucination detection via weighted signal fusion (DeepEval risk, domain confidence, epistemic uncertainty, reflection count, quality scores). Proxy mode with fusible CARF signals. Environment-based feature flagging. Cynefin domain activation.

**Authentication & Cloud Deployment (17D):**
5. **Firebase Auth** (`src/api/auth.py`) — JWT middleware verifying Authorization Bearer tokens. Lazy Firebase Admin SDK init. Bypasses auth for health/docs/CORS endpoints.
6. **AuthGuard + LoginPage** — React components for Firebase Google sign-in. AuthGuard skips auth when Firebase is not configured (local dev).
7. **useAuth hook** — Manages Firebase auth state, provides signIn/signOut/getToken for API Bearer headers.
8. **Cloud SQL Database** (`src/core/database.py`) — Connection factory supporting SQLite (local) and PostgreSQL (cloud) with transparent placeholder adaptation. Cloud Run ADC support.
9. **History Router** (`src/api/routers/history.py`) — Per-user analysis history (save/list/delete) with user isolation via `request.state.user_id`.
10. **Migration Script** (`scripts/migrate_to_cloud_sql.py`) — One-time SQLite → PostgreSQL migration for datasets, feedback, and history tables.

**State & Types (17E):**
11. **CounterfactualEvidence** + **NeurosymbolicEvidence** models in `src/core/state.py` — State carries full evidence trail from all Phase 17 services.
12. **Frontend types** in `carf-cockpit/src/types/carf.ts` — TypeScript interfaces for all Phase 17 API responses.
13. **apiService.ts** — Auth header helper, Phase 17 endpoint functions, retry logic with exponential backoff.

**Infrastructure:**
14. **Dockerfile** — Updated for cloud deployment.
15. **firebase.json** — Firebase Hosting config serving `carf-cockpit/dist` with SPA rewrites.
16. **Doc reorganization** — Legacy docs moved to `docs/archive/`. 5 new research/architecture docs added.

**Testing:** 60+ new tests across 2 test files (`test_phase17_integration.py`, `test_phase17_world_model.py`) covering H-Neuron proxy mode, NeSy-RAG interconnection, SCM-NeSy integration, end-to-end pipeline coherence, and all individual components.

### Phase 16.7: Currency-Aware Financial Policy Enforcement (2026-02-22)

Completed in this cycle:
1. Add shared currency normalization utility for governance/guardian financial checks.
2. Make Guardian contextual financial limits currency-aware when FX configuration is provided.
3. Make CSL-Core state mapping and evaluation fail-safe for unavailable currency conversion.

### Phase 16.8: Benchmark Metric Extraction Reliability Hardening (2026-02-22)

Completed in this cycle:
1. Removed `or`-based metric fallbacks in report hypothesis evaluation for metrics where `0.0` is a valid value.
2. Added explicit first-non-`None` extraction logic for key benchmark metrics (router, bayesian, counterfactual, healthcare, soak).
3. Added regression tests to ensure zero-valued metrics are treated as evaluated evidence, not missing data.

### Phase 16.6: Governance Semantic Graph + Agentic Navigation (2026-02-22)

Completed in this cycle:
1. Added `/governance/semantic-graph` endpoint with typed graph payload (domain/policy/concept nodes + conflict/triple edges + explainability).
2. Added Governance cockpit `Semantic Graph` tab for policy conflict topology and MAP triple visibility.
3. Extended agentic chat navigation to open governance semantic graph directly from natural language and `/goto` routing.

### Phase 16.5: Evidence Gate CLI for CI/Release (2026-02-22)

Completed in this cycle:
1. Added `benchmarks/reports/check_result_evidence.py` for strict evidence gating with configurable thresholds.
2. Added `evaluate_evidence_gate(...)` in `benchmarks/reports/realism.py` to provide deterministic pass/fail criteria and actionable reasons.
3. Added unit tests for evidence gate behavior.
4. Updated benchmark/evaluation/root docs with evidence gate command usage.

### Phase 16.4: Benchmark Provenance Auto-Enrichment (2026-02-22)

Completed in this cycle:
1. Added `finalize_benchmark_report(...)` in `benchmarks/__init__.py` to enforce timestamp, benchmark config, dataset context, sample context, and provenance fields.
2. Applied provenance auto-enrichment to benchmark runners across core, governance, security, compliance, sustainability, UX, industry, performance, resiliency, e2e, and baseline scripts.
3. Updated baseline unified summary path (`baseline_results.summary.json`) to include standardized provenance metadata.
4. Added unit test coverage for benchmark metadata enrichment.

### Phase 16.3: Benchmark Evidence Provenance Enforcement (2026-02-22)

Completed in this cycle:
1. Added result-artifact evidence validation (`validate_result_evidence`) for all loaded benchmark outputs.
2. Integrated evidence metrics into unified reports (`evidence_score_avg`, `strong_evidence_ratio`, `low_evidence_sources`).
3. Tightened realism quality gate to block acceptance when evidence quality is insufficient.
4. Added unit tests for realism/evidence gate behavior.

### Phase 16.2: Governance Extraction + Absolute Readiness Hardening (2026-02-22)

Completed in this cycle:
1. Hardened `/governance/policies/extract` with retry/backoff (`tenacity`) and non-blocking LLM execution (`asyncio.to_thread`) to remove async blocking I/O risk.
2. Added structured explainability outputs for extracted governance rules (`why_this`, `how_confident`, `based_on`, rule-level confidence/evidence/rationale).
3. Added realism hardening metrics to benchmark report scoring (`provenance_ratio`, `production_proxy_ratio`, `synthetic_profile_ratio`) and strict gate-reason reporting.
4. Added conservative pass-rate confidence bound (`pass_rate_lower_95ci`) and `absolute_readiness_index` to benchmark summaries.

### Phase 16.1: Benchmark + Agentic UX Alignment (2026-02-22)

Completed in this cycle:
1. Added benchmark realism/reliability/feasibility quality gate to unified reporting (`benchmarks/reports/realism.py`, `benchmarks/reports/realism_manifest.json`).
2. Integrated realism metrics into report summary + text output (`benchmarks/reports/generate_report.py`).
3. Updated benchmark/evaluation/root docs for 39-hypothesis suite and realism gate policy.
4. Added natural-language chat UI actions for analyst/developer/executive/governance navigation, data onboarding launch, and latest-analysis simulation compare.

### Phase 16: Orchestration Governance (OG) Integration (2026-02-22)

Complete MAP-PRICE-RESOLVE-AUDIT framework integration, transforming CARF from a "Complex Decision Tool" to a "Computable Enterprise Brain" — governed, auditable, and strategically aligned.

**Critical Design Principle:** Governance is a plug-in, not a requirement. Feature-flagged via `GOVERNANCE_ENABLED=true/false` (default `false`). When disabled: zero imports, zero service init, zero performance overhead.

**Backend Foundation (16A):**
1. **Governance Models** (`src/core/governance_models.py`) — 15 Pydantic models: ContextTriple, GovernanceDomain, FederatedPolicy, PolicyConflict, CostBreakdown, ComplianceScore, GovernanceAuditEntry, etc.
2. **EpistemicState Extension** — 2 additive Optional fields: `session_triples`, `cost_breakdown` (zero impact on existing tests)
3. **Governance Service** — Central MAP-PRICE-RESOLVE orchestrator with entity extraction, domain keyword matching, compliance scoring for EU AI Act/CSRD/GDPR/ISO 27001
4. **Federated Policy Service** — Domain-owner policy management from `config/federated_policies/` YAML files, cross-domain conflict detection
5. **Governance Graph Service** — Neo4j triple store with graceful degradation to in-memory
6. **LangGraph Integration** — Governance node wired between Guardian(APPROVED) and END, non-blocking (try/except)
7. **API Router** — 18 endpoints under `/governance/*` (domains, policies, conflicts, compliance, cost, audit, health)

**Cost Intelligence (16B):**
8. **Cost Intelligence Service** — Actual LLM token pricing (DeepSeek $0.14/$0.28, OpenAI $3/$6, Anthropic $3/$15, Ollama $0), risk exposure, opportunity cost, full breakdown
9. **Token Instrumentation** — Thread-local accumulators in `llm.py` for real token usage tracking
10. **Kafka Audit Extension** — 4 new governance fields on KafkaAuditEvent

**Frontend Governance View (16C):**
11. **GovernanceView** — 4-tab layout: Spec Map, Cost Intelligence, Policy Federation, Compliance Audit
12. **SpecMapTab** — ReactFlow domain node visualization (reuses AgentFlowChart pattern)
13. **CostIntelligenceTab** — 4 KPI cards + recharts BarChart/PieChart (reuses ExecutiveKPIPanel pattern)
14. **PolicyFederationTab** — Domain sidebar, policy cards, conflict panel with resolve buttons
15. **ComplianceAuditTab** — Framework selector, score gauge, article accordion, audit timeline
16. **DashboardLayout** — Added governance view tab
17. **TransparencyPanel** — Added cost tab for token usage

**Config & Use Cases (16D):**
18. **5 Federated Policy YAML files** — Procurement (3 rules), Sustainability (4 rules), Security (3 rules), Legal (3 rules), Finance (3 rules)
19. **2 Demo Payloads** — CSRD ESG Reporting, Supply Chain Governance

**Benchmarks (16E):**
20. **Governance Benchmark** (`benchmarks/technical/governance/benchmark_governance.py`) — Tests all 4 pillars: MAP accuracy, PRICE precision, RESOLVE detection, AUDIT validity, plus governance node latency and feature flag overhead
21. **3 New Hypotheses** — H10 (MAP >= 70%), H11 (PRICE >= 95%), H12 (Latency P95 < 50ms) — all passing
22. **Report Generator Updated** — 12 hypotheses total, Grade A (11/12 passed)

**Results:** 923 backend tests (0 failures), 235 frontend tests (all passing), 72% coverage, Grade A (11/12 hypotheses), governance node P95 < 1ms, zero overhead when disabled.

### Phase 15: CYNEPIC UIX Rehaul (2026-02-21)

Comprehensive 7-phase frontend overhaul addressing actionability, data explainability, and view differentiation. Core principle: every view should answer "So what?" and "Now what?".

**Bug Fixes & Markdown (Phase 1):**
1. **MarkdownRenderer** — New shared component using `react-markdown` + `remark-gfm` for proper markdown in chat and response panels (replaces raw `whitespace-pre-wrap`)
2. **ExecutionTrace 0ms fix** — Frontend always shows duration (`< 1ms` when 0), backend `graph.py` now times each node with `time.perf_counter()`
3. **"View Data" routing fix** — Opens data modal instead of onboarding wizard
4. **Confidence tooltips** — ExecutionTrace badges explain what high/medium/low means on hover

**Transparency & Explainability (Phase 2):**
5. **DataModal redesign** — Shows dataset info, column types, variable roles, data quality indicators
6. **Flowchart lineage** — Replaced bullet points with vertical flow: Input → Router → Agent → Guardian → Output
7. **Quality drill-downs** — Clickable score bars with industry baselines and plain-English interpretations
8. **Reliability explanations** — Per-factor Cynefin-aware interpretations (e.g., "highly confident in complicated domain")

**Guardian & Causal Actionability (Phase 3):**
9. **Guardian empty state** — Shows active policy count and thresholds even with no decision
10. **Policy contextualization** — Per-policy descriptions from `/guardian/policies` endpoint
11. **"Ask Follow-Up"** — CausalAnalysisCard generates contextual follow-up questions wired to chat
12. **Section header renames** — "Causal DAG" → "Cause & Effect Map", "Guardian Panel" → "Safety & Compliance Check", etc.

**Sensitivity & Simulator (Phase 4):**
13. **SensitivityPlot dejargonized** — Plain English axes, colored Robust/Fragile zones, expandable modal, robustness interpretation
14. **Multi-parameter What-If** — Treatment + confounder sliders, combined prediction, "Save Scenario", strongest effect highlight
15. **Confounders wired** — Causal result confounders passed to InterventionSimulator

**Developer View (Phase 5):**
16. **AgentFlowChart** — ReactFlow visualization of agent activation sequence with click-to-expand
17. **Real telemetry** — Computed from actual system state instead of hardcoded values
18. **ImprovementModal** — Proper modal replacing `prompt()` dialog, with context pre-population
19. **DeepEval drill-downs** — Clickable metrics with Cynefin-aware recommendations

**Executive View (Phase 6):**
20. **Adaptive charts** — KPI Cards / Bar Chart / Pie Chart with auto-detection and user toggle
21. **Enhanced insights** — Action items as prioritized checklist (Quick Win / Medium Effort / Strategic)
22. **Export Report** — One-click structured summary export

**Proactive UIX (Phase 7):**
23. **useProactiveHighlight hook** — Automatically highlights relevant panels based on query results
24. **3 new walkthrough tracks** — "Causal Analysis Deep Dive", "Running Simulations", "Developer Debugging"
25. **OOM crash fix** — History capped at 50, lightweight summaries in localStorage, lazy-load

**Results:** 201 frontend tests (17 files, all passing), 0 new TypeScript errors from changes, production build succeeds. Backend 737+ tests unaffected (only additive timing change in graph.py).

### Phase 14: Benchmark Gap Closure (2026-02-20)

5 surgical fixes to close remaining SOTA evaluation gaps:

1. **Chaotic Escalation Fix** — Added `CHAOTIC` domain to `should_escalate_to_human()` in `src/core/state.py`. Circuit breaker bypasses Guardian, so chaotic queries now correctly trigger escalation. (3 E2E scenarios fixed)
2. **E2E Data Format Fix** — `benchmark_e2e.py` now wires `benchmark_data` into `causal_estimation` config (`{data, treatment, outcome, covariates}`) for the causal engine. (5 complicated E2E scenarios fixed)
3. **Router Causal Language Boost** — Added `_apply_causal_language_boost()` to `CynefinRouter` that overrides Complex → Complicated when explicit causal phrases are detected. (3 misclassified queries fixed, 100% Complicated routing accuracy)
4. **ChimeraOracle Training Data** — New `scripts/generate_oracle_training_data.py` generates 3 production-grade datasets (benchmark_linear/1000 rows, supply_chain_benchmark/800, healthcare_benchmark/800) and trains CausalForestDML models. H8 now passes.
5. **Experience Buffer Upgrade** — Upgraded from TF-IDF to sentence-transformers (all-MiniLM-L6-v2) with graceful TF-IDF fallback. Zero API changes. Added `embeddings` optional dependency group to `pyproject.toml`.

**Results:** 737 tests passing (12 new for causal boost + 1 for similarity backend), Grade A (8/9 hypotheses — H3 Guardian detection at 67% is the only FAIL, a CSL rule gap). Router: 98% accuracy (Complicated 100%). E2E: 11/13 (84.6%). ChimeraOracle: 32.7x speed, 3.4% accuracy loss (H8 PASS).

### Platform Hardening & Feedback Loop (2026-02-15)

#### Feedback API (Closed-Loop Learning)
1. **Feedback router** (`src/api/routers/feedback.py`) — POST `/feedback`, GET `/feedback/summary`, `/feedback/domain-overrides`, `/feedback/export`
2. **DeveloperView.tsx** feedback buttons now POST to real API (was `console.log` only)
3. **apiService.ts** — `submitFeedback()` and `getFeedbackSummary()` functions added
4. **Domain overrides** tracked separately for Router retraining pipeline

#### Antipattern Documentation
5. **AGENTS.md** — 8 antipatterns documented (AP-1 through AP-8): hardcoded values, mock data, blocking I/O, unbounded collections, currency-blind comparisons, silent null returns, isolated services, test mode leakage

#### Testing & Data Generation
6. **`scripts/generate_all_scenario_data.py`** — Generates 8 datasets (10,000+ rows total) covering all 5 Cynefin domains
7. **New datasets**: `market_uncertainty.csv` (Complex/Bayesian), `crisis_response.csv` (Chaotic/Circuit Breaker)
8. **`docs/UIX_TESTING_WALKTHROUGH.md`** — Comprehensive walkthrough with 8 test suites (A-H), curl commands, verification checklists

#### Remaining Gaps (Documented, Not Yet Implemented)
- ChimeraOracle not wired into LangGraph StateGraph (standalone API only)
- LightRAG / Vector Store (no implementation)
- Guardian currency-aware comparisons
- Router retraining pipeline from feedback data

### UIX & Data Visualization Phase (2026-02-14)

#### Phase A: Domain View Completion
1. **Wired ComplicatedDomainView** into DomainVisualization switch — expert analysis with causal effect summary, refutation stats, Deep Analysis / Sensitivity Check actions
2. **Wired ComplexDomainView** into DomainVisualization switch — uncertainty exploration with epistemic/aleatoric breakdown bar, recommended probes, Run Probe / Explore Scenarios actions
3. **Removed duplicate ExecutiveKPIPanel** from executive view — was rendering twice, now single instance under Analysis Board
4. **Connected causalResult and bayesianResult props** through DashboardLayout to DomainVisualization

#### Phase B: Backend Visualization Config
5. **CynefinVizConfig model** added to visualization_engine.py — domain-specific chart types, color schemes, interaction modes, and recommended panels for all 5 Cynefin domains
6. **GET /api/visualization-config endpoint** — returns combined domain + context visualization configuration
7. **getVisualizationConfig()** API function in apiService.ts with typed interfaces
8. **useVisualizationConfig hook** — React hook with in-memory caching, offline fallbacks, and error resilience

#### Phase C: Plotly.js Integration
9. **PlotlyChart.tsx** — unified Plotly.js wrapper supporting waterfall (causal effects), radar (domain scores), sankey (confounder flows), and gauge (KPI scoring) with dark mode support
10. **react-plotly.js** dependency installed with TypeScript types

#### Phase D: Test Coverage
11. **test_cynefin_viz_config.py** — 11 backend tests (all domains, fallback, case insensitivity, panel recommendations)
12. **DomainVisualization.test.tsx** — 11 component tests (all 5 domain renders, causal effect display, uncertainty bar, action callbacks)
13. **useVisualizationConfig.test.ts** — 4 hook tests (null domain, API fetch, error fallback, caching)
14. **All 65 frontend tests passing**, 0 TypeScript errors

### Bug Fixes (2026-02-01)
1. **Fixed import error** - Removed invalid `visualization_engine` import in main.py
2. **Added POST `/scenarios/load` endpoint** - For frontend scenario loading compatibility
3. **Lowered router confidence threshold** - From 0.85 to 0.70 to prevent false Disorder routing
4. **Fixed E2E test expectations** - Tests now accept wider domain classifications
5. **Increased test timeouts** - From 30s to 60s for LLM-dependent tests
6. **Schema detection endpoint** - `/data/detect-schema` working with file uploads
7. **AI suggestions endpoint** - `/agent/suggest-improvements` returning contextual prompts

### Completed (2026-01-31)
1. Backend schema detection in onboarding wizard with local fallback
2. AI suggestions filtering for items without actions
3. Schema detector ID heuristic fixes
4. Frontend TypeScript build errors resolved

### CHIMEPIC Phase 1 Integration
1. **ChimeraOracleEngine** (`src/services/chimera_oracle.py`) - Fast causal predictions
2. Oracle API endpoints (`/oracle/train`, `/oracle/predict`, `/oracle/models`)
3. **Reflector auto-repair logic** - Fixes budget/threshold/approval violations
4. **StrategyComparisonPanel** - Compare Fast Oracle vs DoWhy analysis
5. **ExperienceBufferPanel** - Learning buffer tracking in Developer view
6. **Executive Effect Summary** - Simplified causal results with confidence %

### Backend Fixes (Previous)
1. Removed duplicate `/simulations/run` and `/simulations/compare` endpoints
2. Fixed test failures in `test_api.py` (camelCase alignment)
3. Fixed `test_log_rotation` and `test_get_state` in developer tests
4. Removed debug print statements from main.py
5. Updated docstring to reflect CYNEPIC branding

### Frontend Enhancements

#### Executive View
- New `ExecutiveKPIPanel` component with:
  - Filterable KPI cards by category (confidence, quality, compliance, performance)
  - Status indicators and trend arrows
  - Executive summary text generation
  - Drill-down capability to analyst view

#### Human-in-the-Loop
- Enhanced `EscalationModal` with:
  - Trigger explanation panel (why was this escalated?)
  - Notification channel configuration (Slack, Email, Teams, Webhook)
  - Manual intervention request option (always available)
  - Impact preview when toggling methods

#### Cynefin Transparency
- Enhanced `CynefinRouter` with:
  - "How does this affect analysis?" expandable section
  - Method impact configuration for each domain
  - Primary/secondary methods display
  - Guardian policies applied per domain
  - Data requirements and uncertainty handling

#### Simulation Arena
- Enhanced with:
  - Analysis method toggles (Causal, Bayesian, Guardian)
  - Confidence threshold slider
  - Benchmark comparison dropdown (Industry, Historical, Custom)
  - Impact preview when methods disabled
  - Re-run with modified methods button

#### Data Onboarding
- Enhanced `DataOnboardingWizard` with:
  - Sample datasets for first-time users (Churn, Healthcare, Marketing)
  - Auto-detected variable suggestions
  - One-click "Apply all suggestions" button
  - Better guidance and tips

---

## Architecture Layers

```
Layer 1: Cynefin Router (Complexity Classification)
├── DistilBERT classifier + entropy calculation
├── Domain scores visualization
├── Method impact transparency
└── Key indicators extraction

Layer 2: Causal-Bayesian Mesh
├── Complicated → DoWhy/EconML causal inference
├── Complex → PyMC Bayesian inference
├── Clear → Deterministic rules
└── Chaotic → Circuit breaker

Layer 3: Causal World Model (Phase 17)
├── Structural Causal Models (SCMs) with OLS learning
├── Counterfactual Engine (Pearl Level-3)
├── Neurosymbolic Engine (LLM + forward-chaining)
└── H-Neuron Sentinel (hallucination detection)

Layer 4: Guardian (Policy Enforcement)
├── OPA policy evaluation
├── Risk level assessment
├── Human escalation triggers
└── Audit trail logging

Layer 5: Human Layer (Escalation)
├── 3-Point Context notifications
├── Channel configuration
├── Manual intervention requests
└── Resolution tracking

Layer 6: Auth & Cloud (Phase 17)
├── Firebase JWT authentication
├── Cloud SQL (SQLite/PostgreSQL)
├── Per-user analysis history
└── Firebase Hosting (SPA)
```

---

## Configuration

### Required Environment Variables
```bash
LLM_PROVIDER=deepseek       # or "openai"
DEEPSEEK_API_KEY=sk-...     # Required if using DeepSeek
```

### Optional Environment Variables
```bash
OPENAI_API_KEY=sk-...       # If using OpenAI
HUMANLAYER_API_KEY=hl-...   # For human escalation
LANGSMITH_API_KEY=ls-...    # For tracing
NEO4J_URI=bolt://localhost:7687
KAFKA_ENABLED=false
OPA_ENABLED=false
DATABASE_URL=postgresql://...  # Cloud SQL (Phase 17, omit for local SQLite)
GOOGLE_APPLICATION_CREDENTIALS=...  # Cloud Run ADC (Phase 17)
H_NEURON_ENABLED=true       # Enable H-Neuron hallucination sentinel (Phase 17)
```

### Frontend Environment Variables (carf-cockpit/.env.production)
```bash
VITE_API_URL=https://...              # Cloud Run API URL
VITE_FIREBASE_API_KEY=...             # Firebase auth (Phase 17)
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...
```

---

## Running the System

### Backend
```bash
cd projectcarf
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev,causal,bayesian]"
python -m src.main
```

### Frontend (React)
```bash
cd carf-cockpit
npm install
npm run dev
```

### Tests
```bash
pytest tests/ -v --cov=src
```

---

## Known Limitations

1. **Causal/Bayesian Engines**: Use LLM simulation when DoWhy/PyMC not available (graceful degradation)
2. **Neo4j Integration**: Connection pool exists but queries need real database; NeSy graph grounding requires Neo4j
3. **Kafka Audit**: Infrastructure ready but not persisting to real Kafka
4. **Streamlit Dashboard**: Deprecated in favor of React cockpit
5. **ChimeraOracle**: Standalone REST API only — not yet wired into LangGraph StateGraph workflow
6. **LightRAG / Vector Store**: Not implemented — semantic search and cross-session knowledge retrieval missing
7. **FX Coverage Dependency**: Non-USD comparisons require configured `CARF_FX_RATES_JSON`; otherwise Guardian/CSL correctly block cross-currency financial actions
8. **Router Retraining**: Feedback collection works but no automated retraining pipeline yet
9. **H-Neuron Mechanistic Mode**: Proxy mode (signal fusion) active; true mechanistic mode (PyTorch hooks) is placeholder only
10. **Firebase Auth**: Requires Firebase project setup for production; local dev bypasses auth entirely

---

## Historical Decisions

### 2026-02-01
- **Bug Fix Release**: Fixed critical import error blocking backend startup
- Lowered Cynefin Router confidence threshold from 0.85 to 0.70 (LLM typically returns 0.75-0.80)
- Added POST `/scenarios/load` endpoint for frontend compatibility
- Verified end-to-end platform functionality with Scope 3 emissions gold standard use case
- All data quality tests passing (6/6), unit tests (15/17), frontend build successful

### 2026-01-22
- **Phase 10 (Usability Polish)**: Implemented on-the-fly API key configuration.
  - Added `SettingsModal` for dynamic LLM provider switching.
  - Implemented backend hot-reload of LLM clients (`/config/update`).
  - Backend schema alignment and duplicate endpoint cleanup.
  - Enhanced all major frontend components for transparency and UX.

### 2026-01-21
- Production Release Enhancements (Phase A-K) completed
- SetupWizard, Simulation endpoints, EscalationModal, Benchmarking

### 2026-01-20
- Socratic Questioning Flow with Panel Highlighting
- Created questioningFlow.ts config

### 2026-01-17
- Phase 9 Testing Complete (43 tests)
- Phase 8 Scenario Sync Complete
- Phase 7 Backend Services Complete

---

## File Structure

```
projectcarf/
├── src/
│   ├── main.py              # FastAPI entry point
│   ├── api/
│   │   ├── auth.py          # Firebase JWT middleware (Phase 17)
│   │   └── routers/         # 14 API routers (+history, +world_model)
│   ├── core/
│   │   ├── state.py         # Pydantic state schemas (+CounterfactualEvidence, +NeurosymbolicEvidence)
│   │   └── database.py      # SQLite/PostgreSQL connection factory (Phase 17)
│   ├── services/            # 20 services (+causal_world_model, +counterfactual_engine, +neurosymbolic_engine, +h_neuron_interceptor)
│   ├── workflows/           # LangGraph nodes (router, guardian, graph)
│   └── mcp/                 # MCP server (15 cognitive tools)
├── carf-cockpit/
│   └── src/
│       ├── components/carf/ # 56 React components (+AuthGuard, +LoginPage)
│       ├── hooks/           # 5 React hooks (+useAuth)
│       ├── services/        # API client + Firebase config
│       ├── __tests__/       # 17 test files (235 tests)
│       └── types/           # TypeScript types (+Phase 17 interfaces)
├── tests/
│   ├── unit/               # 22+ test files (+test_phase17_integration, +test_phase17_world_model)
│   └── e2e/                # End-to-end tests (gold standard scenarios)
├── scripts/
│   └── migrate_to_cloud_sql.py  # SQLite → PostgreSQL migration (Phase 17)
├── demo/
│   ├── data/               # 8 realistic datasets
│   └── payloads/           # 10 scenario configurations
├── docs/                   # Architecture & research docs
│   └── archive/            # Legacy docs (moved in Phase 17)
└── firebase.json           # Firebase Hosting config (Phase 17)
```

---

## CSL-Core Policy Engine Integration

**Status:** Active — built-in Python evaluator enabled by default

### Architecture
- **Primary Layer:** CSL-Core (Z3 formal verification at compile-time, pure Python evaluation at runtime)
- **Secondary Layer:** OPA/YAML fallback for complex contextual policies
- **Tool Guard:** CSLToolGuard wraps workflow nodes with policy enforcement (enforce/log-only modes)

### Policies (4 core + 1 cross-cutting)
| Policy | Rules | Purpose |
|--------|-------|---------|
| budget_limits | 9 | Financial action limits by role and domain |
| action_gates | 8 | Approval requirements for high-risk actions |
| chimera_guards | 7 | Prediction safety bounds for ChimeraOracle |
| data_access | 6 | PII, encryption, and data residency rules |
| cross_cutting | 5 | Cross-domain rules spanning multiple areas |

### API Endpoints
- `GET /csl/status` — Engine status and loaded policies
- `GET /csl/policies` — List all policies with rules
- `POST /csl/policies/{name}/rules` — Add rule (supports natural language)
- `PUT /csl/policies/{name}/rules/{rule_name}` — Update rule constraints
- `DELETE /csl/policies/{name}/rules/{rule_name}` — Remove rule
- `POST /csl/evaluate` — Test-evaluate against sample context
- `POST /csl/reload` — Hot-reload policies without restart
