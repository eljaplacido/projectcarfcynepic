"""Evaluate ExplanationService using CARF UIX standards.

Tests ensure explanations meet the UIX guidelines:
- "Why this?" - reasoning explanation
- "How confident?" - uncertainty quantification
- "Based on what?" - data source citations
- Accessible language for non-experts
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


@pytest.mark.deepeval
def test_explanation_meets_uix_standards(deepeval_model, uix_evaluation_criteria):
    """Test that explanations meet CARF UIX standards: Why? How confident? Based on what?"""

    # Example explanation from ExplanationService
    explanation = """## Analysis Result: Marketing Campaign Impact

**Why this recommendation?**
The analysis classified your query as "Complicated" because it involves causal
relationships that require expert analysis. We used causal inference to determine
the true impact of the marketing campaign on sales, controlling for seasonal
effects and economic factors.

**How confident are we?**
Confidence: 87% (High)
- The causal effect estimate passed 3/3 refutation tests
- Sample size of 1,500 transactions provides strong statistical power
- Uncertainty range: 12-18% sales increase (95% confidence interval)

**Based on what data?**
- Sales transactions: Jan 2024 - Dec 2024
- Marketing spend records from finance system
- Economic indicators from Federal Reserve API
- Seasonal adjustment using X-13ARIMA-SEATS

**What does this mean for you?**
The campaign increased sales by approximately 15%. This is a causal effect,
meaning the increase is directly attributable to the campaign, not just correlation.
You can confidently attribute ROI calculations to this campaign."""

    uix_metric = GEval(
        name="CARF UIX Standard Compliance",
        criteria=uix_evaluation_criteria,
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="Explain the impact of our Q3 marketing campaign on sales",
        actual_output=explanation
    )

    assert_test(test_case, [uix_metric])


@pytest.mark.deepeval
def test_explanation_accessibility(deepeval_model):
    """Test that explanations use accessible language for non-experts."""

    explanation = """## Cynefin Domain: Complicated

**What this means:**
Your question falls into the "Complicated" category. This means there IS a
right answer, but finding it requires careful analysis. Think of it like
diagnosing a car problem - a mechanic can figure it out, but it's not obvious
to everyone.

**How we'll analyze it:**
We'll use a method called "causal inference" - this helps us separate what
actually caused something from what just happened to occur at the same time.
It's like determining whether taking medicine actually cured your headache,
or if it would have gone away on its own.

**What to expect:**
- Analysis will complete in about 30 seconds
- You'll get a confidence percentage (higher = more certain)
- We'll show you what data we used
- If we're not confident enough, we'll ask for human review"""

    accessibility_metric = GEval(
        name="Language Accessibility",
        criteria="""Evaluate if the explanation is accessible to non-technical users:
        1. Avoids jargon or explains technical terms when used
        2. Uses analogies or everyday examples to explain concepts
        3. Breaks down complex ideas into simple steps
        4. Uses clear, conversational language
        5. Appropriate for someone without data science background

        Score 1.0 if fully accessible, lower if technical terms unexplained.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="How do you classify my query?",
        actual_output=explanation
    )

    assert_test(test_case, [accessibility_metric])


