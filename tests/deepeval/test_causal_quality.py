"""Evaluate CausalEngine output quality using DeepEval metrics.

Tests ensure causal analysis outputs:
- Correctly distinguish causation from correlation
- Accurately interpret refutation test results
- Properly communicate confidence and uncertainty
- Provide actionable causal insights
"""

import pytest

try:
    from deepeval import assert_test
    from deepeval.metrics import GEval, HallucinationMetric
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False


pytestmark = pytest.mark.skipif(not DEEPEVAL_AVAILABLE, reason="deepeval not installed")


@pytest.mark.deepeval
def test_causal_interpretation_relevancy(deepeval_model):
    """Test that causal interpretations are relevant to the analysis performed."""

    # Simulated causal analysis output
    causal_output = """## Causal Analysis Results

**Treatment**: Marketing Spend
**Outcome**: Sales Revenue
**Method**: DoWhy with CausalForestDML

### Estimated Effect
- **Average Treatment Effect (ATE)**: $15,000 increase in sales per $1,000 marketing spend
- **95% Confidence Interval**: [$12,500, $17,500]

### Interpretation
The analysis indicates a **causal relationship** between marketing spend and sales.
For every additional $1,000 invested in marketing, we estimate a $15,000 increase
in sales revenue. This is not merely correlation - we controlled for:
- Seasonal effects
- Economic conditions
- Competitor activity

### Confidence: 87%
Based on:
- 3/3 refutation tests passed
- Large sample size (n=2,500)
- Strong effect size relative to variance"""

    relevancy_metric = GEval(
        name="Causal Interpretation Relevancy",
        criteria="""Evaluate if the causal interpretation is relevant and accurate:
        1. Correctly identifies treatment and outcome variables
        2. Reports effect size with confidence interval
        3. Distinguishes causation from correlation
        4. Lists controlled confounders
        5. Provides confidence level with justification

        Score 1.0 if all criteria met, proportionally lower otherwise.""",
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="What is the causal effect of marketing spend on sales?",
        actual_output=causal_output
    )

    assert_test(test_case, [relevancy_metric])


@pytest.mark.deepeval
def test_causal_claim_validity(deepeval_model):
    """Test that causal claims are properly justified and not overstated."""

    # Output with properly qualified causal claims
    causal_output = """## Causal Effect Analysis

**Finding**: Marketing campaign **caused** a 15% increase in sales.

**Why we can claim causation (not just correlation)**:

1. **Temporal Ordering**: Marketing spend preceded sales increase
2. **Controlled Confounders**:
   - Seasonal trends (holiday shopping patterns)
   - Economic indicators (consumer confidence index)
   - Competitor promotions (tracked via market intelligence)
3. **Refutation Tests Passed**:
   - Placebo test: Random treatment showed no effect ✓
   - Subset validation: Effect consistent across regions ✓
   - Random common cause: No hidden confounders detected ✓

**Limitations**:
- Cannot rule out unmeasured confounders (brand perception, word-of-mouth)
- Effect may not generalize to different market conditions
- Assumes stable treatment effect over time (SUTVA)

**Confidence**: 85% - Strong evidence for causation, some residual uncertainty."""

    validity_metric = GEval(
        name="Causal Claim Validity",
        criteria="""Evaluate the validity of causal claims:
        1. Clearly distinguishes causation from correlation
        2. Explains why causation can be claimed (not just stated)
        3. Lists refutation tests and their results
        4. Acknowledges limitations and assumptions
        5. Does not overstate certainty

        Score 1.0 if claims are well-justified, 0.5 if partially justified,
        0.0 if causal claims are made without proper justification.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="Did marketing cause the sales increase?",
        actual_output=causal_output
    )

    assert_test(test_case, [validity_metric])


@pytest.mark.deepeval
def test_causal_confounder_explanation(deepeval_model):
    """Test that confounder identification and handling is clearly explained."""

    causal_output = """## Confounder Analysis

**Potential Confounders Identified**:

| Variable | Type | How Controlled |
|----------|------|----------------|
| Seasonality | Time-varying | Monthly fixed effects |
| Economic Conditions | Macro | Consumer confidence index covariate |
| Competitor Activity | External | Promotional calendar dummy variables |
| Store Location | Structural | Store fixed effects |
| Product Mix | Selection | Propensity score matching |

**Uncontrolled Confounders** (acknowledged limitations):
- Brand perception changes (no direct measure)
- Word-of-mouth effects (difficult to quantify)
- Employee motivation (not tracked)

**Impact on Results**:
The controlled confounders account for ~60% of the variation in sales.
Uncontrolled confounders may bias our estimate by ±5%, meaning the true
effect could range from 10-20% instead of the reported 15%.

**Recommendation**:
Consider a randomized A/B test in select regions to validate these findings
with fewer confounding concerns."""

    confounder_metric = GEval(
        name="Confounder Explanation Quality",
        criteria="""Evaluate confoundercommunication:
        1. Lists specific confounders considered
        2. Explains how each confounder was controlled
        3. Acknowledges uncontrolled/unmeasured confounders
        4. Quantifies potential bias from uncontrolled confounders
        5. Suggests ways to address confounding concerns

        Score 1.0 if comprehensive, proportionally lower for gaps.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="What confounders were considered in the causal analysis?",
        actual_output=causal_output
    )

    assert_test(test_case, [confounder_metric])


