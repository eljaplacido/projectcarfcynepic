"""Cynefin Router - Layer 1 of the CARF Cognitive Stack.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

The Router is the entry point that classifies incoming signals into Cynefin domains
and routes them to the appropriate cognitive agent.

Domains:
- Clear: Deterministic automation (cause-effect obvious)
- Complicated: Causal analysis (requires expert analysis)
- Complex: Bayesian exploration (emergent, probe required)
- Chaotic: Circuit breaker (crisis stabilization)
- Disorder: Human escalation (cannot classify)
"""

import json
import logging
import math
import os
from collections import Counter, deque
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.core.llm import get_router_model
from src.core.state import (
    ConfidenceLevel,
    CynefinDomain,
    EpistemicState,
)
from src.utils.resiliency import async_retry_with_backoff

logger = logging.getLogger("carf.router")


class DomainClassification(BaseModel):
    """Output schema for the domain classification LLM call."""

    domain: CynefinDomain = Field(
        ..., description="The classified Cynefin domain"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Classification confidence (0-1)"
    )
    reasoning: str = Field(
        ..., description="Brief explanation for the classification"
    )
    key_indicators: list[str] = Field(
        default_factory=list, description="Indicators that led to this classification"
    )
    domain_distribution: dict[str, float] | None = Field(
        default=None,
        description=(
            "Full probability distribution over Cynefin domains when available "
            "(e.g. DistilBERT softmax). None for point-estimate classifiers (LLM)."
        ),
    )


class RouterConfig(BaseModel):
    """Configuration for Cynefin Router with per-domain thresholds."""

    # Global thresholds
    confidence_threshold: float = Field(0.70, ge=0.0, le=1.0, description="Below this → Disorder")
    entropy_threshold_chaotic: float = Field(0.9, ge=0.0, le=1.0, description="Above this → Chaotic")

    # Per-domain confidence thresholds (allow finer control)
    clear_threshold: float = Field(0.95, ge=0.0, le=1.0, description="Threshold for Clear domain")
    complicated_threshold: float = Field(0.85, ge=0.0, le=1.0, description="Threshold for Complicated")
    complex_threshold: float = Field(0.70, ge=0.0, le=1.0, description="Threshold for Complex")

    # Per-domain entropy thresholds
    clear_entropy_max: float = Field(0.2, ge=0.0, le=1.0, description="Max entropy for Clear")
    complicated_entropy_max: float = Field(0.5, ge=0.0, le=1.0, description="Max entropy for Complicated")
    complex_entropy_range: tuple[float, float] = Field((0.5, 0.8), description="Entropy range for Complex")

    # Feature flags
    use_data_hints: bool = Field(True, description="Use data structure hints for domain detection")
    use_pattern_matching: bool = Field(True, description="Use pattern matching for domain hints")
    allow_user_override: bool = Field(True, description="Allow user-specified domain hints")

    # Principled Chaotic gate over the domain-probability distribution (R1/G5).
    # Opt-in: when disabled (default) entropy stays informational metadata only,
    # preserving the existing "entropy is not a hard gate" contract. Calibrate the
    # thresholds against the H0 router benchmark before enabling in a profile.
    enable_chaotic_distribution_gate: bool = Field(
        False,
        description=(
            "When True, route to Chaotic (circuit breaker) on high domain-distribution "
            "entropy combined with a rapid distribution shift over the rolling window."
        ),
    )
    chaotic_change_threshold: float = Field(
        0.35,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum Jensen-Shannon distance between the current domain distribution "
            "and the rolling-window mean to qualify as a 'rapid shift' for the Chaotic gate."
        ),
    )
    chaotic_window_size: int = Field(
        20,
        ge=1,
        description="Length of the rolling window of recent domain distributions (AP-4 bounded).",
    )

    # Conformal prediction-set escalation (R1/G2). Opt-in: when enabled, a borderline
    # query (prediction set cardinality > 1) is pushed to Disorder/human escalation.
    # Default off → the prediction set is recorded as metadata only, no routing change.
    conformal_escalate_on_ambiguous: bool = Field(
        False,
        description="Route ambiguous (multi-domain prediction set) queries to human escalation.",
    )


