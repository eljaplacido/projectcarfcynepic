"""DeepEval integration service for runtime LLM quality scoring.

Provides real-time evaluation of LLM outputs using DeepEval metrics:
- Answer relevancy scoring
- Hallucination detection
- Custom UIX compliance metrics
- Reasoning quality assessment

This service integrates with TransparencyService to enrich reliability
assessments with quantitative LLM quality metrics.
"""

import logging
import os
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.evaluation")


class DeepEvalScores(BaseModel):
    """DeepEval quality metrics for LLM outputs.

    These scores provide quantitative measures of LLM response quality
    that complement traditional reliability assessments.
    """
    relevancy_score: float = Field(
        0.0, ge=0.0, le=1.0,
        description="How relevant the response is to the input query (0-1)"
    )
    hallucination_risk: float = Field(
        0.0, ge=0.0, le=1.0,
        description="Risk of hallucinated content (0=no risk, 1=high risk)"
    )
    reasoning_depth: float = Field(
        0.0, ge=0.0, le=1.0,
        description="Quality and depth of reasoning in response (0-1)"
    )
    uix_compliance: float = Field(
        0.0, ge=0.0, le=1.0,
        description="Compliance with CARF UIX standards (0-1)"
    )
    task_completion: bool = Field(
        False,
        description="Whether the response adequately addresses the query"
    )
    evaluated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of evaluation"
    )
    evaluation_model: str = Field(
        "deepseek-chat",
        description="Model used for evaluation"
    )
    evaluation_latency_ms: int = Field(
        0, ge=0,
        description="Time taken for evaluation in milliseconds"
    )


class EvaluationConfig(BaseModel):
    """Configuration for evaluation service."""
    enabled: bool = Field(True, description="Whether evaluation is enabled")
    relevancy_threshold: float = Field(0.7, ge=0.0, le=1.0)
    hallucination_threshold: float = Field(0.3, ge=0.0, le=1.0)
    model_name: str = Field("deepseek-chat")
    api_base_url: str = Field("https://api.deepseek.com")
    timeout_seconds: int = Field(30, ge=1)
    async_evaluation: bool = Field(
        True, description="Run evaluation asynchronously to not block responses"
    )


