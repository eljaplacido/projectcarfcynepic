# CARF CYNEPIC — Deep-Research Integration Roadmap

Companion to [`SOTA_IMPROVEMENT_ROADMAP.md`](SOTA_IMPROVEMENT_ROADMAP.md). Where the
SOTA roadmap is the standing P0–P3 living plan, this document maps a specific
external research brief onto the **current** (post-pull) codebase and turns it
into a prioritised, evidence-graded set of additions.

**Inputs**
- *CARF CYNEPIC Deep Research: Applying Mathematical-Statistical & Neurosymbolic
  Methods to Architecture, Capabilities, Use Cases, and Benchmark Improvement*
  (Jun 2026), which itself synthesises (a) the LUT dissertation on causal,
  uncertainty-aware, neuro-symbolic surrogate modelling for European electricity
  markets and (b) a 2025–2026 neurosymbolic-integration survey.
- Codebase at commit `3869274` (PR1 evidence hardening + PR2 Phase 18E /
  OpenTelemetry + Guardian causal-gate hardening + automated router hint refresh).

**Method.** Every research recommendation was ground-truthed against the code
(file:line evidence below) before being scheduled, so we do not re-recommend
work that already landed.

---

## 0. TL;DR — the five highest-leverage moves

1. **Close the realism gap with real public datasets** (LaLonde, real IHDP,
   EPEX/ENTSO-E, Wikidata). Today **35/37 benchmark sources are synthetic**
   (only two UX surveys use real data; `healthcare` is *IHDP-inspired*, not real
   IHDP). This is the single biggest credibility lever — it converts
   self-reported "Grade A+" into externally verifiable claims.
2. **Add conformal prediction (MAPIE) as a cross-cutting calibration layer.**
   It is **entirely absent** today and unlocks router prediction sets,
   calibrated H-Neuron escalation, Bayesian coverage tests, and a principled
   reflector stop — one dependency, four benchmark wins (new H46, stronger H2/H19).
3. **Promote the symbolic layer from Horn clauses to an OWL/SHACL ontology**
   (G-SPEC / OG-RAG pattern). The RAG symbolic tier and the Guardian both run on
   heuristic triples / Rego today; an ontology gives *provable* governance
   (SHACL) and grounded retrieval (OG-RAG). A W3C PROV-AGENT JSON-LD layer
   (`prov_agent.py`) already exists as the foundation.
4. **Auto-select the causal identification strategy (front-door / IV).** DoWhy's
   `identify_effect()` is called but estimation is hardcoded to
   `backdoor.linear_regression`; front-door and IV are never invoked. Low effort,
   directly strengthens H1/H24 on confounded data.
5. **Give the Disorder domain a formal pre-escalation step (LLM+ASP).** Disorder
   currently escalates to humans unconditionally; an answer-set resolver that
   reclassifies the resolvable fraction reduces the human bottleneck and produces
   an auditable trace.

---

## 1. Current-state reconciliation

The research brief was written against an earlier snapshot. Several of its
recommendations are **already satisfied** at `3869274`. Scheduling only the
remainder keeps the roadmap honest.

