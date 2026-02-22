"""Governance Export Service — JSON-LD, YAML, and CSL Spec Export.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

Exports governance board configurations as machine-readable specifications
for interoperability and re-import.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import yaml

from src.core.governance_models import GovernanceBoard

logger = logging.getLogger("carf.governance.export")


class GovernanceExportService:
    """Exports governance boards in various formats."""

    def export_json_ld(self, board: GovernanceBoard) -> dict[str, Any]:
        """Export board as W3C ODRL-style JSON-LD linked data.

        Returns a JSON-LD document with CARF governance ontology.
        """
        from src.services.federated_policy_service import get_federated_service
        fed_service = get_federated_service()

        policies_data = []
        for ns in board.policy_namespaces:
            policy = fed_service.get_policy(ns)
            if policy:
                rules_data = []
                for rule in policy.rules:
                    rules_data.append({
                        "@type": "odrl:Rule",
                        "uid": rule.rule_id,
                        "carf:name": rule.name,
                        "odrl:constraint": {
                            k: v for k, v in rule.constraint.items()
                        },
                        "odrl:condition": {
                            k: v for k, v in rule.condition.items()
                        },
                        "carf:message": rule.message,
                        "carf:severity": rule.severity.value,
                    })
                policies_data.append({
                    "@type": "odrl:Policy",
                    "uid": str(policy.policy_id),
                    "dcterms:title": policy.name,
                    "dcterms:description": policy.description,
                    "carf:domain": policy.domain_id,
                    "carf:namespace": policy.namespace,
                    "carf:priority": policy.priority,
                    "carf:active": policy.is_active,
                    "odrl:rule": rules_data,
                })

        compliance_data = []
        for config in board.compliance_configs:
            compliance_data.append({
                "@type": "carf:ComplianceConfig",
                "carf:framework": config.framework.value,
                "carf:enabled": config.enabled,
                "carf:targetScore": config.target_score,
            })

        members_data = []
        for member in board.members:
            members_data.append({
                "@type": "foaf:Person",
                "foaf:name": member.name,
                "foaf:mbox": member.email,
                "carf:role": member.role,
            })

        return {
            "@context": {
                "odrl": "http://www.w3.org/ns/odrl/2/",
                "dcterms": "http://purl.org/dc/terms/",
                "foaf": "http://xmlns.com/foaf/0.1/",
                "carf": "https://carf.cisuregen.com/ontology/",
            },
            "@type": "carf:GovernanceBoard",
            "@id": f"urn:carf:board:{board.board_id}",
            "dcterms:title": board.name,
            "dcterms:description": board.description,
            "dcterms:created": board.created_at.isoformat(),
            "dcterms:modified": board.updated_at.isoformat(),
            "carf:templateId": board.template_id,
            "carf:domains": board.domain_ids,
            "carf:active": board.is_active,
            "carf:tags": board.tags,
            "odrl:policy": policies_data,
            "carf:compliance": compliance_data,
            "carf:members": members_data,
        }

    def export_yaml(self, board: GovernanceBoard) -> str:
        """Export board as YAML compatible with federated_policies/ format.

        Returns a YAML string that can be re-imported via the federated policy service.
        """
        from src.services.federated_policy_service import get_federated_service
        fed_service = get_federated_service()

        documents = []
        # Group policies by domain
        domain_policies: dict[str, list[dict[str, Any]]] = {}
        for ns in board.policy_namespaces:
            policy = fed_service.get_policy(ns)
            if policy:
                policy_dict = {
                    "name": policy.name,
                    "namespace": policy.namespace,
                    "description": policy.description,
                    "priority": policy.priority,
                    "is_active": policy.is_active,
                    "version": policy.version,
                    "tags": policy.tags,
                    "rules": [
                        {
                            "name": r.name,
                            "condition": dict(r.condition),
                            "constraint": dict(r.constraint),
                            "message": r.message,
                            "severity": r.severity.value,
                        }
                        for r in policy.rules
                    ],
                }
                domain_policies.setdefault(policy.domain_id, []).append(policy_dict)

        for domain_id, policies in domain_policies.items():
            domain = fed_service.get_domain(domain_id)
            doc = {
                "domain": {
                    "id": domain_id,
                    "display_name": domain.display_name if domain else domain_id.title(),
                    "description": domain.description if domain else "",
                    "namespace": domain.policy_namespace if domain else domain_id,
                    "color": domain.color if domain else "#6B7280",
                    "tags": domain.tags if domain else [],
                },
                "policies": policies,
            }
            documents.append(doc)

        # Combine with board metadata header
        output = {
            "board": {
                "board_id": board.board_id,
                "name": board.name,
                "description": board.description,
                "template_id": board.template_id,
                "tags": board.tags,
                "is_active": board.is_active,
                "compliance_frameworks": [
                    {
                        "framework": c.framework.value,
                        "enabled": c.enabled,
                        "target_score": c.target_score,
                    }
                    for c in board.compliance_configs
                ],
            },
            "domains": documents,
        }

        return yaml.dump(output, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def export_csl(self, board: GovernanceBoard) -> list[dict[str, Any]]:
        """Export board policies as CSL policy format for Guardian integration.

        Returns a list of CSL policy dictionaries.
        """
        from src.services.federated_policy_service import get_federated_service
        fed_service = get_federated_service()

        csl_policies = []
        for ns in board.policy_namespaces:
            policy = fed_service.get_policy(ns)
            if policy and policy.is_active:
                csl_rules = []
                for rule in policy.rules:
                    csl_rules.append({
                        "name": f"fed_{policy.namespace}_{rule.name}",
                        "policy_name": f"federated_{policy.namespace}",
                        "condition": dict(rule.condition),
                        "constraint": dict(rule.constraint),
                        "message": rule.message or f"Federated rule: {rule.name}",
                    })
                csl_policies.append({
                    "name": f"federated_{policy.namespace}",
                    "version": policy.version,
                    "description": f"[Federated] {policy.description}",
                    "rules": csl_rules,
                })

        return csl_policies


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_export_service: GovernanceExportService | None = None


def get_export_service() -> GovernanceExportService:
    """Get or create the governance export service singleton."""
    global _export_service
    if _export_service is None:
        _export_service = GovernanceExportService()
    return _export_service
