"""SHACL Governance Validation Service — Provable Policy Enforcement.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).

Translates Guardian YAML/CSL policies into W3C SHACL shapes and validates
governance data graphs using pyshacl. Fail-closed defence-in-depth layer.

Architecture:
    YAML policies  ──→ SHACL NodeShape + PropertyShape
    CSL policies   ──→ SHACL NodeShape + PropertyShape    ──→ pyshacl.validate()
    Governance state ─→ RDF data graph (rdflib)

Encodability tracking (H49): measures what % of Guardian policies can be
expressed as SHACL constraint shapes. Complex rules (OR, aggregation, external
calls) are noted as non-encodable.

Usage:
    service = SHACLService()
    service.load_yaml_policies("config/policies.yaml")
    service.load_csl_policies("config/policies/")
    data_graph = service.build_data_graph_from_context(governance_context)
    result = service.validate(data_graph)
    print(f"Encodability: {service.encodability_ratio:.1%}")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.shacl")

CARF_NS = "https://carf.cisuregen.com/ontology/"
PROV_NS = "https://cisuregen.local/ns/carf#"
SH = "http://www.w3.org/ns/shacl#"
XSD = "http://www.w3.org/2001/XMLSchema#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
ODRL = "http://www.w3.org/ns/odrl/2/"


class SHACLViolation(BaseModel):
    """A single SHACL validation violation."""

    focus_node: str = Field(default="")
    result_path: str = Field(default="")
    result_message: str = Field(default="")
    source_shape: str = Field(default="")
    source_constraint: str = Field(default="")
    severity: str = Field(default="sh:Violation")


class SHACLResult(BaseModel):
    """SHACL validation result for governance state."""

    conforms: bool
    violations: list[SHACLViolation] = Field(default_factory=list)
    shapes_checked: int = 0
    shapes_violated: int = 0
    encodability_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    total_policies: int = 0
    encodable_policies: int = 0
    validation_time_ms: float = 0.0


@dataclass
class CSLRule:
    """Parsed CSL rule structure."""

    name: str
    policy_name: str
    when_conditions: list[dict[str, Any]] = field(default_factory=list)
    then_constraints: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""


@dataclass
class EncodabilityEntry:
    """Record of whether a specific policy rule is SHACL-encodable."""

    rule_name: str
    policy_name: str
    encodable: bool
    reason: str = ""
    shape_id: str = ""


def _parse_csl_condition(condition_text: str) -> list[dict[str, Any]]:
    """Parse a CSL condition string into structured predicates.

    Handles patterns like:
        user.role == "junior" and action.type == "transfer"
        domain.type == "Clear"
    """
    conditions: list[dict[str, Any]] = []
    if not condition_text or condition_text.strip() == "true":
        return conditions

    parts = re.split(r"\s+and\s+", condition_text)
    for part in parts:
        part = part.strip()
        m = re.match(r"(\S+)\s*(==|!=|>=|<=|>|<)\s*(.+)", part)
        if m:
            left = m.group(1).strip()
            op = m.group(2).strip()
            right = m.group(3).strip().strip('"').strip("'")
            try:
                right_val: Any = (
                    float(right)
                    if right.replace(".", "", 1).replace("-", "", 1).isdigit()
                    else right
                )
            except ValueError:
                right_val = right
            conditions.append({"path": left, "op": op, "value": right_val})
    return conditions


def _parse_csl_constraint(constraint_text: str) -> list[dict[str, Any]]:
    """Parse a CSL constraint string into structured predicates.

    Handles: action.amount <= 1000, action.field in [...], action.field matches "..."
    """
    constraints: list[dict[str, Any]] = []
    if not constraint_text:
        return constraints

    parts = re.split(r"\s+and\s+", constraint_text)
    for part in parts:
        part = part.strip()

        m_range = re.match(r"(\S+)\s*(>=|<=)\s*(-?[\d.]+)\s+and\s+\1\s*(>=|<=)\s*(-?[\d.]+)", part)
        if m_range:
            path = m_range.group(1).strip()
            _op1, val1, _op2, val2 = (
                m_range.group(2),
                float(m_range.group(3)),
                m_range.group(4),
                float(m_range.group(5)),
            )
            constraints.append(
                {
                    "path": path,
                    "op": "range",
                    "min": min(val1, val2),
                    "max": max(val1, val2),
                }
            )
            continue

        m_in = re.match(r"(\S+)\s+in\s+\[(.+)\]", part)
        if m_in:
            path = m_in.group(1).strip()
            vals = [v.strip().strip('"').strip("'") for v in m_in.group(2).split(",")]
            constraints.append({"path": path, "op": "in", "values": vals})
            continue

        m_matches = re.match(r'(\S+)\s+matches\s+["\'](.+)["\']', part)
        if m_matches:
            constraints.append(
                {"path": m_matches.group(1).strip(), "op": "matches", "pattern": m_matches.group(2)}
            )
            continue

        m_cmp = re.match(r"(\S+)\s*(<=|>=|<|>|==|!=)\s*(-?[\d.]+)", part)
        if m_cmp:
            constraints.append(
                {
                    "path": m_cmp.group(1).strip(),
                    "op": m_cmp.group(2),
                    "value": float(m_cmp.group(3)),
                }
            )
            continue

    return constraints


def _parse_csl_file(filepath: Path) -> list[CSLRule]:
    """Parse a .csl policy file into structured rules."""
    rules: list[CSLRule] = []
    if not filepath.exists():
        return rules

    text = filepath.read_text(encoding="utf-8")
    current_policy = filepath.stem

    block = re.findall(r"rule\s+(\S+)\s*\{([^}]+)\}", text, re.DOTALL)
    for rule_name, body in block:
        when_match = re.search(r"when\s+(.+?)(?:\n|then)", body)
        then_match = re.search(r"then\s+(.+?)(?:\n|message)", body)
        msg_match = re.search(r'message\s*=\s*["\'](.+?)["\']', body)

        rule = CSLRule(
            name=rule_name.strip(),
            policy_name=current_policy,
            when_conditions=_parse_csl_condition(
                when_match.group(1).strip() if when_match else "true"
            ),
            then_constraints=_parse_csl_constraint(
                then_match.group(1).strip() if then_match else ""
            ),
            message=msg_match.group(1).strip() if msg_match else "",
        )
        rules.append(rule)

    return rules


class SHACLService:
    """SHACL-based governance validation engine.

    Translates CSL and YAML policies into SHACL shapes, builds RDF data graphs
    from governance state, and validates using pyshacl.
    """

    def __init__(self) -> None:
        self._shapes_graph = None
        self._total_policies = 0
        self._encodable_policies = 0
        self._encodability_entries: list[EncodabilityEntry] = []
        self._initialized = False

    @property
    def available(self) -> bool:
        """Check if pyshacl and rdflib are importable."""
        try:
            import pyshacl  # noqa: F401
            import rdflib  # noqa: F401

            return True
        except ImportError:
            return False

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def encodability_ratio(self) -> float:
        if self._total_policies == 0:
            return 0.0
        return self._encodable_policies / self._total_policies

    @property
    def encodability_details(self) -> list[dict[str, Any]]:
        return [
            {
                "rule_name": e.rule_name,
                "policy_name": e.policy_name,
                "encodable": e.encodable,
                "reason": e.reason,
                "shape_id": e.shape_id,
            }
            for e in self._encodability_entries
        ]

    def _ensure_deps(self):
        if not self.available:
            raise ImportError(
                "pyshacl and rdflib required for SHACL validation. "
                "Install with: pip install carf[shacl]"
            )

    def _carf_uri(self, term: str) -> str:
        return f"{CARF_NS}{term}"

    def _prov_uri(self, term: str) -> str:
        return f"{PROV_NS}{term}"

    # ------------------------------------------------------------------
    # SHACL Shape Generation
    # ------------------------------------------------------------------

    def load_yaml_policies(self, yaml_path: str | Path) -> None:
        """Load YAML policy file and translate to SHACL shapes."""
        self._ensure_deps()
        import yaml

        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            logger.warning("YAML policy file not found: %s", yaml_path)
            return

        with open(yaml_path) as f:
            policies = yaml.safe_load(f) or {}

        shapes: list[tuple[str, str, dict[str, Any]]] = []

        financial = policies.get("financial", {})
        if auto_limit := financial.get("auto_approval_limit"):
            self._total_policies += 1
            shape_id = f"{CARF_NS}Shape_AutoApprovalLimit"
            shapes.append(
                (
                    "shape",
                    shape_id,
                    {
                        "targetClass": self._carf_uri("Action"),
                        "property": [
                            {
                                "path": self._carf_uri("amount"),
                                "maxInclusive": auto_limit.get("value", 100000),
                                "message": f"Amount exceeds auto-approval limit of {auto_limit.get('value', 100000)} {auto_limit.get('currency', 'USD')}",
                            }
                        ],
                    },
                )
            )
            self._encodable_policies += 1
            self._encodability_entries.append(
                EncodabilityEntry(
                    rule_name="auto_approval_limit",
                    policy_name="financial",
                    encodable=True,
                    shape_id=shape_id,
                )
            )

        if daily_limit := financial.get("daily_limit"):
            self._total_policies += 1
            shape_id = f"{CARF_NS}Shape_DailyLimit"
            shapes.append(
                (
                    "shape",
                    shape_id,
                    {
                        "targetClass": self._carf_uri("Action"),
                        "property": [
                            {
                                "path": self._carf_uri("dailyTotal"),
                                "maxInclusive": daily_limit.get("value", 500000),
                                "message": f"Daily total exceeds limit of {daily_limit.get('value', 500000)}",
                            }
                        ],
                    },
                )
            )
            self._encodable_policies += 1
            self._encodability_entries.append(
                EncodabilityEntry(
                    rule_name="daily_limit",
                    policy_name="financial",
                    encodable=True,
                    shape_id=shape_id,
                )
            )

        if "approved_vendors" in financial:
            self._total_policies += 1
            shape_id = f"{CARF_NS}Shape_ApprovedVendors"
            shapes.append(
                (
                    "shape",
                    shape_id,
                    {
                        "targetClass": self._carf_uri("Action"),
                        "property": [
                            {
                                "path": self._carf_uri("vendor"),
                                "minCount": 1,
                                "message": "Vendor must be specified and approved",
                            }
                        ],
                    },
                )
            )
            self._encodable_policies += 1
            self._encodability_entries.append(
                EncodabilityEntry(
                    rule_name="approved_vendors",
                    policy_name="financial",
                    encodable=True,
                    shape_id=shape_id,
                )
            )

        data_policies = policies.get("data", {})
        if pii := data_policies.get("pii_handling"):
            fields = pii.get("fields", [])
            for field in fields:
                self._total_policies += 1
                shape_id = f"{CARF_NS}Shape_PII_{field}"
                shapes.append(
                    (
                        "shape",
                        shape_id,
                        {
                            "targetClass": self._carf_uri("DataPayload"),
                            "property": [
                                {
                                    "path": self._carf_uri(f"hasField_{field}"),
                                    "maxCount": 0,
                                    "message": f"PII field '{field}' must be masked",
                                }
                            ],
                        },
                    )
                )
                self._encodable_policies += 1
                self._encodability_entries.append(
                    EncodabilityEntry(
                        rule_name=f"pii_{field}",
                        policy_name="data",
                        encodable=True,
                        shape_id=shape_id,
                    )
                )

        if residency := data_policies.get("data_residency"):
            regions = residency.get("approved_regions", [])
            self._total_policies += 1
            shape_id = f"{CARF_NS}Shape_DataResidency"
            shapes.append(
                (
                    "shape",
                    shape_id,
                    {
                        "targetClass": self._carf_uri("DataPayload"),
                        "property": [
                            {
                                "path": self._carf_uri("region"),
                                "in": regions,
                                "message": f"Data region must be one of: {', '.join(regions)}",
                            }
                        ],
                    },
                )
            )
            self._encodable_policies += 1
            self._encodability_entries.append(
                EncodabilityEntry(
                    rule_name="data_residency",
                    policy_name="data",
                    encodable=True,
                    shape_id=shape_id,
                )
            )

        operational = policies.get("operational", {})
        if max_ref := operational.get("max_reflection_attempts"):
            self._total_policies += 1
            shape_id = f"{CARF_NS}Shape_MaxReflections"
            shapes.append(
                (
                    "shape",
                    shape_id,
                    {
                        "targetClass": self._carf_uri("Session"),
                        "property": [
                            {
                                "path": self._carf_uri("reflectionCount"),
                                "maxInclusive": max_ref.get("value", 3),
                                "message": f"Reflection count exceeds maximum of {max_ref.get('value', 3)}",
                            }
                        ],
                    },
                )
            )
            self._encodable_policies += 1
            self._encodability_entries.append(
                EncodabilityEntry(
                    rule_name="max_reflection_attempts",
                    policy_name="operational",
                    encodable=True,
                    shape_id=shape_id,
                )
            )

        if timeout := operational.get("timeout"):
            self._total_policies += 1
            shape_id = f"{CARF_NS}Shape_Timeout"
            shapes.append(
                (
                    "shape",
                    shape_id,
                    {
                        "targetClass": self._carf_uri("Session"),
                        "property": [
                            {
                                "path": self._carf_uri("durationSeconds"),
                                "maxInclusive": timeout.get("value_seconds", 300),
                                "message": f"Execution time exceeds limit of {timeout.get('value_seconds', 300)}s",
                            }
                        ],
                    },
                )
            )
            self._encodable_policies += 1
            self._encodability_entries.append(
                EncodabilityEntry(
                    rule_name="timeout",
                    policy_name="operational",
                    encodable=True,
                    shape_id=shape_id,
                )
            )

        risk_policies = policies.get("risk", {})
        if conf_threshold := risk_policies.get("confidence_threshold"):
            self._total_policies += 1
            shape_id = f"{CARF_NS}Shape_ConfidenceThreshold"
            shapes.append(
                (
                    "shape",
                    shape_id,
                    {
                        "targetClass": self._carf_uri("Session"),
                        "property": [
                            {
                                "path": self._carf_uri("confidence"),
                                "minInclusive": conf_threshold.get("value", 0.85),
                                "message": f"Confidence below threshold of {conf_threshold.get('value', 0.85)}",
                            }
                        ],
                    },
                )
            )
            self._encodable_policies += 1
            self._encodability_entries.append(
                EncodabilityEntry(
                    rule_name="confidence_threshold",
                    policy_name="risk",
                    encodable=True,
                    shape_id=shape_id,
                )
            )

        if entropy_policy := risk_policies.get("entropy_alert"):
            self._total_policies += 1
            shape_id = f"{CARF_NS}Shape_EntropyAlert"
            shapes.append(
                (
                    "shape",
                    shape_id,
                    {
                        "targetClass": self._carf_uri("Session"),
                        "property": [
                            {
                                "path": self._carf_uri("entropy"),
                                "maxInclusive": entropy_policy.get("threshold", 0.9),
                                "message": f"Entropy exceeds alert threshold of {entropy_policy.get('threshold', 0.9)}",
                            }
                        ],
                    },
                )
            )
            self._encodable_policies += 1
            self._encodability_entries.append(
                EncodabilityEntry(
                    rule_name="entropy_alert",
                    policy_name="risk",
                    encodable=True,
                    shape_id=shape_id,
                )
            )

        escalation = policies.get("escalation", {})
        if always_esc := escalation.get("always_escalate"):
            for action_name in always_esc.get("actions", []):
                self._total_policies += 1
                self._encodability_entries.append(
                    EncodabilityEntry(
                        rule_name=f"always_escalate_{action_name}",
                        policy_name="escalation",
                        encodable=False,
                        reason="Escalation rules require external system (HumanLayer) interaction — not expressible as SHACL shape",
                    )
                )

        self._build_shapes_graph(shapes)

    def load_csl_policies(self, csl_dir: str | Path) -> None:
        """Load CSL policy files and translate to SHACL shapes."""
        self._ensure_deps()

        csl_dir = Path(csl_dir)
        if not csl_dir.exists():
            logger.warning("CSL policy directory not found: %s", csl_dir)
            return

        shapes: list[tuple[str, str, dict[str, Any]]] = []

        for csl_file in sorted(csl_dir.glob("*.csl")):
            rules = _parse_csl_file(csl_file)
            for rule in rules:
                self._total_policies += 1
                shape_entry = self._translate_csl_rule_to_shape(rule)
                if shape_entry:
                    shapes.append(shape_entry)
                    self._encodable_policies += 1
                    self._encodability_entries.append(
                        EncodabilityEntry(
                            rule_name=rule.name,
                            policy_name=rule.policy_name,
                            encodable=True,
                            shape_id=shape_entry[1],
                        )
                    )
                else:
                    self._encodability_entries.append(
                        EncodabilityEntry(
                            rule_name=rule.name,
                            policy_name=rule.policy_name,
                            encodable=False,
                            reason="Complex condition or constraint not expressible as atomic SHACL shape",
                        )
                    )

        self._build_shapes_graph(shapes)

    def _translate_csl_rule_to_shape(self, rule: CSLRule) -> tuple[str, str, dict[str, Any]] | None:
        """Translate a single CSL rule to a SHACL shape. Returns None if not encodable."""
        properties: list[dict[str, Any]] = []

        if not rule.then_constraints:
            return None

        for constraint in rule.then_constraints:
            path = self._carf_uri(constraint["path"].replace(".", "_"))
            prop_shape: dict[str, Any] = {"path": path}

            op = constraint["op"]
            if op in ("<=", "=="):
                prop_shape["maxInclusive"] = constraint["value"]
            elif op == ">=":
                prop_shape["minInclusive"] = constraint["value"]
            elif op in ("<", "!="):
                return None
            elif op == "range":
                prop_shape["minInclusive"] = constraint["min"]
                prop_shape["maxInclusive"] = constraint["max"]
            elif op == "in":
                prop_shape["in"] = constraint["values"]
            else:
                return None

            if rule.message:
                prop_shape["message"] = rule.message

            properties.append(prop_shape)

        if not properties:
            return None

        shape_id = f"{CARF_NS}Shape_{rule.policy_name}_{rule.name}"

        shape_def: dict[str, Any] = {
            "targetClass": self._carf_uri("Action"),
            "property": properties,
        }

        return ("shape", shape_id, shape_def)

    def _build_shapes_graph(self, shapes: list[tuple[str, str, dict[str, Any]]]) -> None:
        """Build the combined SHACL shapes graph from translated policies."""
        self._ensure_deps()
        from rdflib import Graph, Literal, URIRef
        from rdflib.namespace import RDF as RDF_NS
        from rdflib.namespace import XSD as XSD_NS

        g = Graph()
        g.bind("sh", SH)
        g.bind("carf", CARF_NS)
        g.bind("xsd", XSD_NS)

        SH_NodeShape = URIRef(f"{SH}NodeShape")
        SH_PropertyShape = URIRef(f"{SH}PropertyShape")
        SH_targetClass = URIRef(f"{SH}targetClass")
        SH_property = URIRef(f"{SH}property")
        SH_path = URIRef(f"{SH}path")
        SH_message = URIRef(f"{SH}message")
        SH_maxInclusive = URIRef(f"{SH}maxInclusive")
        SH_minInclusive = URIRef(f"{SH}minInclusive")
        SH_minCount = URIRef(f"{SH}minCount")
        SH_maxCount = URIRef(f"{SH}maxCount")
        SH_in = URIRef(f"{SH}in")

        for _kind, shape_id, shape_def in shapes:
            shape_uri = URIRef(shape_id)
            g.add((shape_uri, RDF_NS.type, SH_NodeShape))

            if "targetClass" in shape_def:
                g.add((shape_uri, SH_targetClass, URIRef(shape_def["targetClass"])))

            for prop_def in shape_def.get("property", []):
                prop_uri = URIRef(f"{shape_id}_prop_{len(list(g))}")
                g.add((prop_uri, RDF_NS.type, SH_PropertyShape))
                g.add((shape_uri, SH_property, prop_uri))

                if "path" in prop_def:
                    g.add((prop_uri, SH_path, URIRef(prop_def["path"])))

                if "maxInclusive" in prop_def:
                    g.add((prop_uri, SH_maxInclusive, Literal(prop_def["maxInclusive"])))
                if "minInclusive" in prop_def:
                    g.add((prop_uri, SH_minInclusive, Literal(prop_def["minInclusive"])))
                if "minCount" in prop_def:
                    g.add((prop_uri, SH_minCount, Literal(prop_def["minCount"])))
                if "maxCount" in prop_def:
                    g.add((prop_uri, SH_maxCount, Literal(prop_def["maxCount"])))
                if "in" in prop_def:
                    in_list = URIRef(f"{shape_id}_inList")
                    from rdflib.collection import Collection

                    Collection(g, in_list, [Literal(v) for v in prop_def["in"]])
                    g.add((prop_uri, SH_in, in_list))

                if "message" in prop_def:
                    g.add((prop_uri, SH_message, Literal(prop_def["message"])))

        self._shapes_graph = g

    # ------------------------------------------------------------------
    # Data Graph Construction
    # ------------------------------------------------------------------

    def build_data_graph_from_context(self, context: dict[str, Any]) -> Any:
        """Build an RDF data graph from a flat governance context dict.

        The context dict uses dot-notation keys (e.g. 'action.amount', 'user.role')
        that map to CARF ontology predicates.
        """
        self._ensure_deps()
        from rdflib import Graph, Literal, URIRef
        from rdflib.namespace import RDF as RDF_NS

        g = Graph()
        g.bind("carf", CARF_NS)
        g.bind("sh", SH)
        g.bind("xsd", XSD)

        action_uri = URIRef(f"{CARF_NS}action/current")
        session_uri = URIRef(f"{CARF_NS}session/current")
        data_uri = URIRef(f"{CARF_NS}data/current")

        g.add((action_uri, RDF_NS.type, URIRef(self._carf_uri("Action"))))
        g.add((session_uri, RDF_NS.type, URIRef(self._carf_uri("Session"))))
        g.add((data_uri, RDF_NS.type, URIRef(self._carf_uri("DataPayload"))))

        carf_Amount = URIRef(self._carf_uri("amount"))
        carf_DailyTotal = URIRef(self._carf_uri("dailyTotal"))
        carf_ReflectionCount = URIRef(self._carf_uri("reflectionCount"))
        carf_DurationSeconds = URIRef(self._carf_uri("durationSeconds"))
        carf_Confidence = URIRef(self._carf_uri("confidence"))
        carf_Entropy = URIRef(self._carf_uri("entropy"))
        carf_Vendor = URIRef(self._carf_uri("vendor"))
        carf_Region = URIRef(self._carf_uri("region"))

        # Map known dot-path keys to CARF predicates
        key_to_predicate: dict[str, Any] = {
            "action.amount": carf_Amount,
            "action.daily_total": carf_DailyTotal,
            "session.reflection_count": carf_ReflectionCount,
            "session.duration_seconds": carf_DurationSeconds,
            "domain.confidence": carf_Confidence,
            "domain.entropy": carf_Entropy,
            "data.region": carf_Region,
            "action.vendor": carf_Vendor,
        }

        for key, value in context.items():
            if key in key_to_predicate:
                pred = key_to_predicate[key]
                if key.startswith("action."):
                    subj = action_uri
                elif key.startswith("session."):
                    subj = session_uri
                elif key.startswith("domain."):
                    subj = session_uri
                elif key.startswith("data."):
                    subj = data_uri
                else:
                    subj = action_uri

                if isinstance(value, (int, float)):
                    g.add((subj, pred, Literal(value)))
                elif isinstance(value, bool):
                    g.add((subj, pred, Literal(value)))
                else:
                    g.add((subj, pred, Literal(str(value))))

        return g

    def build_data_graph_from_state(self, state: Any) -> Any:
        """Build RDF data graph from EpistemicState for SHACL validation."""
        from rdflib import Graph, Literal, URIRef
        from rdflib.namespace import RDF as RDF_NS

        g = Graph()
        g.bind("carf", CARF_NS)
        g.bind("sh", SH)

        session_uri = URIRef(f"{CARF_NS}session/{state.session_id}")
        action_uri = URIRef(f"{CARF_NS}action/current")

        g.add((session_uri, RDF_NS.type, URIRef(self._carf_uri("Session"))))

        carf_Confidence = URIRef(self._carf_uri("confidence"))
        carf_Entropy = URIRef(self._carf_uri("entropy"))
        carf_ReflectionCount = URIRef(self._carf_uri("reflectionCount"))

        g.add((session_uri, carf_Confidence, Literal(float(state.domain_confidence))))
        g.add((session_uri, carf_Entropy, Literal(float(state.domain_entropy))))
        g.add((session_uri, carf_ReflectionCount, Literal(int(state.reflection_count))))

        if state.proposed_action:
            g.add((action_uri, RDF_NS.type, URIRef(self._carf_uri("Action"))))
            carf_Amount = URIRef(self._carf_uri("amount"))
            amount = state.proposed_action.get("amount")
            if amount is not None:
                g.add((action_uri, carf_Amount, Literal(float(amount))))

        return g

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, data_graph: Any) -> SHACLResult:
        """Validate a data graph against the loaded SHACL shapes graph.

        Args:
            data_graph: rdflib.Graph of governance data (from build_data_graph_*)

        Returns:
            SHACLResult with conformance status and violations.
        """
        self._ensure_deps()

        import time as _time

        from pyshacl import validate as pyshacl_validate
        from rdflib import URIRef

        if self._shapes_graph is None:
            return SHACLResult(
                conforms=True,
                encodability_ratio=self.encodability_ratio,
                total_policies=self._total_policies,
                encodable_policies=self._encodable_policies,
            )

        t0 = _time.perf_counter()
        try:
            conforms, results_graph, results_text = pyshacl_validate(
                data_graph,
                shacl_graph=self._shapes_graph,
                inference="none",
                abort_on_first=False,
                allow_infos=False,
                allow_warnings=False,
            )
        except Exception as exc:
            logger.error("SHACL validation error: %s", exc)
            return SHACLResult(
                conforms=False,
                violations=[
                    SHACLViolation(
                        focus_node="validation",
                        result_message=f"SHACL validation failed: {exc}",
                    )
                ],
                encodability_ratio=self.encodability_ratio,
                total_policies=self._total_policies,
                encodable_policies=self._encodable_policies,
                validation_time_ms=(_time.perf_counter() - t0) * 1000,
            )

        elapsed_ms = (_time.perf_counter() - t0) * 1000

        violations: list[SHACLViolation] = []
        shapes_violated: set[str] = set()

        for _s, _p, o in results_graph.triples((None, URIRef(f"{SH}result"), None)):
            violation = SHACLViolation(focus_node=str(o))

            for _, _, msg in results_graph.triples((o, URIRef(f"{SH}resultMessage"), None)):
                violation.result_message = str(msg)

            for _, _, path in results_graph.triples((o, URIRef(f"{SH}resultPath"), None)):
                violation.result_path = str(path)

            for _, _, shape in results_graph.triples((o, URIRef(f"{SH}sourceShape"), None)):
                violation.source_shape = str(shape)
                shapes_violated.add(str(shape))

            for _, _, sc in results_graph.triples(
                (o, URIRef(f"{SH}sourceConstraintComponent"), None)
            ):
                violation.source_constraint = str(sc).replace(str(SH), "sh:")

            for _, _, sev in results_graph.triples((o, URIRef(f"{SH}resultSeverity"), None)):
                violation.severity = str(sev).replace(str(SH), "sh:")

            violations.append(violation)

        return SHACLResult(
            conforms=conforms,
            violations=violations,
            shapes_checked=self._total_policies,
            shapes_violated=len(shapes_violated),
            encodability_ratio=self.encodability_ratio,
            total_policies=self._total_policies,
            encodable_policies=self._encodable_policies,
            validation_time_ms=elapsed_ms,
        )

    def validate_context(self, context: dict[str, Any]) -> SHACLResult:
        """Convenience: build data graph from context dict and validate."""
        data_graph = self.build_data_graph_from_context(context)
        return self.validate(data_graph)

    def validate_state(self, state: Any) -> SHACLResult:
        """Convenience: build data graph from EpistemicState and validate."""
        data_graph = self.build_data_graph_from_state(state)
        return self.validate(data_graph)

    # ------------------------------------------------------------------
    # Load all
    # ------------------------------------------------------------------

    def load_all(
        self,
        yaml_path: str | Path | None = None,
        csl_dir: str | Path | None = None,
    ) -> None:
        """Load both YAML and CSL policies, translating to SHACL shapes."""
        self._total_policies = 0
        self._encodable_policies = 0
        self._encodability_entries.clear()

        if yaml_path is None:
            yaml_path = Path(__file__).parent.parent.parent / "config" / "policies.yaml"
        if csl_dir is None:
            csl_dir = Path(__file__).parent.parent.parent / "config" / "policies"

        self.load_yaml_policies(yaml_path)
        self.load_csl_policies(csl_dir)
        self._initialized = True
        logger.info(
            "SHACL service loaded: %d/%d policies encodable (%.1f%%)",
            self._encodable_policies,
            self._total_policies,
            self.encodability_ratio * 100,
        )


_shacl_instance: SHACLService | None = None


def get_shacl_service() -> SHACLService:
    """Get or create the SHACL service singleton."""
    global _shacl_instance
    if _shacl_instance is None:
        _shacl_instance = SHACLService()
    return _shacl_instance


def reset_shacl_service() -> None:
    """Reset the singleton (test helper)."""
    global _shacl_instance
    _shacl_instance = None
