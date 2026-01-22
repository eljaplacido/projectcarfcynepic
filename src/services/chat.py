"""LLM-Powered Chat Service for CARF.

Provides context-aware conversational AI that can:
- Interpret analysis results
- Explain CARF components
- Suggest improvements
- Guide users through the platform
"""

import logging
import os
from typing import Any

from pydantic import BaseModel, Field

from src.core.llm import get_chat_model

logger = logging.getLogger("carf.chat")


class ChatMessage(BaseModel):
    """A message in the chat conversation."""

    role: str = Field(..., description="user, assistant, or system")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request for chat completion."""

    messages: list[ChatMessage] = Field(..., description="Conversation history")
    query_context: dict[str, Any] | None = Field(None, description="Last query response for context")
    system_prompt: str | None = Field(None, description="Custom system prompt")
    max_tokens: int = Field(1024, description="Max response tokens")


class ChatResponse(BaseModel):
    """Response from chat completion."""

    message: str = Field(..., description="Assistant response")
    suggestions: list[str] | None = Field(None, description="Follow-up suggestions")
    linked_panels: list[str] | None = Field(None, description="Related UI panels")
    confidence: str | None = Field(None, description="Response confidence level")


# System prompts for different contexts
SYSTEM_PROMPTS = {
    "default": """You are CARF Assistant, an AI expert in causal inference, Bayesian analysis, and decision-making under uncertainty.

Your role is to help users:
1. Understand their analysis results
2. Interpret causal effects and uncertainty measures
3. Suggest improvements to their analysis
4. Guide them through the CARF platform
5. Explain complex concepts in accessible language

When responding:
- Be concise but thorough
- Use specific numbers from the analysis when available
- Highlight key insights and implications
- Suggest concrete next steps
- Be honest about limitations and uncertainty

Available commands you can suggest:
- /analyze - Upload and analyze data
- /question - Start Socratic mode for guided analysis
- /query [text] - Run a causal query
- /analysis - View last analysis snapshot
- /history - Browse past analyses
- /help [topic] - Get help on causal, bayesian, cynefin, or guardian topics""",

    "result_interpretation": """You are CARF Assistant helping interpret analysis results.

Given the analysis context, help the user understand:
1. What the effect size means in practical terms
2. How confident they should be in the result
3. What the refutation tests tell us
4. How to act on this information
5. What additional analysis might be valuable

Be specific and use actual numbers from the results.""",

    "socratic": """You are CARF Assistant in Socratic mode.

Ask probing questions to help the user improve their analysis:
1. Clarify the business context and decision
2. Identify potential confounders
3. Question assumptions
4. Suggest validation approaches
5. Explore alternative hypotheses

Ask one question at a time and build on their responses.""",
}


# Demo responses for when no API key is available
DEMO_RESPONSES = {
    "greeting": """Welcome to CARF! I can help you:
- Interpret analysis results
- Explain any component (right-click for details)
- Suggest improvements to reliability
- Analyze your data with /analyze
- Guide you through the platform

What would you like to explore?""",

    "result_interpretation": """Based on the analysis:

**Effect Size**: The treatment shows a {effect_direction} effect of {effect_size} {unit}. This means {interpretation}.

**Statistical Confidence**: With a p-value of {p_value}, this result is {significance}. The 95% confidence interval [{ci_low}, {ci_high}] suggests the true effect is likely within this range.

**Robustness**: {refutation_passed}/{refutation_total} refutation tests passed, indicating {robustness_assessment}.

**Recommendation**: {recommendation}

Would you like me to explain any of these results in more detail?""",

    "help": """Here are the available commands:

| Command | Description |
|---------|-------------|
| `/analyze` | Upload and analyze a file or text |
| `/question` | Start Socratic mode for guided analysis |
| `/query [text]` | Execute an analysis query |
| `/analysis` | View last analysis snapshot |
| `/history` | Browse past analyses |
| `/help [topic]` | Get help (topics: causal, bayesian, cynefin, guardian) |

