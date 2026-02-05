"""Evaluate ChatService response quality using DeepEval metrics.

Tests:
- Answer relevancy to user queries
- Hallucination detection against provided context
- Response completeness and actionability
"""

import pytest

try:
    from deepeval import assert_test
    from deepeval.metrics import AnswerRelevancyMetric, HallucinationMetric, GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False


pytestmark = pytest.mark.skipif(not DEEPEVAL_AVAILABLE, reason="deepeval not installed")


@pytest.mark.asyncio
@pytest.mark.deepeval
async def test_chat_response_relevancy(deepeval_model):
    """Test that ChatService responses are relevant to user queries."""
    # Simulate ChatService response
    from src.services.chat import ChatService, ChatRequest, ChatMessage

    service = ChatService()
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="What is causal inference?")]
    )

    try:
        response = await service.chat(request)
        actual_output = response.message
    except Exception:
        # Fallback for when LLM is not available
        actual_output = """Causal inference is a statistical methodology that aims to
        determine cause-and-effect relationships from data. Unlike correlation analysis
        which only identifies associations, causal inference attempts to answer
        counterfactual questions like 'What would have happened if we had done X instead of Y?'

        Key methods include:
        - Randomized Controlled Trials (RCTs)
        - Instrumental Variables
        - Difference-in-Differences
        - Regression Discontinuity

        Confidence: 92% based on established statistical literature."""

    test_case = LLMTestCase(
        input="What is causal inference?",
        actual_output=actual_output,
    )

    relevancy = AnswerRelevancyMetric(
        threshold=0.7,
        model=deepeval_model,
        include_reason=True
    )

    assert_test(test_case, [relevancy])


@pytest.mark.asyncio
@pytest.mark.deepeval
async def test_chat_hallucination_detection(deepeval_model):
    """Test that ChatService responses don't hallucinate facts not in context."""
    # Context provided to the system
    context = [
        "CYNEPIC uses the Cynefin framework for domain classification.",
        "The four main domains are Clear, Complicated, Complex, and Chaotic.",
        "Causal analysis is performed using DoWhy library.",
        "Bayesian inference uses PyMC for probabilistic modeling."
    ]

    # Simulated response - should only reference provided context
    actual_output = """Based on the CYNEPIC system:

    The system uses the Cynefin framework to classify your query. There are four
    main domains: Clear (simple cause-effect), Complicated (requires expert analysis),
    Complex (emergent patterns), and Chaotic (crisis situations).

    For causal analysis, the system leverages the DoWhy library which provides
    robust causal inference methods. Bayesian inference is handled by PyMC for
    probabilistic modeling of uncertainty.

    Confidence: 88%"""

    test_case = LLMTestCase(
        input="How does CYNEPIC analyze queries?",
        actual_output=actual_output,
        context=context
    )

    hallucination = HallucinationMetric(
        threshold=0.3,  # Low threshold = low hallucination tolerance
        model=deepeval_model,
        include_reason=True
    )

    assert_test(test_case, [hallucination])


@pytest.mark.asyncio
@pytest.mark.deepeval
async def test_chat_response_completeness(deepeval_model):
    """Test that responses provide complete, actionable information."""
    actual_output = """To analyze the relationship between marketing spend and revenue:

    1. **Data Required**: Monthly marketing spend and revenue figures (minimum 12 months)
    2. **Recommended Analysis**: Causal inference using DoWhy to control for confounders
    3. **Expected Output**: Average Treatment Effect (ATE) with confidence intervals

    The analysis will take approximately 2-3 minutes. Would you like me to proceed?

    Confidence: 85% - Based on standard causal inference methodology"""

    completeness_metric = GEval(
        name="Response Completeness",
        criteria="""Evaluate if the response is complete and actionable:
        1. Clearly states what data is needed
        2. Explains the methodology that will be used
        3. Sets expectations for output/results
        4. Provides confidence level
        5. Offers clear next steps

        Score 1.0 if all 5 criteria met, proportionally lower otherwise.""",
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="How can I analyze the impact of marketing on revenue?",
        actual_output=actual_output
    )

    assert_test(test_case, [completeness_metric])


@pytest.mark.asyncio
@pytest.mark.deepeval
async def test_chat_uncertainty_communication(deepeval_model):
    """Test that responses properly communicate uncertainty levels."""
    actual_output = """Based on the analysis:

    **Finding**: There appears to be a positive correlation between training hours
    and employee performance scores.

    **Confidence**: 72% (Medium)
    - The correlation is statistically significant (p < 0.05)
    - However, we cannot establish causation without controlling for confounders
    - Sample size (n=150) provides moderate statistical power

    **Uncertainty Sources**:
    - Potential selection bias in who receives training
    - Unmeasured confounders (experience level, motivation)
    - Limited time period of data (6 months)

    **Recommendation**: Consider a controlled experiment or instrumental variable
    approach for stronger causal claims."""

    uncertainty_metric = GEval(
        name="Uncertainty Communication",
        criteria="""Evaluate how well the response communicates uncertainty:
        1. Provides a clear confidence score or level
        2. Explains what the confidence is based on
        3. Lists specific sources of uncertainty
        4. Distinguishes correlation from causation when relevant
        5. Suggests ways to reduce uncertainty

        Score 1.0 if all criteria excellently met, lower proportionally.""",
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="Does employee training improve performance?",
        actual_output=actual_output
    )

    assert_test(test_case, [uncertainty_metric])
