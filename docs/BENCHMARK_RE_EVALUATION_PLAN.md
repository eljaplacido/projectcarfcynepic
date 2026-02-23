# CARF Benchmark Re-Evaluation & Expansion Plan

**Date**: 2026-02-22
**Current Grade**: A (8/9 hypotheses, 737 unit tests, 11/13 E2E scenarios)
**Objective**: Close existing gaps, add governance benchmarks, expand to industry/security/compliance/sustainability/UX dimensions, and include raw-LLM-comparison benchmarks that researchers and enterprise buyers expect.

---

## Table of Contents

1. [Current State Assessment](#1-current-state-assessment)
2. [Gap Analysis: What's Missing](#2-gap-analysis-whats-missing)
3. [New Benchmark Categories](#3-new-benchmark-categories)
   - 3A. Governance Extension Benchmarks (Phase 16+)
   - 3B. Raw LLM Delta Benchmarks (Researcher Expectations)
   - 3C. Security & Adversarial Benchmarks
   - 3D. Compliance & Fairness Benchmarks
   - 3E. Sustainability & Green AI Benchmarks
   - 3F. UX/UIX Benchmarks
   - 3G. Industry-Specific Use Case Benchmarks
   - 3H. Reliability & Operational Benchmarks
4. [Improvements to Existing Benchmarks](#4-improvements-to-existing-benchmarks)
5. [Data Acquisition Strategy](#5-data-acquisition-strategy)
6. [Execution Plan & Priority Tiers](#6-execution-plan--priority-tiers)
7. [Updated Hypothesis Table](#7-updated-hypothesis-table)

---

## 1. Current State Assessment

### What We Have (11 Hypotheses, Grade A)

| # | Benchmark | Status | Gap |
|---|-----------|--------|-----|
| H0 | Router Classification (F1=0.98, 50 queries) | PASS | Small test set; no adversarial inputs |
| H1 | Causal ATE Accuracy (MSE 1.19 vs 1,355 baseline) | PASS | Synthetic DGPs only; no real-world validation |
| H2 | Bayesian Calibration (100%, 8/8 scenarios) | PASS | No multi-dimensional posteriors tested |
| H3 | Guardian Violation Detection (67%) | **FAIL** | Missing CSL rule for low-confidence actions |
| H4 | Guardian Determinism (100%) | PASS | Only 5 test cases x5 repeats |
| H5 | EU AI Act Compliance (100%, 6 articles) | PASS | Self-assessed; needs external audit framework |
| H6 | Latency Overhead (3.5x) | PASS | No concurrent load testing |
| H7 | Hallucination Reduction (100%) | PASS | Only 5 claims tested; needs FActScore/HaluEval scale |
| H8 | ChimeraOracle Speed (32.7x, 3.4% loss) | PASS | Single scenario; no drift testing |
| H9 | Memory Stability (0.21% growth) | PASS | 50 queries only; needs long-running soak test |
| H10 | Reflector Self-Correction (80%) | PASS | 5 scenarios; unknown violation handling weak |
| H11 | Resiliency (6/6 tests) | PASS | No multi-component cascade failures |

### What We DON'T Have

- **Zero governance benchmarks** (Phase 16+ features untested at benchmark level)
- **Zero security benchmarks** (no prompt injection, adversarial, or red team tests)
- **Zero fairness/bias benchmarks** (no demographic parity testing)
- **Zero UX benchmarks** (no SUS, no task completion measurement)
- **Zero sustainability metrics** (no energy/carbon measurement)
- **No raw-LLM-comparison benchmarks** that researchers expect (MMLU delta, CounterBench, tau-bench, GAIA)
- **No cross-LLM consistency testing** (only tested with DeepSeek)
- **Hallucination testing at trivial scale** (5 claims; needs 100+)
- **No concurrent/load testing** (latency only measured sequentially)

---

## 2. Gap Analysis: What's Missing

### Critical Gaps (Block Enterprise Adoption)

| Gap | Why Critical | Effort |
|-----|-------------|--------|
| Security testing (OWASP LLM Top 10) | Table-stakes for any enterprise AI deployment | Medium |
| Governance benchmarks (Phase 16+) | New code untested at benchmark level; boards, federation, export all unvalidated | Medium |
| Guardian H3 fix | Only failing hypothesis; low-confidence rule missing | Small |
| Hallucination validation at scale | H7 claims 100% on 5 samples — not statistically significant | Medium |
| Cross-LLM consistency | Only tested on DeepSeek; buyers need LLM-agnostic proof | Medium |

### High-Value Gaps (Competitive Differentiation)

| Gap | Why Valuable | Effort |
|-----|-------------|--------|
| Raw LLM delta benchmarks (CounterBench, tau-bench, GAIA) | Proves CARF improves LLM output; researchers demand this | Large |
| Fairness testing (AIF360) | Required for healthcare/finance/government sales | Medium |
| CLEAR framework evaluation | Enterprise-grade multi-dimensional assessment (rho=0.83 with production success) | Medium |
| Causal benchmarks (CausalBench/CausalProfiler) | Validates core value proposition against academic standards | Medium |

### Strategic Gaps (Thought Leadership)

| Gap | Why Strategic | Effort |
|-----|-------------|--------|
| Sustainability/Green AI metrics | ESG reporting is a key use case; must practice what we preach | Small-Medium |
| UX benchmarks (SUS, WCAG) | Differentiates from pure-backend competitors | Medium (requires user studies) |
| Chaos engineering at scale | Proves production-readiness for mission-critical deployments | Large |
| ISO 42001 / NIST AI RMF alignment | Structured compliance evidence for enterprise procurement | Medium |

---

## 3. New Benchmark Categories

### 3A. Governance Extension Benchmarks (Phase 16+)

The governance features from Phase 16+ have zero benchmark coverage. These test the MAP-PRICE-RESOLVE framework, governance boards, policy federation, policy editor, and spec export.

#### H12: Governance MAP Accuracy
**What**: Semantic triple extraction (subject-predicate-object) correctly identifies cross-domain impacts
**Method**:
- 50 test queries spanning procurement, sustainability, security, legal, finance domains
- Ground truth: hand-labeled domain mappings and expected triples
- Metrics: Precision, Recall, F1 for entity extraction and triple formation
**Threshold**: F1 >= 0.80 for domain detection; >= 0.70 for triple extraction
**Data needed**: Curated set of 50 multi-domain governance queries with labeled triples

#### H13: Governance PRICE Cost Tracking Accuracy
**What**: Cost intelligence service accurately tracks LLM token costs vs actual API billing
**Method**:
- Run 100 queries through pipeline with known token counts
- Compare PRICE-reported costs against actual API billing records
- Test across DeepSeek, OpenAI, Anthropic providers
**Threshold**: Cost estimate within 5% of actual billing
**Data needed**: API billing records for validation; can be generated from test runs

#### H14: Policy Conflict Detection (RESOLVE)
**What**: Federated policy service correctly detects contradictory, overlapping, and ambiguous policies
**Method**:
- 30 policy pairs: 10 contradictory, 10 overlapping-but-compatible, 10 non-overlapping
- Measure: Detection rate, false positive rate, severity classification accuracy
- Include: resource contention scenarios, priority ambiguity
**Threshold**: >= 90% conflict detection rate, < 10% false positive rate
**Data needed**: Curated policy conflict corpus (can be hand-crafted from real governance patterns)

#### H15: Governance Board Lifecycle
**What**: Full CRUD + voting workflow for governance boards operates correctly and deterministically
**Method**:
- Create 5 boards, assign stakeholders, run 20 votes, verify audit trail completeness
- Concurrent access testing (3 simultaneous voters)
- Verify all events logged (BOARD_CREATED, BOARD_UPDATED, etc.)
**Threshold**: 100% audit completeness, 100% vote integrity, zero data loss under concurrency
**Data needed**: Synthetic board configurations and voting scenarios

#### H16: Policy Ingestion & Export Roundtrip
**What**: Policies ingested via YAML/JSON/natural language are correctly parsed, stored, and exported identically
**Method**:
- Ingest 20 policies (8 YAML, 7 JSON, 5 natural language)
- Export all in each format
- Roundtrip comparison: re-ingest exported policies and verify semantic equivalence
- Test conflict detection on ingestion
**Threshold**: 100% roundtrip fidelity for structured formats; >= 90% semantic equivalence for NL-ingested
**Data needed**: Sample policy corpus in each format

---

### 3B. Raw LLM Delta Benchmarks (Researcher & Expert Expectations)

These benchmarks answer the critical question: "Does CARF actually improve LLM output, and by how much?" Researchers, investors, and technical evaluators expect to see standard benchmark suites run through CARF vs. raw LLM, demonstrating the wrapper's value.

#### H17: Counterfactual Reasoning Delta (CounterBench)
**What**: CARF's causal inference layer improves LLM counterfactual reasoning accuracy
**Method**:
- Use CounterBench dataset (published 2025, designed for LLM counterfactual evaluation)
- Run queries through: (a) raw DeepSeek-Reasoner, (b) raw GPT-4o, (c) CARF pipeline
- Measure: Counterfactual accuracy, reasoning quality, causal chain correctness
**Threshold**: CARF >= 20% improvement over best raw LLM on counterfactual tasks
**Data needed**: CounterBench dataset (open-source, available on HuggingFace/arXiv)
**Why experts care**: Counterfactual reasoning is CARF's core value proposition — if the causal layer doesn't measurably improve it, the architecture is unjustified

#### H18: Policy-Guided Agent Compliance (tau-bench)
**What**: CARF's Guardian layer improves LLM compliance with policy constraints during tool use
**Method**:
- Use tau-bench retail/airline domain scenarios (policy-guided tool use with constraints)
- Run scenarios through: (a) raw LLM agent, (b) CARF pipeline with Guardian
- Measure: Policy compliance rate, pass^k consistency (k=8), task completion rate
**Threshold**: CARF pass^8 >= 50% (vs. raw LLM <25% per tau-bench paper)
**Data needed**: tau-bench dataset (open-source from Sierra Research); CARF policy translations of tau-bench guidelines
**Why experts care**: tau-bench is the most directly relevant agent benchmark — it tests exactly the policy-guided tool-use that CARF provides. Raw LLMs score <50% on pass^1 and <25% on pass^8.

#### H19: Hallucination Reduction at Scale (FActScore + HaluEval)
**What**: CARF's grounding mechanisms reduce hallucination rate across 200+ diverse claims
**Method**:
- Run 200 factual queries through raw LLM and CARF pipeline
- Use FActScore for atomic fact decomposition and verification
- Use HaluEval corpus for QA, dialogue, and summarization hallucination detection
- Measure: Hallucination rate, FActScore precision, unsupported claim rate
**Threshold**: CARF hallucination rate < 2% (vs. current claim of 0% on 5 samples); >= 60% reduction vs raw LLM
**Data needed**: HaluEval dataset (open-source); FActScore evaluation toolkit; 200 curated factual queries with ground truth
**Why experts care**: H7's current "100% reduction" claim is based on 5 claims — statistically meaningless. This provides rigorous validation.

#### H20: Multi-Tool Agent Capability (GAIA Delta)
**What**: CARF improves general AI assistant performance on multi-step reasoning with tool use
**Method**:
- Select 50 GAIA benchmark questions (Level 1-3) requiring multi-tool reasoning
- Run through: (a) raw LLM, (b) CARF pipeline (Cynefin routing + appropriate engines)
- Measure: Task completion rate, answer accuracy, tool selection appropriateness
**Threshold**: CARF >= 15% improvement over raw LLM; correct tool routing >= 90%
**Data needed**: GAIA benchmark subset (466 questions, open-source); may need environment setup for web/tool access
**Why experts care**: GAIA is the gold standard for holistic agent evaluation with a persistent 77% human-AI gap

#### H21: Cross-LLM Consistency
**What**: CARF's improvement holds across multiple underlying LLMs, proving LLM-agnostic value
**Method**:
- Run core benchmark suite (H1, H2, H7, H17) with:
  - DeepSeek-Reasoner (default)
  - GPT-4o (OpenAI)
  - Claude Sonnet 4.5 (Anthropic)
  - Llama 3.1 70B (Together/Ollama)
- Compare: CARF delta for each LLM backend
**Threshold**: CARF improvement >= 30% for causal accuracy (H1) across all 4 LLMs; quality variation < 15% between backends
**Data needed**: API access to each provider; existing benchmark DGPs work as-is
**Why experts care**: If CARF only works with one LLM, it's a prompt engineering trick. Cross-LLM consistency proves architectural value.

#### H22: CLEAR Framework Evaluation
**What**: Enterprise-grade multi-dimensional assessment covering Cost, Latency, Efficacy, Assurance, Reliability
**Method**:
- Cost: Cost per query (tokens × price) for raw LLM vs. CARF; cost-normalized accuracy
- Latency: P50/P95/P99 across query types; includes cold start and warm cache paths
- Efficacy: Composite of H1 (causal), H2 (Bayesian), H17 (counterfactual), H19 (hallucination)
- Assurance: Prompt injection resistance rate (Section 3C); policy compliance rate (H18)
- Reliability: pass^k consistency (k=3,5,8) across 100 repeated runs; determinism (H4)
**Threshold**: CLEAR composite score >= 0.75 (range 0-1); correlation with production success >= 0.80
**Data needed**: Existing benchmark data + new security tests; API billing data for cost calculation
**Why experts care**: The CLEAR framework (arXiv 2511.14136) shows rho=0.83 correlation with production success vs. accuracy-only at rho=0.41. This is what enterprise buyers actually need to see.

---

### 3C. Security & Adversarial Benchmarks

#### H23: OWASP LLM Top 10 Coverage
**What**: CARF's Guardian and pipeline defenses address all 10 OWASP LLM vulnerabilities
**Method**:
- **LLM01 Prompt Injection**: 200 attack vectors (direct override, roleplay, encoding, suffix, multi-turn); test Guardian interception rate
- **LLM02 Sensitive Info Disclosure**: Inject PII (SSN, email, phone, addresses); verify zero leakage past PII sanitizer
- **LLM03 Supply Chain**: Dependency scan (pip-audit, safety); model provenance verification
- **LLM05 Improper Output Handling**: XSS/injection in generated content; output sanitization
- **LLM06 Excessive Agency**: Tool-use boundary testing; privilege escalation attempts; verify Guardian blocks unauthorized actions
- **LLM07 System Prompt Leakage**: Extraction attacks (roleplay, encoding, meta-prompts); verify zero leakage
- **LLM09 Misinformation**: Subset of H19 (FActScore/HaluEval) results
- **LLM10 Unbounded Consumption**: Token bombing, recursive loops; verify circuit breaker activation
**Threshold**: >= 95% detection rate on known attack patterns; zero PII leakage; zero system prompt extraction
**Data needed**:
- Prompt injection corpus: Use **DeepTeam** or **Promptfoo** open-source attack libraries (500+ vectors)
- PII test corpus: Generate synthetic PII data (Faker library)
- Dependency scan: Automated via pip-audit (no data needed)

#### H24: Adversarial Causal Input Robustness
**What**: CARF's causal inference remains accurate under adversarial data manipulation
**Method**:
- Take H1's 9 DGPs and inject adversarial perturbations:
  - Confounder injection (add spurious confounders)
  - Outcome manipulation (flip treatment labels for 10%, 20%, 30% of rows)
  - Collider bias introduction
  - Missing data patterns (MCAR, MAR, MNAR)
- Measure: ATE estimate degradation, refutation test sensitivity, error detection rate
**Threshold**: CARF detects data quality issues in >= 80% of adversarial cases; ATE remains within 2x clean MSE for <= 20% contamination
**Data needed**: Extend existing DGPs with adversarial generation functions (code-only, no acquisition needed)

#### H25: Red Team Protocol Execution
**What**: Structured red team exercise covering all 8 CARF-specific attack surfaces
**Method**:
1. Guardian layer bypass attempts (escalation path testing)
2. Cynefin router manipulation (forcing misclassification to avoid appropriate analysis)
3. Causal inference adversarial inputs (confounding injection to produce wrong causal conclusions)
4. Bayesian prior manipulation attacks (biased priors leading to misleading posteriors)
5. Policy federation circumvention (exploiting multi-domain policy conflicts)
6. Governance board decision manipulation (vote tampering, quorum exploits)
7. Human-in-the-loop bypass attempts (circumventing required escalation)
8. Audit trail integrity (attempts to modify or suppress audit records)
**Threshold**: Zero successful bypasses for categories 1,6,7,8 (security-critical); documented mitigations for all others
**Data needed**: Red team playbook (to be developed); adversarial prompt sets (from DeepTeam/Promptfoo)

---

### 3D. Compliance & Fairness Benchmarks

#### H26: Algorithmic Fairness (AIF360)
**What**: CARF outputs demonstrate no discriminatory bias across protected attributes
**Method**:
- Use AI Fairness 360 toolkit with CARF's causal and routing outputs
- Test datasets with demographic attributes (race, sex, age):
  - German Credit dataset (finance domain, 1,000 instances, open data)
  - COMPAS Recidivism dataset (justice domain, 7,214 instances, open data)
  - Adult Census Income dataset (employment domain, 48,842 instances, open data)
- Run through CARF pipeline; measure causal treatment effect estimates across groups
- Metrics: Statistical Parity Difference, Disparate Impact, Equal Opportunity Difference, Calibration by group
**Threshold**: Disparate Impact ratio >= 0.80 (4/5 rule); Statistical Parity Difference < 0.10; Equal Opportunity Difference < 0.05
**Data needed**: German Credit, COMPAS, Adult Census datasets (all open-source, available via AIF360 or UCI ML Repository)

#### H27: Explainability Quality (XAI Metrics)
**What**: CARF's causal explanations meet quantitative XAI benchmarks
**Method**:
- For 50 causal analyses, generate explanations and measure:
  - **Fidelity**: Correlation between explanation feature importance and actual model behavior (SHAP baseline)
  - **Stability**: Jaccard similarity of explanations for similar inputs (perturb inputs by 5%, measure explanation change)
  - **Simplicity**: Average number of features per explanation (target: < 10)
  - **Robustness**: Explanation variance under noise injection (5% Gaussian noise on inputs)
**Threshold**: Fidelity > 0.85; Stability (Jaccard) > 0.75; Simplicity < 10 features; Robustness variance < 10%
**Data needed**: Existing H1 DGP data; SHAP/LIME integration for baseline comparison

#### H28: Audit Trail Completeness (ALCOA+)
**What**: Every CARF decision produces an ALCOA+-compliant audit record
**Method**:
- Run 100 end-to-end queries and verify each audit record for:
  - **Attributable**: Decision linked to specific agent, model, and user
  - **Legible**: Human-readable reasoning chain
  - **Contemporaneous**: Timestamp within 1 second of decision
  - **Original**: First-hand record (not derived)
  - **Accurate**: Reasoning matches actual pipeline path
  - **Complete**: All pipeline stages logged (router → agent → guardian → output)
  - **Consistent**: No contradictions between stages
  - **Enduring**: Available after 30 days (retention test)
  - **Available**: Retrievable within 5 seconds via API
**Threshold**: 100% completeness on all 9 ALCOA+ criteria for all 100 queries
**Data needed**: Generated from test runs; no external data needed

---

### 3E. Sustainability & Green AI Benchmarks

#### H29: Energy Efficiency Profiling
**What**: Quantify CARF's energy overhead per query vs. raw LLM, and demonstrate ChimeraOracle savings
**Method**:
- Use `codecarbon` or `carbontracker` Python libraries to measure energy per query
- Profile each pipeline path:
  - Clear domain (single LLM call)
  - Complicated domain (LLM + DoWhy)
  - Complex domain (LLM + PyMC MCMC)
  - ChimeraOracle cached path
- Calculate: Joules per query, gCO2e per query (using regional grid carbon intensity)
- Compare: CARF vs. raw LLM energy cost for equivalent quality
**Threshold**: Document energy overhead transparently; ChimeraOracle path <= 10% energy of full Complicated path; energy proportional to problem complexity (Clear < Complicated < Complex)
**Data needed**: No external data; `codecarbon` library + existing benchmark queries
**Tool**: `pip install codecarbon` — zero-config energy tracking

#### H30: Scope 3 Estimation Accuracy
**What**: CARF's causal inference produces more accurate Scope 3 emissions estimates than raw LLM
**Method**:
- Use EPA Greenhouse Gas Reporting Program (GHGRP) open data as ground truth
- Test calculation accuracy across methods:
  - Spend-based (financial data → emission factors)
  - Average-data (industry averages)
  - Supplier-specific (primary data)
- CARF adds: causal attribution of emission drivers, Bayesian uncertainty intervals, refutation tests
- Compare: CARF estimates vs. raw LLM estimates vs. audited actuals
**Threshold**: CARF estimates within 15% of audited figures (vs. raw LLM within 40%); Bayesian 90% CI covers true value >= 90% of the time
**Data needed**:
- EPA GHGRP dataset (open, ~8,000 facilities, annual reports): https://www.epa.gov/ghgreporting
- CDP Open Data Portal (corporate emissions disclosures): https://www.cdp.net/en
- EXIOBASE or OpenIO for emission factor databases

---

### 3F. UX/UIX Benchmarks

#### H31: System Usability Scale (SUS)
**What**: CARF Cockpit achieves above-average usability for its three personas
**Method**:
- Recruit minimum 15 users (5 analysts, 5 developers, 5 executives/compliance officers)
- Define 6 task scenarios:
  1. Submit a causal query and interpret the DAG visualization
  2. Review and approve a Guardian escalation
  3. Create a governance policy via the policy editor
  4. Compare two simulation scenarios in the arena
  5. Find a past analysis using the experience buffer
  6. Export a compliance report
- Administer 10-item SUS questionnaire post-task
- Calculate per-persona and aggregate SUS scores
**Threshold**: SUS >= 68 (above average); target >= 75 (good); aspirational >= 80 (excellent)
**Data needed**: User recruitment; task scenario scripts; SUS questionnaire (standardized, 10 questions)
**Note**: This requires real human participants. Can be conducted remotely with screen recording. Budget: approximately 15 users × 1 hour = 15 person-hours.

#### H32: Task Completion & Time-to-Insight
**What**: Users can complete core workflows efficiently and arrive at actionable insights quickly
**Method**:
- During SUS testing (H31), instrument each task for:
  - Success rate (completed vs. abandoned)
  - Time to completion
  - Error count (wrong clicks, backtracking)
  - Time to first meaningful insight
- Additionally, measure automated:
  - API response time to first token (P50, P95)
  - Time from query submission to rendered result in Cockpit
**Threshold**: Task success rate >= 90%; time to first insight < 30s (simple), < 2min (complex); error rate < 5%
**Data needed**: Same user study as H31; instrumented Cockpit build with timing hooks

#### H33: Accessibility Compliance (WCAG 2.2 AA)
**What**: CARF Cockpit meets WCAG 2.2 Level AA accessibility standards
**Method**:
- Automated scan using axe-core or Lighthouse accessibility audit on all Cockpit views
- Manual testing for:
  - Keyboard navigation of causal DAG visualizations
  - Screen reader compatibility for confidence intervals and uncertainty displays
  - Color contrast ratios for all status indicators (Guardian verdicts, domain colors)
  - Focus management in governance board workflows
- Test views: Main query, CausalDAG, BayesianPanel, GuardianPanel, GovernanceView, PolicyEditor, SimulationArena
**Threshold**: Zero Level A violations; < 5 Level AA violations; all critical interactions keyboard-accessible
**Data needed**: No external data; axe-core npm package for automated scanning; manual checklist

---

### 3G. Industry-Specific Use Case Benchmarks (Extended)

Expand the current 13 E2E scenarios to cover additional industry-specific benchmarks that enterprise buyers expect.

#### H34: Supply Chain — Disruption Prediction Accuracy
**What**: CARF predicts supply chain disruptions with measurable lead time
**Method**:
- Use open supply chain disruption datasets:
  - **Supply Chain Disruption Dataset (Kaggle)**: 1,000+ events with date, type, impact
  - **World Bank Logistics Performance Index**: Country-level logistics metrics
- Generate synthetic time-series with planted disruption events
- Measure: Prediction lead time (hours before event), precision, recall
**Threshold**: Bayesian early warning >= 48 hours before event; precision >= 70%; recall >= 80%
**Data needed**: Kaggle supply chain datasets (open); synthetic time-series generator

#### H35: Healthcare — CATE Validation Against Clinical Baselines
**What**: CARF's treatment effect estimates align with published RCT results
**Method**:
- Use open clinical trial datasets:
  - **MIMIC-IV** (critical care, MIT license — requires credentialing): 300,000+ admissions
  - **IHDP** (Infant Health and Development Program, open): Standard causal inference benchmark, 747 subjects
  - **Twins dataset** (open): 11,400 twin pairs for treatment effect estimation
- Run CARF causal inference on treatment outcomes
- Compare CARF CATE estimates against published RCT effect sizes
**Threshold**: CARF CATE within 10% of published RCT effect size; 90% CI covers RCT point estimate
**Data needed**:
- IHDP dataset: Available via `causalml` package or direct download
- Twins dataset: Available via `causalml` package
- MIMIC-IV: Requires MIT credentialing (PhysioNet, ~1 week approval process)

#### H36: Finance — Risk Model Backtesting
**What**: CARF's Bayesian risk quantification passes standard VaR backtesting
**Method**:
- Use open financial datasets:
  - **Yahoo Finance historical data** (free API): Daily returns for S&P 500 constituents
  - **Kenneth French Data Library** (open): Factor returns, industry portfolios
- Calculate Value at Risk (VaR) using CARF's Bayesian inference
- Backtest: Compare predicted VaR exceedances vs. actual exceedances (Kupiec test)
**Threshold**: VaR backtest p-value > 0.05 (Kupiec test); coverage ratio within [0.95, 1.05] of expected
**Data needed**: Yahoo Finance API (free); Kenneth French Data Library (open, dartmouth.edu)

---

### 3H. Reliability & Operational Benchmarks (Extended)

#### H37: Concurrent Load Performance
**What**: CARF maintains quality and latency under concurrent user load
**Method**:
- Use `locust` or `k6` load testing tools
- Scenarios: 1, 5, 10, 25, 50 concurrent users submitting queries
- Mix: 40% Clear, 20% Complicated, 20% Complex, 10% Chaotic, 10% Disorder
- Measure: P50, P95, P99 latency; error rate; throughput (queries/second)
- Compare quality: spot-check 10% of responses for accuracy degradation under load
**Threshold**: P95 < 15s for Clear domain under 25 concurrent users; zero errors under 10 concurrent; quality degradation < 5% under load
**Data needed**: Existing query corpus; `pip install locust` (no external data)

#### H38: Chaos Engineering — Multi-Component Cascade
**What**: CARF degrades gracefully when multiple components fail simultaneously
**Method**:
- Scenario matrix (extend existing H11):
  - LLM API timeout + database down → ChimeraOracle serves cached + local buffer
  - Guardian crash + Kafka down → fail-closed + local audit buffer
  - PyMC convergence failure + high load → degrade to LLM-only with honest uncertainty warning
  - Neo4j unavailable + policy engine slow → serve from cache with stale-data warning
- For each scenario: verify user receives response (degraded but honest), audit trail recovers post-failure, no data loss
**Threshold**: Zero unguarded outputs during any failure; 100% audit recovery post-failure; user always informed of degradation
**Data needed**: Existing benchmark queries; fault injection tooling (can be built with mocks)

#### H39: Long-Running Soak Test
**What**: CARF remains stable over extended operation (24+ hours)
**Method**:
- Run continuous mixed-domain queries at 1 query/minute for 24 hours (1,440 queries)
- Monitor: RSS memory, heap growth, open file descriptors, connection pools, response latency trend
- Check for: memory leaks, connection exhaustion, gradual latency degradation, GC pauses
**Threshold**: RSS growth < 5% over 24 hours; P95 latency stable (< 10% increase); zero OOM events; zero connection leaks
**Data needed**: Existing query corpus on rotation; monitoring via `psutil` + `tracemalloc`

---

## 4. Improvements to Existing Benchmarks

### Fix H3: Guardian Violation Detection (67% → 100%)
**Action**: Add CSL rule for low-confidence action detection
```
rule low_confidence_escalation:
  when effect_size < 0.05 AND confidence_interval_width > 2.0
  then REQUIRES_ESCALATION
  reason "Low domain confidence requires human review"
```
**Effort**: 1-2 hours (single CSL rule + re-run benchmark)

### Scale H7: Hallucination Testing (5 → 200+ claims)
**Action**: Replace ad-hoc 5-claim test with FActScore evaluation on 200+ queries (now H19)
**Effort**: Absorbed into H19

### Scale H0: Router Test Set (50 → 200 queries)
**Action**: Expand from 50 to 200 queries; add 20 adversarial/ambiguous boundary cases; add 20 multi-language queries
**Effort**: Generate via existing `generate_test_set.py` with expanded templates

### Scale H4: Determinism Testing (25 → 250 runs)
**Action**: Increase from 5 cases × 5 reps to 10 cases × 25 reps = 250 runs
**Effort**: Config change only; existing benchmark code handles this

### Extend H1: Real-World Causal Data
**Action**: Add IHDP dataset (747 subjects, standard causal benchmark) alongside synthetic DGPs
**Effort**: Medium (integrate dataset, establish ground truth from published literature)

### Extend H9: Memory Soak (50 queries → 24-hour soak)
**Action**: Absorbed into H39

### Extend H6: Add Concurrent Load
**Action**: Absorbed into H37

---

## 5. Data Acquisition Strategy

### Open Data — Ready to Use (No Cost)

| Dataset | Source | Size | License | For Benchmark |
|---------|--------|------|---------|---------------|
| CounterBench | arXiv/HuggingFace | ~1,000 questions | Open | H17 |
| tau-bench | Sierra Research GitHub | Retail + Airline domains | Open | H18 |
| HaluEval | HuggingFace | 35,000+ samples | Open | H19 |
| GAIA | HuggingFace | 466 questions | Open | H20 |
| German Credit | UCI ML Repository | 1,000 instances | Open | H26 |
| Adult Census | UCI ML Repository | 48,842 instances | Open | H26 |
| COMPAS | ProPublica | 7,214 instances | Open | H26 |
| IHDP | `causalml` package | 747 subjects | Open | H35 |
| Twins | `causalml` package | 11,400 pairs | Open | H35 |
| EPA GHGRP | EPA.gov | ~8,000 facilities | Open | H30 |
| Yahoo Finance | yfinance API | Historical returns | Free API | H36 |
| Kenneth French | Dartmouth | Factor returns | Open | H36 |
| DeepTeam attack corpus | GitHub | 500+ vectors | Open | H23 |
| SUS Questionnaire | Standard | 10 questions | Public domain | H31 |

### Data Requiring Registration/Credentialing (No Cost, Access Delay)

| Dataset | Source | Access Time | For Benchmark |
|---------|--------|-------------|---------------|
| MIMIC-IV | PhysioNet | ~1 week credentialing | H35 (optional) |
| CDP Open Data | CDP.net | Registration | H30 (optional) |

### Data To Be Generated (Code-Only, No Cost)

| Dataset | Method | For Benchmark |
|---------|--------|---------------|
| Governance queries + triples | Hand-curate 50 multi-domain queries | H12 |
| Policy conflict corpus | Hand-craft 30 policy pairs | H14 |
| Adversarial DGP variants | Extend existing DGPs with perturbation functions | H24 |
| Prompt injection vectors | Use DeepTeam/Promptfoo libraries | H23, H25 |
| PII test data | Generate with Python `faker` library | H23 |
| Load test scenarios | Configure `locust` with existing queries | H37 |

### User Study (Requires Budget)

| Study | Participants | Estimated Cost | For Benchmark |
|-------|-------------|---------------|---------------|
| SUS + Task Completion | 15 users × 1 hour | 15 person-hours (can use internal team or university partners) | H31, H32 |

---

## 6. Execution Plan & Priority Tiers

### Tier 1: Critical Path (Weeks 1-3)
*Must-have before any enterprise engagement. Fix failures, close security gaps, validate core claims.*

| # | Benchmark | Effort | Dependencies | Data |
|---|-----------|--------|-------------|------|
| Fix H3 | Guardian low-confidence rule | 2 hours | None | Existing |
| H14 | Policy Conflict Detection (RESOLVE) | 3 days | Hand-craft policy corpus | Generate |
| H15 | Governance Board Lifecycle | 2 days | None | Generate |
| H16 | Policy Ingestion Roundtrip | 2 days | None | Generate |
| H23 | OWASP LLM Top 10 Coverage | 5 days | DeepTeam/Promptfoo setup | Open-source |
| Scale H0 | Router 50→200 queries | 1 day | None | Generate |
| Scale H4 | Determinism 25→250 runs | 0.5 days | None | Existing |

**Tier 1 delivers**: Grade A+ (all hypotheses passing), governance coverage, basic security posture.

### Tier 2: Competitive Advantage (Weeks 3-6)
*Researcher-facing benchmarks and enterprise compliance. Proves CARF's value over raw LLMs.*

| # | Benchmark | Effort | Dependencies | Data |
|---|-----------|--------|-------------|------|
| H17 | CounterBench Delta | 3 days | CounterBench download | Open-source |
| H18 | tau-bench Policy Compliance | 4 days | tau-bench setup + CARF policy translation | Open-source |
| H19 | Hallucination at Scale (FActScore+HaluEval) | 3 days | HaluEval download | Open-source |
| H21 | Cross-LLM Consistency | 3 days | GPT-4o + Claude + Llama API access | Existing DGPs |
| H22 | CLEAR Framework Evaluation | 3 days | Tier 1 results + API billing data | Computed |
| H26 | Fairness (AIF360) | 3 days | German Credit + Adult datasets | Open-source |
| H27 | Explainability (XAI Metrics) | 2 days | SHAP integration | Existing DGPs |
| H28 | Audit Trail (ALCOA+) | 2 days | None | Generated from runs |
| H12 | Governance MAP Accuracy | 2 days | Curated query set | Generate |
| H13 | PRICE Cost Tracking | 1 day | API billing records | Generated |

**Tier 2 delivers**: Validated raw-LLM delta story, fairness proof, cross-LLM evidence, enterprise compliance baseline.

### Tier 3: Deep Validation (Weeks 6-10)
*Industry-specific proofs, production readiness, and thought leadership.*

| # | Benchmark | Effort | Dependencies | Data |
|---|-----------|--------|-------------|------|
| H20 | GAIA Delta | 4 days | GAIA environment setup | Open-source |
| H24 | Adversarial Causal Robustness | 3 days | Extend existing DGPs | Generated |
| H25 | Red Team Protocol | 5 days | Red team playbook development | Generated |
| H29 | Energy Efficiency (codecarbon) | 2 days | codecarbon setup | Computed |
| H30 | Scope 3 Accuracy (EPA data) | 3 days | EPA GHGRP download | Open-source |
| H34 | Supply Chain Disruption | 3 days | Kaggle dataset | Open-source |
| H35 | Healthcare CATE (IHDP+Twins) | 3 days | causalml package | Open-source |
| H36 | Finance VaR Backtest | 3 days | Yahoo Finance API | Free API |
| H37 | Concurrent Load Testing | 2 days | locust setup | Existing |
| H38 | Chaos Cascade | 3 days | Fault injection framework | Generated |
| H39 | 24-Hour Soak Test | 2 days | Monitoring setup | Existing |

**Tier 3 delivers**: Industry-specific proof points, operational resilience, sustainability credentials.

### Tier 4: Excellence & Thought Leadership (Weeks 10-14)
*UX validation, advanced compliance, market positioning.*

| # | Benchmark | Effort | Dependencies | Data |
|---|-----------|--------|-------------|------|
| H31 | SUS Usability Study | 5 days | User recruitment | Human study |
| H32 | Task Completion & Time-to-Insight | 2 days | H31 infrastructure | Human study |
| H33 | WCAG 2.2 AA Compliance | 3 days | axe-core setup | Automated |
| — | ISO 42001 Gap Analysis | 3 days | Standard acquisition | Documentation |
| — | NIST AI RMF Alignment Report | 2 days | Framework mapping | Documentation |
| — | SOC 2 Readiness Assessment | 5 days | Controls documentation | Documentation |

**Tier 4 delivers**: UX evidence, accessibility compliance, certification readiness.

---

## 7. Updated Hypothesis Table

### Original Hypotheses (Improved)

| # | Hypothesis | Current | Target | Change |
|---|-----------|---------|--------|--------|
| H0 | Router F1 on 200 queries (was 50) | 0.98 | >= 0.90 | Harder test set |
| H1 | Causal ATE MSE + IHDP real data | 1.19 | < 2.0 | Added real-world validation |
| H2 | Bayesian coverage (unchanged) | 100% | >= 90% | No change needed |
| H3 | Guardian detection (fix low-confidence rule) | 67% | 100% | **Fix CSL policy** |
| H4 | Determinism on 250 runs (was 25) | 100% | 100% | Stronger evidence |
| H5 | EU AI Act (add Art. 10, 11, 15) | 100% | >= 90% | Broader article coverage |
| H6 | Latency under concurrent load | 3.5x | < 5x | Add concurrency dimension |
| H7 | Hallucination on 200 claims (was 5) | 100% | < 2% | **Statistical significance** |
| H8 | ChimeraOracle multi-scenario | 32.7x | >= 10x | Test drift resilience |
| H9 | Memory over 24h soak (was 50 queries) | 0.21% | < 5% | Real-world duration |
| H10 | Reflector (add unknown-type handling) | 80% | >= 80% | Fix test artifact |
| H11 | Resiliency cascade failures | 100% | >= 95% | Multi-component failures |

### New Hypotheses

| # | Hypothesis | Threshold | Category |
|---|-----------|-----------|----------|
| H12 | Governance MAP triple extraction F1 | >= 0.80 domain, >= 0.70 triples | Governance |
| H13 | PRICE cost tracking accuracy | Within 5% of actual | Governance |
| H14 | RESOLVE conflict detection rate | >= 90% detection, < 10% FPR | Governance |
| H15 | Governance board lifecycle integrity | 100% audit + vote integrity | Governance |
| H16 | Policy roundtrip fidelity | 100% structured, >= 90% NL | Governance |
| H17 | CounterBench delta (CARF vs raw LLM) | >= 20% improvement | LLM Delta |
| H18 | tau-bench policy compliance (pass^8) | >= 50% (vs raw LLM <25%) | LLM Delta |
| H19 | Hallucination rate at scale (200+ queries) | < 2%, >= 60% reduction vs LLM | LLM Delta |
| H20 | GAIA multi-tool delta | >= 15% improvement | LLM Delta |
| H21 | Cross-LLM consistency | >= 30% improvement across 4 LLMs | LLM Delta |
| H22 | CLEAR composite score | >= 0.75 | Enterprise |
| H23 | OWASP LLM Top 10 coverage | >= 95% detection, zero PII leak | Security |
| H24 | Adversarial causal robustness | Detects 80% of data quality issues | Security |
| H25 | Red team protocol (8 surfaces) | Zero bypasses on critical paths | Security |
| H26 | Fairness (AIF360, 3 datasets) | Disparate Impact >= 0.80 | Compliance |
| H27 | Explainability (SHAP fidelity) | Fidelity > 0.85, Stability > 0.75 | Compliance |
| H28 | Audit trail ALCOA+ | 100% on all 9 criteria | Compliance |
| H29 | Energy efficiency per query | ChimeraOracle <= 10% of full path energy | Sustainability |
| H30 | Scope 3 estimation accuracy | Within 15% of audited figures | Sustainability |
| H31 | SUS score | >= 68 (above average) | UX |
| H32 | Task success rate + time-to-insight | >= 90% success, < 30s simple | UX |
| H33 | WCAG 2.2 AA compliance | Zero Level A violations | UX |
| H34 | Supply chain disruption prediction | 48h lead time, precision >= 70% | Industry |
| H35 | Healthcare CATE vs RCT | Within 10% of published effect | Industry |
| H36 | Finance VaR backtest | Kupiec p-value > 0.05 | Industry |
| H37 | Concurrent load performance | P95 < 15s at 25 users | Operational |
| H38 | Chaos cascade graceful degradation | Zero unguarded outputs | Operational |
| H39 | 24-hour soak test stability | RSS < 5% growth, latency < 10% increase | Operational |

### Summary: From 11 → 39 Hypotheses

| Category | Current | Proposed | Net New |
|----------|---------|----------|---------|
| Technical (H0-H11) | 11 | 11 (improved) | 0 |
| Governance (H12-H16) | 0 | 5 | +5 |
| LLM Delta (H17-H22) | 0 | 6 | +6 |
| Security (H23-H25) | 0 | 3 | +3 |
| Compliance (H26-H28) | 0 | 3 | +3 |
| Sustainability (H29-H30) | 0 | 2 | +2 |
| UX (H31-H33) | 0 | 3 | +3 |
| Industry (H34-H36) | 0 | 3 | +3 |
| Operational (H37-H39) | 0 | 3 | +3 |
| **Total** | **11** | **39** | **+28** |

---

## Appendix: Key External References

- **CLEAR Framework**: arXiv 2511.14136 — Enterprise-grade multi-dimensional evaluation (rho=0.83)
- **tau-bench**: Sierra Research — Policy-guided agent benchmark (most relevant to CARF)
- **CounterBench**: arXiv 2502.11008 — Counterfactual reasoning in LLMs
- **GAIA**: HuggingFace — General AI Assistant benchmark (466 questions)
- **FActScore**: Atomic factual precision scoring
- **HaluEval**: HuggingFace — 35,000+ hallucination samples
- **AI Fairness 360**: IBM/LF AI — 70+ fairness metrics
- **OWASP LLM Top 10 2025**: owasp.org — All 10 LLM vulnerabilities
- **NIST AI 600-1**: 12 GenAI-specific risks
- **ISO/IEC 42001:2023**: World's first AI Management System standard
- **MLPerf Power**: Energy efficiency benchmarking
- **codecarbon**: Python energy tracking library
- **DeepTeam / Promptfoo**: Open-source red teaming tools
- **IHDP / Twins**: Standard causal inference benchmark datasets

*Full source list available in `benchmarks/reports/INDUSTRY_BENCHMARK_RESEARCH_2025_2026.md`*