You can also ask me any question about your analysis or the CARF platform!""",

    "no_context": """I'd be happy to help! However, I don't have any analysis results to discuss yet.

To get started:
1. **Select a scenario** from the dropdown to explore pre-built demos
2. **Use /analyze** to upload your own data
3. **Type a query** to run causal analysis

What would you like to do?""",
}


class ChatService:
    """Service for LLM-powered chat."""

    def __init__(self):
        self._demo_mode = not os.getenv("OPENAI_API_KEY") and not os.getenv("DEEPSEEK_API_KEY")
        if self._demo_mode:
            logger.info("ChatService running in demo mode (no API key)")

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Process chat request and return response.

        Args:
            request: Chat request with messages and context

        Returns:
            ChatResponse with assistant message and suggestions
        """
        if self._demo_mode:
            return self._get_demo_response(request)

        return await self._get_llm_response(request)

    def _get_demo_response(self, request: ChatRequest) -> ChatResponse:
        """Get pre-defined response for demo mode."""
        last_user_message = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                last_user_message = msg.content.lower()
                break

        # Check for common patterns
        if not last_user_message or "hello" in last_user_message or "hi" in last_user_message:
            return ChatResponse(
                message=DEMO_RESPONSES["greeting"],
                suggestions=["/analyze", "/question", "/help"],
                confidence="high",
            )

        if "help" in last_user_message:
            return ChatResponse(
                message=DEMO_RESPONSES["help"],
                suggestions=["/analyze", "/question"],
                confidence="high",
            )

        # If we have query context, provide interpretation
        if request.query_context:
            return self._interpret_results(request.query_context)

        # Default response
        return ChatResponse(
            message=DEMO_RESPONSES["no_context"],
            suggestions=["Select a scenario", "/analyze", "/help"],
            confidence="medium",
        )

    def _interpret_results(self, context: dict[str, Any]) -> ChatResponse:
        """Generate result interpretation from context."""
        causal = context.get("causalResult") or context.get("causal_result")
        bayesian = context.get("bayesianResult") or context.get("bayesian_result")
        guardian = context.get("guardianResult") or context.get("guardian_result")

        parts = []
        suggestions = []
        linked_panels = []

        if causal:
            effect = causal.get("effect", 0)
            effect_direction = "positive" if effect > 0 else "negative" if effect < 0 else "neutral"
            p_value = causal.get("pValue") or causal.get("p_value", "N/A")
            ci = causal.get("confidenceInterval") or [causal.get("ci_low", 0), causal.get("ci_high", 0)]
            refut_passed = causal.get("refutationsPassed") or causal.get("refutations_passed", 0)
            refut_total = causal.get("refutationsTotal") or causal.get("refutations_total", 0)

            significance = "statistically significant" if isinstance(p_value, (int, float)) and p_value < 0.05 else "not statistically significant"

            parts.append(f"""**Causal Analysis Results**

The analysis found a **{effect_direction} effect** of **{effect}** units.
- p-value: {p_value} ({significance})
- 95% CI: [{ci[0]:.3f}, {ci[1]:.3f}]
- Refutation tests: {refut_passed}/{refut_total} passed""")

            linked_panels.append("causal-results")
            suggestions.append("What do the refutation tests mean?")

        if bayesian:
            epistemic = bayesian.get("epistemicUncertainty") or bayesian.get("epistemic_uncertainty", 0)
            aleatoric = bayesian.get("aleatoricUncertainty") or bayesian.get("aleatoric_uncertainty", 0)
            posterior = bayesian.get("posteriorMean") or bayesian.get("posterior_mean", 0)

            parts.append(f"""
**Bayesian Analysis**

Posterior mean: **{posterior:.3f}**
- Epistemic uncertainty: {epistemic:.1%} (reducible with more data)
- Aleatoric uncertainty: {aleatoric:.1%} (inherent randomness)""")

            linked_panels.append("bayesian-panel")
            if epistemic > 0.3:
                suggestions.append("How can I reduce epistemic uncertainty?")

        if guardian:
            verdict = guardian.get("overallStatus") or guardian.get("verdict", "unknown")
            policies_passed = guardian.get("policies_passed", 0)
            policies_total = guardian.get("policies_total", 0)

            parts.append(f"""
**Guardian Verdict: {verdict.upper()}**

Policy checks: {policies_passed}/{policies_total} passed""")

            linked_panels.append("guardian-panel")

        if not parts:
            return ChatResponse(
                message="I see the analysis completed. Could you tell me what specific aspect you'd like me to explain?",
                suggestions=["Explain the effect size", "What are refutation tests?", "Is this result reliable?"],
                confidence="medium",
            )

        message = "\n".join(parts) + "\n\nWould you like me to explain any of these results in more detail?"

        return ChatResponse(
            message=message,
            suggestions=suggestions or ["Explain more", "What should I do next?", "Show methodology"],
            linked_panels=linked_panels,
            confidence="high",
        )

    async def _get_llm_response(self, request: ChatRequest) -> ChatResponse:
        """Get LLM-generated response."""
        llm = get_chat_model(temperature=0.5, purpose="chat")

        # Build system prompt
        system_prompt = request.system_prompt or SYSTEM_PROMPTS["default"]

        # Add context if available
        if request.query_context:
            system_prompt += f"\n\nCurrent analysis context:\n{self._format_context(request.query_context)}"

        # Build messages for LLM
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend([{"role": m.role, "content": m.content} for m in request.messages])

        try:
            response = await llm.ainvoke(messages)

            # Extract suggestions (look for bullet points or numbered items)
            suggestions = self._extract_suggestions(response.content)

            return ChatResponse(
                message=response.content,
                suggestions=suggestions[:3] if suggestions else None,
                confidence="high",
            )

        except Exception as e:
            logger.error(f"LLM chat failed: {e}")
            return ChatResponse(
                message="I apologize, but I encountered an error processing your request. Please try again.",
                suggestions=["/help", "Try a different question"],
                confidence="low",
            )

    def _format_context(self, context: dict[str, Any]) -> str:
        """Format query context for system prompt."""
        parts = []

        if "domain" in context:
            parts.append(f"Domain: {context['domain']} (confidence: {context.get('domainConfidence', 'N/A')})")

        causal = context.get("causalResult") or context.get("causal_result")
        if causal:
            parts.append(f"Causal effect: {causal.get('effect', 'N/A')} (p={causal.get('pValue') or causal.get('p_value', 'N/A')})")
            parts.append(f"Refutations: {causal.get('refutationsPassed') or causal.get('refutations_passed', 0)}/{causal.get('refutationsTotal') or causal.get('refutations_total', 0)} passed")

        bayesian = context.get("bayesianResult") or context.get("bayesian_result")
        if bayesian:
            parts.append(f"Bayesian posterior: {bayesian.get('posteriorMean') or bayesian.get('posterior_mean', 'N/A')}")
            parts.append(f"Epistemic uncertainty: {bayesian.get('epistemicUncertainty') or bayesian.get('epistemic_uncertainty', 'N/A')}")

        guardian = context.get("guardianResult") or context.get("guardian_result")
        if guardian:
            parts.append(f"Guardian verdict: {guardian.get('overallStatus') or guardian.get('verdict', 'N/A')}")

        return "\n".join(parts) if parts else "No analysis context available"

    def _extract_suggestions(self, text: str) -> list[str]:
        """Extract potential follow-up suggestions from response."""
        suggestions = []
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            # Look for bullet points or numbered items
            if line.startswith(("- ", "* ", "• ")) or (len(line) > 2 and line[0].isdigit() and line[1] in ".):"):
                # Clean up the suggestion
                suggestion = line.lstrip("-*•0123456789.): ").strip()
                if len(suggestion) > 10 and len(suggestion) < 100 and "?" in suggestion:
                    suggestions.append(suggestion)

        return suggestions


# Singleton instance
_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    """Get singleton ChatService instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
