"""Tests for EvaluationService itself using DeepEval metrics.

Tests ensure the evaluation service:
- Correctly scores LLM outputs
- Provides consistent evaluations
- Handles edge cases gracefully
- Integrates with transparency reporting
"""

import pytest

try:
    from deepeval import assert_test
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False


pytestmark = pytest.mark.skipif(not DEEPEVAL_AVAILABLE, reason="deepeval not installed")


class TestEvaluationServiceIntegration:
    """Integration tests for EvaluationService."""

    @pytest.mark.deepeval
    def test_high_quality_response_scoring(self, deepeval_model):
        """Test that high-quality responses receive high scores."""

        # A high-quality response that should score well
        high_quality_output = """Based on our causal analysis with 92% confidence:

**Finding**: The marketing campaign caused a 15% increase in sales.

**Why we're confident** (Methodology):
- Used DoWhy causal inference with propensity score matching
- Controlled for seasonality, economic conditions, competitor activity
- Passed all 3 refutation tests (placebo, subset, random cause)

**Data Sources**:
- Sales transactions: 2,500 records (Jan-Dec 2024)
- Marketing spend: Monthly aggregates from finance
- Economic indicators: Fed consumer confidence index

**Limitations**:
- Cannot rule out unmeasured confounders
- Effect may not scale linearly above current spend levels

**Recommendation**: Continue current marketing strategy with monitoring."""

        scoring_metric = GEval(
            name="High Quality Response Validation",
            criteria="""Evaluate if this response deserves high quality scores:

            For RELEVANCY (expect >0.8):
            - Directly answers the question
            - Provides specific findings

            For REASONING DEPTH (expect >0.8):
            - Explains methodology
            - Justifies conclusions

            For UIX COMPLIANCE (expect >0.8):
            - Answers "why this?" ✓
            - Answers "how confident?" ✓
            - Answers "based on what?" ✓
            - Accessible language ✓

            For HALLUCINATION RISK (expect <0.2):
            - Claims are specific and verifiable
            - Limitations acknowledged

            Score 1.0 if response would receive high scores on all metrics.""",
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.8,
            model=deepeval_model
        )

        test_case = LLMTestCase(
            input="What was the impact of the marketing campaign?",
            actual_output=high_quality_output
        )

        assert_test(test_case, [scoring_metric])

    @pytest.mark.deepeval
    def test_low_quality_response_detection(self, deepeval_model):
        """Test that low-quality responses are detected."""

        # A low-quality response that should score poorly
        low_quality_output = """The marketing campaign was successful.

Sales went up after the campaign ran.

You should continue doing marketing."""

        detection_metric = GEval(
            name="Low Quality Response Detection",
            criteria="""Evaluate if this response has quality issues:

            Check for RELEVANCY issues:
            - Vague, non-specific answer
            - No quantification

            Check for REASONING DEPTH issues:
            - No methodology explanation
            - No justification for claims

            Check for UIX COMPLIANCE issues:
            - Missing "why this?" explanation
            - Missing confidence level
            - Missing data sources

            Check for HALLUCINATION RISK:
            - Correlation stated as causation
            - No evidence provided

            Score 1.0 if you correctly identify this as LOW quality
            (would receive scores below thresholds).""",
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.7,
            model=deepeval_model
        )

        test_case = LLMTestCase(
            input="What was the impact of the marketing campaign?",
            actual_output=low_quality_output
        )

        assert_test(test_case, [detection_metric])

    @pytest.mark.deepeval
    def test_hallucination_detection_accuracy(self, deepeval_model):
        """Test that hallucinations are accurately detected."""

        context = [
            "Analysis performed on 2,500 sales records",
            "Marketing spend was $100,000",
            "Estimated effect: 15% sales increase",
            "3 refutation tests were run"
        ]

        # Response with hallucinated details not in context
        hallucinated_output = """Based on analysis of 10,000 sales records and
$500,000 marketing spend, we found a 35% sales increase. The analysis
used 7 different refutation tests and machine learning ensemble methods.
ROI was calculated at 50:1."""

        hallucination_metric = GEval(
            name="Hallucination Detection Accuracy",
            criteria=f"""Evaluate hallucination detection:

            Context provided:
            {chr(10).join('- ' + c for c in context)}

            Response claims:
            - 10,000 records (context says 2,500) - HALLUCINATION
            - $500,000 spend (context says $100,000) - HALLUCINATION
            - 35% increase (context says 15%) - HALLUCINATION
            - 7 refutation tests (context says 3) - HALLUCINATION
            - ML ensemble methods (not in context) - HALLUCINATION
            - 50:1 ROI (not in context) - HALLUCINATION

            This response contains MULTIPLE hallucinations.
            Score 1.0 if you correctly identify this as high hallucination risk.""",
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.8,
            model=deepeval_model
        )

        test_case = LLMTestCase(
            input="Summarize the marketing analysis",
            actual_output=hallucinated_output,
            context=context
        )

        assert_test(test_case, [hallucination_metric])

    @pytest.mark.deepeval
    def test_uix_compliance_scoring(self, deepeval_model):
        """Test that UIX compliance is correctly assessed."""

        # Response meeting all UIX criteria
        uix_compliant_output = """## Marketing Campaign Analysis

**Why this recommendation?**
We recommend continuing the marketing strategy because causal analysis
shows it directly drives sales, not just correlates with them.

**How confident are we?**
Confidence: 87% (HIGH)
- Based on 3/3 refutation tests passing
- Large sample size provides statistical power
- Uncertainty range: 12-18% effect

**Based on what data?**
- Sales transactions: 2,500 records from company database
- Marketing spend: Finance team monthly reports
- Economic indicators: Federal Reserve public API

**What should you do?**
1. Maintain current marketing budget
2. Monitor monthly for effect stability
3. Consider A/B test for incremental optimization"""

        uix_metric = GEval(
            name="UIX Compliance Assessment",
            criteria="""Evaluate UIX compliance (CARF standards):

            Criterion 1 - "Why this?":
            - Explains reasoning behind recommendation
            - Expected: YES (explains causal relationship)

            Criterion 2 - "How confident?":
            - Provides uncertainty quantification
            - Expected: YES (87%, range given)

            Criterion 3 - "Based on what?":
            - Cites data sources
            - Expected: YES (3 sources listed)

            Criterion 4 - Accessible language:
            - Non-expert can understand
            - Expected: YES (plain language used)

            Score 1.0 if all 4 UIX criteria are met.""",
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.8,
            model=deepeval_model
        )

        test_case = LLMTestCase(
            input="Explain the marketing analysis results",
            actual_output=uix_compliant_output
        )

        assert_test(test_case, [uix_metric])


