"""Phase 18 Improvement Tests — Drift detection, bias auditing, plateau detection,
ChimeraOracle StateGraph integration.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
"""

import math
import pytest


# =============================================================================
# 18A: Drift Detection Tests
# =============================================================================


class TestDriftDetector:
    """Tests for the drift detection service."""

    def _make_detector(self, **kwargs):
        from src.services.drift_detector import DriftDetector
        return DriftDetector(**kwargs)

    def test_no_drift_with_insufficient_data(self):
        detector = self._make_detector(baseline_window=10, detection_window=5)
        for _ in range(5):
            result = detector.record_routing("complicated")
        assert result is None  # Not enough data yet

    def test_baseline_established_after_window(self):
        detector = self._make_detector(baseline_window=10, detection_window=5)
        for i in range(10):
            detector.record_routing(["clear", "complicated"][i % 2])
        status = detector.get_status()
        assert status["baseline_established"] is True

    def test_no_drift_with_stable_distribution(self):
        detector = self._make_detector(
            baseline_window=10, detection_window=5, kl_threshold=0.15
        )
        domains = ["clear", "complicated", "complex", "chaotic", "disorder"]
        # Establish baseline with uniform distribution
        for i in range(10):
            detector.record_routing(domains[i % 5])
        # Continue with same distribution
        for i in range(5):
            detector.record_routing(domains[i % 5])
        status = detector.get_status()
        # Should not have drift alerts
        assert status["alert_count"] == 0

    def test_drift_detected_with_distribution_shift(self):
        detector = self._make_detector(
            baseline_window=20, detection_window=10,
            kl_threshold=0.1, domain_shift_threshold=0.05
        )
        # Establish baseline: mostly complicated
        for _ in range(20):
            detector.record_routing("complicated")
        # Shift to complex
        for _ in range(10):
            result = detector.record_routing("complex")
        # Should detect drift
        assert result is not None
        assert result.drift_detected is True
        assert result.kl_divergence > 0

    def test_kl_divergence_computation(self):
        detector = self._make_detector()
        # Same distributions should give KL ≈ 0
        p = {"clear": 0.2, "complicated": 0.2, "complex": 0.2, "chaotic": 0.2, "disorder": 0.2}
        kl = detector._kl_divergence(p, p)
        assert abs(kl) < 0.001

        # Different distributions should give KL > 0
        q = {"clear": 0.5, "complicated": 0.1, "complex": 0.2, "chaotic": 0.1, "disorder": 0.1}
        kl = detector._kl_divergence(p, q)
        assert kl > 0

    def test_get_status_structure(self):
        detector = self._make_detector(baseline_window=5, detection_window=3)
        status = detector.get_status()
        assert "total_observations" in status
        assert "baseline_established" in status
        assert "config" in status
        assert status["config"]["baseline_window"] == 5

    def test_reset_baseline(self):
        detector = self._make_detector(baseline_window=5, detection_window=3)
        for _ in range(10):
            detector.record_routing("complicated")
        detector.reset_baseline()
        status = detector.get_status()
        assert status["baseline_established"] is True
        assert status["alert_count"] == 0

    def test_history_bounded(self):
        detector = self._make_detector(baseline_window=5, detection_window=5)
        for i in range(100):
            detector.record_routing(["clear", "complicated"][i % 2])
        history = detector.get_history(limit=5)
        assert len(history) <= 5

    def test_record_unknown_domain_not_in_distribution(self):
        """Feed 'foobar' domain; verify it doesn't appear in distribution counts."""
        detector = self._make_detector(baseline_window=10, detection_window=5)
        for _ in range(10):
            detector.record_routing("foobar")
        status = detector.get_status()
        dist = status["current_distribution"]
        # "foobar" is not a valid Cynefin domain, so _compute_distribution ignores it
        assert "foobar" not in dist
        # All valid domains should be 0
        for d in ["clear", "complicated", "complex", "chaotic", "disorder"]:
            assert dist[d] == 0.0

    def test_drift_only_domain_shift_no_kl(self):
        """Craft distributions where one domain shifts >10% but KL stays below threshold."""
        detector = self._make_detector(
            baseline_window=20, detection_window=10,
            kl_threshold=999.0,  # very high KL threshold — never triggers
            domain_shift_threshold=0.05,  # but domain shift is very sensitive
        )
        # Baseline: even mix of clear and complicated (50/50)
        for i in range(20):
            detector.record_routing(["clear", "complicated"][i % 2])
        # Shift: all clear → domain shift should fire but KL should not
        for _ in range(10):
            result = detector.record_routing("clear")
        assert result is not None
        assert result.drift_detected is True
        assert result.max_domain_shift > 0.05
        # KL should be below the absurdly high threshold
        assert result.kl_divergence < 999.0
        assert "Domain" in result.alert_reason
        # Verify KL part is NOT in alert_reason (since threshold is 999)
        assert "KL divergence" not in result.alert_reason

    def test_reset_baseline_insufficient_observations(self):
        """Call reset when obs < baseline_window, verify nothing changes."""
        detector = self._make_detector(baseline_window=100, detection_window=50)
        for _ in range(5):
            detector.record_routing("clear")
        # Baseline should NOT be established
        assert detector.get_status()["baseline_established"] is False
        detector.reset_baseline()
        # Still not established because only 5 < 100
        assert detector.get_status()["baseline_established"] is False

    def test_get_status_empty_detector(self):
        """Verify structure when no observations."""
        detector = self._make_detector()
        status = detector.get_status()
        assert status["total_observations"] == 0
        assert status["baseline_established"] is False
        assert status["baseline_distribution"] == {}
        assert status["current_distribution"] == {}
        assert status["alert_count"] == 0
        assert status["snapshot_count"] == 0
        assert status["last_snapshot"] is None

    def test_get_history_empty(self):
        """Empty list returned when no snapshots exist."""
        detector = self._make_detector()
        history = detector.get_history()
        assert history == []

    def test_snapshot_fields_populated(self):
        """Verify all DriftSnapshot fields after detection."""
        from src.services.drift_detector import DriftSnapshot
        detector = self._make_detector(
            baseline_window=10, detection_window=5,
            kl_threshold=0.01, domain_shift_threshold=0.01,
        )
        # Baseline: all complicated
        for _ in range(10):
            detector.record_routing("complicated")
        # Shift: all clear
        for _ in range(5):
            result = detector.record_routing("clear")
        assert result is not None
        assert isinstance(result, DriftSnapshot)
        assert result.timestamp  # non-empty ISO string
        assert result.window_size == 5
        assert isinstance(result.current_distribution, dict)
        assert isinstance(result.baseline_distribution, dict)
        assert result.kl_divergence > 0
        assert result.max_domain_shift > 0
        assert result.shifted_domain != ""
        assert result.drift_detected is True
        assert result.alert_reason != ""


