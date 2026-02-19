# Router Classification Benchmark

Measures CARF's Cynefin domain classification accuracy against a labeled test set.

## Test Set

`test_set.jsonl` — 456 labeled queries across all 5 domains:
- Clear: 101 (factual, deterministic, lookup)
- Complicated: 102 (causal, analytical, diagnostic)
- Complex: 101 (uncertain, emergent, Bayesian)
- Chaotic: 50 (crisis, emergency, urgent)
- Disorder: 102 (ambiguous, contradictory, vague)

## Metrics

| Metric | Target |
|--------|--------|
| Weighted F1 | >= 0.85 |
| ECE (Expected Calibration Error) | < 0.10 |
| Per-domain accuracy drop | < 10% from overall |
| Latency per classification | < 2s |

## Usage

```bash
# Generate test set (already included)
python benchmarks/technical/router/generate_test_set.py

# Run router benchmark
python benchmarks/technical/router/benchmark_router.py

# Run with custom test set
python benchmarks/technical/router/benchmark_router.py --test-set custom.jsonl
```
