# Demo Assets

This folder contains sample data and payloads to exercise the research demo.

## Files

- `data/causal_sample.csv`: Small dataset for DoWhy/EconML demos.
- `payloads/causal_estimation.json`: Example API payload using the sample CSV.
- `payloads/bayesian_inference.json`: Example API payload for PyMC-style inference.

## Usage

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d @demo/payloads/causal_estimation.json
```

If DoWhy is not installed, the service falls back to LLM-based estimation.
Set `CARF_TEST_MODE=1` to avoid requiring API keys when testing.