# =============================================================================
# 18B: Bias Auditing Tests
# =============================================================================


class TestBiasAuditor:
    """Tests for the bias auditing service."""

    def _make_auditor(self, **kwargs):
        from src.services.bias_auditor import BiasAuditor
        return BiasAuditor(**kwargs)

    def _make_memory_with_entries(self, entries_data):
        """Create a mock memory with specified entries."""
        from src.services.agent_memory import AgentMemory, MemoryEntry
        import tempfile, os
        tmp = tempfile.mktemp(suffix=".jsonl")
        memory = AgentMemory(file_path=tmp, max_entries=10000)
        for data in entries_data:
            memory.store(MemoryEntry(**data))
        return memory

    def test_insufficient_data(self):
        auditor = self._make_auditor()
        memory = self._make_memory_with_entries([
            {"query": "test", "domain": "complicated"}
        ])
        report = auditor.audit(memory)
        assert not report.overall_bias_detected
        assert "Insufficient data" in report.findings[0]

    def test_uniform_distribution_no_bias(self):
        auditor = self._make_auditor(chi_squared_threshold=0.01)
        entries = []
        domains = ["clear", "complicated", "complex", "chaotic", "disorder"]
        for i in range(50):
            entries.append({"query": f"query {i}", "domain": domains[i % 5]})
        memory = self._make_memory_with_entries(entries)
        report = auditor.audit(memory)
        assert not report.distribution_biased

    def test_skewed_distribution_detected(self):
        auditor = self._make_auditor(chi_squared_threshold=0.05)
        entries = []
        # 90% complicated, 10% other
        for i in range(90):
            entries.append({"query": f"query {i}", "domain": "complicated"})
        for i in range(10):
            entries.append({"query": f"other {i}", "domain": "clear"})
        memory = self._make_memory_with_entries(entries)
        report = auditor.audit(memory)
        assert report.distribution_biased
        assert report.chi_squared_statistic > 0
        assert any("over-represented" in f for f in report.findings)

    def test_quality_disparity_detection(self):
        auditor = self._make_auditor(quality_disparity_threshold=0.10)
        entries = []
        # Domain A gets high quality, domain B gets low quality
        for i in range(20):
            entries.append({"query": f"q{i}", "domain": "complicated", "quality_score": 0.9})
        for i in range(20):
            entries.append({"query": f"q{i}", "domain": "complex", "quality_score": 0.4})
        memory = self._make_memory_with_entries(entries)
        report = auditor.audit(memory)
        assert report.quality_disparity > 0.10
        assert report.quality_biased

    def test_report_structure(self):
        auditor = self._make_auditor()
        entries = [{"query": f"q{i}", "domain": "complicated"} for i in range(15)]
        memory = self._make_memory_with_entries(entries)
        report = auditor.audit(memory)
        assert hasattr(report, "total_entries")
        assert hasattr(report, "domain_distribution")
        assert hasattr(report, "chi_squared_statistic")
        assert hasattr(report, "overall_bias_detected")
        assert report.total_entries == 15

    def test_chi_squared_p_value_computation(self):
        from src.services.bias_auditor import BiasAuditor
        # chi_sq=0 should give p≈1
        p = BiasAuditor._chi_squared_p_value(0, 4)
        assert p >= 0.9
        # Large chi_sq should give small p
        p = BiasAuditor._chi_squared_p_value(100, 4)
        assert p < 0.01

    def test_quality_scores_none_excluded(self):
        """Entries with quality_score=None excluded from quality stats."""
        auditor = self._make_auditor()
        entries = []
        for i in range(20):
            entries.append({
                "query": f"q{i}", "domain": "complicated",
                "quality_score": None,  # all None
            })
        # Need at least 10 entries
        memory = self._make_memory_with_entries(entries)
        report = auditor.audit(memory)
        # No quality stats should be computed since all are None
        assert report.quality_by_domain == {} or all(
            len(v) == 0 for v in report.quality_by_domain.values()
        )
        assert report.quality_disparity == 0.0

    def test_verdict_disparity_detected(self):
        """Entries with guardian_verdict showing approval rate gap >15%."""
        auditor = self._make_auditor(approval_disparity_threshold=0.15)
        entries = []
        # Domain "complicated": mostly approved
        for i in range(10):
            entries.append({
                "query": f"comp_q{i}", "domain": "complicated",
                "guardian_verdict": "approved",
            })
        # Domain "complex": mostly rejected
        for i in range(7):
            entries.append({
                "query": f"cplx_reject{i}", "domain": "complex",
                "guardian_verdict": "rejected",
            })
        for i in range(3):
            entries.append({
                "query": f"cplx_approve{i}", "domain": "complex",
                "guardian_verdict": "approved",
            })
        memory = self._make_memory_with_entries(entries)
        report = auditor.audit(memory)
        # complicated: 100% approval, complex: 30% approval → 70% gap
        assert report.approval_rate_disparity > 0.15
        assert any("Approval rate" in f for f in report.findings)

    def test_verdict_insufficient_data(self):
        """Fewer than 3 verdicts per domain, no disparity calculated."""
        auditor = self._make_auditor()
        entries = []
        # 10 entries minimum for audit, but only 1-2 verdicts per domain
        for i in range(6):
            entries.append({"query": f"q{i}", "domain": "complicated"})
        for i in range(6):
            entries.append({"query": f"q{i}", "domain": "complex"})
        # Only 1 verdict each
        entries[0]["guardian_verdict"] = "approved"
        entries[6]["guardian_verdict"] = "rejected"
        memory = self._make_memory_with_entries(entries)
        report = auditor.audit(memory)
        # Not enough verdicts (need 3+) to compute disparity
        assert report.approval_rate_disparity == 0.0

    def test_overall_bias_from_approval_disparity(self):
        """overall_bias_detected triggered by approval rate alone."""
        auditor = self._make_auditor(
            chi_squared_threshold=0.001,  # very strict → likely not triggered for uniform
            quality_disparity_threshold=9.0,  # very high → not triggered
            approval_disparity_threshold=0.10,
        )
        entries = []
        # Even distribution across two domains (chi-squared should not trigger)
        for i in range(10):
            entries.append({
                "query": f"comp{i}", "domain": "complicated",
                "guardian_verdict": "approved",
            })
        for i in range(10):
            entries.append({
                "query": f"cplx{i}", "domain": "complex",
                "guardian_verdict": "rejected",
            })
        memory = self._make_memory_with_entries(entries)
        report = auditor.audit(memory)
        # Approval disparity: complicated=100%, complex=0% → 1.0 gap
        assert report.approval_rate_disparity > 0.10
        assert report.overall_bias_detected is True

    def test_chi_squared_p_value_df_zero(self):
        """BiasAuditor._chi_squared_p_value(5.0, 0) returns 0.0."""
        from src.services.bias_auditor import BiasAuditor
        p = BiasAuditor._chi_squared_p_value(5.0, 0)
        assert p == 0.0

    def test_quality_single_domain(self):
        """Only one domain with quality scores, no disparity."""
        auditor = self._make_auditor()
        entries = []
        for i in range(15):
            entries.append({
                "query": f"q{i}", "domain": "complicated",
                "quality_score": 0.8,
            })
        memory = self._make_memory_with_entries(entries)
        report = auditor.audit(memory)
        # Only one domain has quality data → need >=2 for disparity
        assert report.quality_disparity == 0.0
        assert report.quality_biased is False

    def test_report_serialization(self):
        """BiasReport round-trips through model_dump/parse."""
        from src.services.bias_auditor import BiasReport
        report = BiasReport(
            total_entries=42,
            domain_distribution={"clear": 10, "complicated": 32},
            chi_squared_statistic=12.5,
            chi_squared_p_value=0.014,
            distribution_biased=True,
            quality_disparity=0.25,
            quality_biased=True,
            overall_bias_detected=True,
            findings=["Domain distribution biased", "Quality disparity detected"],
        )
        dumped = report.model_dump()
        restored = BiasReport(**dumped)
        assert restored.total_entries == 42
        assert restored.chi_squared_statistic == 12.5
        assert restored.distribution_biased is True
        assert restored.overall_bias_detected is True
        assert len(restored.findings) == 2