| Research recommendation | Actual state @ `3869274` | Verdict |
|---|---|---|
| Replace keyword entropy with Shannon entropy (§2.1) | `router.py:435-449` computes true Shannon entropy — but over the **input token distribution**, not the **domain-softmax**; used as metadata, not a hard Chaotic gate | PARTIAL → refine |
| DML cross-fitting for ChimeraOracle (§2.3) | `chimera_oracle.py:304-312` uses `CausalForestDML` (EconML default 2-fold orthogonalisation) | DONE → minor tune |
| CATE confidence intervals (§2.3) | `chimera_oracle.py:475` `effect_interval(alpha=.05)`; Guardian gates CI **width** | DONE → add subgroup policy |
| Causal robustness / refutation (§4.3) | `causal_sensitivity.py` E-values + refutation battery, wired as mandatory Guardian gate `guardian.py:953-1004` | DONE |
| Expose aleatoric vs epistemic (§2.5) | `state.py:112-113,254-265`, surfaced via `/transparency` | DONE |
| Conjugate posteriors + inference modes (§2.5) | Phase 18E: `InferenceMode{full,approximate,cached}`, Beta + Normal-Inverse-Gamma, `PosteriorCache` | DONE |
| Async I/O hardening — aiokafka/async OPA (§7.1) | `kafka_audit.py` touched in PR2; confirm no sync `flush()`/blocking OPA remain | VERIFY |
| OpenTelemetry per-node spans + trace→eval (§7, SOTA P1) | `utils/tracing.py`, `utils/telemetry.py`, `utils/trace_eval_loop.py` | DONE |
| Closed-loop router feedback (FAOS L5, §3.7) | `router_retraining_service.py:309-369` auto-refreshes hints on ≥5 overrides | DONE (router only) |
| Wire H40–H43 into the unified report (SOTA P0.6) | `generate_report.py:770-827` — all four have real evaluation branches | DONE |
| Conformal prediction (§2.4) | none (`mapie/crepes/nonconformist` absent) | **GAP** |
| Identification-strategy selection: front-door/IV (§2.2) | `identify_effect()` then hardcoded `backdoor.linear_regression` | **GAP** |
| Transportability, Bareinboim-Pearl (§2.2) | absent | **GAP** |
| Counterfactual validated vs do-calculus (§2.2) | `causal_world_model.py:229-276` abduction-action-prediction mechanics correct, no formal validation / assumption audit | **GAP** |
| SHACL over Neo4j governance graph (§3.2) | YAML→CSL-Core(Z3)→OPA; no `pyshacl/rdflib` | **GAP** |
| OG-RAG / OWL symbolic layer (§3.3) | symbolic tier = CSL Horn clauses `neurosymbolic_engine.py:229-261`; no OWL/RDF | **GAP** |
| H-Neuron KG-verified claim checking (§3.4) | 8-signal proxy fusion `h_neuron_interceptor.py:76-85`; no KG match/SPARQL; mechanistic mode stubbed | **GAP** |
| LLM+ASP for Disorder (§3.5) | `graph.py:972-973` Disorder → human escalation, no auto-resolution | **GAP** |
| ARIMA/GARCH on routing/latency (§2.6) | KL-divergence drift only `drift_detector.py:122-131`; no statsmodels/time-series | **GAP** |
| Credal sets for cold-start (§2.5) | absent | **GAP** |
| MC Dropout for LLM causal fallback (§2.5) | absent | **GAP** |
| ATA offline repair library for reflector (§3.6/§6.1) | `smart_reflector.py` heuristic+LLM, fixed 0.7 threshold; runtime LLM still in path | PARTIAL → harden |
| RAGAS-style RAG metrics (SOTA P1) | DeepEval relevancy/hallucination only; no context-precision/recall/faithfulness | **GAP** |
| PC causal discovery on emission DAGs (§5.3) | `causal-learn` is a dependency; discovery used in counterfactual path, not for scenario DAGs | PARTIAL |
| Real-data benchmarks (§4.1) | 35/37 synthetic | **GAP** |
| PINN / DeepOPF energy use case (§5.1) | absent | **GAP (research track)** |
| Multi-agent causal discovery (§4.2, SOTA P3) | absent (designed as 18F/H45) | **GAP (planned)** |

---

## 2. Gap register (prioritised)

Priority = (benchmark/realism impact) ÷ (effort), with safety weighting.
Effort reflects dependency availability: EconML, `causal-learn`, PyMC, Neo4j,
torch, deepeval, OpenTelemetry are **already** present; MAPIE, pyshacl/rdflib,
statsmodels/arch, clingo, owlready2 would be **new but lightweight** additions.

