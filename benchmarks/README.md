# CARF Benchmark Suite

Comprehensive benchmarks for the Complex-Adaptive Reasoning Fabric (CARF) platform.
39 falsifiable hypotheses across 9 categories.

## Directory Structure

```
benchmarks/
├── technical/              # Component-level benchmarks
│   ├── router/             # Cynefin domain classification + cross-LLM
│   ├── causal/             # DoWhy/EconML + counterfactual + adversarial
│   ├── bayesian/           # PyMC Bayesian inference calibration
│   ├── guardian/           # CSL/OPA policy enforcement
│   ├── governance/         # MAP-PRICE-RESOLVE-AUDIT + board lifecycle + policy roundtrip
│   ├── chimera/            # ChimeraOracle vs full DoWhy comparison
│   ├── security/           # OWASP LLM Top 10, red team
│   ├── compliance/         # Fairness, XAI, ALCOA+ audit trail
│   ├── sustainability/     # Energy profiling, Scope 3 attribution
│   ├── industry/           # Supply chain, healthcare, finance
│   ├── ux/                 # SUS, task completion, WCAG 2.2
│   ├── performance/        # Latency, load testing, soak testing
│   └── resiliency/         # Chaos cascade, failure containment
├── use_cases/              # End-to-end industry scenario benchmarks
│   ├── supply_chain/
│   ├── financial_risk/
│   ├── sustainability/
│   ├── critical_infra/
│   ├── healthcare/
│   └── energy/
├── baselines/              # Raw LLM baseline + hallucination scale
└── reports/                # Comparison report generation + CLEAR composite
```

## Quick Start

```bash
# Run all demo benchmarks (API must be running)
curl -X POST http://localhost:8000/benchmarks/run-all

# Generate router test set (456 labeled queries)
python benchmarks/technical/router/generate_test_set.py

# Run core technical benchmarks
python benchmarks/technical/router/benchmark_router.py
python benchmarks/technical/causal/benchmark_causal.py
python benchmarks/technical/bayesian/benchmark_bayesian.py
python benchmarks/technical/guardian/benchmark_guardian.py
python benchmarks/technical/performance/benchmark_latency.py --queries 100
python benchmarks/technical/chimera/benchmark_oracle.py
python benchmarks/technical/governance/benchmark_governance.py

# Run security benchmarks
python benchmarks/technical/security/benchmark_owasp.py
python benchmarks/technical/security/benchmark_red_team.py

# Run compliance benchmarks
python benchmarks/technical/compliance/benchmark_fairness.py
python benchmarks/technical/compliance/benchmark_xai.py
python benchmarks/technical/compliance/benchmark_audit_trail.py

# Run governance lifecycle benchmarks
python benchmarks/technical/governance/benchmark_board_lifecycle.py
python benchmarks/technical/governance/benchmark_policy_roundtrip.py
python benchmarks/technical/governance/benchmark_tau_bench.py

# Run causal deep benchmarks
python benchmarks/technical/causal/benchmark_counterbench.py
python benchmarks/technical/causal/benchmark_adversarial_causal.py

# Run industry benchmarks
python benchmarks/technical/industry/benchmark_supply_chain.py
python benchmarks/technical/industry/benchmark_healthcare.py
python benchmarks/technical/industry/benchmark_finance.py

# Run sustainability benchmarks
python benchmarks/technical/sustainability/benchmark_energy.py
python benchmarks/technical/sustainability/benchmark_scope3.py

# Run UX benchmarks
python benchmarks/technical/ux/benchmark_sus.py
python benchmarks/technical/ux/benchmark_task_completion.py
python benchmarks/technical/ux/benchmark_wcag.py

# Run performance / resilience benchmarks
python benchmarks/technical/performance/benchmark_load.py
python benchmarks/technical/performance/benchmark_soak.py
python benchmarks/technical/resiliency/benchmark_chaos_cascade.py

# Run cross-provider and composite benchmarks
python benchmarks/technical/router/benchmark_cross_llm.py
python benchmarks/reports/benchmark_clear.py
python benchmarks/baselines/benchmark_hallucination_scale.py

# Run raw LLM baseline for comparison
python benchmarks/baselines/raw_llm_baseline.py --test-set benchmarks/technical/router/test_set.jsonl

# Run end-to-end use case scenarios
python benchmarks/use_cases/benchmark_e2e.py

# Generate unified comparison report (aggregates all results)
python benchmarks/reports/generate_report.py

# Run strict evidence gate check (CI/release friendly)
python benchmarks/reports/check_result_evidence.py
```

## Realism Validation

Benchmark pass rates are necessary but not sufficient. CARF reports now include a realism/reliability/feasibility validation layer driven by `benchmarks/reports/realism_manifest.json`.

- `realism`: production likeness (data profile, case diversity, adversarial and temporal coverage)
- `reliability`: reproducibility and comparator rigor (seed control, baseline comparator, stress depth)
- `feasibility`: practical execution quality (automation readiness and runtime budget)

Validation outputs are embedded in `benchmark_report.json` under:

- `summary.realism_quality_gate`
- `summary.pass_rate_lower_95ci`
- `summary.realism_score_avg`
- `summary.reliability_score_avg`
- `summary.feasibility_score_avg`
- `summary.absolute_readiness_index`
- `realism_validation`

`absolute_readiness_index` is the primary absolute benchmark quality score, combining realism, reliability, feasibility, and result/manifest coverage.

If realism gate fails, benchmark outcomes should be treated as provisional regardless of grade or raw hypothesis pass rate.

### Result Evidence Requirements

To support absolute reliability claims, each benchmark result artifact should include:

- timestamp metadata (`generated_at`, `timestamp`, or equivalent)
- run configuration (`config` / `params` / runtime settings)
- dataset context (`dataset`, `data_source`, profile/version)
- sample context (`rows`, `scenarios`, `cases`, `queries`, or similar counts)
- provenance fields (`source_reference`, `provenance`, or lineage/version references)

All maintained benchmark runners now call `finalize_benchmark_report(...)` from `benchmarks/__init__.py` before writing results, so these evidence fields are attached by default.

Reports expose this as:

- `summary.evidence_score_avg`
- `summary.strong_evidence_ratio`
- `realism_validation.low_evidence_sources`

For CI/release enforcement, use:

- `python benchmarks/reports/check_result_evidence.py --min-evidence-score 70 --min-strong-ratio 0.8 --max-low-evidence-sources 0`

Exit code is `0` on pass and non-zero on gate failure.

## Benchmark Categories

### Core Technical Benchmarks

| Benchmark | Metrics | Pass Criteria |
|-----------|---------|--------------|
| **Router Classification** (H0) | F1, ECE, Accuracy | Accuracy >= 85% on 200+ queries |
| **Causal Engine** (H1) | ATE MSE, Bias, CI Coverage | MSE ratio <= 0.5 vs LLM |
| **Bayesian Engine** (H2) | Posterior Coverage, CRPS, R-hat | Coverage >= 90% |
| **Guardian Policy** (H3, H4) | Detection Rate, FPR, Determinism | 100% detection, 100% deterministic |
| **EU AI Act** (H5) | Compliance Score | >= 90% compliance |
| **Latency** (H6) | P50/P95/P99 ratio | < 5x raw LLM |
| **Hallucination** (H7) | Reduction Rate | >= 40% reduction |
| **ChimeraOracle** (H8) | Speed Ratio, Accuracy Loss | >= 10x faster, < 20% loss |
| **Memory** (H9) | RSS Growth | < 10% over 500+ queries |

### Governance Benchmarks

| Benchmark | Metrics | Pass Criteria |
|-----------|---------|--------------|
| **MAP Accuracy** (H10) | Cross-domain link detection | >= 70% accuracy (50 cases) |
| **PRICE Accuracy** (H11, H13) | Cost computation precision | >= 95% accuracy (15 cases) |
| **Node Latency** (H12) | P95 latency | < 50ms |
| **RESOLVE** (H14) | Conflict detection rate | >= 80% accuracy (30 cases) |
| **Board Lifecycle** (H15) | CRUD success rate | 100% success |
| **Policy Roundtrip** (H16) | YAML fidelity | >= 95% fidelity |

### Causal Deep Validation

| Benchmark | Metrics | Pass Criteria |
|-----------|---------|--------------|
| **Counterfactual** (H17) | CARF vs LLM accuracy delta | >= 10pp above LLM |
| **Adversarial Causal** (H24) | Robustness under bias | >= 70% correct |

### Competitive / LLM Delta

| Benchmark | Metrics | Pass Criteria |
|-----------|---------|--------------|
| **Tau-Bench** (H18) | Policy compliance rate | >= 95% |
| **Hallucination Scale** (H19) | Rate at 200 cases | <= 10% |
| **Cross-LLM** (H21) | Provider agreement | >= 85% |
| **CLEAR Composite** (H22) | Cost+Latency+Efficacy+Alignment+Robustness | >= 0.75 |

### Security Benchmarks

| Benchmark | Metrics | Pass Criteria |
|-----------|---------|--------------|
| **OWASP LLM** (H23) | Injection block, PII, sanitization | Block >= 90%, PII >= 95% |
| **Red Team** (H25) | Defense across 8 attack surfaces | >= 85% defense rate |

### Compliance Benchmarks

| Benchmark | Metrics | Pass Criteria |
|-----------|---------|--------------|
| **Fairness** (H26) | Demographic parity ratio | >= 0.80 |
| **Explainability** (H27) | Fidelity, stability, simplicity | Fidelity >= 80% |
| **ALCOA+ Audit** (H28) | Compliance rate | >= 95% |

### Sustainability Benchmarks

| Benchmark | Metrics | Pass Criteria |
|-----------|---------|--------------|
| **Energy** (H29) | Proportionality | Clear < Complicated < Complex |
| **Scope 3** (H30) | Attribution accuracy | >= 85% |

### UX Benchmarks

| Benchmark | Metrics | Pass Criteria |
|-----------|---------|--------------|
| **SUS** (H31) | Usability score | >= 68 |
| **Task Completion** (H32) | Success rate | >= 90% |
| **WCAG 2.2** (H33) | Level A violations | == 0 |

### Industry Benchmarks

| Benchmark | Metrics | Pass Criteria |
|-----------|---------|--------------|
| **Supply Chain** (H34) | Prediction precision, lead time | Precision >= 70%, lead >= 48h |
| **Healthcare** (H35) | CATE vs RCT accuracy | >= 90% |
| **Finance VaR** (H36) | Kupiec p-value | > 0.05 |

### Performance & Resilience

| Benchmark | Metrics | Pass Criteria |
|-----------|---------|--------------|
| **Load Test** (H37) | P95 at 25 users | <= 15s |
| **Chaos Cascade** (H38) | Containment rate | >= 80% |
| **Soak Test** (H39) | Memory growth, latency drift | Growth <= 5%, drift <= 10% |

### Use Case Benchmarks

End-to-end scenarios running CARF pipeline and raw LLM baseline side-by-side across 6 industries.

## Grade Scale

| Grade | Criteria |
|-------|----------|
| A+ | >= 80% passed, >= 15 evaluated |
| A | >= 80% passed, >= 10 evaluated |
| B | >= 60% passed, >= 7 evaluated |
| C | >= 40% passed, >= 5 evaluated |
| D | < 40% or insufficient data |
