"""Cynefin Router - Layer 1 of the CARF Cognitive Stack.

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
import os
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


class CynefinRouter:
    """The Sense-Making Gateway for CARF.

    Classifies incoming requests into Cynefin domains using:
    1. LLM-based semantic classification
    2. Signal entropy analysis
    3. Confidence thresholding

    If confidence falls below threshold (default 0.85), routes to Disorder
    for human escalation via HumanLayer.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.85,
        entropy_threshold_chaotic: float = 0.9,
        mode: str | None = None,
        model_path: str | None = None,
    ):
        """Initialize the Cynefin Router.

        Args:
            confidence_threshold: Below this → Disorder
            entropy_threshold_chaotic: Above this → Chaotic
            mode: "llm" or "distilbert" (defaults to ROUTER_MODE env or "llm")
            model_path: Path to trained model (defaults to ROUTER_MODEL_PATH env)

        Note: LLM provider is configured via environment variables.
        Set LLM_PROVIDER=deepseek and DEEPSEEK_API_KEY for cost-efficient operation.
        """
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
        self.confidence_threshold = confidence_threshold
        self.entropy_threshold_chaotic = entropy_threshold_chaotic

        self.system_prompt = self._build_system_prompt()

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

    def _calculate_entropy(self, text: str, context: dict[str, Any]) -> float:
        """Calculate signal entropy as a proxy for system stability.

        Higher entropy indicates more uncertainty/volatility.
        This is a simplified heuristic - Phase 2 will use proper information theory.

        Args:
            text: The input text
            context: Additional context data

        Returns:
            Entropy score between 0 and 1
        """
        entropy = 0.3  # Base entropy

        # Heuristic: Emergency/crisis keywords increase entropy
        crisis_keywords = {
            "emergency", "urgent", "critical", "down", "crash", "breach",
            "failure", "broken", "error", "alert", "warning", "immediately"
        }
        text_lower = text.lower()
        crisis_count = sum(1 for kw in crisis_keywords if kw in text_lower)
        entropy += min(crisis_count * 0.15, 0.6)

        # Heuristic: Question marks and uncertainty language
        uncertainty_keywords = {"maybe", "might", "could", "possibly", "uncertain", "unknown"}
        uncertainty_count = sum(1 for kw in uncertainty_keywords if kw in text_lower)
        entropy += min(uncertainty_count * 0.1, 0.2)

        # Heuristic: Very short inputs have higher entropy (less information)
        if len(text.split()) < 5:
            entropy += 0.1

        # Context can provide stability signals
        if context.get("historical_pattern_known"):
            entropy -= 0.2
        if context.get("system_stable"):
            entropy -= 0.1

        return max(0.0, min(1.0, entropy))

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

        return DomainClassification(
            domain=domain,
            confidence=confidence,
            reasoning=f"DistilBERT classification: {domain_label}",
            key_indicators=indicators,
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

        # Step 1: Calculate signal entropy
        entropy = round(
            self._calculate_entropy(state.user_input, state.context),
            2,
        )
        state.domain_entropy = entropy

        # Step 2: Check for immediate Chaotic classification based on entropy
        if entropy >= self.entropy_threshold_chaotic:
            logger.warning(f"High entropy ({entropy:.2f}) detected - routing to Chaotic")
            state.cynefin_domain = CynefinDomain.CHAOTIC
            state.domain_confidence = 0.95
            state.overall_confidence = ConfidenceLevel.HIGH
            state.add_reasoning_step(
                node_name="router",
                action="Classified as CHAOTIC due to high entropy",
                input_summary=f"Entropy: {entropy:.2f}",
                output_summary="Domain: Chaotic (emergency protocol)",
                confidence=ConfidenceLevel.HIGH,
            )
            return state

        # Step 3: Model or LLM classification
        if self.mode == "distilbert":
            classification = await self._classify_with_model(state.user_input)
        else:
            classification = await self._classify_with_llm(state.user_input)

        # Step 4: Apply confidence threshold
        if classification.confidence < self.confidence_threshold:
            logger.info(
                f"Low confidence ({classification.confidence:.2f}) - "
                f"overriding {classification.domain} to Disorder"
            )
            final_domain = CynefinDomain.DISORDER
            final_confidence = classification.confidence
        else:
            final_domain = classification.domain
            final_confidence = classification.confidence

        # Step 5: Update state
        state.cynefin_domain = final_domain
        state.domain_confidence = final_confidence
        state.overall_confidence = self._determine_confidence_level(final_confidence)
        state.current_hypothesis = classification.reasoning

        # Step 6: Record reasoning step
        state.add_reasoning_step(
            node_name="router",
            action=f"Classified as {final_domain.value}",
            input_summary=f"Query: {state.user_input[:50]}...",
            output_summary=(
                f"Domain: {final_domain.value}, "
                f"Confidence: {final_confidence:.2f}, "
                f"Indicators: {classification.key_indicators}"
            ),
            confidence=state.overall_confidence,
        )

        logger.info(
            f"Classification complete: {final_domain.value} "
            f"(confidence: {final_confidence:.2f})"
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


async def cynefin_router_node(state: EpistemicState) -> EpistemicState:
    """LangGraph node function for the Cynefin Router.

    Usage in LangGraph:
        workflow.add_node("router", cynefin_router_node)
    """
    router = get_router()
    return await router.classify(state)