| # | Gap | Effort | New dep | Benchmark / realism impact |
|---|---|---|---|---|
| G1 | Real public-data benchmark track | M (per dataset) | none | **Very high** — H1/H17/H35/H36 externally credible |
| G2 | Conformal prediction layer (MAPIE) | L–M | mapie | High — new H46; strengthens H2, H19 |
| G3 | Identification auto-select (front-door/IV) | L–M | none | High — H1/H24 on confounded data |
| G4 | CATE subgroup-differential Guardian policy | L | none | Med — H3/H17 |
| G5 | Domain-softmax entropy + rolling-window Chaotic gate | L | none | Med — honest H0/H38 |
| G6 | ARIMA/GARCH on routing + latency | L–M | statsmodels/arch | Med — H40/H42 false-positive rate; H37 SLA |
| G7 | PC discovery for scenario/emission DAGs | L–M | none (`causal-learn`) | Med — Scope 3 / energy realism |
| G8 | SHACL over Neo4j governance graph (G-SPEC) | M | pyshacl, rdflib | High — new H49; provable H3/H23 |
| G9 | H-Neuron KG-verified two-stage claim checking | M | none (Neo4j) | High — new H47; precision-recall H7/H19 |
| G10 | ATA offline repair library + conformal stop | M | none (+mapie) | Med — H4/H23 determinism under reflector |
| G11 | Credal sets (cold-start) + MC Dropout (LLM fallback) | M | none (torch) | Med — H2 cold-start; honest LLM uncertainty |
| G12 | RAGAS-style RAG metrics | L–M | ragas or deepeval | Med — faithfulness/citation accuracy |
| G13 | OG-RAG / OWL ontology for symbolic RAG | H | owlready2/rdflib | Very high — new H47/H50; H7/H10 |
| G14 | LLM+ASP Disorder pre-escalation | M–H | clingo | Med — escalation-reduction metric, H18 |
| G15 | Transportability (selection diagrams) | H | none | High — new H48 |
| G16 | Counterfactual do-calculus validation + assumption audit | M | none | Med — externally credible H17 |
| G17 | PINN / DeepOPF electricity-market use case | VH | torch/cvxpylayers | Very high — new energy benchmark |
| G18 | Multi-agent causal discovery | VH | none | High — new H45 (already 18F) |

---

## 3. Phased roadmap

Numbering continues the SOTA roadmap (which ends at P3). These are **R**esearch
phases R1–R5; each is independently shippable and each new benchmark must ship a
graded manifest entry or `check_result_evidence.py --strict-manifest` fails.

### R1 — Calibration & honest-routing quick wins (1 sprint)

Low-effort, high-defensibility. No architecture change.

- **G5 Domain-softmax entropy. ✅ DONE** (`feat/r1-calibration-quick-wins`).
  `router.py` now captures the real DistilBERT softmax (`DomainClassification.
  domain_distribution`), computes normalized Shannon entropy over the domain
  distribution (distinct from the existing token entropy), and adds a bounded
  rolling-window Jensen-Shannon change detector. The principled Chaotic gate is
  **opt-in** (`RouterConfig.enable_chaotic_distribution_gate`, default off) so the
  existing "entropy is metadata" contract and all benchmarks are preserved until
  thresholds are calibrated against the H0 set. Entropy/change exposed via
  `state.context`. 12 new tests.
- **G2 Conformal router. ✅ DONE.** `src/utils/conformal.py` implements pure-NumPy
  split-conformal (LAC; the same marginal-coverage method MAPIE provides — chosen
  for graceful degradation since `mapie` is not a dependency). The router loads an
  optional calibration artifact (`CARF_CONFORMAL_PATH`) and attaches a prediction
  set to `state.context`; cardinality > 1 flags a borderline query and (opt-in,
  `conformal_escalate_on_ambiguous`) routes to human escalation. New **H46
  (Conformal Router Coverage)** benchmark + graded manifest entry: empirical
  coverage 0.949/0.897/0.806 vs nominal 0.95/0.90/0.80 with set size growing as α
  shrinks. 12 new tests prove the coverage guarantee. `conformal_alpha` added to
  `ProfileConfig`.
- **G3 Identification auto-select. ✅ DONE.** `causal.py` now calls
  `identify_effect(proceed_when_unidentifiable=True)` and selects the estimation
  method from the realisable strategies — front-door when a mediator exists, IV
  when a valid instrument exists — falling back only when the requested (default
  back-door) family is unidentifiable. Fully backward-compatible (back-door case
  unchanged); selection surfaced in the interpretation. 7 new tests.
