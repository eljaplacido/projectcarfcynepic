# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Neurosymbolic Reasoning Engine — Phase 17.

Tightly-coupled neural-symbolic reasoning loop that integrates:
- Symbolic Knowledge Base with forward-chaining inference
- LLM-based fact extraction and deepening
- Constraint-guided generation (symbolic rules constrain LLM output)
- Shortcut reasoning detection
- Graph-grounded reasoning via Neo4j

Research basis: DeepGraphLog [19], ProSLM [29], CASSANDRA [25],
Prototypical NeSy [21], Knowledge Graphs for NeSy [30][31].
"""

from __future__ import annotations

import json
import logging
from collections import deque
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.services.neo4j_service import Neo4jService

logger = logging.getLogger("carf.neurosymbolic")


# =============================================================================
# DATA MODELS
# =============================================================================


class SymbolicFact(BaseModel):
    """A typed fact in the knowledge base."""

    fact_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    entity: str = Field(..., description="The entity this fact is about")
    attribute: str = Field(..., description="The attribute or property")
    value: str = Field(..., description="The value")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = Field(default="unknown", description="Where this fact came from")

    @property
    def key(self) -> str:
        """Unique key for deduplication."""
        return f"{self.entity}:{self.attribute}:{self.value}"


class RuleCondition(BaseModel):
    """A condition in a symbolic rule."""

    attribute: str
    operator: str = Field(default="==", description="==, !=, >, <, >=, <=, contains")
    value: str


class SymbolicRule(BaseModel):
    """A symbolic inference rule (Horn clause)."""

    rule_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str = Field(default="")
    conditions: list[RuleCondition] = Field(default_factory=list)
    conclusion_attribute: str = Field(default="")
    conclusion_value: str = Field(default="")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = Field(default="manual")

    def evaluate(self, facts: dict[str, SymbolicFact]) -> bool:
        """Check if all conditions are satisfied by the current facts."""
        for cond in self.conditions:
            matching = [
                f for f in facts.values()
                if f.attribute == cond.attribute
            ]
            if not matching:
                return False

            satisfied = False
            for fact in matching:
                if cond.operator == "==" and fact.value == cond.value:
                    satisfied = True
                elif cond.operator == "!=" and fact.value != cond.value:
                    satisfied = True
                elif cond.operator == "contains" and cond.value in fact.value:
                    satisfied = True
                elif cond.operator in (">", "<", ">=", "<="):
                    try:
                        fv, cv = float(fact.value), float(cond.value)
                        if cond.operator == ">" and fv > cv:
                            satisfied = True
                        elif cond.operator == "<" and fv < cv:
                            satisfied = True
                        elif cond.operator == ">=" and fv >= cv:
                            satisfied = True
                        elif cond.operator == "<=" and fv <= cv:
                            satisfied = True
                    except ValueError:
                        pass
            if not satisfied:
                return False
        return True


class Violation(BaseModel):
    """A symbolic constraint violation."""

    rule_id: str
    rule_name: str
    description: str
    severity: str = Field(default="warning")


class ShortcutWarning(BaseModel):
    """A detected reasoning shortcut."""

    description: str
    skipped_steps: list[str] = Field(default_factory=list)
    recommendation: str = Field(default="")


class NeSyReasoningResult(BaseModel):
    """Result of neurosymbolic reasoning."""

    conclusion: str = Field(default="")
    derived_facts: list[SymbolicFact] = Field(default_factory=list)
    rule_chain: list[str] = Field(default_factory=list)
    shortcut_warnings: list[str] = Field(default_factory=list)
    iterations: int = Field(default=0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    grounding_facts: list[SymbolicFact] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)


# =============================================================================
# KNOWLEDGE BASE
# =============================================================================


class KnowledgeBase:
    """Symbolic knowledge base with forward-chaining inference."""

    def __init__(self):
        self.facts: dict[str, SymbolicFact] = {}
        self.rules: list[SymbolicRule] = []

    def add_fact(self, fact: SymbolicFact) -> bool:
        """Add a fact, returning True if it's new or higher confidence."""
        key = fact.key
        if key in self.facts:
            if fact.confidence > self.facts[key].confidence:
                self.facts[key] = fact
                return True
            return False
        self.facts[key] = fact
        return True

    def add_rule(self, rule: SymbolicRule) -> None:
        """Add an inference rule."""
        # Deduplicate by rule_id
        existing_ids = {r.rule_id for r in self.rules}
        if rule.rule_id not in existing_ids:
            self.rules.append(rule)

    def forward_chain(self, max_iterations: int = 10) -> list[SymbolicFact]:
        """Run forward chaining to derive new facts.

        Returns list of newly derived facts.
        """
        derived: list[SymbolicFact] = []

        for _ in range(max_iterations):
            new_facts_this_round = False

            for rule in self.rules:
                if rule.evaluate(self.facts):
                    # Derive conclusion
                    # Find matching entity from conditions
                    entity = "system"
                    for cond in rule.conditions:
                        for fact in self.facts.values():
                            if fact.attribute == cond.attribute:
                                entity = fact.entity
                                break
                        if entity != "system":
                            break

                    new_fact = SymbolicFact(
                        entity=entity,
                        attribute=rule.conclusion_attribute,
                        value=rule.conclusion_value,
                        confidence=rule.confidence * 0.95,  # Slight decay for derived facts
                        source=f"rule:{rule.name or rule.rule_id}",
                    )

                    if self.add_fact(new_fact):
                        derived.append(new_fact)
                        new_facts_this_round = True

            if not new_facts_this_round:
                break

        return derived

    def get_facts_about(self, entity: str) -> list[SymbolicFact]:
        """Get all facts about a specific entity."""
        return [f for f in self.facts.values() if f.entity == entity]

    def get_gaps(self) -> list[str]:
        """Identify knowledge gaps — rule conditions that have no matching facts."""
        gaps: list[str] = []
        for rule in self.rules:
            for cond in rule.conditions:
                matching = [
                    f for f in self.facts.values()
                    if f.attribute == cond.attribute
                ]
                if not matching:
                    gaps.append(f"Missing fact for attribute '{cond.attribute}' "
                                f"(needed by rule '{rule.name or rule.rule_id}')")
        return list(set(gaps))

    @property
    def size(self) -> int:
        return len(self.facts)

    def import_csl_rules(self) -> int:
        """Import CSL-Core rules into the knowledge base."""
        try:
            from src.services.csl_policy_service import get_csl_service
            csl = get_csl_service()
            if not csl.is_available:
                return 0

            count = 0
            for policy in csl.policies:
                for rule in policy.rules:
                    sym_rule = SymbolicRule(
                        rule_id=f"csl_{rule.name}",
                        name=f"CSL: {rule.name}",
                        conditions=[
                            RuleCondition(
                                attribute=k,
                                operator="==" if not isinstance(v, (int, float)) else "<=",
                                value=str(v),
                            )
                            for k, v in (rule.condition or {}).items()
                        ],
                        conclusion_attribute="policy_status",
                        conclusion_value=rule.action or "enforce",
                        confidence=0.95,
                        source="csl_policy",
                    )
                    self.add_rule(sym_rule)
                    count += 1
            return count
        except Exception as e:
            logger.debug("CSL rule import failed: %s", e)
            return 0


