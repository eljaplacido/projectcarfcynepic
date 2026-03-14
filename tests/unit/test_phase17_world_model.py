# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Unit tests for Phase 17 — World Model, Neurosymbolic, and Counterfactual.

Tests cover:
- CausalWorldModel (SCM evaluation, simulation, counterfactuals, learning)
- KnowledgeBase (facts, rules, forward chaining, gap detection)
- CounterfactualEngine data models
- State model extensions (CounterfactualEvidence, NeurosymbolicEvidence)
- API router route registration and request/response model validation
"""

import math

import numpy as np
import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# CausalWorldModel imports
# ---------------------------------------------------------------------------
from src.services.causal_world_model import (
    CausalWorldModel,
    CounterfactualResult as WMCounterfactualResult,
    SimulationTrajectory,
    StructuralEquation,
)

# ---------------------------------------------------------------------------
# Neurosymbolic imports
# ---------------------------------------------------------------------------
from src.services.neurosymbolic_engine import (
    KnowledgeBase,
    RuleCondition,
    SymbolicFact,
    SymbolicRule,
)

# ---------------------------------------------------------------------------
# Counterfactual engine imports
# ---------------------------------------------------------------------------
from src.services.counterfactual_engine import (
    CausalAttributionItem,
    CounterfactualQuery,
    CounterfactualResult as CFCounterfactualResult,
)

# ---------------------------------------------------------------------------
# State model imports
# ---------------------------------------------------------------------------
from src.core.state import (
    CounterfactualEvidence,
    EpistemicState,
    NeurosymbolicEvidence,
)

# ---------------------------------------------------------------------------
# CausalGraph imports (for learn_from_data)
# ---------------------------------------------------------------------------
from src.services.causal import CausalGraph, CausalVariable


# =============================================================================
# 1. CausalWorldModel tests
# =============================================================================


class TestStructuralEquation:
    """Tests for StructuralEquation.evaluate()."""

    def test_linear_evaluate_no_parents(self):
        """Linear equation with no parents returns intercept + noise."""
        eq = StructuralEquation(
            variable="Y",
            parents=[],
            coefficients={},
            intercept=5.0,
            noise_std=0.1,
            equation_type="linear",
        )
        result = eq.evaluate({}, noise=0.0)
        assert result == pytest.approx(5.0)

    def test_linear_evaluate_with_parents(self):
        """Linear equation: Y = 2.0 + 3.0*X1 + (-1.0)*X2."""
        eq = StructuralEquation(
            variable="Y",
            parents=["X1", "X2"],
            coefficients={"X1": 3.0, "X2": -1.0},
            intercept=2.0,
            equation_type="linear",
        )
        result = eq.evaluate({"X1": 1.0, "X2": 2.0}, noise=0.0)
        # 2.0 + 3.0*1.0 + (-1.0)*2.0 = 2.0 + 3.0 - 2.0 = 3.0
        assert result == pytest.approx(3.0)

    def test_linear_evaluate_with_noise(self):
        """Linear equation adds noise term."""
        eq = StructuralEquation(
            variable="Y",
            parents=[],
            coefficients={},
            intercept=10.0,
            equation_type="linear",
        )
        result = eq.evaluate({}, noise=0.5)
        assert result == pytest.approx(10.5)

    def test_logistic_evaluate(self):
        """Logistic equation applies sigmoid."""
        eq = StructuralEquation(
            variable="Y",
            parents=["X"],
            coefficients={"X": 1.0},
            intercept=0.0,
            equation_type="logistic",
        )
        # sigmoid(0) = 0.5
        result = eq.evaluate({"X": 0.0}, noise=0.0)
        assert result == pytest.approx(0.5)

    def test_logistic_evaluate_large_positive(self):
        """Logistic equation for large positive input approaches 1.0."""
        eq = StructuralEquation(
            variable="Y",
            parents=["X"],
            coefficients={"X": 1.0},
            intercept=0.0,
            equation_type="logistic",
        )
        result = eq.evaluate({"X": 10.0}, noise=0.0)
        assert result > 0.99

    def test_logistic_evaluate_large_negative(self):
        """Logistic equation for large negative input approaches 0.0."""
        eq = StructuralEquation(
            variable="Y",
            parents=["X"],
            coefficients={"X": 1.0},
            intercept=0.0,
            equation_type="logistic",
        )
        result = eq.evaluate({"X": -10.0}, noise=0.0)
        assert result < 0.01

    def test_missing_parent_defaults_to_zero(self):
        """Missing parent value defaults to 0.0."""
        eq = StructuralEquation(
            variable="Y",
            parents=["X"],
            coefficients={"X": 5.0},
            intercept=1.0,
            equation_type="linear",
        )
        result = eq.evaluate({}, noise=0.0)
        # 1.0 + 5.0*0.0 = 1.0
        assert result == pytest.approx(1.0)


class TestCausalWorldModelEvaluate:
    """Tests for CausalWorldModel.evaluate()."""

    def _build_simple_scm(self) -> CausalWorldModel:
        """Build X -> Y SCM: Y = 1.0 + 2.0*X."""
        model = CausalWorldModel(model_id="test")
        model.add_equation(StructuralEquation(
            variable="X",
            parents=[],
            coefficients={},
            intercept=3.0,
            equation_type="linear",
        ))
        model.add_equation(StructuralEquation(
            variable="Y",
            parents=["X"],
            coefficients={"X": 2.0},
            intercept=1.0,
            equation_type="linear",
        ))
        return model

    def test_basic_evaluate(self):
        """Evaluate SCM without interventions or noise."""
        model = self._build_simple_scm()
        state = model.evaluate()
        # X = 3.0, Y = 1.0 + 2.0*3.0 = 7.0
        assert state["X"] == pytest.approx(3.0)
        assert state["Y"] == pytest.approx(7.0)

    def test_evaluate_with_exogenous_noise(self):
        """Evaluate SCM with exogenous noise terms."""
        model = self._build_simple_scm()
        state = model.evaluate(exogenous={"X": 0.5, "Y": -0.5})
        # X = 3.0 + 0.5 = 3.5, Y = 1.0 + 2.0*3.5 + (-0.5) = 7.5
        assert state["X"] == pytest.approx(3.5)
        assert state["Y"] == pytest.approx(7.5)

    def test_evaluate_with_intervention(self):
        """do(X=10) overrides the structural equation for X."""
        model = self._build_simple_scm()
        state = model.evaluate(interventions={"X": 10.0})
        # X = 10.0 (intervention), Y = 1.0 + 2.0*10.0 = 21.0
        assert state["X"] == pytest.approx(10.0)
        assert state["Y"] == pytest.approx(21.0)

    def test_evaluate_intervention_on_child(self):
        """do(Y=0) overrides Y regardless of X."""
        model = self._build_simple_scm()
        state = model.evaluate(interventions={"Y": 0.0})
        # X = 3.0 (normal), Y = 0.0 (intervention)
        assert state["X"] == pytest.approx(3.0)
        assert state["Y"] == pytest.approx(0.0)


class TestCausalWorldModelSimulate:
    """Tests for CausalWorldModel.simulate()."""

    def _build_model(self) -> CausalWorldModel:
        model = CausalWorldModel(model_id="sim-test")
        model.add_equation(StructuralEquation(
            variable="X",
            parents=[],
            coefficients={},
            intercept=1.0,
            noise_std=0.01,
            equation_type="linear",
        ))
        model.add_equation(StructuralEquation(
            variable="Y",
            parents=["X"],
            coefficients={"X": 2.0},
            intercept=0.0,
            noise_std=0.01,
            equation_type="linear",
        ))
        return model

    def test_trajectory_length(self):
        """Simulation with N steps produces N+1 trajectory entries."""
        model = self._build_model()
        result = model.simulate(steps=5, seed=42)
        assert isinstance(result, SimulationTrajectory)
        assert len(result.trajectory) == 6  # initial + 5 steps
        assert result.steps == 5

    def test_trajectory_length_custom_steps(self):
        """Different step counts produce correct trajectory lengths."""
        model = self._build_model()
        for steps in (1, 3, 10):
            result = model.simulate(steps=steps, seed=0)
            assert len(result.trajectory) == steps + 1

    def test_simulation_with_intervention(self):
        """Intervention holds the intervened variable constant."""
        model = self._build_model()
        result = model.simulate(interventions={"X": 5.0}, steps=3, seed=42)
        for entry in result.trajectory:
            assert entry["X"] == pytest.approx(5.0)

    def test_simulation_variables_and_model_id(self):
        """Simulation result carries variable names and model id."""
        model = self._build_model()
        result = model.simulate(steps=1, seed=0)
        assert set(result.variables) == {"X", "Y"}
        assert result.model_id == "sim-test"

    def test_deterministic_with_seed(self):
        """Same seed produces identical trajectories."""
        model = self._build_model()
        r1 = model.simulate(steps=5, seed=123)
        r2 = model.simulate(steps=5, seed=123)
        for a, b in zip(r1.trajectory, r2.trajectory):
            for var in model.variables:
                assert a[var] == pytest.approx(b[var])


class TestCausalWorldModelCounterfactual:
    """Tests for CausalWorldModel.counterfactual() — three-step reasoning."""

    def _build_model(self) -> CausalWorldModel:
        """X -> Y: Y = 1 + 2*X."""
        model = CausalWorldModel(model_id="cf-test")
        model.add_equation(StructuralEquation(
            variable="X", parents=[], coefficients={}, intercept=3.0,
        ))
        model.add_equation(StructuralEquation(
            variable="Y", parents=["X"], coefficients={"X": 2.0}, intercept=1.0,
        ))
        return model

    def test_counterfactual_returns_result(self):
        """Counterfactual returns a CounterfactualResult with all fields."""
        model = self._build_model()
        factual = {"X": 3.0, "Y": 7.0}
        result = model.counterfactual(factual, intervention={"X": 5.0})
        assert isinstance(result, WMCounterfactualResult)
        assert result.factual_state == factual
        assert "X" in result.counterfactual_state
        assert "Y" in result.counterfactual_state
        assert "X" in result.intervention

    def test_counterfactual_correct_values(self):
        """Counterfactual computes correct values for simple SCM."""
        model = self._build_model()
        # Factual: X=3, Y=7 (matches structural equations perfectly)
        factual = {"X": 3.0, "Y": 7.0}
        result = model.counterfactual(factual, intervention={"X": 5.0})
        # Counterfactual: do(X=5), Y = 1 + 2*5 = 11
        assert result.counterfactual_state["X"] == pytest.approx(5.0)
        assert result.counterfactual_state["Y"] == pytest.approx(11.0)

    def test_counterfactual_differences(self):
        """Differences dict = counterfactual - factual for each variable."""
        model = self._build_model()
        factual = {"X": 3.0, "Y": 7.0}
        result = model.counterfactual(factual, intervention={"X": 5.0})
        assert result.differences["X"] == pytest.approx(2.0)
        assert result.differences["Y"] == pytest.approx(4.0)

    def test_counterfactual_with_noise_abduction(self):
        """Abduction step correctly infers noise when factual deviates from model."""
        model = self._build_model()
        # Factual observation where Y deviates: model predicts 7, observed 8 -> noise=1
        factual = {"X": 3.0, "Y": 8.0}
        result = model.counterfactual(factual, intervention={"X": 5.0})
        # Abducted noise for Y should be 1.0 (8.0 - 7.0)
        assert result.abducted_noise["Y"] == pytest.approx(1.0)
        # Counterfactual: Y = 1 + 2*5 + 1 (abducted noise) = 12
        assert result.counterfactual_state["Y"] == pytest.approx(12.0)


class TestCausalWorldModelLearnFromData:
    """Tests for CausalWorldModel.learn_from_data()."""

    def _make_graph(self) -> CausalGraph:
        """Build a simple X -> Y causal graph."""
        graph = CausalGraph()
        graph.add_node(CausalVariable(
            name="X", description="treatment", variable_type="continuous", role="treatment",
        ))
        graph.add_node(CausalVariable(
            name="Y", description="outcome", variable_type="continuous", role="outcome",
        ))
        graph.add_edge("X", "Y")
        return graph

    def test_learn_produces_equations(self):
        """Learning from data produces structural equations for all variables."""
        rng = np.random.default_rng(42)
        n = 100
        x = rng.normal(5.0, 1.0, n)
        y = 2.0 + 3.0 * x + rng.normal(0, 0.1, n)
        data = [{"X": float(x[i]), "Y": float(y[i])} for i in range(n)]

        graph = self._make_graph()
        model = CausalWorldModel.learn_from_data(data, graph)

        assert "X" in model.equations
        assert "Y" in model.equations

    def test_learned_coefficients_approximate(self):
        """Learned coefficient for Y ~ X is close to the true value."""
        rng = np.random.default_rng(42)
        n = 200
        x = rng.normal(5.0, 1.0, n)
        y = 2.0 + 3.0 * x + rng.normal(0, 0.1, n)
        data = [{"X": float(x[i]), "Y": float(y[i])} for i in range(n)]

        graph = self._make_graph()
        model = CausalWorldModel.learn_from_data(data, graph)

        eq_y = model.equations["Y"]
        assert eq_y.coefficients["X"] == pytest.approx(3.0, abs=0.2)
        assert eq_y.intercept == pytest.approx(2.0, abs=0.5)

    def test_learn_root_node_intercept(self):
        """Root node (no parents) learns intercept ~ mean of data."""
        rng = np.random.default_rng(0)
        n = 100
        x = rng.normal(10.0, 1.0, n)
        y = 1.0 + 2.0 * x + rng.normal(0, 0.1, n)
        data = [{"X": float(x[i]), "Y": float(y[i])} for i in range(n)]

        graph = self._make_graph()
        model = CausalWorldModel.learn_from_data(data, graph)

        eq_x = model.equations["X"]
        assert eq_x.parents == []
        assert eq_x.intercept == pytest.approx(10.0, abs=0.5)

    def test_learn_empty_data(self):
        """Learning from empty data returns model with no equations."""
        graph = self._make_graph()
        model = CausalWorldModel.learn_from_data([], graph)
        assert len(model.equations) == 0


class TestTopologicalOrder:
    """Tests for CausalWorldModel.topological_order."""

    def test_simple_chain(self):
        """X -> Y -> Z gives order [X, Y, Z]."""
        model = CausalWorldModel()
        model.add_equation(StructuralEquation(variable="Z", parents=["Y"], coefficients={"Y": 1.0}))
        model.add_equation(StructuralEquation(variable="Y", parents=["X"], coefficients={"X": 1.0}))
        model.add_equation(StructuralEquation(variable="X", parents=[], coefficients={}))

        order = model.topological_order
        assert order.index("X") < order.index("Y")
        assert order.index("Y") < order.index("Z")

    def test_diamond_dag(self):
        """X -> M1, X -> M2, M1 -> Y, M2 -> Y: X before M1,M2 before Y."""
        model = CausalWorldModel()
        model.add_equation(StructuralEquation(variable="X", parents=[]))
        model.add_equation(StructuralEquation(
            variable="M1", parents=["X"], coefficients={"X": 1.0},
        ))
        model.add_equation(StructuralEquation(
            variable="M2", parents=["X"], coefficients={"X": 1.0},
        ))
        model.add_equation(StructuralEquation(
            variable="Y", parents=["M1", "M2"],
            coefficients={"M1": 1.0, "M2": 1.0},
        ))

        order = model.topological_order
        assert order.index("X") < order.index("M1")
        assert order.index("X") < order.index("M2")
        assert order.index("M1") < order.index("Y")
        assert order.index("M2") < order.index("Y")

    def test_no_equations(self):
        """Model with no equations has empty topological order."""
        model = CausalWorldModel()
        assert model.topological_order == []

    def test_single_variable(self):
        """Single root variable."""
        model = CausalWorldModel()
        model.add_equation(StructuralEquation(variable="X", parents=[]))
        assert model.topological_order == ["X"]

    def test_caching_invalidation(self):
        """Adding a new equation invalidates cached topological order."""
        model = CausalWorldModel()
        model.add_equation(StructuralEquation(variable="X", parents=[]))
        order1 = model.topological_order
        assert order1 == ["X"]

        model.add_equation(StructuralEquation(
            variable="Y", parents=["X"], coefficients={"X": 1.0},
        ))
        order2 = model.topological_order
        assert "Y" in order2


# =============================================================================
# 2. KnowledgeBase tests
# =============================================================================


class TestKnowledgeBaseAddFact:
    """Tests for KnowledgeBase.add_fact() — deduplication and confidence."""

    def test_add_new_fact(self):
        """Adding a new fact returns True."""
        kb = KnowledgeBase()
        fact = SymbolicFact(entity="CO2", attribute="type", value="greenhouse_gas")
        assert kb.add_fact(fact) is True
        assert kb.size == 1

    def test_duplicate_fact_same_confidence(self):
        """Adding duplicate fact with same confidence returns False."""
        kb = KnowledgeBase()
        f1 = SymbolicFact(entity="CO2", attribute="type", value="greenhouse_gas", confidence=0.9)
        f2 = SymbolicFact(entity="CO2", attribute="type", value="greenhouse_gas", confidence=0.9)
        kb.add_fact(f1)
        assert kb.add_fact(f2) is False
        assert kb.size == 1

    def test_higher_confidence_replaces(self):
        """A fact with higher confidence replaces the existing one."""
        kb = KnowledgeBase()
        f1 = SymbolicFact(entity="CO2", attribute="type", value="greenhouse_gas", confidence=0.5)
        f2 = SymbolicFact(entity="CO2", attribute="type", value="greenhouse_gas", confidence=0.9)
        kb.add_fact(f1)
        result = kb.add_fact(f2)
        assert result is True
        assert kb.size == 1
        key = f2.key
        assert kb.facts[key].confidence == 0.9

    def test_lower_confidence_does_not_replace(self):
        """A fact with lower confidence does NOT replace."""
        kb = KnowledgeBase()
        f1 = SymbolicFact(entity="CO2", attribute="type", value="greenhouse_gas", confidence=0.9)
        f2 = SymbolicFact(entity="CO2", attribute="type", value="greenhouse_gas", confidence=0.5)
        kb.add_fact(f1)
        assert kb.add_fact(f2) is False
        key = f1.key
        assert kb.facts[key].confidence == 0.9

    def test_different_values_are_separate(self):
        """Facts with different values are not duplicates."""
        kb = KnowledgeBase()
        f1 = SymbolicFact(entity="CO2", attribute="effect", value="warming")
        f2 = SymbolicFact(entity="CO2", attribute="effect", value="acidification")
        kb.add_fact(f1)
        kb.add_fact(f2)
        assert kb.size == 2


class TestKnowledgeBaseAddRule:
    """Tests for KnowledgeBase.add_rule() — deduplication."""

    def test_add_rule(self):
        """Adding a rule increases rules list."""
        kb = KnowledgeBase()
        rule = SymbolicRule(
            rule_id="r1",
            name="test-rule",
            conditions=[RuleCondition(attribute="type", operator="==", value="greenhouse_gas")],
            conclusion_attribute="risk",
            conclusion_value="high",
        )
        kb.add_rule(rule)
        assert len(kb.rules) == 1

    def test_duplicate_rule_id_ignored(self):
        """Rule with same rule_id is not added twice."""
        kb = KnowledgeBase()
        rule = SymbolicRule(rule_id="r1", name="test-rule")
        kb.add_rule(rule)
        kb.add_rule(rule)
        assert len(kb.rules) == 1

    def test_different_rule_ids_both_added(self):
        """Rules with different ids are both added."""
        kb = KnowledgeBase()
        kb.add_rule(SymbolicRule(rule_id="r1", name="rule-1"))
        kb.add_rule(SymbolicRule(rule_id="r2", name="rule-2"))
        assert len(kb.rules) == 2


class TestKnowledgeBaseForwardChain:
    """Tests for KnowledgeBase.forward_chain()."""

    def test_derives_new_fact(self):
        """Forward chaining derives a new fact when conditions are met."""
        kb = KnowledgeBase()
        kb.add_fact(SymbolicFact(
            entity="CO2", attribute="type", value="greenhouse_gas",
        ))
        kb.add_rule(SymbolicRule(
            rule_id="r1",
            name="ghg-risk",
            conditions=[RuleCondition(attribute="type", operator="==", value="greenhouse_gas")],
            conclusion_attribute="risk_level",
            conclusion_value="high",
        ))

        derived = kb.forward_chain()
        assert len(derived) >= 1
        assert any(f.attribute == "risk_level" and f.value == "high" for f in derived)

    def test_no_derivation_when_conditions_unmet(self):
        """No facts derived when rule conditions are not satisfied."""
        kb = KnowledgeBase()
        kb.add_fact(SymbolicFact(
            entity="H2O", attribute="type", value="liquid",
        ))
        kb.add_rule(SymbolicRule(
            rule_id="r1",
            name="ghg-risk",
            conditions=[RuleCondition(attribute="type", operator="==", value="greenhouse_gas")],
            conclusion_attribute="risk_level",
            conclusion_value="high",
        ))

        derived = kb.forward_chain()
        assert len(derived) == 0

    def test_chained_derivation(self):
        """Forward chaining can chain: A -> B -> C."""
        kb = KnowledgeBase()
        kb.add_fact(SymbolicFact(
            entity="system", attribute="temperature", value="high",
        ))
        kb.add_rule(SymbolicRule(
            rule_id="r1",
            name="temp-to-stress",
            conditions=[RuleCondition(attribute="temperature", operator="==", value="high")],
            conclusion_attribute="stress",
            conclusion_value="elevated",
        ))
        kb.add_rule(SymbolicRule(
            rule_id="r2",
            name="stress-to-alert",
            conditions=[RuleCondition(attribute="stress", operator="==", value="elevated")],
            conclusion_attribute="alert",
            conclusion_value="yes",
        ))

        derived = kb.forward_chain()
        attrs = {f.attribute for f in derived}
        assert "stress" in attrs
        assert "alert" in attrs

    def test_derived_fact_has_decayed_confidence(self):
        """Derived facts have slightly decayed confidence (rule.confidence * 0.95)."""
        kb = KnowledgeBase()
        kb.add_fact(SymbolicFact(entity="X", attribute="a", value="1"))
        kb.add_rule(SymbolicRule(
            rule_id="r1",
            name="derive-b",
            conditions=[RuleCondition(attribute="a", operator="==", value="1")],
            conclusion_attribute="b",
            conclusion_value="2",
            confidence=1.0,
        ))

        derived = kb.forward_chain()
        assert len(derived) == 1
        assert derived[0].confidence == pytest.approx(0.95)


class TestKnowledgeBaseGetGaps:
    """Tests for KnowledgeBase.get_gaps()."""

    def test_identifies_missing_attribute(self):
        """Reports gap when a rule condition has no matching fact."""
        kb = KnowledgeBase()
        kb.add_rule(SymbolicRule(
            rule_id="r1",
            name="needs-temp",
            conditions=[RuleCondition(attribute="temperature", operator=">", value="30")],
            conclusion_attribute="alert",
            conclusion_value="yes",
        ))

        gaps = kb.get_gaps()
        assert len(gaps) == 1
        assert "temperature" in gaps[0]

    def test_no_gaps_when_all_conditions_met(self):
        """No gaps when all rule conditions have matching facts."""
        kb = KnowledgeBase()
        kb.add_fact(SymbolicFact(entity="sensor", attribute="temperature", value="35"))
        kb.add_rule(SymbolicRule(
            rule_id="r1",
            name="temp-check",
            conditions=[RuleCondition(attribute="temperature", operator=">", value="30")],
            conclusion_attribute="alert",
            conclusion_value="yes",
        ))

        gaps = kb.get_gaps()
        assert len(gaps) == 0

    def test_multiple_gaps(self):
        """Reports multiple gaps from different rules."""
        kb = KnowledgeBase()
        kb.add_rule(SymbolicRule(
            rule_id="r1",
            name="rule-a",
            conditions=[RuleCondition(attribute="pressure", operator=">", value="100")],
            conclusion_attribute="x",
            conclusion_value="y",
        ))
        kb.add_rule(SymbolicRule(
            rule_id="r2",
            name="rule-b",
            conditions=[RuleCondition(attribute="humidity", operator="<", value="20")],
            conclusion_attribute="x",
            conclusion_value="y",
        ))

        gaps = kb.get_gaps()
        assert len(gaps) == 2


class TestRuleOperators:
    """Tests for SymbolicRule.evaluate() with different operators."""

    def _make_kb_with_fact(self, attribute: str, value: str) -> dict[str, SymbolicFact]:
        fact = SymbolicFact(entity="test", attribute=attribute, value=value)
        return {fact.key: fact}

    def test_equals_operator(self):
        """== operator matches exact value."""
        rule = SymbolicRule(
            rule_id="r1",
            conditions=[RuleCondition(attribute="status", operator="==", value="active")],
        )
        facts = self._make_kb_with_fact("status", "active")
        assert rule.evaluate(facts) is True

    def test_not_equals_operator(self):
        """!= operator matches different value."""
        rule = SymbolicRule(
            rule_id="r1",
            conditions=[RuleCondition(attribute="status", operator="!=", value="active")],
        )
        facts = self._make_kb_with_fact("status", "inactive")
        assert rule.evaluate(facts) is True

    def test_not_equals_fails_on_same(self):
        """!= operator fails when value matches."""
        rule = SymbolicRule(
            rule_id="r1",
            conditions=[RuleCondition(attribute="status", operator="!=", value="active")],
        )
        facts = self._make_kb_with_fact("status", "active")
        assert rule.evaluate(facts) is False

    def test_greater_than_operator(self):
        """> operator works with numeric strings."""
        rule = SymbolicRule(
            rule_id="r1",
            conditions=[RuleCondition(attribute="temperature", operator=">", value="30")],
        )
        facts = self._make_kb_with_fact("temperature", "35")
        assert rule.evaluate(facts) is True

    def test_less_than_operator(self):
        """< operator works with numeric strings."""
        rule = SymbolicRule(
            rule_id="r1",
            conditions=[RuleCondition(attribute="count", operator="<", value="10")],
        )
        facts = self._make_kb_with_fact("count", "5")
        assert rule.evaluate(facts) is True

    def test_contains_operator(self):
        """contains operator checks substring."""
        rule = SymbolicRule(
            rule_id="r1",
            conditions=[RuleCondition(attribute="description", operator="contains", value="carbon")],
        )
        facts = self._make_kb_with_fact("description", "carbon dioxide emissions")
        assert rule.evaluate(facts) is True

    def test_contains_operator_fails(self):
        """contains operator fails when substring not present."""
        rule = SymbolicRule(
            rule_id="r1",
            conditions=[RuleCondition(attribute="description", operator="contains", value="methane")],
        )
        facts = self._make_kb_with_fact("description", "carbon dioxide emissions")
        assert rule.evaluate(facts) is False

    def test_missing_attribute_fails(self):
        """Rule fails when no fact matches the condition attribute."""
        rule = SymbolicRule(
            rule_id="r1",
            conditions=[RuleCondition(attribute="nonexistent", operator="==", value="x")],
        )
        facts = self._make_kb_with_fact("other", "x")
        assert rule.evaluate(facts) is False


# =============================================================================
# 3. CounterfactualEngine data models
# =============================================================================


class TestCounterfactualEngineModels:
    """Tests for Pydantic models in the counterfactual engine."""

    def test_counterfactual_query_construction(self):
        """CounterfactualQuery can be created with all fields."""
        query = CounterfactualQuery(
            factual_description="Sales dropped 20%",
            intervention_variable="marketing_budget",
            intervention_value="doubled",
            target_variable="sales",
            context={"region": "EU"},
        )
        assert query.intervention_variable == "marketing_budget"
        assert query.context["region"] == "EU"

    def test_counterfactual_query_defaults(self):
        """CounterfactualQuery defaults to empty strings and dict."""
        query = CounterfactualQuery()
        assert query.factual_description == ""
        assert query.intervention_variable == ""
        assert query.context == {}

    def test_counterfactual_result_construction(self):
        """CounterfactualResult can be created with all fields."""
        result = CFCounterfactualResult(
            factual_outcome="Sales were 100k",
            counterfactual_outcome="Sales would be 150k",
            confidence=0.75,
            narrative="Doubling the budget would increase sales.",
            reasoning_steps=["Step 1", "Step 2"],
            method="scm",
        )
        assert result.confidence == 0.75
        assert result.method == "scm"
        assert len(result.reasoning_steps) == 2

    def test_counterfactual_result_default_method(self):
        """Default method is llm_assisted."""
        result = CFCounterfactualResult()
        assert result.method == "llm_assisted"

    def test_counterfactual_result_confidence_bounds(self):
        """Confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            CFCounterfactualResult(confidence=1.5)

    def test_causal_attribution_item(self):
        """CausalAttributionItem construction and field access."""
        item = CausalAttributionItem(
            cause="marketing",
            importance=0.8,
            but_for_result=True,
            description="Marketing was the primary driver.",
        )
        assert item.cause == "marketing"
        assert item.importance == 0.8
        assert item.but_for_result is True

    def test_causal_attribution_importance_bounds(self):
        """Importance must be between 0 and 1."""
        with pytest.raises(ValidationError):
            CausalAttributionItem(cause="x", importance=2.0)