- **G4 CATE subgroup policy. ✅ DONE.** Wired end-to-end: a shared
  `_compute_subgroup_cate` helper (`causal.py`, also now backing `run_deep_analysis`
  with CIs — single source of truth) produces per-subgroup CATE intervals on the main
  path when `profile.cate_subgroup_analysis` is on; they flow through
  `CausalAnalysisResult.subgroup_intervals → proposed_action.cate_subgroups`; the
  Guardian's `_check_causal_recommendation` escalates a sign-conflicting recommendation
  when `profile.cate_require_consistent_sign` is on, via the pure, DoWhy-free
  `assess_cate_consistency` (`causal_sensitivity.py`). Both flags default off. 12 new
  tests (incl. an end-to-end DoWhy test recovering opposite-sign subgroups).
- **G6 ARIMA/GARCH monitors. ✅ DONE (core).** New `src/utils/timeseries_monitor.py`
  provides ARIMA/SARIMAX forecast intervals (`statsmodels`) and conditional-volatility
  regimes (GARCH via optional `arch`, robust rolling-std fallback otherwise). Wired into
  `drift_detector.py` as **opt-in** ARIMA seasonal false-positive suppression
  (`seasonal_suppression`, default off, fail-safe: never silences an alert when the model
  can't be fitted) — a KL value within the forecast interval of the historical KL series
  is "expected variation". New `forecasting` extra in `pyproject.toml`. 14 new tests.
  *Follow-up:* wire `volatility_regime` into live latency telemetry (H37) and the
  plateau/convergence check (H42).

**Status: R1 COMPLETE.** G5/G2/G3/G4/G6 landed on `feat/r1-calibration-quick-wins` with
57 new tests, new files ruff- and mypy-clean, strict-manifest gate green, full unit suite
(1280) passing. `volatility_regime` is wired into the convergence/plateau check (H42).
Remaining R1 follow-ups (non-blocking): `generate_report.py` H44–H46 report-table wiring,
live latency-volatility telemetry (H37), and deliberate profile enablement of the opt-in
gates after calibration. Next: **R2 — real-data realism track.**

### R2 — Realism track: real public datasets (1–2 sprints)

The highest-leverage credibility work. Each dataset ships as a benchmark with an
`evidence_grade` of `validated` (real ground truth) or
`needs-independent-replication`.

| Dataset | Method | Extends |
|---|---|---|
| LaLonde / NSW (job training, RCT) | back-door vs IV; compare to RCT ATE | H1, H24 |
| IHDP (real, not "inspired") | Causal Forest CATE vs known DGP | H35 |
| EPEX / ENTSO-E (European electricity, public) | Causal Forest DML + conformal intervals | H1, H36 (energy) |
| Wikidata / DBpedia subgraph | OG-RAG vs vector RAG grounding | H7, H10 |
| Finnish + Portuguese query set | cross-lingual ontology gain | H21, new H50 |

Pairs naturally with the LUT-dissertation electricity-market alignment.

**Status: IN PROGRESS** (branch `feat/r2-real-data-realism`).
- **LaLonde NSW/PSID — ✅ DONE (H51).** `benchmarks/technical/realworld/benchmark_lalonde.py`
  runs CARF's actual causal engine on the real Dehejia-Wahba RCT (bundled via
  `dowhy.datasets`, no network). Results: experimental ground-truth ATE **$1,794**,
  CARF recovers **$1,676 (6.6% rel error)**; on the confounded NSW+PSID set the naive
  estimate is **−$15,205** while CARF's adjusted estimate is **$752**, a **93.9% bias
  reduction** toward the experimental truth. First `validated` real-ground-truth entry;
  graceful `aspirational`/skipped path if the dataset is ever absent (no fabrication).
  7 tests (pure metrics + real-data recovery).