class EvaluationService:
    """Runtime LLM output evaluation using DeepEval.

    This service provides real-time quality scoring of LLM outputs,
    enabling:
    - Confidence calibration based on actual output quality
    - Hallucination detection before presenting to users
    - UIX compliance verification
    - Continuous quality monitoring

    Usage:
        service = EvaluationService()
        scores = await service.evaluate_response(
            input="What is causal inference?",
            output="Causal inference is a method...",
            context=["DoWhy library documentation"]
        )
    """

    def __init__(self, config: EvaluationConfig | None = None):
        self.config = config or EvaluationConfig()
        self._deepeval_available = self._check_deepeval()
        self._evaluator = None

    def _check_deepeval(self) -> bool:
        """Check if DeepEval is available."""
        try:
            import deepeval  # noqa: F401
            return True
        except ImportError:
            logger.warning(
                "DeepEval not installed. Install with: pip install deepeval"
            )
            return False

    def _get_evaluator(self) -> Any:
        """Get or create the DeepEval evaluator model."""
        if self._evaluator is not None:
            return self._evaluator

        if not self._deepeval_available:
            return None

        try:
            from deepeval.models import DeepEvalBaseLLM
            from openai import OpenAI

            class DeepSeekEvaluator(DeepEvalBaseLLM):
                def __init__(self, config: EvaluationConfig):
                    self.config = config
                    self._client = None

                def load_model(self):
                    if self._client is None:
                        self._client = OpenAI(
                            api_key=os.getenv("DEEPSEEK_API_KEY"),
                            base_url=self.config.api_base_url
                        )
                    return self._client

                def generate(self, prompt: str) -> str:
                    client = self.load_model()
                    response = client.chat.completions.create(
                        model=self.config.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.0
                    )
                    return response.choices[0].message.content or ""

                async def a_generate(self, prompt: str) -> str:
                    return self.generate(prompt)

                def get_model_name(self) -> str:
                    return self.config.model_name

            self._evaluator = DeepSeekEvaluator(self.config)
            return self._evaluator

        except Exception as e:
            logger.error(f"Failed to initialize evaluator: {e}")
            return None

    async def evaluate_response(
        self,
        input: str,
        output: str,
        context: list[str] | None = None,
        expected_output: str | None = None,
    ) -> DeepEvalScores:
        """Evaluate a response and return quality scores.

        Args:
            input: The user's query/input
            output: The LLM's response to evaluate
            context: Optional list of context strings used by the LLM
            expected_output: Optional expected output for comparison

        Returns:
            DeepEvalScores with relevancy, hallucination risk, and other metrics
        """
        if not self.config.enabled:
            return DeepEvalScores(
                relevancy_score=0.5,
                hallucination_risk=0.5,
                reasoning_depth=0.5,
                uix_compliance=0.5,
                task_completion=True,
                evaluation_model="disabled"
            )

        start_time = datetime.utcnow()

        if not self._deepeval_available:
            # Return default scores when DeepEval not available
            return self._generate_heuristic_scores(input, output, context)

        try:
            scores = await self._run_deepeval_evaluation(
                input, output, context, expected_output
            )
            latency = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            scores.evaluation_latency_ms = latency
            return scores

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return self._generate_heuristic_scores(input, output, context)

    async def _run_deepeval_evaluation(
        self,
        input: str,
        output: str,
        context: list[str] | None,
        expected_output: str | None,
    ) -> DeepEvalScores:
        """Run DeepEval metrics on the response."""
        from deepeval.metrics import AnswerRelevancyMetric, HallucinationMetric, GEval
        from deepeval.test_case import LLMTestCase, LLMTestCaseParams

        evaluator = self._get_evaluator()

        # Create test case
        test_case = LLMTestCase(
            input=input,
            actual_output=output,
            context=context or [],
            expected_output=expected_output
        )

        # Initialize metrics
        relevancy_metric = AnswerRelevancyMetric(
            threshold=self.config.relevancy_threshold,
            model=evaluator,
            include_reason=False  # Faster evaluation
        )

        hallucination_metric = HallucinationMetric(
            threshold=self.config.hallucination_threshold,
            model=evaluator,
            include_reason=False
        ) if context else None

        reasoning_metric = GEval(
            name="Reasoning Depth",
            criteria="""Evaluate the depth and quality of reasoning:
            1. Provides clear logical steps
            2. Justifies conclusions with evidence
            3. Acknowledges uncertainty appropriately
            4. Considers alternatives""",
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.6,
            model=evaluator
        )

        uix_metric = GEval(
            name="UIX Compliance",
            criteria="""Evaluate CARF UIX compliance:
            1. Answers 'Why this?' - explains reasoning
            2. Answers 'How confident?' - quantifies uncertainty
            3. Answers 'Based on what?' - cites sources
            4. Uses accessible language""",
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.6,
            model=evaluator
        )

        # Run evaluations
        relevancy_metric.measure(test_case)
        relevancy_score = relevancy_metric.score or 0.0

        hallucination_score = 0.0
        if hallucination_metric and context:
            hallucination_metric.measure(test_case)
            hallucination_score = hallucination_metric.score or 0.0

        reasoning_metric.measure(test_case)
        reasoning_score = reasoning_metric.score or 0.0

        uix_metric.measure(test_case)
        uix_score = uix_metric.score or 0.0

        # Determine task completion
        task_complete = relevancy_score >= self.config.relevancy_threshold

        return DeepEvalScores(
            relevancy_score=relevancy_score,
            hallucination_risk=hallucination_score,
            reasoning_depth=reasoning_score,
            uix_compliance=uix_score,
            task_completion=task_complete,
            evaluation_model=self.config.model_name
        )

    def _generate_heuristic_scores(
        self,
        input: str,
        output: str,
        context: list[str] | None
    ) -> DeepEvalScores:
        """Generate heuristic scores when DeepEval unavailable.

        Uses simple heuristics to estimate quality:
        - Length-based relevancy estimation
        - Keyword matching for context adherence
        - Confidence phrase detection
        """
        # Simple heuristics
        output_length = len(output)
        input_keywords = set(input.lower().split())
        output_lower = output.lower()

        # Relevancy: Check keyword overlap
        keyword_matches = sum(1 for kw in input_keywords if kw in output_lower)
        relevancy = min(1.0, keyword_matches / max(len(input_keywords), 1) * 1.5)

        # Hallucination risk: Check context adherence
        hallucination_risk = 0.3  # Default medium-low
        if context:
            context_text = " ".join(context).lower()
            # If output mentions things not in context, higher risk
            output_words = set(output_lower.split())
            context_words = set(context_text.split())
            novel_words = output_words - context_words - input_keywords
            hallucination_risk = min(1.0, len(novel_words) / max(len(output_words), 1))

        # Reasoning depth: Check for reasoning indicators
        reasoning_indicators = [
            "because", "therefore", "however", "although", "first", "second",
            "in conclusion", "this means", "as a result", "confidence"
        ]
        reasoning_count = sum(1 for ind in reasoning_indicators if ind in output_lower)
        reasoning_depth = min(1.0, reasoning_count / 5)

        # UIX compliance: Check for required elements
        uix_elements = [
            "confidence" in output_lower or "%" in output,  # Confidence
            "based on" in output_lower or "source" in output_lower,  # Sources
            "because" in output_lower or "reason" in output_lower,  # Reasoning
            output_length > 100  # Sufficient detail
        ]
        uix_compliance = sum(uix_elements) / len(uix_elements)

        # Task completion
        task_complete = relevancy > 0.5 and output_length > 50

        return DeepEvalScores(
            relevancy_score=relevancy,
            hallucination_risk=hallucination_risk,
            reasoning_depth=reasoning_depth,
            uix_compliance=uix_compliance,
            task_completion=task_complete,
            evaluation_model="heuristic"
        )

    async def evaluate_batch(
        self,
        evaluations: list[dict[str, Any]]
    ) -> list[DeepEvalScores]:
        """Evaluate multiple responses in batch.

        Args:
            evaluations: List of dicts with input, output, context keys

        Returns:
            List of DeepEvalScores for each evaluation
        """
        results = []
        for eval_data in evaluations:
            scores = await self.evaluate_response(
                input=eval_data.get("input", ""),
                output=eval_data.get("output", ""),
                context=eval_data.get("context"),
                expected_output=eval_data.get("expected_output")
            )
            results.append(scores)
        return results

    def get_aggregate_scores(
        self,
        scores_list: list[DeepEvalScores]
    ) -> dict[str, float]:
        """Calculate aggregate statistics from multiple evaluations.

        Returns:
            Dict with mean, min, max for each metric
        """
        if not scores_list:
            return {}

        metrics = ["relevancy_score", "hallucination_risk", "reasoning_depth", "uix_compliance"]
        aggregates = {}

        for metric in metrics:
            values = [getattr(s, metric) for s in scores_list]
            aggregates[f"{metric}_mean"] = sum(values) / len(values)
            aggregates[f"{metric}_min"] = min(values)
            aggregates[f"{metric}_max"] = max(values)

        aggregates["task_completion_rate"] = sum(
            1 for s in scores_list if s.task_completion
        ) / len(scores_list)

        aggregates["avg_latency_ms"] = sum(
            s.evaluation_latency_ms for s in scores_list
        ) / len(scores_list)

        return aggregates


# Singleton instance
_evaluation_service: EvaluationService | None = None


def get_evaluation_service() -> EvaluationService:
    """Get singleton EvaluationService instance."""
    global _evaluation_service
    if _evaluation_service is None:
        _evaluation_service = EvaluationService()
    return _evaluation_service