# =============================================================================
# 4. State model extensions
# =============================================================================


class TestCounterfactualEvidence:
    """Tests for CounterfactualEvidence model."""

    def test_creation(self):
        """CounterfactualEvidence can be created with all fields."""
        ev = CounterfactualEvidence(
            factual_outcome="Revenue was $10M",
            counterfactual_outcome="Revenue would be $15M",
            intervention_description="Doubled marketing spend",
            causal_attributions=[{"cause": "marketing", "importance": 0.9}],
            confidence=0.85,
            narrative="Doubling marketing would have increased revenue.",
        )
        assert ev.confidence == 0.85
        assert len(ev.causal_attributions) == 1

    def test_defaults(self):
        """CounterfactualEvidence defaults are correct."""
        ev = CounterfactualEvidence()
        assert ev.factual_outcome == ""
        assert ev.counterfactual_outcome == ""
        assert ev.causal_attributions == []
        assert ev.confidence == 0.0

    def test_serialization_round_trip(self):
        """CounterfactualEvidence serializes and deserializes correctly."""
        ev = CounterfactualEvidence(
            factual_outcome="X",
            counterfactual_outcome="Y",
            confidence=0.7,
            narrative="test",
        )
        data = ev.model_dump()
        restored = CounterfactualEvidence(**data)
        assert restored.factual_outcome == "X"
        assert restored.confidence == 0.7