# Data structure patterns that hint at specific domains
DATA_STRUCTURE_HINTS = {
    "Complicated": {
        "column_patterns": [
            "treatment", "intervention", "program", "campaign", "exposure",
            "outcome", "result", "effect", "impact", "conversion", "churn",
            "confounder", "covariate", "control"
        ],
        "indicators": ["causal", "effect", "treatment", "outcome"],
    },
    "Complex": {
        "column_patterns": [
            "probability", "belief", "prior", "posterior", "uncertainty",
            "hypothesis", "prediction", "forecast", "scenario"
        ],
        "indicators": ["uncertain", "belief", "probability", "forecast", "predict"],
    },
    "Clear": {
        "column_patterns": ["id", "lookup", "reference", "key"],
        "indicators": ["lookup", "find", "get", "retrieve", "what is"],
    },
    "Chaotic": {
        "column_patterns": ["alert", "incident", "emergency", "critical"],
        "indicators": ["emergency", "critical", "down", "breach", "failure", "crisis"],
    },
}


def _load_persisted_router_hints() -> None:
    """Load persisted router hint overrides and merge into in-memory hints."""
    try:
        from src.services.router_retraining_service import get_router_retraining_service

        service = get_router_retraining_service()
        overrides = service.load_persisted_hint_overrides()
        if not overrides:
            return

        for raw_domain, values in overrides.items():
            canonical = raw_domain.capitalize()
            if canonical not in DATA_STRUCTURE_HINTS:
                continue
            domain_hints = DATA_STRUCTURE_HINTS[canonical]
            indicators = list(domain_hints.get("indicators", []))
            existing = {str(v).lower() for v in indicators}

            additions = 0
            for value in values:
                normalized = str(value).strip().lower()
                if not normalized or normalized in existing:
                    continue
                indicators.append(normalized)
                existing.add(normalized)
                additions += 1

            domain_hints["indicators"] = indicators
            if additions:
                logger.info(
                    "Loaded %d persisted router hint(s) for %s",
                    additions,
                    canonical,
                )
    except Exception as exc:
        logger.debug("Persisted router hints not loaded: %s", exc)


_load_persisted_router_hints()


