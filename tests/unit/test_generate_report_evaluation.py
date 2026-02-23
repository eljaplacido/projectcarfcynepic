"""Regression tests for hypothesis evaluation fallback handling."""

from benchmarks.reports.generate_report import evaluate_hypotheses


def _eval_by_id(evaluations: list[dict], hypothesis_id: str) -> dict:
    for evaluation in evaluations:
        if evaluation.get("id") == hypothesis_id:
            return evaluation
    raise AssertionError(f"Hypothesis {hypothesis_id} not found")


def test_evaluate_hypotheses_preserves_zero_metrics():
    """Zero-valued metrics must still be treated as present/evaluated."""
    results = {
        "causal": {"mse": 0.0},
        "baseline": {"causal_mse": 1.0},
        "bayesian": {"coverage": 0.0},
        "router": {"overall_accuracy": 0.0},
        "counterbench": {"accuracy_delta": 0.0},
        "healthcare": {"cate_accuracy_vs_rct": 0.0},
        "soak": {"memory_growth_pct": 0.0, "latency_drift_pct": 0.0},
    }

    evaluations = evaluate_hypotheses(results)

    h2 = _eval_by_id(evaluations, "H2")
    assert h2["status"] == "evaluated"
    assert h2["metric_value"] == 0.0

    h17 = _eval_by_id(evaluations, "H17")
    assert h17["status"] == "evaluated"
    assert h17["metric_value"] == 0.0

    h35 = _eval_by_id(evaluations, "H35")
    assert h35["status"] == "evaluated"
    assert h35["metric_value"] == 0.0

    h39 = _eval_by_id(evaluations, "H39")
    assert h39["status"] == "evaluated"
    assert h39["metric_value"] == 0.0
    assert h39["details"].get("latency_drift") == 0.0


def test_evaluate_hypotheses_reads_nested_metrics_payloads():
    """Nested `metrics` payloads must be recognized for new benchmark suites."""
    results = {
        "counterbench": {"metrics": {"accuracy_gap": 0.12}},
        "adversarial_causal": {"metrics": {"robustness_rate": 0.75}},
        "tau_bench": {"metrics": {"policy_compliance_rate": 0.97, "correct_escalation_rate": 0.98}},
        "hallucination_scale": {"metrics": {"carf_hallucination_rate": 0.05, "reduction": 0.7}},
        "cross_llm": {"metrics": {"cross_provider_agreement": 0.9}},
        "clear": {"metrics": {"clear_composite": 0.8, "sub_scores": {"cost": 0.8}}},
        "fairness": {"metrics": {"demographic_parity_ratio": 0.85, "equalized_odds_diff": 0.02}},
        "xai": {"metrics": {"fidelity": 0.88, "stability": 0.91, "avg_steps": 4.2}},
        "audit_trail": {"metrics": {"alcoa_compliance_rate": 0.99}},
        "energy": {"metrics": {"energy_proportional": True}},
        "scope3": {"metrics": {"estimate_accuracy": 0.9}},
        "sus": {"metrics": {"sus_score": 72.0}},
        "task_completion": {"metrics": {"success_rate": 0.94}},
        "wcag": {"metrics": {"level_a_violations": 0}},
        "supply_chain": {"metrics": {"precision": 0.77, "prediction_lead_time_hours": 72}},
        "healthcare": {"metrics": {"cate_accuracy_vs_rct": 0.93}},
        "finance": {"metrics": {"kupiec_pvalue": 0.12}},
        "load": {"metrics": {"p95_at_25_users": 12.5}},
        "chaos_cascade": {"metrics": {"cascade_containment": 0.88}},
        "soak": {"metrics": {"memory_growth_pct": 2.2, "latency_drift_pct": 1.1}},
    }

    evaluations = evaluate_hypotheses(results)

    assert _eval_by_id(evaluations, "H17")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H24")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H18")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H19")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H21")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H22")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H26")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H27")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H28")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H29")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H30")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H31")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H32")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H33")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H34")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H35")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H36")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H37")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H38")["status"] == "evaluated"
    assert _eval_by_id(evaluations, "H39")["status"] == "evaluated"