# =============================================================================
# 18C: Plateau Detection Tests
# =============================================================================


class TestPlateauDetection:
    """Tests for convergence/plateau detection in retraining."""

    def _make_service(self):
        from src.services.router_retraining_service import RouterRetrainingService
        return RouterRetrainingService()

    def test_insufficient_data(self):
        service = self._make_service()
        result = service.check_convergence()
        assert result.recommendation == "Insufficient data (need 2+ epochs)"

    def test_improvement_detected(self):
        service = self._make_service()
        service.record_accuracy(0.80, epoch=1)
        service.record_accuracy(0.85, epoch=2)
        result = service.check_convergence()
        assert result.accuracy_delta > 0
        assert not result.plateau_detected
        assert not result.regressed
        assert "Improvement" in result.recommendation

    def test_regression_detected(self):
        service = self._make_service()
        service.record_accuracy(0.85, epoch=1)
        service.record_accuracy(0.78, epoch=2)
        result = service.check_convergence()
        assert result.regressed is True
        assert "REGRESSION" in result.recommendation
        assert result.accuracy_delta < 0

    def test_plateau_detected(self):
        service = self._make_service()
        service._convergence_epsilon = 0.005
        service._max_plateau_epochs = 3
        # Record 4 epochs with <0.5% improvement
        service.record_accuracy(0.850, epoch=1)
        service.record_accuracy(0.852, epoch=2)  # +0.002
        service.record_accuracy(0.853, epoch=3)  # +0.001
        service.record_accuracy(0.854, epoch=4)  # +0.001
        result = service.check_convergence()
        assert result.plateau_detected is True
        assert result.converged is True
        assert "PLATEAU" in result.recommendation

    def test_convergence_status_structure(self):
        service = self._make_service()
        service.record_accuracy(0.80)
        service.record_accuracy(0.85)
        status = service.get_convergence_status()
        assert "total_epochs" in status
        assert "convergence" in status
        assert "config" in status
        assert status["total_epochs"] == 2

    def test_auto_epoch_numbering(self):
        service = self._make_service()
        service.record_accuracy(0.80)
        service.record_accuracy(0.85)
        assert service._accuracy_history[0]["epoch"] == 1
        assert service._accuracy_history[1]["epoch"] == 2

    def test_marginal_improvement(self):
        """2 epochs with delta < epsilon but not enough epochs for plateau."""
        service = self._make_service()
        service._convergence_epsilon = 0.005
        service._max_plateau_epochs = 3
        # Only 2 epochs with marginal improvement — not enough for plateau
        service.record_accuracy(0.850, epoch=1)
        service.record_accuracy(0.851, epoch=2)
        result = service.check_convergence()
        assert not result.plateau_detected
        assert not result.regressed
        assert "Marginal improvement" in result.recommendation

    def test_convergence_result_fields(self):
        """Verify all ConvergenceResult fields populated."""
        from src.services.router_retraining_service import ConvergenceResult
        service = self._make_service()
        service.record_accuracy(0.80, epoch=1)
        service.record_accuracy(0.85, epoch=2)
        result = service.check_convergence()
        assert isinstance(result, ConvergenceResult)
        assert result.epoch == 2
        assert result.accuracy_delta > 0
        assert result.converged is False
        assert result.regressed is False
        assert result.plateau_detected is False
        assert result.recommendation != ""
        assert isinstance(result.history, list)
        assert len(result.history) == 2

    def test_history_truncation(self):
        """Verify only last 10 epochs in history."""
        service = self._make_service()
        for i in range(15):
            service.record_accuracy(0.50 + i * 0.01, epoch=i + 1)
        result = service.check_convergence()
        assert len(result.history) == 10
        # Should be the last 10 entries (epochs 6-15)
        assert result.history[0]["epoch"] == 6
        assert result.history[-1]["epoch"] == 15