class CynefinRouter:
    """The Sense-Making Gateway for CARF.

    Classifies incoming requests into Cynefin domains using:
    1. LLM-based semantic classification
    2. Signal entropy analysis
    3. Confidence thresholding
    4. Data structure hints (NEW)
    5. Query pattern matching (NEW)

    If confidence falls below threshold (default 0.85), routes to Disorder
    for human escalation via HumanLayer.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.70,
        entropy_threshold_chaotic: float = 0.9,
        mode: str | None = None,
        model_path: str | None = None,
        config: RouterConfig | None = None,
    ):
        """Initialize the Cynefin Router.

        Args:
            confidence_threshold: Below this → Disorder
            entropy_threshold_chaotic: Above this → Chaotic
            mode: "llm" or "distilbert" (defaults to ROUTER_MODE env or "llm")
            model_path: Path to trained model (defaults to ROUTER_MODEL_PATH env)
            config: Full router configuration (overrides individual params)

        Note: LLM provider is configured via environment variables.
        Set LLM_PROVIDER=deepseek and DEEPSEEK_API_KEY for cost-efficient operation.
        """
        # Load configuration
        if config:
            self.config = config
        else:
            self.config = RouterConfig(
                confidence_threshold=confidence_threshold,
                entropy_threshold_chaotic=entropy_threshold_chaotic,
            )

        self.mode = (mode or os.getenv("ROUTER_MODE", "llm")).lower()
        if self.mode not in {"llm", "distilbert"}:
            logger.warning(f"Unknown router mode '{self.mode}', defaulting to LLM.")
            self.mode = "llm"
        self.model_path = model_path or os.getenv("ROUTER_MODEL_PATH", "models/router_distilbert")
        self.model = None
        self.tokenizer = None
        self._torch = None
        self._device = None
        self._id_to_label: dict[int, str] = {
            0: "Clear",
            1: "Complicated",
            2: "Complex",
            3: "Chaotic",
            4: "Disorder",
        }

        if self.mode == "distilbert":
            if not self._load_distilbert():
                self.mode = "llm"

        if self.mode == "llm":
            self.model = get_router_model()

        # Use config values
        self.confidence_threshold = self.config.confidence_threshold
        self.entropy_threshold_chaotic = self.config.entropy_threshold_chaotic

        # Rolling window of recent domain distributions for the Chaotic gate (AP-4 bounded).
        self._recent_distributions: deque[dict[str, float]] = deque(
            maxlen=self.config.chaotic_window_size
        )

        # Optional split-conformal calibration artifact (R1/G2). Absent → no-op.
        self._conformal = self._load_conformal_calibration()

        self.system_prompt = self._build_system_prompt()

    def _load_conformal_calibration(self):
        """Load a conformal calibration artifact if one is configured (graceful)."""
        try:
            from src.utils.conformal import load_calibration

            path = os.getenv("CARF_CONFORMAL_PATH", "models/router_conformal.json")
            calibration = load_calibration(path)
            if calibration is not None:
                logger.info(
                    "Loaded conformal router calibration (alpha=%.2f, n=%d) from %s",
                    calibration.alpha, calibration.n_calibration, path,
                )
            return calibration
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Conformal calibration unavailable: %s", exc)
            return None

    def _load_distilbert(self) -> bool:
        """Load a DistilBERT model for local routing."""
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError:
            logger.warning("Router model deps missing; falling back to LLM mode.")
            return False

        model_dir = Path(self.model_path)
        if not model_dir.exists():
            logger.warning("Router model path not found; falling back to LLM mode.")
            return False

        try:
            self._torch = torch
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
            self.model.to(self._device)
            self.model.eval()
            self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir))

            mapping_path = model_dir / "label_mappings.json"
            if mapping_path.exists():
                mappings = json.loads(mapping_path.read_text(encoding="utf-8"))
                id_to_label = mappings.get("id_to_label", {})
                self._id_to_label = {int(k): v for k, v in id_to_label.items()}
            return True
        except Exception as exc:
            logger.warning(f"Failed to load router model ({exc}); falling back to LLM.")
            return False

    def _build_system_prompt(self) -> str:
        """Build the classification system prompt."""
        return """You are a context classifier for the CARF (Complex-Adaptive Reasoning Fabric) system.
Your task is to classify incoming requests into one of five Cynefin domains.

## Domains:

1. **Clear**: The answer is obvious and requires no analysis. Direct lookup or standard procedure.
   - Examples: "What is 2+2?", "Look up customer ID 123", "Get current stock price"
   - Indicators: simple lookup, standard procedure, known answer, deterministic

2. **Complicated**: Requires expert analysis but has a knowable answer. Root cause analysis needed.
   - Examples: "Why did our costs increase 15%?", "Optimize this database query", "Diagnose this error"
   - Indicators: root cause analysis, optimization required, multiple factors, expert needed

3. **Complex**: Novel situation where cause-effect is only clear in retrospect. Requires probing.
   - Examples: "How will the market react?", "Predict user adoption", "What's the best strategy?"
   - Indicators: novel situation, high uncertainty, emergent behavior, probe required

4. **Chaotic**: Emergency requiring immediate stabilization. Crisis mode.
   - Examples: "System is down!", "Security breach detected", "Data corruption in progress"
   - Indicators: emergency, critical failure, immediate action needed, crisis

5. **Disorder**: You cannot confidently classify the request. Needs human clarification.
   - Use when: request is ambiguous, missing context, contradictory, or you're genuinely unsure
   - Indicators: unclear intent, missing information, ambiguous language

## Output Format:
Respond with a JSON object only, no other text:
{
    "domain": "Clear|Complicated|Complex|Chaotic|Disorder",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of classification",
    "key_indicators": ["indicator1", "indicator2"]
}