class TestNeurosymbolicEvidence:
    """Tests for NeurosymbolicEvidence model."""

    def test_creation(self):
        """NeurosymbolicEvidence can be created with all fields."""
        ev = NeurosymbolicEvidence(
            conclusion="CO2 causes warming",
            derived_facts_count=5,
            rules_fired=["ghg-rule", "warming-rule"],
            shortcut_warnings=["skipped intermediate step"],
            grounding_source="knowledge_graph",
            iterations=3,
            confidence=0.9,
        )
        assert ev.derived_facts_count == 5
        assert len(ev.rules_fired) == 2
        assert ev.grounding_source == "knowledge_graph"

    def test_defaults(self):
        """NeurosymbolicEvidence defaults are correct."""
        ev = NeurosymbolicEvidence()
        assert ev.conclusion == ""
        assert ev.derived_facts_count == 0
        assert ev.rules_fired == []
        assert ev.shortcut_warnings == []
        assert ev.grounding_source == "none"
        assert ev.iterations == 0
        assert ev.confidence == 0.0

    def test_serialization_round_trip(self):
        """NeurosymbolicEvidence serializes and deserializes correctly."""
        ev = NeurosymbolicEvidence(
            conclusion="test",
            derived_facts_count=3,
            iterations=2,
            confidence=0.8,
        )
        data = ev.model_dump()
        restored = NeurosymbolicEvidence(**data)
        assert restored.conclusion == "test"
        assert restored.derived_facts_count == 3