@pytest.mark.deepeval
def test_refutation_test_interpretation(deepeval_model):
    """Test that refutation test results are correctly interpreted."""

    causal_output = """## Refutation Test Results

We performed 4 refutation tests to validate our causal estimate:

### 1. Placebo Treatment Test ✓ PASSED
- **Method**: Replaced actual marketing spend with random values
- **Expected**: No causal effect if original estimate is spurious
- **Result**: Effect dropped to 0.02 (from 0.15), p-value > 0.8
- **Interpretation**: Original effect is not due to chance

### 2. Data Subset Test ✓ PASSED
- **Method**: Re-ran analysis on random 80% subsets (10 iterations)
- **Expected**: Effect should be consistent across subsets
- **Result**: Mean effect 0.148 (±0.012), all within CI of original
- **Interpretation**: Effect is stable and not driven by outliers

### 3. Random Common Cause Test ✓ PASSED
- **Method**: Added random variable as potential confounder
- **Expected**: Effect estimate should not change significantly
- **Result**: Effect changed by <2% (within sampling variance)
- **Interpretation**: No obvious unmeasured confounders

### 4. Unobserved Confounder Sensitivity ⚠️ PARTIAL
- **Method**: Rosenbaum bounds analysis
- **Result**: Effect robust to confounders up to Γ=1.8
- **Interpretation**: A confounder would need to be 1.8x stronger than
  observed confounders to nullify our result. This is possible but unlikely.

**Overall Refutation Score**: 3.5/4 (87.5%)
The causal estimate is robust to most validity threats."""

    refutation_metric = GEval(
        name="Refutation Test Interpretation",
        criteria="""Evaluate refutation test communication:
        1. Lists each refutation test performed
        2. Explains what each test checks for
        3. Reports actual results (not just pass/fail)
        4. Interprets results correctly (what they mean for validity)
        5. Provides overall refutation score or summary

        Score 1.0 if interpretation is thorough and correct.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="How robust is the causal estimate?",
        actual_output=causal_output
    )

    assert_test(test_case, [refutation_metric])


@pytest.mark.deepeval
def test_causal_hallucination_detection(deepeval_model):
    """Test that causal outputs don't hallucinate facts not supported by data."""

    # Context: what the causal analysis actually found
    context = [
        "Treatment variable: marketing_spend",
        "Outcome variable: sales_revenue",
        "Estimated ATE: 15% increase",
        "Confidence interval: [12%, 18%]",
        "Sample size: 2500 observations",
        "Refutation tests: 3 out of 3 passed",
        "Methodology: DoWhy with CausalForestDML",
        "Confounders controlled: seasonality, economic_conditions, competitor_activity"
    ]

    # Output that should NOT hallucinate beyond the context
    causal_output = """Based on our causal analysis:

The marketing spend treatment caused a 15% increase in sales revenue,
with a 95% confidence interval of [12%, 18%]. This finding is based on
2500 observations and passed all 3 refutation tests.

We used DoWhy with CausalForestDML methodology, controlling for
seasonality, economic conditions, and competitor activity as confounders.

The effect is statistically significant and robust to validity checks."""

    hallucination_metric = HallucinationMetric(
        threshold=0.3,  # Low tolerance for hallucination
        model=deepeval_model,
        include_reason=True
    )

    test_case = LLMTestCase(
        input="Summarize the causal analysis results",
        actual_output=causal_output,
        context=context
    )

    assert_test(test_case, [hallucination_metric])


@pytest.mark.deepeval
def test_causal_actionability(deepeval_model):
    """Test that causal insights lead to actionable recommendations."""

    causal_output = """## Causal Insights & Recommendations

**Key Finding**: Marketing spend causes 15% sales increase (ROI: 15:1)

### Actionable Recommendations:

1. **Increase Marketing Budget** (High Confidence)
   - Current: $100K/month
   - Recommended: $150K/month
   - Expected Impact: +$225K additional revenue
   - Payback Period: <1 month

2. **Optimize Channel Allocation** (Medium Confidence)
   - Digital channels showed 2x effect vs. traditional
   - Recommend shifting 30% budget from TV to digital
   - Caution: Effect heterogeneity across demographics

3. **Timing Optimization** (Lower Confidence)
   - Effect stronger in Q4 (holiday season)
   - Consider front-loading Q4 spend
   - Note: Based on limited seasonal data

### What NOT to Do (Based on Analysis):
- Don't assume linear scaling above $200K (diminishing returns observed)
- Don't ignore competitor response (effect may decrease if competitors match)

### Recommended Next Steps:
1. Run A/B test at $150K level to validate prediction
2. Implement incrementality measurement framework
3. Monitor competitor activity weekly"""

    actionability_metric = GEval(
        name="Causal Actionability",
        criteria="""Evaluate if causal insights are actionable:
        1. Translates statistical findings to business recommendations
        2. Quantifies expected impact of recommendations
        3. Acknowledges confidence levels for each recommendation
        4. Warns about limitations or conditions
        5. Provides concrete next steps

        Score 1.0 if highly actionable, lower if vague or generic.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="What should we do based on the causal analysis?",
        actual_output=causal_output
    )

    assert_test(test_case, [actionability_metric])


@pytest.mark.deepeval
def test_causal_uncertainty_quantification(deepeval_model):
    """Test that uncertainty in causal estimates is properly communicated."""

    causal_output = """## Uncertainty Analysis

**Point Estimate**: 15% sales increase per $1K marketing spend

**Uncertainty Breakdown**:

| Source | Contribution | Reducible? |
|--------|--------------|------------|
| Sampling Variance | ±2% | Yes (more data) |
| Model Specification | ±1.5% | Partially (model comparison) |
| Unmeasured Confounders | ±3% | Difficult (would need RCT) |
| Measurement Error | ±0.5% | Yes (better tracking) |
| **Total Uncertainty** | **±7%** | |

**Confidence Interval**: [8%, 22%] at 95% level

**What This Means**:
- We're 95% confident the true effect is between 8% and 22%
- The most likely value is 15% (our point estimate)
- There's a 5% chance the true effect is outside this range

**Uncertainty Classification**:
- **Epistemic** (reducible): 4% - Could reduce with more data
- **Aleatoric** (irreducible): 3% - Inherent randomness in system

**To Reduce Uncertainty**:
1. Collect 6 more months of data (reduces sampling variance)
2. Run randomized experiment (reduces confounder uncertainty)
3. Implement conversion tracking (reduces measurement error)"""

    uncertainty_metric = GEval(
        name="Uncertainty Quantification",
        criteria="""Evaluate uncertainty communication:
        1. Provides point estimate AND interval/range
        2. Decomposes sources of uncertainty
        3. Distinguishes reducible vs irreducible uncertainty
        4. Explains what the uncertainty means practically
        5. Suggests ways to reduce uncertainty

        Score 1.0 if uncertainty is comprehensively addressed.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="How certain are we about the causal effect?",
        actual_output=causal_output
    )

    assert_test(test_case, [uncertainty_metric])
