"""Policy scaffold service for domain-specific policy loading.

Loads policy scaffolds by scenario domain type, enabling dynamic policy
configuration based on the nature of the analysis being performed.

Scaffold types:
    - environmental: Scope 3 emissions, carbon tracking
    - financial: Budget management, transaction processing
    - safety: Grid stability, infrastructure monitoring
    - operational: Churn prevention, customer management
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger("carf.policy_scaffold")


class PolicyScaffold(BaseModel):
    """A domain-specific policy scaffold configuration."""

    name: str
    domain: str
    version: str = "1.0"
    description: str = ""
    csl_policies: list[str] = Field(default_factory=list)
    csl_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    domain_rules: dict[str, dict[str, Any]] = Field(default_factory=dict)
    opa_policies: list[str] = Field(default_factory=list)


class PolicyScaffoldService:
    """Service for loading and managing domain-specific policy scaffolds.

    Scaffolds define which CSL policies to activate and what overrides
    to apply for a given domain context (environmental, financial, etc.).

    Usage:
        service = get_scaffold_service()
        scaffold = service.get_scaffold("financial")
        if scaffold:
            # Apply scaffold overrides to CSL evaluation context
    """

    def __init__(self, scaffold_dir: str | Path | None = None) -> None:
        self._scaffolds: dict[str, PolicyScaffold] = {}
        self._load_scaffolds(scaffold_dir)

    def _load_scaffolds(self, scaffold_dir: str | Path | None) -> None:
        """Load all scaffold YAML files from the scaffold directory."""
        if scaffold_dir is None:
            scaffold_dir = Path(__file__).parent.parent.parent / "config" / "policy_scaffolds"
        else:
            scaffold_dir = Path(scaffold_dir)

        if not scaffold_dir.exists():
            logger.warning(f"Scaffold directory not found: {scaffold_dir}")
            return

        for yaml_file in scaffold_dir.glob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f) or {}

                scaffold_data = data.get("scaffold", {})
                scaffold = PolicyScaffold(
                    name=scaffold_data.get("name", yaml_file.stem),
                    domain=scaffold_data.get("domain", yaml_file.stem),
                    version=scaffold_data.get("version", "1.0"),
                    description=scaffold_data.get("description", ""),
                    csl_policies=data.get("csl_policies", []),
                    csl_overrides=data.get("csl_overrides", {}),
                    domain_rules=data.get("domain_rules", {}),
                    opa_policies=data.get("opa_policies", []),
                )

                self._scaffolds[scaffold.domain] = scaffold
                logger.info(f"Loaded scaffold '{scaffold.name}' for domain '{scaffold.domain}'")

            except Exception as e:
                logger.error(f"Failed to load scaffold from {yaml_file}: {e}")

        logger.info(f"Loaded {len(self._scaffolds)} policy scaffolds")

    def get_scaffold(self, domain: str) -> PolicyScaffold | None:
        """Get a scaffold by domain name.

        Args:
            domain: Domain type (environmental, financial, safety, operational)

        Returns:
            PolicyScaffold if found, None otherwise
        """
        return self._scaffolds.get(domain.lower())

    def get_scaffold_for_scenario(self, scenario_metadata: dict[str, Any]) -> PolicyScaffold | None:
        """Get the appropriate scaffold based on scenario metadata.

        Inspects scenario metadata to determine the domain type and
        returns the matching scaffold.

        Args:
            scenario_metadata: Dict with scenario configuration

        Returns:
            Matching PolicyScaffold or None
        """
        domain = scenario_metadata.get("domain_type", "").lower()
        if domain:
            return self.get_scaffold(domain)

        # Try to infer domain from scenario keywords
        keywords = scenario_metadata.get("keywords", [])
        scenario_name = scenario_metadata.get("name", "").lower()

        domain_keywords = {
            "environmental": ["emission", "carbon", "scope3", "sustainability", "climate"],
            "financial": ["budget", "transaction", "payment", "transfer", "cost"],
            "safety": ["grid", "voltage", "frequency", "stability", "infrastructure"],
            "operational": ["churn", "customer", "retention", "discount", "outreach"],
        }

        for domain_name, domain_kws in domain_keywords.items():
            for kw in domain_kws:
                if kw in scenario_name or kw in " ".join(keywords).lower():
                    return self.get_scaffold(domain_name)

        return None

    def apply_scaffold_overrides(
        self,
        scaffold: PolicyScaffold,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply scaffold-specific overrides to a CSL context.

        Modifies the evaluation context with domain-specific adjustments
        from the scaffold configuration.

        Args:
            scaffold: The policy scaffold to apply
            context: Base CSL evaluation context

        Returns:
            Modified context with scaffold overrides applied
        """
        modified = dict(context)
        modified["_scaffold"] = {
            "name": scaffold.name,
            "domain": scaffold.domain,
            "active_csl_policies": scaffold.csl_policies,
            "active_opa_policies": scaffold.opa_policies,
        }

        # Apply domain rule overrides
        for rule_name, rule_config in scaffold.domain_rules.items():
            if rule_name not in modified:
                modified[rule_name] = {}
            if isinstance(modified[rule_name], dict) and isinstance(rule_config, dict):
                modified[rule_name].update(rule_config)

        return modified

    @property
    def available_domains(self) -> list[str]:
        """List all available scaffold domains."""
        return list(self._scaffolds.keys())

    @property
    def scaffold_count(self) -> int:
        """Get the number of loaded scaffolds."""
        return len(self._scaffolds)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_scaffold_service: PolicyScaffoldService | None = None


def get_scaffold_service() -> PolicyScaffoldService:
    """Get or create the policy scaffold service singleton."""
    global _scaffold_service
    if _scaffold_service is None:
        _scaffold_service = PolicyScaffoldService()
    return _scaffold_service