class TestEpistemicStatePhase17Fields:
    """Tests for Phase 17 fields on EpistemicState."""

    def test_counterfactual_evidence_field(self):
        """EpistemicState accepts counterfactual_evidence."""
        state = EpistemicState(
            counterfactual_evidence=CounterfactualEvidence(
                factual_outcome="A",
                counterfactual_outcome="B",
                confidence=0.6,
            ),
        )
        assert state.counterfactual_evidence is not None
        assert state.counterfactual_evidence.confidence == 0.6

    def test_neurosymbolic_evidence_field(self):
        """EpistemicState accepts neurosymbolic_evidence."""
        state = EpistemicState(
            neurosymbolic_evidence=NeurosymbolicEvidence(
                conclusion="derived",
                iterations=2,
            ),
        )
        assert state.neurosymbolic_evidence is not None
        assert state.neurosymbolic_evidence.iterations == 2

    def test_both_phase17_fields_default_none(self):
        """Both Phase 17 evidence fields default to None."""
        state = EpistemicState()
        assert state.counterfactual_evidence is None
        assert state.neurosymbolic_evidence is None

    def test_full_state_with_both_evidence_types(self):
        """EpistemicState can carry both evidence types simultaneously."""
        state = EpistemicState(
            user_input="test query",
            counterfactual_evidence=CounterfactualEvidence(confidence=0.7),
            neurosymbolic_evidence=NeurosymbolicEvidence(confidence=0.8),
        )
        assert state.counterfactual_evidence.confidence == 0.7
        assert state.neurosymbolic_evidence.confidence == 0.8

    def test_state_serialization_with_phase17(self):
        """EpistemicState with Phase 17 fields serializes correctly."""
        state = EpistemicState(
            counterfactual_evidence=CounterfactualEvidence(narrative="test"),
            neurosymbolic_evidence=NeurosymbolicEvidence(conclusion="test"),
        )
        data = state.model_dump()
        assert data["counterfactual_evidence"]["narrative"] == "test"
        assert data["neurosymbolic_evidence"]["conclusion"] == "test"