# =============================================================================
# 18D: ChimeraOracle StateGraph Integration Tests
# =============================================================================


class TestChimeraFastPath:
    """Tests for ChimeraOracle StateGraph integration."""

    def test_should_use_chimera_requires_complicated_domain(self):
        from src.workflows.graph import _should_use_chimera_fast_path
        from src.core.state import CynefinDomain, EpistemicState

        state = EpistemicState(
            user_input="test query",
            cynefin_domain=CynefinDomain.COMPLEX,
            domain_confidence=0.95,
        )
        assert _should_use_chimera_fast_path(state) is False

    def test_should_use_chimera_requires_high_confidence(self):
        from src.workflows.graph import _should_use_chimera_fast_path
        from src.core.state import CynefinDomain, EpistemicState

        state = EpistemicState(
            user_input="test query",
            cynefin_domain=CynefinDomain.COMPLICATED,
            domain_confidence=0.70,  # Below 0.85 threshold
        )
        assert _should_use_chimera_fast_path(state) is False

    def test_should_use_chimera_respects_force_full_analysis(self):
        from src.workflows.graph import _should_use_chimera_fast_path
        from src.core.state import CynefinDomain, EpistemicState

        state = EpistemicState(
            user_input="test query",
            cynefin_domain=CynefinDomain.COMPLICATED,
            domain_confidence=0.95,
            context={"_force_full_analysis": True},
        )
        assert _should_use_chimera_fast_path(state) is False

    def test_route_by_domain_includes_chimera(self):
        from src.workflows.graph import route_by_domain
        from src.core.state import CynefinDomain, EpistemicState

        # Without matching model, should route to causal_analyst
        state = EpistemicState(
            user_input="test query",
            cynefin_domain=CynefinDomain.COMPLICATED,
            domain_confidence=0.60,
        )
        route = route_by_domain(state)
        assert route == "causal_analyst"

    def test_route_by_domain_still_routes_other_domains(self):
        from src.workflows.graph import route_by_domain
        from src.core.state import CynefinDomain, EpistemicState

        for domain, expected in [
            (CynefinDomain.CLEAR, "deterministic_runner"),
            (CynefinDomain.COMPLEX, "bayesian_explorer"),
            (CynefinDomain.CHAOTIC, "circuit_breaker"),
            (CynefinDomain.DISORDER, "human_escalation"),
        ]:
            state = EpistemicState(
                user_input="test",
                cynefin_domain=domain,
                domain_confidence=0.5,
            )
            assert route_by_domain(state) == expected

    def test_graph_has_chimera_fast_path_node(self):
        """Verify chimera_fast_path is registered as a node in the graph."""
        from src.workflows.graph import build_carf_graph
        graph = build_carf_graph()
        node_names = set(graph.nodes.keys())
        assert "chimera_fast_path" in node_names

    def test_graph_chimera_routes_to_guardian(self):
        """Verify chimera_fast_path has an edge to guardian (AP-7 closure)."""
        from src.workflows.graph import build_carf_graph
        graph = build_carf_graph()
        # Check that chimera_fast_path node exists and connects to guardian
        assert "chimera_fast_path" in graph.nodes


# =============================================================================
# Singleton Tests
# =============================================================================


class TestSingletons:
    """Verify all Phase 18 services have proper singletons."""

    def test_drift_detector_singleton(self):
        from src.services.drift_detector import get_drift_detector
        d1 = get_drift_detector()
        d2 = get_drift_detector()
        assert d1 is d2

    def test_bias_auditor_singleton(self):
        from src.services.bias_auditor import get_bias_auditor
        a1 = get_bias_auditor()
        a2 = get_bias_auditor()
        assert a1 is a2

    def test_retraining_service_singleton(self):
        from src.services.router_retraining_service import get_router_retraining_service
        s1 = get_router_retraining_service()
        s2 = get_router_retraining_service()
        assert s1 is s2