@pytest.mark.deepeval
def test_explanation_causal_reasoning(deepeval_model):
    """Test that causal explanations properly communicate causal vs correlational findings."""

    explanation = """## Causal Analysis Results

**Key Finding:**
Marketing spend CAUSES a 15% increase in sales (not just correlation).

**Why we can claim causation:**
1. **Controlled for confounders**: We accounted for:
   - Seasonal effects (holiday shopping)
   - Economic conditions (consumer confidence index)
   - Competitor actions (promotional calendar)

2. **Refutation tests passed**:
   - Placebo test: Random treatment showed no effect ✓
   - Subset test: Effect consistent across regions ✓
   - Random common cause: No hidden confounders detected ✓

3. **Temporal ordering**: Marketing spend preceded sales increase

**What this is NOT:**
- This is not just a correlation (things happening together)
- This is not confounded by other factors we could measure
- This is not a fluke - the effect is statistically significant

**Confidence: 89%**
The remaining 11% uncertainty comes from:
- Unmeasurable confounders (brand perception, word-of-mouth)
- Measurement error in sales attribution"""

    causal_reasoning_metric = GEval(
        name="Causal Reasoning Quality",
        criteria="""Evaluate the quality of causal reasoning explanation:
        1. Clearly distinguishes causation from correlation
        2. Explains what confounders were controlled
        3. Describes refutation/validation tests performed
        4. Acknowledges limitations and sources of uncertainty
        5. Uses precise causal language (causes, leads to, results in)

        Score 1.0 if causal reasoning is rigorous and well-explained.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="Did our marketing campaign actually cause the sales increase?",
        actual_output=explanation
    )

    assert_test(test_case, [causal_reasoning_metric])


@pytest.mark.deepeval
def test_explanation_bayesian_uncertainty(deepeval_model):
    """Test that Bayesian analysis explanations properly communicate uncertainty."""

    explanation = """## Bayesian Analysis: Customer Behavior Prediction

**Prediction:**
Customer churn probability: 34% (range: 28% - 41%)

**How certain are we?**
This prediction has MEDIUM certainty:
- We're fairly confident the true probability is between 28-41%
- The most likely value is 34%
- There's meaningful uncertainty because:
  - Customer behavior is inherently unpredictable
  - We have limited historical data (18 months)
  - Some customers behave very differently from others

**What does the range mean?**
- Best case: 28% churn (if favorable market conditions)
- Most likely: 34% churn (our central estimate)
- Worst case: 41% churn (if economic downturn)

**Recommendation:**
Given the uncertainty, we recommend:
1. Plan for 34% churn in base case scenarios
2. Stress-test plans against 41% churn scenario
3. Monitor leading indicators monthly to update predictions

**Confidence improves with:**
- More customer data (each month adds ~2% confidence)
- Additional features (engagement metrics, support tickets)"""

    bayesian_metric = GEval(
        name="Bayesian Uncertainty Communication",
        criteria="""Evaluate how well Bayesian uncertainty is communicated:
        1. Provides point estimate AND credible interval/range
        2. Explains what the uncertainty range means in practical terms
        3. Identifies sources of uncertainty (epistemic vs aleatoric)
        4. Gives actionable recommendations despite uncertainty
        5. Explains how uncertainty could be reduced

        Score 1.0 if uncertainty is thoroughly and accessibly explained.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="What's the probability of customer churn next quarter?",
        actual_output=explanation
    )

    assert_test(test_case, [bayesian_metric])


@pytest.mark.deepeval
def test_explanation_guardian_decision(deepeval_model):
    """Test that Guardian layer decisions are transparently explained."""

    explanation = """## Guardian Decision: Human Review Required

**Decision:** ESCALATE to human reviewer

**Why this decision?**
Your request involves a financial decision exceeding automated approval limits:
- Requested action: Approve $75,000 marketing budget
- Auto-approval limit: $50,000
- Policy: Transactions >$50K require human oversight

**Policies Evaluated:**

| Policy | Status | Reason |
|--------|--------|--------|
| Financial Limit | ⚠️ TRIGGERED | Amount exceeds $50K threshold |
| Confidence Check | ✓ PASSED | Analysis confidence 87% > 75% minimum |
| Data Quality | ✓ PASSED | Data quality score 91% |
| Risk Assessment | ✓ PASSED | Estimated risk: LOW |

**What happens next?**
1. Your request has been sent to the Finance team via Slack
2. Expected response time: 4 business hours
3. You'll receive notification when approved/rejected

**Can I override this?**
No - financial limits are mandatory policies that cannot be overridden
for compliance reasons. However, you can:
- Split the request into amounts under $50K
- Provide additional justification to expedite review"""

    guardian_metric = GEval(
        name="Guardian Transparency",
        criteria="""Evaluate transparency of Guardian layer decision:
        1. Clearly states the decision and why it was made
        2. Lists all policies that were evaluated
        3. Explains which policies passed vs triggered
        4. Describes what happens next
        5. Explains user's options (appeal, override, alternatives)

        Score 1.0 if fully transparent and actionable.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="Approve the Q4 marketing budget of $75,000",
        actual_output=explanation
    )

    assert_test(test_case, [guardian_metric])
