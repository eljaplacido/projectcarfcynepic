# CARF Benchmark Suite

Comprehensive benchmarks for the Complex-Adaptive Reasoning Fabric (CARF) platform.

## Directory Structure

```
benchmarks/
├── technical/          # Component-level benchmarks
│   ├── router/         # Cynefin domain classification accuracy
│   ├── causal/         # DoWhy/EconML causal effect estimation
│   ├── bayesian/       # PyMC Bayesian inference calibration
│   ├── guardian/       # CSL/OPA policy enforcement
│   ├── chimera/        # ChimeraOracle vs full DoWhy comparison
│   └── performance/    # Latency, memory, concurrency
├── use_cases/          # End-to-end industry scenario benchmarks
│   ├── supply_chain/
│   ├── financial_risk/
│   ├── sustainability/
│   ├── critical_infra/
│   ├── healthcare/
│   └── energy/
├── baselines/          # Raw LLM baseline (no CARF pipeline)
└── reports/            # Comparison report generation
```

## Quick Start

```bash
# Run all demo benchmarks (API must be running)
curl -X POST http://localhost:8000/benchmarks/run-all

# Generate router test set (456 labeled queries)
python benchmarks/technical/router/generate_test_set.py

# Run individual technical benchmarks
python benchmarks/technical/router/benchmark_router.py
python benchmarks/technical/causal/benchmark_causal.py
python benchmarks/technical/bayesian/benchmark_bayesian.py
python benchmarks/technical/guardian/benchmark_guardian.py
python benchmarks/technical/performance/benchmark_latency.py --queries 100
python benchmarks/technical/chimera/benchmark_oracle.py

# Run raw LLM baseline for comparison
python benchmarks/baselines/raw_llm_baseline.py --test-set benchmarks/technical/router/test_set.jsonl

# Run end-to-end use case scenarios
python benchmarks/use_cases/benchmark_e2e.py

# Generate unified comparison report (aggregates all results)
python benchmarks/reports/generate_report.py
```

## Benchmark Categories

### Technical Benchmarks

| Benchmark | Metrics | Pass Criteria |
|-----------|---------|--------------|
| **Router Classification** | F1, ECE, Latency | F1 >= 0.85, ECE < 0.10 |
| **Causal Engine** | ATE MSE, Bias, CI Coverage | MSE < 0.5 (IHDP) |
| **Bayesian Engine** | Posterior Coverage, CRPS, R-hat | Coverage >= 90% |
| **Guardian Policy** | Detection Rate, FPR, Determinism | 100% detection, < 5% FPR |
| **ChimeraOracle** | RMSE vs DoWhy, Speed Ratio | Within 20%, >= 10x faster |
| **Performance** | P50/P95/P99, Memory, Concurrency | P95 < 10s |

### Use Case Benchmarks

End-to-end scenarios running CARF pipeline and raw LLM baseline side-by-side across 6 industries.

### Hypotheses Tested

9 falsifiable hypotheses comparing CARF vs raw LLM on:
- H1: ATE accuracy (>=50% lower MSE)
- H2: Posterior coverage (>=90% vs ~60-70%)
- H3: Policy violation detection (100% vs ~80%)
- H4: Guardian determinism (100% vs variable)
- H5: EU AI Act compliance (>=90% vs <30%)
- H6: Latency tradeoff (2-5x slower, quality compensates)
- H7: Hallucination reduction (>=40%)
- H8: ChimeraOracle speed (>=10x, <20% accuracy loss)
- H9: Memory stability (stable over 500+ queries)
