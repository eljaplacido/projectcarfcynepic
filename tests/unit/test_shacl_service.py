"""Unit tests for SHACL Governance Validation Service (R3)."""

import os
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


@pytest.fixture(autouse=True)
def reset_shacl():
    from src.services.shacl_service import reset_shacl_service

    reset_shacl_service()
    yield
    reset_shacl_service()


class TestSHACLServiceAvailability:
    def test_service_import(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        assert service is not None

    def test_service_available(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        assert service.available is True

    def test_singleton(self):
        from src.services.shacl_service import get_shacl_service

        s1 = get_shacl_service()
        s2 = get_shacl_service()
        assert s1 is s2


class TestSHACLEncodability:
    def test_yaml_load_encodability(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        yaml_path = _PROJECT_ROOT / "config" / "policies.yaml"
        service.load_yaml_policies(yaml_path)

        assert service._total_policies > 0
        assert service._encodable_policies > 0
        assert 0.0 < service.encodability_ratio <= 1.0

    def test_csl_load_encodability(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        csl_dir = _PROJECT_ROOT / "config" / "policies"
        service.load_csl_policies(csl_dir)

        assert service._total_policies > 0
        assert 0.0 <= service.encodability_ratio <= 1.0

    def test_load_all(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        service.load_all()

        assert service.initialized
        assert service._total_policies >= 40
        assert service._encodable_policies > 0
        assert 0.0 < service.encodability_ratio <= 1.0

    def test_encodability_details_structure(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        service.load_all()

        details = service.encodability_details
        assert len(details) == service._total_policies
        for entry in details:
            assert "rule_name" in entry
            assert "policy_name" in entry
            assert "encodable" in entry
            assert "reason" in entry

    def test_encodability_ratio_is_float(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        service.load_all()
        ratio = service.encodability_ratio
        assert isinstance(ratio, float)
        assert 0.0 <= ratio <= 1.0


class TestSHACLDataGraph:
    def test_build_from_context_empty(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        service.load_all()
        data_graph = service.build_data_graph_from_context({})
        assert data_graph is not None
        assert len(data_graph) >= 0

    def test_build_from_context_with_values(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        service.load_all()
        context = {
            "action.amount": 1000,
            "domain.confidence": 0.95,
            "domain.entropy": 0.2,
            "data.region": "us-east-1",
        }
        data_graph = service.build_data_graph_from_context(context)
        assert data_graph is not None
        assert len(data_graph) >= 4

    def test_context_graph_includes_rdf_types(self):
        from rdflib.namespace import RDF

        from src.services.shacl_service import SHACLService

        service = SHACLService()
        service.load_all()
        data_graph = service.build_data_graph_from_context({"action.amount": 500})
        types = list(data_graph.triples((None, RDF.type, None)))
        assert len(types) >= 2


class TestSHACLValidation:
    def test_validate_empty_context(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        service.load_all()
        result = service.validate_context({})
        assert result is not None
        assert hasattr(result, "conforms")

    def test_validate_result_structure(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        service.load_all()
        result = service.validate_context({"action.amount": 500})
        assert hasattr(result, "conforms")
        assert hasattr(result, "violations")
        assert hasattr(result, "encodability_ratio")
        assert result.encodability_ratio > 0.0

    def test_validate_within_policy(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        service.load_all()
        result = service.validate_context(
            {
                "domain.confidence": 0.95,
                "domain.entropy": 0.15,
                "action.amount": 500,
                "session.reflection_count": 1,
                "session.duration_seconds": 30,
            }
        )
        assert result is not None
        assert isinstance(result.conforms, bool)

    def test_validate_no_shapes(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        result = service.validate_context({"action.amount": 500})
        assert result.conforms is True

    def test_validate_context_convenience(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        service.load_all()
        result = service.validate_context({"action.amount": 500, "domain.confidence": 0.99})
        assert result is not None


class TestCSLParsing:
    def test_parse_csl_condition_equality(self):
        from src.services.shacl_service import _parse_csl_condition

        result = _parse_csl_condition('user.role == "junior"')
        assert len(result) == 1
        assert result[0]["op"] == "=="
        assert result[0]["path"] == "user.role"
        assert result[0]["value"] == "junior"

    def test_parse_csl_condition_and(self):
        from src.services.shacl_service import _parse_csl_condition

        result = _parse_csl_condition('user.role == "junior" and action.type == "transfer"')
        assert len(result) == 2
        assert result[0]["path"] == "user.role"
        assert result[1]["path"] == "action.type"

    def test_parse_csl_constraint_lte(self):
        from src.services.shacl_service import _parse_csl_constraint

        result = _parse_csl_constraint("action.amount <= 1000")
        assert len(result) == 1
        assert result[0]["op"] == "<="
        assert result[0]["value"] == 1000

    def test_parse_csl_constraint_range(self):
        from src.services.shacl_service import _parse_csl_constraint

        result = _parse_csl_constraint(
            "prediction.effect_size >= -1.0 and prediction.effect_size <= 1.0"
        )
        assert len(result) >= 1
        ops = {c["op"] for c in result}
        assert "range" in ops or ("<=" in ops and ">=" in ops)

    def test_parse_csl_constraint_in(self):
        from src.services.shacl_service import _parse_csl_constraint

        result = _parse_csl_constraint('data.region in ["us-east-1", "eu-west-1"]')
        assert len(result) >= 1


class TestEncodabilityTracking:
    def test_all_yaml_key_policies_encodable(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        yaml_path = _PROJECT_ROOT / "config" / "policies.yaml"
        service.load_yaml_policies(yaml_path)

        encodable_names = {e.rule_name for e in service._encodability_entries if e.encodable}
        assert "auto_approval_limit" in encodable_names
        assert "confidence_threshold" in encodable_names
        assert "data_residency" in encodable_names

    def test_escalation_rules_not_encodable(self):
        from src.services.shacl_service import SHACLService

        service = SHACLService()
        yaml_path = _PROJECT_ROOT / "config" / "policies.yaml"
        service.load_yaml_policies(yaml_path)

        escalation_entries = [
            e for e in service._encodability_entries if e.policy_name == "escalation"
        ]
        for entry in escalation_entries:
            assert not entry.encodable
            assert "escalation" in entry.reason.lower() or "extern" in entry.reason.lower()
