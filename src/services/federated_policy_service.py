"""Federated Policy Service for CARF Orchestration Governance.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

Manages domain-owner contributed policies loaded from config/federated_policies/.
Provides cross-cutting conflict detection and CSL policy conversion.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from src.core.governance_models import (
    ConflictSeverity,
    ConflictType,
    FederatedPolicy,
    FederatedPolicyRule,
    GovernanceAuditEntry,
    GovernanceDomain,
    GovernanceEventType,
    PolicyConflict,
)

logger = logging.getLogger("carf.governance.policy")

# Default directory for federated policy YAML files
_DEFAULT_POLICY_DIR = "config/federated_policies"


class FederatedPolicyService:
    """Service for managing federated governance policies.

    Loads domain-owner policies from YAML config files and provides:
    - Domain CRUD operations
    - Policy registration and management
    - Cross-cutting conflict detection
    - Conversion to CSL policy format for seamless Guardian integration
    """

    def __init__(self, policy_dir: str | None = None) -> None:
        self._policy_dir = policy_dir or os.getenv(
            "FEDERATED_POLICY_DIR", _DEFAULT_POLICY_DIR
        )
        self._domains: dict[str, GovernanceDomain] = {}
        self._policies: dict[str, FederatedPolicy] = {}  # keyed by namespace
        self._conflicts: dict[str, PolicyConflict] = {}   # keyed by conflict_id
        self._audit_log: list[GovernanceAuditEntry] = []
        self._loaded = False

    def load_policies(self) -> None:
        """Load all federated policies from YAML config directory."""
        policy_path = Path(self._policy_dir)
        if not policy_path.is_absolute():
            policy_path = Path(__file__).resolve().parent.parent.parent / policy_path

        if not policy_path.exists():
            logger.warning(f"Federated policy directory not found: {policy_path}")
            self._loaded = True
            return

        for yaml_file in sorted(policy_path.glob("*.yaml")):
            try:
                self._load_policy_file(yaml_file)
            except Exception as exc:
                logger.warning(f"Failed to load policy file {yaml_file.name}: {exc}")

        self._loaded = True
        logger.info(
            f"Loaded {len(self._domains)} domains with {len(self._policies)} policies "
            f"from {policy_path}"
        )

    def _load_policy_file(self, filepath: Path) -> None:
        """Load a single policy YAML file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or not isinstance(data, dict):
            return

        # Register domain
        domain_data = data.get("domain", {})
        domain_id = domain_data.get("id", filepath.stem)
        domain = GovernanceDomain(
            domain_id=domain_id,
            display_name=domain_data.get("display_name", domain_id.title()),
            description=domain_data.get("description", ""),
            owner_email=domain_data.get("owner_email", ""),
            policy_namespace=domain_data.get("namespace", domain_id),
            tags=domain_data.get("tags", []),
            color=domain_data.get("color", "#6B7280"),
        )
        self._domains[domain_id] = domain

        # Register policies
        for policy_data in data.get("policies", []):
            rules = []
            for rule_data in policy_data.get("rules", []):
                rules.append(FederatedPolicyRule(
                    name=rule_data.get("name", "unnamed"),
                    condition=rule_data.get("condition", {}),
                    constraint=rule_data.get("constraint", {}),
                    message=rule_data.get("message", ""),
                    severity=ConflictSeverity(
                        rule_data.get("severity", "medium")
                    ),
                ))

            namespace = policy_data.get("namespace", f"{domain_id}.{policy_data.get('name', 'default')}")
            policy = FederatedPolicy(
                name=policy_data.get("name", "unnamed"),
                domain_id=domain_id,
                namespace=namespace,
                description=policy_data.get("description", ""),
                rules=rules,
                priority=policy_data.get("priority", 50),
                is_active=policy_data.get("is_active", True),
                version=policy_data.get("version", "1.0"),
                tags=policy_data.get("tags", []),
            )
            self._policies[namespace] = policy

        self._log_event(GovernanceEventType.POLICY_REGISTERED, f"system", [domain_id], {
            "file": filepath.name,
            "policies_loaded": len(data.get("policies", [])),
        })

    # --- Domain CRUD ---

    def register_domain(self, domain: GovernanceDomain) -> GovernanceDomain:
        """Register a new governance domain."""
        self._domains[domain.domain_id] = domain
        self._log_event(GovernanceEventType.DOMAIN_CREATED, "api", [domain.domain_id], {
            "display_name": domain.display_name,
        })
        return domain

    def get_domain(self, domain_id: str) -> GovernanceDomain | None:
        return self._domains.get(domain_id)

    def list_domains(self) -> list[GovernanceDomain]:
        if not self._loaded:
            self.load_policies()
        return list(self._domains.values())

    def update_domain(self, domain_id: str, updates: dict[str, Any]) -> GovernanceDomain | None:
        domain = self._domains.get(domain_id)
        if domain is None:
            return None
        for key, value in updates.items():
            if hasattr(domain, key):
                setattr(domain, key, value)
        return domain

    # --- Policy CRUD ---

    def add_policy(self, policy: FederatedPolicy) -> FederatedPolicy:
        """Register a new federated policy."""
        self._policies[policy.namespace] = policy
        # Auto-detect conflicts
        conflicts = self.detect_conflicts(policy)
        self._log_event(GovernanceEventType.POLICY_REGISTERED, "api", [policy.domain_id], {
            "namespace": policy.namespace,
            "rules_count": len(policy.rules),
            "conflicts_detected": len(conflicts),
        })
        return policy

    def get_policy(self, namespace: str) -> FederatedPolicy | None:
        if not self._loaded:
            self.load_policies()
        return self._policies.get(namespace)

    def list_policies(self, domain_id: str | None = None) -> list[FederatedPolicy]:
        if not self._loaded:
            self.load_policies()
        if domain_id:
            return [p for p in self._policies.values() if p.domain_id == domain_id]
        return list(self._policies.values())

    def update_policy(self, namespace: str, updates: dict[str, Any]) -> FederatedPolicy | None:
        policy = self._policies.get(namespace)
        if policy is None:
            return None
        for key, value in updates.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
        from datetime import datetime
        policy.updated_at = datetime.utcnow()
        self._log_event(GovernanceEventType.POLICY_UPDATED, "api", [policy.domain_id], {
            "namespace": namespace,
        })
        return policy

    def remove_policy(self, namespace: str) -> bool:
        policy = self._policies.pop(namespace, None)
        if policy:
            self._log_event(GovernanceEventType.POLICY_DEACTIVATED, "api", [policy.domain_id], {
                "namespace": namespace,
            })
            return True
        return False

    # --- Conflict Detection ---

    def detect_conflicts(self, new_policy: FederatedPolicy) -> list[PolicyConflict]:
        """Detect cross-cutting contradictions between new and existing policies."""
        conflicts: list[PolicyConflict] = []

        for existing in self._policies.values():
            if existing.namespace == new_policy.namespace:
                continue
            if existing.domain_id == new_policy.domain_id:
                continue  # Same domain policies don't conflict for cross-silo detection

            for new_rule in new_policy.rules:
                for existing_rule in existing.rules:
                    conflict = self._check_rule_conflict(
                        new_policy, new_rule, existing, existing_rule
                    )
                    if conflict:
                        self._conflicts[str(conflict.conflict_id)] = conflict
                        conflicts.append(conflict)
                        self._log_event(
                            GovernanceEventType.CONFLICT_DETECTED, "system",
                            [new_policy.domain_id, existing.domain_id],
                            {"conflict_id": str(conflict.conflict_id), "type": conflict.conflict_type.value},
                        )

        return conflicts

    def _check_rule_conflict(
        self,
        policy_a: FederatedPolicy,
        rule_a: FederatedPolicyRule,
        policy_b: FederatedPolicy,
        rule_b: FederatedPolicyRule,
    ) -> PolicyConflict | None:
        """Check if two rules from different domains conflict."""
        # Overlap detection: same condition keys with different constraints
        a_keys = set(rule_a.condition.keys())
        b_keys = set(rule_b.condition.keys())
        shared_keys = a_keys & b_keys

        if not shared_keys:
            return None

        # Check for contradictory constraints
        a_constraint_keys = set(rule_a.constraint.keys())
        b_constraint_keys = set(rule_b.constraint.keys())
        shared_constraints = a_constraint_keys & b_constraint_keys

        if not shared_constraints:
            return None

        # Found overlapping conditions AND constraints — potential conflict
        conflict_type = ConflictType.OVERLAPPING
        severity = ConflictSeverity.MEDIUM

        # Check for direct contradiction (opposite constraint values)
        for key in shared_constraints:
            val_a = rule_a.constraint[key]
            val_b = rule_b.constraint[key]
            if isinstance(val_a, bool) and isinstance(val_b, bool) and val_a != val_b:
                conflict_type = ConflictType.CONTRADICTORY
                severity = ConflictSeverity.HIGH
                break
            if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                # Numeric constraints with significant difference
                if val_a != val_b:
                    conflict_type = ConflictType.RESOURCE_CONTENTION
                    severity = ConflictSeverity.MEDIUM

        return PolicyConflict(
            policy_a_id=str(policy_a.policy_id),
            policy_a_name=policy_a.name,
            policy_a_domain=policy_a.domain_id,
            policy_b_id=str(policy_b.policy_id),
            policy_b_name=policy_b.name,
            policy_b_domain=policy_b.domain_id,
            conflict_type=conflict_type,
            severity=severity,
            description=(
                f"Rules '{rule_a.name}' ({policy_a.domain_id}) and "
                f"'{rule_b.name}' ({policy_b.domain_id}) have overlapping conditions "
                f"on {shared_keys} with conflicting constraints on {shared_constraints}"
            ),
        )

    def resolve_conflict(
        self, conflict_id: str, resolution: str, resolved_by: str = "system"
    ) -> PolicyConflict | None:
        """Mark a conflict as resolved."""
        conflict = self._conflicts.get(conflict_id)
        if conflict is None:
            return None
        from datetime import datetime
        conflict.resolution = resolution
        conflict.resolved_at = datetime.utcnow()
        conflict.resolved_by = resolved_by
        self._log_event(
            GovernanceEventType.CONFLICT_RESOLVED, resolved_by,
            [conflict.policy_a_domain, conflict.policy_b_domain],
            {"conflict_id": conflict_id, "resolution": resolution},
        )
        return conflict

    def get_unresolved_conflicts(self) -> list[PolicyConflict]:
        return [c for c in self._conflicts.values() if c.resolution is None]

    def get_all_conflicts(self) -> list[PolicyConflict]:
        return list(self._conflicts.values())

    # --- CSL Integration ---

    def get_csl_policies(self) -> list[Any]:
        """Convert federated policies to CSLPolicy format for Guardian integration.

        Returns a list of CSLPolicy objects that the CSL policy service can evaluate.
        """
        if not self._loaded:
            self.load_policies()

        try:
            from src.services.csl_policy_service import CSLPolicy, CSLRule

            csl_policies = []
            for policy in self._policies.values():
                if not policy.is_active:
                    continue

                csl_policy = CSLPolicy(
                    name=f"federated_{policy.namespace}",
                    version=policy.version,
                    description=f"[Federated] {policy.description}",
                )

                for rule in policy.rules:
                    csl_rule = CSLRule(
                        name=f"fed_{policy.namespace}_{rule.name}",
                        policy_name=csl_policy.name,
                        condition=rule.condition,
                        constraint=rule.constraint,
                        message=rule.message or f"Federated rule: {rule.name}",
                    )
                    csl_policy.add_rule(csl_rule)

                if csl_policy.rules:
                    csl_policies.append(csl_policy)

            logger.info(f"Converted {len(csl_policies)} federated policies to CSL format")
            return csl_policies

        except ImportError:
            logger.warning("CSL policy service not available for federated integration")
            return []

    # --- Audit ---

    def _log_event(
        self, event_type: GovernanceEventType, actor: str,
        affected_domains: list[str], details: dict[str, Any],
    ) -> None:
        self._audit_log.append(GovernanceAuditEntry(
            event_type=event_type,
            actor=actor,
            affected_domains=affected_domains,
            details=details,
        ))

    def get_audit_log(
        self, limit: int = 100, domain_id: str | None = None,
        event_type: GovernanceEventType | None = None,
    ) -> list[GovernanceAuditEntry]:
        entries = self._audit_log
        if domain_id:
            entries = [e for e in entries if domain_id in e.affected_domains]
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]
        return sorted(entries, key=lambda e: e.timestamp, reverse=True)[:limit]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_federated_service: FederatedPolicyService | None = None


def get_federated_service() -> FederatedPolicyService:
    """Get or create the federated policy service singleton."""
    global _federated_service
    if _federated_service is None:
        _federated_service = FederatedPolicyService()
    return _federated_service