## Important Rules:
- Be conservative: if unsure, classify as Disorder to escalate to a human
- High confidence (>0.9) only for unambiguous cases
- Consider the ACTION required, not just the topic
- Emergency keywords should bias toward Chaotic
- Vague or philosophical questions should bias toward Complex or Disorder"""

    def _detect_data_hints(self, context: dict[str, Any]) -> tuple[str | None, list[str]]:
        """Detect domain hints from data structure.

        Analyzes column names and data patterns to suggest domain.

        Args:
            context: Context containing data/column information

        Returns:
            Tuple of (suggested_domain, indicators)
        """
        if not self.config.use_data_hints:
            return None, []

        indicators = []

        # Check causal estimation config
        causal_config = context.get("causal_estimation")
        if causal_config:
            if causal_config.get("treatment") and causal_config.get("outcome"):
                indicators.append(f"treatment={causal_config.get('treatment')}")
                indicators.append(f"outcome={causal_config.get('outcome')}")
                return "Complicated", indicators

        # Check bayesian inference config
        bayesian_config = context.get("bayesian_inference")
        if bayesian_config:
            if bayesian_config.get("prior_belief") or bayesian_config.get("observations"):
                indicators.append("bayesian_inference_config_present")
                return "Complex", indicators

        # Check for column names in dataset selection
        dataset_selection = context.get("dataset_selection")
        if dataset_selection:
            columns = []
            if isinstance(dataset_selection, dict):
                columns = [
                    dataset_selection.get("treatment", ""),
                    dataset_selection.get("outcome", ""),
                ] + dataset_selection.get("covariates", [])

            columns_lower = [c.lower() for c in columns if c]

            for domain, hints in DATA_STRUCTURE_HINTS.items():
                for pattern in hints.get("column_patterns", []):
                    if any(pattern in col for col in columns_lower):
                        indicators.append(f"column_pattern={pattern}")
                        if len(indicators) >= 2:
                            return domain, indicators

        return None, indicators

    def _detect_query_patterns(self, query: str) -> tuple[str | None, list[str]]:
        """Detect domain from query text patterns.

        Uses keyword matching for initial domain hints.

        Args:
            query: User query text

        Returns:
            Tuple of (suggested_domain, indicators)
        """
        if not self.config.use_pattern_matching:
            return None, []

        query_lower = query.lower()
        indicators = []
        scores = {domain: 0 for domain in DATA_STRUCTURE_HINTS}

        for domain, hints in DATA_STRUCTURE_HINTS.items():
            for indicator in hints.get("indicators", []):
                if indicator in query_lower:
                    scores[domain] += 1
                    indicators.append(f"query_pattern={indicator}")

        # Return domain with highest score if above threshold
        max_domain = max(scores, key=scores.get)
        if scores[max_domain] >= 2:
            return max_domain, indicators

        return None, indicators

    def _apply_causal_language_boost(
        self,
        query: str,
        classification: DomainClassification,
    ) -> DomainClassification:
        """Boost Complex → Complicated when explicit causal language is present.

        The LLM sometimes classifies queries with clear causal phrasing as Complex
        (e.g., "What is the causal effect of X on Y?"). This post-hoc check
        overrides to Complicated when strong causal indicators are found.

        Only triggers when LLM classified as Complex.
        """
        if classification.domain != CynefinDomain.COMPLEX:
            return classification

        query_lower = query.lower()

        causal_phrases = [
            "causal effect", "causal relationship", "causal impact",
            "root cause", "what caused",
            "impact of", "effect of", "determine the impact",
        ]
        outcome_patterns = [" on ", " -> ", "effect", "impact", "relationship between"]

        has_causal = any(phrase in query_lower for phrase in causal_phrases)
        has_outcome = any(pattern in query_lower for pattern in outcome_patterns)

        if has_causal and has_outcome:
            logger.info(
                f"Causal language boost: Complex → Complicated "
                f"(was {classification.confidence:.2f})"
            )
            return DomainClassification(
                domain=CynefinDomain.COMPLICATED,
                confidence=max(classification.confidence, 0.85),
                reasoning=f"Causal language boost applied: {classification.reasoning}",
                key_indicators=classification.key_indicators + ["causal_language_boost"],
            )

        return classification

    def _calculate_entropy(self, text: str, context: dict[str, Any]) -> float:
        """Calculate Shannon entropy over the token distribution of the input.

        Higher entropy indicates a more diverse/complex vocabulary, which serves
        as a proxy for input complexity and uncertainty.

        Args:
            text: The input text
            context: Additional context data

        Returns:
            Entropy score between 0 and 1
        """
        tokens = text.lower().split()
        vocab_size = len(set(tokens))

        if vocab_size <= 1:
            # A single unique token (or empty input) carries no distributional entropy;
            # treat as maximum uncertainty since we have almost no signal.
            shannon = 1.0
        else:
            counts = Counter(tokens)
            total = len(tokens)
            raw = -sum(
                (c / total) * math.log2(c / total) for c in counts.values()
            )
            # Normalize to [0, 1] by dividing by the theoretical maximum
            shannon = raw / math.log2(vocab_size)

        # Context signals act as additive modifiers
        if context.get("historical_pattern_known"):
            shannon -= 0.2
        if context.get("system_stable"):
            shannon -= 0.1
        # Known scenario with domain hint reduces uncertainty
        if context.get("domain_hint"):
            shannon -= 0.3
        if context.get("scenario_id") or context.get("scenario"):
            shannon -= 0.2

        return max(0.0, min(1.0, shannon))

    def _domain_distribution(self, classification: DomainClassification) -> dict[str, float]:
        """Return a probability distribution over all Cynefin domains.

        Prefers the classifier's real distribution (DistilBERT softmax). For
        point-estimate classifiers (LLM) it synthesises the same confidence-derived
        shape used for ``state.domain_scores`` so the metric is always defined.
        """
        if classification.domain_distribution:
            return dict(classification.domain_distribution)

        conf = classification.confidence
        remaining = max(0.0, 1.0 - conf)
        others = [d for d in CynefinDomain if d != classification.domain]
        per = remaining / len(others) if others else 0.0
        return {
            d.value: (conf if d == classification.domain else per)
            for d in CynefinDomain
        }

    def _distribution_entropy(self, distribution: dict[str, float]) -> float:
        """Normalized Shannon entropy over the domain probability distribution.

        H(X) = -sum p_i log2 p_i, normalized by log2(K) to lie in [0, 1] where K is
        the number of domains. Low entropy → concentrated mass (Clear/Complicated);
        high entropy → diffuse mass (Complex/Disorder). This is the principled
        epistemic-regime signal recommended by the deep-research brief, distinct from
        the lexical token entropy in ``_calculate_entropy``.
        """
        total = sum(v for v in distribution.values() if v > 0)
        if total <= 0 or len(distribution) <= 1:
            return 0.0
        probs = [v / total for v in distribution.values() if v > 0]
        raw = -sum(p * math.log2(p) for p in probs)
        return raw / math.log2(len(distribution))

    @staticmethod
    def _js_distance(p: dict[str, float], q: dict[str, float]) -> float:
        """Jensen-Shannon distance (sqrt of base-2 JSD) between two distributions, in [0, 1]."""
        keys = set(p) | set(q)
        sp = sum(p.values()) or 1.0
        sq = sum(q.values()) or 1.0
        pn = {k: p.get(k, 0.0) / sp for k in keys}
        qn = {k: q.get(k, 0.0) / sq for k in keys}
        m = {k: 0.5 * (pn[k] + qn[k]) for k in keys}

        def _kl(a: dict[str, float], b: dict[str, float]) -> float:
            return sum(a[k] * math.log2(a[k] / b[k]) for k in keys if a[k] > 0 and b[k] > 0)

        jsd = 0.5 * _kl(pn, m) + 0.5 * _kl(qn, m)
        return math.sqrt(max(0.0, jsd))

    def _track_distribution_change(self, current: dict[str, float]) -> float:
        """Measure the shift of ``current`` vs the rolling-window mean, then record it."""
        window = list(self._recent_distributions)
        change = 0.0
        if window:
            keys = set().union(*[set(d) for d in window], set(current))
            mean = {k: sum(d.get(k, 0.0) for d in window) / len(window) for k in keys}
            change = self._js_distance(current, mean)
        self._recent_distributions.append(dict(current))
        return change

    def _is_chaotic_by_distribution(
        self, dist_entropy: float, dist_change: float, has_explicit_hint: bool
    ) -> bool:
        """Decide whether the principled Chaotic gate should fire.

        Fail-safe: fires only when explicitly enabled, no expert domain hint is present,
        AND both the domain-distribution entropy and the rolling-window shift exceed their
        calibrated thresholds. It can only escalate to Chaotic (circuit breaker), never relax.
        """
        return (
            self.config.enable_chaotic_distribution_gate
            and not has_explicit_hint
            and dist_entropy >= self.entropy_threshold_chaotic
            and dist_change >= self.config.chaotic_change_threshold
        )

    @async_retry_with_backoff(max_attempts=3, exceptions=(Exception,))
    async def _classify_with_llm(self, text: str) -> DomainClassification:
        """Call LLM to classify the domain.

        Args:
            text: User input to classify

        Returns:
            DomainClassification with domain, confidence, reasoning
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Classify this request:\n\n{text}"),
        ]

        response = await self.model.ainvoke(messages)
        content = response.content

        # Parse JSON response
        try:
            # Handle potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())
            return DomainClassification(**data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response: {e}. Defaulting to Disorder.")
            return DomainClassification(
                domain=CynefinDomain.DISORDER,
                confidence=0.0,
                reasoning=f"Failed to parse classification response: {str(e)}",
                key_indicators=["parse_error"],
            )

    async def _classify_with_model(self, text: str) -> DomainClassification:
        """Classify using a local DistilBERT model."""
        if not self.model or not self.tokenizer or not self._torch or not self._device:
            logger.warning("Router model not ready; falling back to LLM.")
            return await self._classify_with_llm(text)

        inputs = self.tokenizer(
            text,
            truncation=True,
            padding=True,
            max_length=128,
            return_tensors="pt",
        )
        inputs = {key: value.to(self._device) for key, value in inputs.items()}
        with self._torch.no_grad():
            outputs = self.model(**inputs)
            probs = self._torch.softmax(outputs.logits, dim=-1)[0]
            predicted_id = int(self._torch.argmax(probs).item())
            confidence = float(probs[predicted_id].item())

        domain_label = self._id_to_label.get(predicted_id, "Disorder")
        domain = CynefinDomain(domain_label)
        topk = self._torch.topk(probs, k=min(3, probs.shape[0]))
        indicators = [
            f"{self._id_to_label.get(int(idx), idx)}: {float(probs[int(idx)].item()):.2f}"
            for idx in topk.indices
        ]

        # Preserve the full softmax distribution over domains so the router can
        # compute principled domain-distribution entropy (R1/G5) rather than only
        # a confidence-derived approximation.
        distribution = {
            self._id_to_label.get(i, str(i)): float(probs[i].item())
            for i in range(int(probs.shape[0]))
        }

        return DomainClassification(
            domain=domain,
            confidence=confidence,
            reasoning=f"DistilBERT classification: {domain_label}",
            key_indicators=indicators,
            domain_distribution=distribution,
        )

    def _determine_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Map numeric confidence to categorical level."""
        if confidence >= 0.85:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.6:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    async def classify(self, state: EpistemicState) -> EpistemicState:
        """Classify the input and update the epistemic state.

        This is the main entry point, designed to be used as a LangGraph node.

        Args:
            state: Current epistemic state with user_input

        Returns:
            Updated epistemic state with domain classification
        """
        logger.info(f"Router classifying input: {state.user_input[:100]}...")

        # Step 1: Calculate signal entropy (informational metadata, not a hard gate)
        entropy = round(
            self._calculate_entropy(state.user_input, state.context),
            2,
        )
        state.domain_entropy = entropy

        # Step 1b: Check memory augmentation for domain pattern hints (soft signal)
        memory_hint_domain = None
        memory_aug = state.context.get("_memory_augmentation")
        if memory_aug:
            domain_patterns = memory_aug.get("domain_patterns", {})
            similar_queries = memory_aug.get("memory_similar_queries", [])
            # If recent similar queries consistently map to a single domain,
            # use it as a soft hint (low weight, never overrides)
            if similar_queries:
                domain_votes: dict[str, float] = {}
                for sq in similar_queries:
                    d = sq.get("domain", "")
                    sim = sq.get("similarity", 0.0)
                    if d and sim > 0.3:
                        domain_votes[d] = domain_votes.get(d, 0) + sim
                if domain_votes:
                    top_domain = max(domain_votes, key=domain_votes.get)  # type: ignore[arg-type]
                    if domain_votes[top_domain] > 0.5:
                        memory_hint_domain = top_domain
                        logger.debug(
                            "Memory hint domain: %s (score=%.2f)",
                            top_domain, domain_votes[top_domain],
                        )

        # Step 2: Check for domain_hint from scenario context (explicit user override)
        domain_hint = state.context.get("domain_hint")
        if domain_hint:
            logger.info(f"Domain hint provided: {domain_hint}")

        # Step 2b: Detect hints from data structure (NEW)
        data_hint, data_indicators = self._detect_data_hints(state.context)
        if data_hint and not domain_hint:
            logger.info(f"Data structure suggests domain: {data_hint} ({data_indicators})")
            if self.config.use_data_hints:
                domain_hint = data_hint

        # Step 2c: Detect hints from query patterns (NEW)
        query_hint, query_indicators = self._detect_query_patterns(state.user_input)
        if query_hint and not domain_hint:
            logger.info(f"Query pattern suggests domain: {query_hint} ({query_indicators})")

        # Step 3: Model or LLM classification
        if self.mode == "distilbert":
            classification = await self._classify_with_model(state.user_input)
        else:
            classification = await self._classify_with_llm(state.user_input)

        # Step 3b: Apply causal language boost (Complex → Complicated)
        classification = self._apply_causal_language_boost(state.user_input, classification)

        # Step 4: Apply domain hint override when present
        # Domain hints from scenarios are explicit configuration from domain experts
        # and should take precedence unless LLM classification is the same
        if domain_hint:
            try:
                hint_domain = CynefinDomain(domain_hint.capitalize())
                if classification.domain != hint_domain:
                    logger.info(
                        f"Applying domain hint override: {hint_domain.value} "
                        f"(LLM said {classification.domain.value} @ {classification.confidence:.2f})"
                    )
                    classification = DomainClassification(
                        domain=hint_domain,
                        confidence=max(classification.confidence, 0.88),
                        reasoning=f"Scenario domain hint ({domain_hint}): {classification.reasoning}",
                        key_indicators=classification.key_indicators + [f"domain_hint={domain_hint}"],
                    )
                else:
                    logger.info(f"Domain hint matches LLM classification: {hint_domain.value}")
            except ValueError:
                logger.warning(f"Invalid domain_hint value: {domain_hint}")

        # Step 4b: Principled domain-distribution entropy + rolling-window change (R1/G5).
        # Always computed as additive metadata; only drives routing when the opt-in gate
        # is enabled, preserving the existing "entropy is metadata" contract by default.
        domain_distribution = self._domain_distribution(classification)
        distribution_entropy = self._distribution_entropy(domain_distribution)
        distribution_change = self._track_distribution_change(domain_distribution)
        state.context["domain_distribution_entropy"] = round(distribution_entropy, 4)
        state.context["domain_distribution_change"] = round(distribution_change, 4)
        chaotic_by_gate = self._is_chaotic_by_distribution(
            distribution_entropy, distribution_change, has_explicit_hint=bool(domain_hint)
        )
        if chaotic_by_gate:
            logger.warning(
                "Chaotic distribution gate fired (entropy=%.3f >= %.2f, change=%.3f >= %.2f) "
                "- routing to circuit breaker",
                distribution_entropy,
                self.entropy_threshold_chaotic,
                distribution_change,
                self.config.chaotic_change_threshold,
            )

        # Step 4c: Conformal prediction set (R1/G2). Distribution-free calibrated set;
        # cardinality > 1 flags a borderline query. Recorded as metadata always; only
        # forces escalation when the opt-in flag is set and no explicit hint applies.
        conformal_force_disorder = False
        if self._conformal is not None:
            from src.utils.conformal import prediction_set

            pset = prediction_set(domain_distribution, self._conformal)
            state.context["router_prediction_set"] = pset
            state.context["router_ambiguous"] = len(pset) > 1
            if (
                len(pset) > 1
                and self.config.conformal_escalate_on_ambiguous
                and not domain_hint
                and not chaotic_by_gate
            ):
                conformal_force_disorder = True
                logger.info(
                    "Conformal prediction set %s is ambiguous - escalating to human review", pset
                )

        # Step 5: Apply Chaotic gate (fail-safe), conformal escalation, then confidence threshold
        if chaotic_by_gate:
            final_domain = CynefinDomain.CHAOTIC
            final_confidence = classification.confidence
            classification.key_indicators.append(
                f"chaotic_distribution_gate(H={distribution_entropy:.2f},"
                f"JS={distribution_change:.2f})"
            )
        elif conformal_force_disorder:
            final_domain = CynefinDomain.DISORDER
            final_confidence = classification.confidence
            classification.key_indicators.append(
                f"conformal_ambiguous{state.context.get('router_prediction_set', [])}"
            )
        elif classification.confidence < self.confidence_threshold:
            logger.info(
                f"Low confidence ({classification.confidence:.2f}) - "
                f"overriding {classification.domain} to Disorder"
            )
            final_domain = CynefinDomain.DISORDER
            final_confidence = classification.confidence
        else:
            final_domain = classification.domain
            final_confidence = classification.confidence

        # Step 6: Update state
        state.cynefin_domain = final_domain
        state.domain_confidence = final_confidence
        state.overall_confidence = self._determine_confidence_level(final_confidence)
        state.current_hypothesis = classification.reasoning
        state.router_key_indicators = classification.key_indicators

        # Compute triggered method based on domain
        method_map = {
            CynefinDomain.CLEAR: "deterministic_runner",
            CynefinDomain.COMPLICATED: "causal_inference",
            CynefinDomain.COMPLEX: "bayesian_inference",
            CynefinDomain.CHAOTIC: "circuit_breaker",
            CynefinDomain.DISORDER: "human_escalation",
        }
        state.triggered_method = method_map.get(final_domain, "unknown")

        # Generate domain scores (primary domain gets confidence, others split remainder)
        remaining = 1.0 - final_confidence
        other_domains = [d for d in CynefinDomain if d != final_domain]
        per_domain = remaining / len(other_domains) if other_domains else 0
        state.domain_scores = {
            d.value: (final_confidence if d == final_domain else per_domain)
            for d in CynefinDomain
        }

        # Step 6b: Apply memory hint as soft signal (never overrides, small weight)
        if memory_hint_domain and state.domain_scores:
            _MEMORY_HINT_WEIGHT = 0.03
            if memory_hint_domain in state.domain_scores:
                state.domain_scores[memory_hint_domain] = min(
                    1.0,
                    state.domain_scores[memory_hint_domain] + _MEMORY_HINT_WEIGHT,
                )

        # Step 7: Record reasoning step
        state.add_reasoning_step(
            node_name="router",
            action=f"Classified as {final_domain.value}",
            input_summary=f"Query: {state.user_input[:50]}...",
            output_summary=(
                f"Domain: {final_domain.value}, "
                f"Confidence: {final_confidence:.2f}, "
                f"Entropy: {entropy:.2f}, "
                f"DistEntropy: {distribution_entropy:.2f}, "
                f"Indicators: {classification.key_indicators}"
            ),
            confidence=state.overall_confidence,
        )

        logger.info(
            f"Classification complete: {final_domain.value} "
            f"(confidence: {final_confidence:.2f}, entropy: {entropy:.2f})"
        )

        return state


# Singleton instance for use in LangGraph
_router_instance: CynefinRouter | None = None


def get_router() -> CynefinRouter:
    """Get or create the router singleton."""
    global _router_instance
    if _router_instance is None:
        _router_instance = CynefinRouter()
    return _router_instance


def update_router_config(config: RouterConfig) -> CynefinRouter:
    """Update router configuration and recreate instance."""
    global _router_instance
    _router_instance = CynefinRouter(config=config)
    logger.info(f"Router configuration updated: {config.model_dump()}")
    return _router_instance


def get_router_config() -> RouterConfig:
    """Get current router configuration."""
    router = get_router()
    return router.config


async def cynefin_router_node(state: EpistemicState) -> EpistemicState:
    """LangGraph node function for the Cynefin Router.

    Usage in LangGraph:
        workflow.add_node("router", cynefin_router_node)
    """
    router = get_router()
    return await router.classify(state)