- **IHDP NPCI — ✅ DONE (H52).** `benchmark_ihdp.py` runs CARF's engine + the
  ChimeraOracle estimator (`CausalForestDML`) on the real-covariate semi-synthetic
  Hill (2011) benchmark (fetched from the public NPCI mirror, cached under `var/`, not
  vendored). True ATE **4.016**, CARF recovers **3.93 (2.2% rel error)**; CATE **PEHE
  0.66 vs 0.86** constant-effect baseline (**23.5% improvement** — captures the real
  heterogeneity). Replaces the old "IHDP-*inspired*" synthetic proxy. Graded
  `needs-independent-replication` (real covariates, *simulated* effects). 8 tests.
  Shared `realworld/_engine.py` helper now backs the engine call (DRY).
- EPEX-ENTSO-E / Wikidata / cross-lingual — PENDING (same harness pattern).

**Exit:** realism manifest median grade moves off "synthetic-only"; H1/H35/H36
gain real-data variants with CIs.

### R3 — Provable governance & grounded verification (2–3 sprints)

- **G8 SHACL governance.** Add a `pyshacl.validate(governance_graph,
  shacl_graph=policy_shapes)` fail-closed step before Guardian approval, reusing
  the `prov_agent.py` JSON-LD context as the ontology seed. New **H49 (SHACL
  Safety Completeness)**: fraction of Guardian policies that are SHACL-encodable
  → provable zero-violation, a stronger claim than 100% detection on synthetic
  cases. Keep CSL-Core/OPA as defence-in-depth.
- **G9 H-Neuron two-stage verification.** Tag LLM claims as propositions →
  validate each against Neo4j (exact match + reachability) → flag unverifiable
  claims with epistemic scores instead of a binary label. New **H47 (NeSy
  Hallucination Precision)**: precision-recall over KG-verifiable claim types.
- **G10 ATA reflector hardening.** Pre-generate an offline, human-reviewed repair
  library keyed by violation type; execute symbolically at runtime; add a
  conformal stop (escalate when calibrated P(retry k succeeds) < α) replacing the
  fixed 0.7 threshold. Restores H4 determinism / H23 injection-resistance through
  the reflector path.
- **G12 RAGAS metrics.** Add context-precision/recall, faithfulness, citation
  accuracy to the RAG eval.

**Exit:** H47, H49 added & graded; reflector path determinism benchmarked.

### R4 — Uncertainty depth & cross-domain transfer (2–3 sprints)

- **G11 Credal sets + MC Dropout.** Credal interval prior for cold-start domains
  (no Experience-Buffer history) to prevent overconfident onboarding approvals;
  MC-Dropout posterior for the LLM causal fallback to replace confidence-string
  parsing. Extends H2 (cold-start coverage); add conformal coverage test to make
  **H44** an interval-calibration test, not a point check.
- **G16 Counterfactual validation.** Validate abduction-action-prediction against
  the do-calculus derivation and audit SCM assumptions (acyclicity, no latent
  confounding) before accepting a counterfactual.
- **G15 Transportability.** Encode selection diagrams; transport a CATE model
  from one scenario DGP to another with partial recalibration. New **H48
  (Transportability)**: CATE transfer accuracy supply-chain → healthcare.
- **G7 PC discovery** for Scope 3 emission-factor DAGs (uses existing
  `causal-learn`) so DAGs are discovered, not hand-specified per scenario.

**Exit:** H44 upgraded to coverage test; H48 added; emission DAGs discovered.

### R5 — Strategic / research tracks (multi-sprint, parallelisable)

- **G13 OG-RAG / OWL ontology** for the symbolic RAG tier (sustainability ESRS,
  supply-chain, medical SNOMED/RxNorm ontologies). Drives H7/H10 and **H50
  (cross-lingual ontology gain)**. Microsoft's OG-RAG is open source — integrate,
  don't re-derive.
- **G14 LLM+ASP Disorder resolution** with an escalation-reduction metric.
- **G17 PINN + DeepOPF electricity-market** use case (physics-as-Guardian-policy,
  differentiable DC-OPF) — the deepest dissertation-aligned capability.
- **G18 Multi-agent causal discovery** (SOTA P3 / Phase 18F) → **H45** on
  >20-variable graphs.

---

## 4. New & upgraded benchmark hypotheses