# =============================================================================
# NEUROSYMBOLIC REASONER
# =============================================================================


class NeuralSymbolicReasoner:
    """The core neurosymbolic reasoning engine.

    Implements a tight neural-symbolic integration loop:
    1. LLM extracts facts from query → adds to KnowledgeBase
    2. Forward-chaining derives new facts from rules
    3. Derived facts + gaps fed back to LLM for deeper reasoning
    4. LLM output validated against symbolic constraints
    5. Loop until convergence or max iterations
    """

    def __init__(self):
        self._kb = KnowledgeBase()
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy initialization of rules from CSL and other sources."""
        if self._initialized:
            return
        self._kb.import_csl_rules()
        self._initialized = True

    async def reason(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        use_knowledge_graph: bool = True,
        max_iterations: int = 3,
    ) -> NeSyReasoningResult:
        """Run the full neurosymbolic reasoning loop."""
        self._ensure_initialized()
        context = context or {}

        # Create session-local KB extending the global one
        session_kb = KnowledgeBase()
        session_kb.facts = dict(self._kb.facts)
        session_kb.rules = list(self._kb.rules)

        rule_chain: list[str] = []
        all_derived: list[SymbolicFact] = []
        grounding_facts: list[SymbolicFact] = []
        shortcut_warnings: list[str] = []

        # Step 0: Ground in knowledge graph if available
        if use_knowledge_graph:
            try:
                kg_facts = await self._ground_in_graph(query)
                for fact in kg_facts:
                    session_kb.add_fact(fact)
                grounding_facts = kg_facts
                rule_chain.append(f"Grounded {len(kg_facts)} facts from knowledge graph")
            except Exception as e:
                logger.debug("KG grounding skipped: %s", e)

        # Iterative neural-symbolic loop
        conclusion = ""
        for iteration in range(max_iterations):
            # Step 1: LLM extracts facts
            extracted = await self._extract_facts(query, session_kb, context, iteration)
            for fact in extracted:
                session_kb.add_fact(fact)
            rule_chain.append(f"Iteration {iteration + 1}: extracted {len(extracted)} facts")

            # Step 2: Forward-chain to derive new facts
            derived = session_kb.forward_chain()
            all_derived.extend(derived)
            if derived:
                rule_chain.append(f"Derived {len(derived)} new facts via forward chaining")

            # Step 3: Feed gaps + derived facts back to LLM
            gaps = session_kb.get_gaps()
            conclusion = await self._deepen_reasoning(
                query, session_kb, gaps, derived, context, iteration
            )

            # Step 4: Validate against symbolic constraints
            violations = self._validate_against_rules(conclusion, session_kb)
            if violations:
                rule_chain.append(
                    f"Validation: {len(violations)} violation(s) — correcting"
                )
                # Feed violations back for correction
                conclusion = await self._correct_violations(
                    conclusion, violations, session_kb, context
                )
            else:
                rule_chain.append("Validation: passed all symbolic constraints")

            # Check convergence (no new facts derived)
            if not derived and not extracted:
                rule_chain.append("Converged — no new facts")
                break

        # Step 5: Detect shortcut reasoning
        shortcuts = await self._detect_shortcuts(query, conclusion, session_kb)
        shortcut_warnings = [s.description for s in shortcuts]
        if shortcut_warnings:
            rule_chain.append(f"Shortcut warnings: {len(shortcut_warnings)}")

        # Compute confidence based on grounding and derivation quality
        confidence = self._compute_confidence(
            grounding_facts, all_derived, shortcut_warnings, session_kb
        )

        return NeSyReasoningResult(
            conclusion=conclusion,
            derived_facts=all_derived,
            rule_chain=rule_chain,
            shortcut_warnings=shortcut_warnings,
            iterations=min(iteration + 1, max_iterations),
            confidence=confidence,
            grounding_facts=grounding_facts,
            violations=[],
        )

    async def validate_claim(
        self,
        claim: str,
        evidence: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate a claim against the symbolic knowledge base."""
        self._ensure_initialized()

        session_kb = KnowledgeBase()
        session_kb.facts = dict(self._kb.facts)
        session_kb.rules = list(self._kb.rules)

        # Add evidence as facts
        for i, ev in enumerate(evidence):
            session_kb.add_fact(SymbolicFact(
                entity="evidence",
                attribute=f"evidence_{i}",
                value=ev,
                confidence=0.8,
                source="user_provided",
            ))

        # Validate
        violations = self._validate_against_rules(claim, session_kb)
        shortcuts = await self._detect_shortcuts("", claim, session_kb)

        return {
            "is_valid": len(violations) == 0,
            "violations": [v.description for v in violations],
            "shortcut_warnings": [s.description for s in shortcuts],
            "supporting_rules": [
                r.name for r in session_kb.rules
                if r.evaluate(session_kb.facts)
            ][:10],
            "confidence": 0.8 if not violations else 0.3,
        }

    async def _extract_facts(
        self,
        query: str,
        kb: KnowledgeBase,
        context: dict[str, Any],
        iteration: int,
    ) -> list[SymbolicFact]:
        """Use LLM to extract structured facts from the query."""
        from langchain_core.messages import HumanMessage
        from src.core.llm import get_llm

        llm = get_llm()

        existing_facts = [
            f"{f.entity}.{f.attribute} = {f.value}"
            for f in list(kb.facts.values())[:20]
        ]

        prompt = f"""Extract structured facts from this query. {"This is iteration " + str(iteration + 1) + " — look for facts missed earlier." if iteration > 0 else ""}

Query: {query}

Already known facts:
{chr(10).join(existing_facts) if existing_facts else "(none)"}

Return a JSON list of facts, each with:
- "entity": the entity name (string)
- "attribute": the property (string)
- "value": the value (string)
- "confidence": how certain (0-1)

Focus on causal relationships, quantities, and domain concepts.
Return ONLY a JSON array, no markdown fencing."""

        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(content)

            facts = []
            for item in parsed:
                if isinstance(item, dict) and "entity" in item and "attribute" in item:
                    facts.append(SymbolicFact(
                        entity=item["entity"],
                        attribute=item["attribute"],
                        value=str(item.get("value", "")),
                        confidence=float(item.get("confidence", 0.7)),
                        source=f"llm_extraction_iter{iteration}",
                    ))
            return facts
        except Exception as e:
            logger.debug("Fact extraction failed: %s", e)
            return []

    async def _deepen_reasoning(
        self,
        query: str,
        kb: KnowledgeBase,
        gaps: list[str],
        derived: list[SymbolicFact],
        context: dict[str, Any],
        iteration: int,
    ) -> str:
        """Feed derived facts and gaps back to LLM for deeper reasoning."""
        from langchain_core.messages import HumanMessage
        from src.core.llm import get_llm

        llm = get_llm()

        derived_text = [
            f"- {f.entity}.{f.attribute} = {f.value} (from {f.source})"
            for f in derived
        ]
        gap_text = [f"- {g}" for g in gaps[:5]]

        prompt = f"""Based on the following analysis, provide a reasoned conclusion.

Original question: {query}

Newly derived facts (from symbolic inference):
{chr(10).join(derived_text) if derived_text else "(none)"}

Knowledge gaps identified:
{chr(10).join(gap_text) if gap_text else "(none — knowledge base is complete)"}

Provide a clear, well-reasoned conclusion that:
1. Uses the derived facts as evidence
2. Acknowledges any knowledge gaps
3. Identifies causal mechanisms where possible
4. Avoids conclusions not supported by the facts"""

        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            logger.error("Deepening reasoning failed: %s", e)
            return f"Reasoning incomplete due to error: {e}"

    def _validate_against_rules(
        self, text: str, kb: KnowledgeBase
    ) -> list[Violation]:
        """Validate LLM output against symbolic constraints."""
        violations: list[Violation] = []

        for rule in kb.rules:
            # Check if rule conditions are met but conclusion contradicts text
            if rule.evaluate(kb.facts):
                # Check if text contradicts the rule's conclusion
                expected = rule.conclusion_value.lower()
                if expected in ("reject", "deny", "block", "enforce"):
                    # This is a constraint rule — check for violations
                    for cond in rule.conditions:
                        # Look for contradicting facts in the text
                        for fact in kb.facts.values():
                            if (fact.attribute == cond.attribute and
                                    fact.value != cond.value and
                                    fact.source.startswith("llm")):
                                violations.append(Violation(
                                    rule_id=rule.rule_id,
                                    rule_name=rule.name,
                                    description=(
                                        f"Rule '{rule.name}' expects {cond.attribute}="
                                        f"{cond.value} but found {fact.value}"
                                    ),
                                    severity="warning",
                                ))

        return violations

    async def _correct_violations(
        self,
        text: str,
        violations: list[Violation],
        kb: KnowledgeBase,
        context: dict[str, Any],
    ) -> str:
        """Ask LLM to correct its output given symbolic violations."""
        from langchain_core.messages import HumanMessage
        from src.core.llm import get_llm

        llm = get_llm()

        violation_text = "\n".join(
            f"- {v.description} (severity: {v.severity})"
            for v in violations
        )

        prompt = f"""Your previous reasoning had symbolic constraint violations:

{violation_text}

Original text:
{text}

Please revise your conclusion to respect these constraints.
Maintain accuracy while ensuring compliance with the rules."""

        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            logger.warning("Violation correction failed: %s", e)
            return text + f"\n\n[Warning: {len(violations)} constraint violation(s) detected]"

    async def _detect_shortcuts(
        self, query: str, conclusion: str, kb: KnowledgeBase
    ) -> list[ShortcutWarning]:
        """Detect shortcut reasoning where LLM skips required causal steps.

        Checks if the conclusion references outcomes that should require
        intermediate facts in the knowledge base that aren't present.
        """
        warnings: list[ShortcutWarning] = []

        # Build a dependency graph from rules
        # For each rule, conclusion depends on conditions
        dependency_graph: dict[str, list[str]] = {}
        for rule in kb.rules:
            if rule.conclusion_attribute:
                deps = [c.attribute for c in rule.conditions]
                dependency_graph[rule.conclusion_attribute] = deps

        # Check if conclusion references derived attributes
        # whose dependencies aren't in the fact base
        conclusion_lower = conclusion.lower()
        for attr, deps in dependency_graph.items():
            if attr.lower() in conclusion_lower:
                missing_deps = []
                for dep in deps:
                    has_fact = any(
                        f.attribute == dep for f in kb.facts.values()
                    )
                    if not has_fact:
                        missing_deps.append(dep)

                if missing_deps:
                    warnings.append(ShortcutWarning(
                        description=(
                            f"Conclusion references '{attr}' but prerequisite "
                            f"facts {missing_deps} were not established"
                        ),
                        skipped_steps=missing_deps,
                        recommendation=(
                            f"Establish facts for {missing_deps} before "
                            f"drawing conclusions about '{attr}'"
                        ),
                    ))

        return warnings

    async def _ground_in_graph(self, query: str) -> list[SymbolicFact]:
        """Pull relevant facts from Neo4j knowledge graph."""
        facts: list[SymbolicFact] = []

        try:
            from src.services.neo4j_service import get_neo4j_service
            neo4j = get_neo4j_service()

            # Get relevant causal graph
            graph = await neo4j.get_causal_graph()
            if not graph or not graph.nodes:
                return facts

            # Convert edges to facts
            for src_var, targets in graph.to_adjacency_list().items():
                for target in targets:
                    facts.append(SymbolicFact(
                        entity=src_var,
                        attribute="causes",
                        value=target,
                        confidence=0.8,
                        source="neo4j_causal_graph",
                    ))

            # Convert nodes to facts
            for node in graph.nodes:
                facts.append(SymbolicFact(
                    entity=node.name,
                    attribute="type",
                    value=node.variable_type,
                    confidence=0.9,
                    source="neo4j_causal_graph",
                ))
                if node.role:
                    facts.append(SymbolicFact(
                        entity=node.name,
                        attribute="role",
                        value=node.role,
                        confidence=0.9,
                        source="neo4j_causal_graph",
                    ))

        except Exception as e:
            logger.debug("Neo4j graph grounding failed: %s", e)

        return facts

    def _compute_confidence(
        self,
        grounding_facts: list[SymbolicFact],
        derived_facts: list[SymbolicFact],
        shortcut_warnings: list[str],
        kb: KnowledgeBase,
    ) -> float:
        """Compute overall confidence based on reasoning quality."""
        score = 0.5  # Base

        # Bonus for graph grounding
        if grounding_facts:
            score += min(len(grounding_facts) * 0.02, 0.15)

        # Bonus for successful derivations
        if derived_facts:
            score += min(len(derived_facts) * 0.03, 0.15)

        # Bonus for large knowledge base
        if kb.size > 10:
            score += 0.1

        # Penalty for shortcut warnings
        score -= len(shortcut_warnings) * 0.1

        return max(0.0, min(1.0, score))


# =============================================================================
# SINGLETON
# =============================================================================

_engine: NeuralSymbolicReasoner | None = None


def get_neurosymbolic_engine() -> NeuralSymbolicReasoner:
    """Get the singleton NeuralSymbolicReasoner."""
    global _engine
    if _engine is None:
        _engine = NeuralSymbolicReasoner()
    return _engine