# =============================================================================
# 5. API Router tests
# =============================================================================


class TestWorldModelRouter:
    """Tests for the world_model API router configuration."""

    def test_router_has_expected_routes(self):
        """Router registers all 10 expected routes."""
        from src.api.routers.world_model import router

        paths = [route.path for route in router.routes]
        expected = [
            "/world-model/counterfactual",
            "/world-model/counterfactual/compare",
            "/world-model/counterfactual/attribute",
            "/world-model/simulate",
            "/world-model/neurosymbolic/reason",
            "/world-model/neurosymbolic/validate",
            "/world-model/h-neuron/status",
            "/world-model/h-neuron/assess",
            "/world-model/retrieve/neurosymbolic",
            "/world-model/analyze-deep",
        ]
        for path in expected:
            assert path in paths, f"Missing route: {path}"

    def test_router_prefix(self):
        """Router has the /world-model prefix."""
        from src.api.routers.world_model import router

        assert router.prefix == "/world-model"

    def test_router_tags(self):
        """Router is tagged with 'World Model'."""
        from src.api.routers.world_model import router

        assert "World Model" in router.tags


class TestWorldModelRequestResponseModels:
    """Tests for API request/response Pydantic models."""

    def test_counterfactual_request_requires_query(self):
        """CounterfactualRequest requires a query field."""
        from src.api.routers.world_model import CounterfactualRequest

        with pytest.raises(ValidationError):
            CounterfactualRequest()

        req = CounterfactualRequest(query="What if X?")
        assert req.query == "What if X?"

    def test_simulation_request_defaults(self):
        """WorldModelSimulationRequest has sensible defaults."""
        from src.api.routers.world_model import WorldModelSimulationRequest

        req = WorldModelSimulationRequest(query="Simulate climate")
        assert req.steps == 5
        assert req.initial_conditions == {}
        assert req.interventions == {}

    def test_simulation_request_step_bounds(self):
        """Simulation steps must be between 1 and 50."""
        from src.api.routers.world_model import WorldModelSimulationRequest

        with pytest.raises(ValidationError):
            WorldModelSimulationRequest(query="test", steps=0)
        with pytest.raises(ValidationError):
            WorldModelSimulationRequest(query="test", steps=51)

    def test_neurosymbolic_request_defaults(self):
        """NeurosymbolicReasoningRequest has correct defaults."""
        from src.api.routers.world_model import NeurosymbolicReasoningRequest

        req = NeurosymbolicReasoningRequest(query="Why?")
        assert req.use_knowledge_graph is True
        assert req.max_iterations == 3

    def test_scenario_comparison_request_requires_fields(self):
        """ScenarioComparisonRequest requires base_query, interventions, outcome."""
        from src.api.routers.world_model import ScenarioComparisonRequest

        with pytest.raises(ValidationError):
            ScenarioComparisonRequest()

        req = ScenarioComparisonRequest(
            base_query="What if",
            alternative_interventions=[{"X": 1.0}],
            outcome_variable="Y",
        )
        assert req.outcome_variable == "Y"

    def test_counterfactual_response_model(self):
        """CounterfactualResponse can be constructed."""
        from src.api.routers.world_model import CounterfactualResponse

        resp = CounterfactualResponse(
            factual_outcome="A",
            counterfactual_outcome="B",
            confidence=0.5,
        )
        assert resp.factual_outcome == "A"

    def test_causal_attribution_request(self):
        """CausalAttributionRequest requires outcome_description."""
        from src.api.routers.world_model import CausalAttributionRequest

        with pytest.raises(ValidationError):
            CausalAttributionRequest()

        req = CausalAttributionRequest(outcome_description="Sales dropped")
        assert req.outcome_description == "Sales dropped"
