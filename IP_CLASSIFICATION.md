# Intellectual Property Classification

All code in this repository is governed by the Business Source
License 1.1. This document identifies the IP tier of core modules
per the Cisuregen IP framework.

## Tier 1 -- Core Innovation

Original architectural contributions with no prior art equivalent:

- `src/workflows/router.py` -- Entropy-aware Cynefin routing logic
  (Shannon entropy, memory augmentation, causal language boost,
  dual-model classification, per-domain confidence thresholds)
- `src/workflows/guardian.py` -- Deterministic policy enforcement
  pipeline (CSL-Core + OPA + decomposed risk scoring, fail-closed)
- `src/workflows/graph.py` -- LangGraph state graph orchestration
  (domain-routed analytical pipeline with conditional fast-path)
- `src/core/state.py` -- EpistemicState schema (the central state
  object carrying classification, evidence, uncertainty, policy
  verdicts, and audit provenance through all processing stages)
- `config/policies/` -- CSL-Core formal constraint definitions
  (domain-specific constraint language compiled to Z3 SMT)

## Tier 2 -- Differentiating Assets

Proprietary orchestration and integration logic built on
third-party libraries:

- `src/services/causal.py` -- Causal engine workflow (DAG
  construction, do-calculus identification, multi-method estimation,
  automated refutation testing, ChimeraOracle fast-path)
- `src/services/bayesian.py` -- Bayesian active inference
  (epistemic/aleatoric uncertainty decomposition, MCMC posterior
  sampling, safe-to-fail exploration probes)
- `src/services/neurosymbolic_engine.py` -- Neural-symbolic
  integration loop (LLM fact extraction, forward-chaining, shortcut
  detection, constraint validation)
- `src/services/causal_world_model.py` -- Structural Causal Models
  (SCM simulation, counterfactual reasoning)
- `src/services/counterfactual_engine.py` -- Pearl Level 3
  counterfactual procedure (abduction, action, prediction)
- `src/services/h_neuron_interceptor.py` -- H-Neuron multi-signal
  hallucination detection (8-signal weighted fusion)
- `src/services/drift_detector.py` -- KL-divergence drift monitoring
- `src/services/bias_auditor.py` -- Chi-squared fairness auditing
- `src/services/router_retraining_service.py` -- Active learning
  pipeline with plateau detection

## Tier 3 -- Supporting Assets

- `src/services/governance_service.py` -- MAP-PRICE-RESOLVE
  orchestrator (semantic extraction, cost tracking, conflict
  detection)
- `src/services/transparency.py` -- Agent reliability, EU AI Act
  compliance reporting, chain-of-thought tracing
- `src/services/insights_service.py` -- Persona-based insights
  (analyst, developer, executive)
- `src/services/agent_tracker.py` -- LLM usage tracking (tokens,
  latency, cost)
- `src/api/routers/` -- 17 API routers exposing CARF capabilities

## Tier 4 -- Third-Party Dependencies

DoWhy, EconML, PyMC, NetworkX, Neo4j, LangGraph, OPA, Kafka, Z3,
DistilBERT, Sentence-Transformers, FastAPI, React.

These are NOT Cisuregen IP. See `pyproject.toml` for versions
and their respective licenses. See `NOTICE` for full attribution.

## Trade Secret Notice

Specific threshold calibrations, scoring weights, trained model
artifacts, and policy enforcement matrices are trade secrets and
are NOT included in this repository. The source code shows the
architecture and algorithms; the production-grade configurations
that make them effective are available only under commercial license.