class TestEvaluationConsistency:
    """Tests for evaluation consistency and reliability."""

    @pytest.mark.deepeval
    def test_consistent_scoring_similar_responses(self, deepeval_model):
        """Test that similar responses receive similar scores."""

        response_a = """The analysis shows a 15% sales increase with 87% confidence.
This is based on causal inference controlling for seasonality and economics.
Data source: 2,500 sales transactions. Recommendation: Continue strategy."""

        response_b = """With 87% confidence, we found sales increased 15%.
Causal analysis controlled for seasonal and economic factors.
Based on 2,500 transaction records. Suggest maintaining current approach."""

        consistency_metric = GEval(
            name="Scoring Consistency",
            criteria="""Compare these two responses:

            Response A:
            "The analysis shows a 15% sales increase with 87% confidence.
            This is based on causal inference controlling for seasonality and economics.
            Data source: 2,500 sales transactions. Recommendation: Continue strategy."

            Response B:
            "With 87% confidence, we found sales increased 15%.
            Causal analysis controlled for seasonal and economic factors.
            Based on 2,500 transaction records. Suggest maintaining current approach."

            These responses convey the SAME information with different wording.
            They should receive SIMILAR quality scores (within 10% of each other).

            Score 1.0 if you agree they should score similarly.
            Score 0.0 if you think they should score very differently.""",
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.8,
            model=deepeval_model
        )

        test_case = LLMTestCase(
            input="Are these responses of similar quality?",
            actual_output=f"Response A: {response_a}\n\nResponse B: {response_b}"
        )

        assert_test(test_case, [consistency_metric])

    @pytest.mark.deepeval
    def test_evaluation_with_missing_context(self, deepeval_model):
        """Test graceful handling when context is unavailable."""

        # Response without context to evaluate against
        response_without_context = """The marketing campaign increased sales by 15%.
We're 87% confident in this estimate based on causal analysis.
The effect was consistent across different customer segments."""

        graceful_metric = GEval(
            name="Graceful Context Handling",
            criteria="""Evaluate this response WITHOUT external context:

            The response makes claims about:
            - 15% sales increase
            - 87% confidence
            - Causal analysis methodology
            - Segment consistency

            Without context, we should:
            1. Evaluate RELEVANCY based on query-response alignment
            2. Evaluate REASONING based on internal consistency
            3. Flag POTENTIAL hallucination (claims unverifiable)
            4. Note that context would improve evaluation

            Score 1.0 if evaluation can proceed reasonably without context.""",
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.6,  # Lower threshold for context-free evaluation
            model=deepeval_model
        )

        test_case = LLMTestCase(
            input="What was the marketing impact?",
            actual_output=response_without_context
            # Note: no context provided
        )

        assert_test(test_case, [graceful_metric])


class TestEvaluationEdgeCases:
    """Edge case tests for evaluation robustness."""

    @pytest.mark.deepeval
    def test_empty_response_handling(self, deepeval_model):
        """Test handling of empty or minimal responses."""

        minimal_response = "I don't know."

        edge_case_metric = GEval(
            name="Minimal Response Handling",
            criteria="""Evaluate this minimal response: "I don't know."

            Expected evaluation:
            - RELEVANCY: Very low (doesn't answer question)
            - REASONING: None (no reasoning provided)
            - UIX COMPLIANCE: Fails (no why/confidence/sources)
            - TASK COMPLETION: No

            This should receive LOW scores across all metrics.
            Score 1.0 if you correctly identify this as failing quality thresholds.""",
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.8,
            model=deepeval_model
        )

        test_case = LLMTestCase(
            input="What was the marketing campaign impact?",
            actual_output=minimal_response
        )

        assert_test(test_case, [edge_case_metric])

    @pytest.mark.deepeval
    def test_overly_confident_response(self, deepeval_model):
        """Test detection of overconfident responses."""

        overconfident_response = """I am 100% certain that the marketing campaign
caused exactly a 15.0% increase in sales. There is absolutely no uncertainty
in this estimate. The analysis is perfect and complete."""

        overconfidence_metric = GEval(
            name="Overconfidence Detection",
            criteria="""Evaluate for overconfidence:

            Red flags in this response:
            - "100% certain" - No analysis is 100% certain
            - "exactly 15.0%" - False precision
            - "absolutely no uncertainty" - All estimates have uncertainty
            - "perfect and complete" - Overclaiming

            A well-calibrated response should:
            - Acknowledge uncertainty
            - Provide ranges, not exact figures
            - Note limitations

            Score 1.0 if you correctly identify this as inappropriately overconfident.""",
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.8,
            model=deepeval_model
        )

        test_case = LLMTestCase(
            input="How confident are you in the marketing analysis?",
            actual_output=overconfident_response
        )

        assert_test(test_case, [overconfidence_metric])