| ID | Hypothesis | Measurement | Status |
|---|---|---|---|
| H44 | Approximate-inference fidelity | conformal coverage of conjugate posteriors vs full MCMC | upgrade (add coverage) |
| H45 | Multi-agent discovery accuracy | DAG F1: multi- vs single-agent on >20 vars | planned (18F) |
| H46 | Conformal router coverage | prediction set contains true domain at 1−α | **new (R1)** |
| H47 | NeSy hallucination precision | PR curve over KG-verifiable claims | **new (R3)** |
| H48 | Transportability | CATE transfer accuracy across DGPs | **new (R4)** |
| H49 | SHACL safety completeness | % of Guardian policies SHACL-encodable | **new (R3)** |
| H50 | Cross-lingual ontology gain | FI/PT QA: OG-RAG vs vector-only | **new (R5)** |
| H1′/H17′/H35′/H36′ | Real-data variants | LaLonde/IHDP/EPEX/ENTSO-E with RCT/known ground truth | **new (R2)** |

Plus a benchmark-integrity check (SOTA §4.3): assert ground-truth DGP parameters
are **not** in the pipeline environment during evaluation (engine-first principle).

---

## 5. Use-case expansion

- **Electricity-market clearing** (direct LUT alignment): PINN surrogate with
  power-balance constraints as Guardian policies; differentiable DC-OPF on the
  Complicated path; multi-fidelity ARIMA(low)/MCMC(high) via the existing
  `InferenceMode`.
- **Financial risk:** conformal VaR at the Basel-III 99% level + GARCH volatility
  → the most rigorous variant of H36.
- **Climate / sustainability:** PC-discovered emission DAGs; epistemic
  (which factor applies) vs aleatoric (IPCC ±20–30%) split driving different
  Guardian thresholds.
- **Healthcare:** SNOMED CT / RxNorm OWL ontology in the RAG path to replicate
  clinical GraphRAG accuracy within CARF's framework (H35 extension).

---

## 6. Neurosymbolic maturity uplift (FAOS L0–L5)

| Component | Now | Target | Lever |
|---|---|---|---|
| Cynefin Router | L1 (symbolic labels) | L3 | OWL domain taxonomy + conformal sets (G2, G13) |
| Causal Engine | L2 | L4 | identification auto-select + SCM-topology output validation (G3, G16) |
| Guardian / CSL | L4 | L5 | SHACL + closed-loop violation→rule updates (G8) |
| H-Neuron Sentinel | L1 (proxy) | L3 | KG-verified claim checking (G9) |
| 3-Layer RAG | L2 | L4 | OG-RAG OWL/SHACL grounding (G13) |

Router feedback→hint loop already gives router-level L5 behaviour; the work above
extends closed-loop grounding to the other four components.

---

## 7. Safety / SRR alignment

Every item is additive and Guardian-gated, consistent with Supervised Recursive
Refinement and the AP-1…AP-10 antipatterns:

- Conformal/credal layers are **fail-safe**: wider sets/intervals → more
  escalation, never fewer.
- SHACL and the ATA repair library make the governance and reflector paths *more*
  deterministic (AP-3/AP-7 aligned), not less.
- New monitors (ARIMA/GARCH) reduce false positives without loosening any gate.
- Memory-hint weight stays capped at 0.03; closed-loop additions (SHACL rule
  updates, router hints) remain human-reviewable before promotion.

---

## 8. Sequencing & first batch

```
R1 (calibration quick wins)  ──┐
R2 (real-data realism)        ─┼─ parallelisable after R1
R3 (provable governance)       │
R4 (uncertainty + transfer)  ──┘  depends on R1 conformal layer
R5 (strategic research)            independent long-poles
```

**Suggested first PR (R1 batch), all low-effort, zero new architecture:**
1. Domain-softmax entropy + Chaotic rolling-window gate (G5)
2. MAPIE conformal router + H46 benchmark (G2)
3. Front-door/IV identification auto-select (G3)
4. CATE subgroup-differential Guardian policy (G4)

Each ships with a graded manifest entry and a regression test, per the PR1
evidence floor.
