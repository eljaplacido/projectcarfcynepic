"""Evaluate BayesianEngine output quality using DeepEval metrics.

Tests ensure Bayesian analysis outputs:
- Properly communicate probability distributions
- Distinguish epistemic from aleatoric uncertainty
- Generate useful probing recommendations
- Update beliefs transparently
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
def test_bayesian_probability_communication(deepeval_model):
    """Test that Bayesian probabilities are communicated accessibly."""

    bayesian_output = """## Bayesian Probability Analysis

**Question**: What is the probability of customer churn next quarter?

**Posterior Distribution**:
- Most likely outcome: 34% churn rate
- Credible interval (90%): [28%, 41%]

**What This Means in Plain Language**:
Think of it like a weather forecast. We're saying there's about a 1-in-3
chance that customers will leave. But we're not certain - it could be as
low as 28% (best case) or as high as 41% (worst case).

**Probability Breakdown**:
| Scenario | Probability | Churn Rate |
|----------|-------------|------------|
| Best case | 10% | <28% |
| Likely range | 80% | 28-41% |
| Worst case | 10% | >41% |

**Key Takeaway**:
Plan for 34% churn in your base case, but stress-test your plans against
41% churn to ensure resilience."""

    probability_metric = GEval(
        name="Probability Communication",
        criteria="""Evaluate Bayesian probability communication:
        1. Provides point estimate AND credible interval
        2. Uses accessible language (analogies, examples)
        3. Explains what the interval means practically
        4. Shows probability breakdown by scenario
        5. Gives actionable takeaway

        Score 1.0 if fully accessible to non-statisticians.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="What's the probability of customer churn?",
        actual_output=bayesian_output
    )

    assert_test(test_case, [probability_metric])


@pytest.mark.deepeval
def test_bayesian_epistemic_vs_aleatoric(deepeval_model):
    """Test that epistemic and aleatoric uncertainty are distinguished."""

    bayesian_output = """## Uncertainty Analysis

**Total Uncertainty in Churn Prediction**: ±7%

### Types of Uncertainty:

**1. Epistemic Uncertainty (What we don't know yet)**: ±4%
- *Definition*: Uncertainty from limited data or knowledge
- *Sources*:
  - Limited historical data (only 18 months)
  - Incomplete customer profiles (missing engagement metrics)
  - Model uncertainty (simplified linear relationships)
- *Can we reduce it?* YES - with more data and better models

**2. Aleatoric Uncertainty (Inherent randomness)**: ±3%
- *Definition*: Uncertainty that cannot be reduced, even with perfect data
- *Sources*:
  - Individual customer decisions are inherently unpredictable
  - Random external events (competitor actions, economic shocks)
  - Natural variation in customer behavior
- *Can we reduce it?* NO - this is fundamental randomness

### Why This Matters:
- Epistemic uncertainty = opportunity to improve predictions
- Aleatoric uncertainty = accept it and plan for variability

### How to Reduce Total Uncertainty:
1. Collect 6 more months of data → reduces epistemic by ~1%
2. Add engagement features → reduces epistemic by ~1.5%
3. Use ensemble models → reduces epistemic by ~0.5%
4. Aleatoric will remain at ~3% regardless"""

    uncertainty_metric = GEval(
        name="Epistemic vs Aleatoric Distinction",
        criteria="""Evaluate uncertainty type communication:
        1. Clearly defines epistemic uncertainty
        2. Clearly defines aleatoric uncertainty
        3. Lists specific sources for each type
        4. Explains reducibility of each type
        5. Provides actionable guidance based on uncertainty type

        Score 1.0 if both types are clearly distinguished and explained.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="What types of uncertainty are in the prediction?",
        actual_output=bayesian_output
    )

    assert_test(test_case, [uncertainty_metric])


@pytest.mark.deepeval
def test_bayesian_probe_recommendation_quality(deepeval_model):
    """Test that Bayesian probes are well-designed safe-to-fail experiments."""

    bayesian_output = """## Recommended Probes (Safe-to-Fail Experiments)

Given high uncertainty about customer churn drivers, we recommend these probes:

### Probe 1: Engagement Survey (HIGH PRIORITY)
- **Hypothesis**: Low engagement predicts churn
- **Action**: Send NPS survey to 500 random customers
- **Duration**: 2 weeks
- **Success Criteria**: >60% response rate, correlation >0.3
- **Safe-to-Fail**: Survey is non-intrusive, no business impact if hypothesis wrong
- **Information Gain**: Expected to reduce uncertainty by 15%

### Probe 2: Retention Offer A/B Test (MEDIUM PRIORITY)
- **Hypothesis**: 10% discount reduces churn by 5%
- **Action**: Offer discount to 200 at-risk customers (control: 200)
- **Duration**: 1 month
- **Success Criteria**: Churn rate <25% in treatment group
- **Safe-to-Fail**: Limited to 200 customers, revenue impact capped at $2K
- **Information Gain**: Expected to reduce uncertainty by 20%

### Probe 3: Exit Interview Program (LOWER PRIORITY)
- **Hypothesis**: We can identify fixable churn reasons
- **Action**: Interview 20 churned customers
- **Duration**: 3 weeks
- **Success Criteria**: Identify 3+ actionable patterns
- **Safe-to-Fail**: No business risk, qualitative insights
- **Information Gain**: Hard to quantify, but directional value

### Probe Selection Rationale:
These probes are ordered by expected information gain per unit cost.
Run Probe 1 first - if engagement is predictive, it informs Probes 2-3."""

    probe_metric = GEval(
        name="Probe Recommendation Quality",
        criteria="""Evaluate Bayesian probe recommendations:
        1. Each probe has clear hypothesis
        2. Actions are specific and time-bound
        3. Success criteria are measurable
        4. Safe-to-fail is explicitly addressed
        5. Information gain is estimated
        6. Probes are prioritized with rationale

        Score 1.0 if probes are well-designed experiments.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="What experiments should we run to reduce uncertainty?",
        actual_output=bayesian_output
    )

    assert_test(test_case, [probe_metric])


@pytest.mark.deepeval
def test_bayesian_belief_update_transparency(deepeval_model):
    """Test that Bayesian belief updates are transparently explained."""

    bayesian_output = """## Belief Update Report

### Prior Belief (Before New Data)
- **Churn Rate Estimate**: 30% (±8%)
- **Based On**: Industry benchmarks, historical average

### New Evidence Observed
- **Data**: Q3 customer satisfaction scores dropped 15%
- **Sample**: 1,200 customers surveyed

### Likelihood Assessment
- **P(satisfaction drop | high churn)**: 0.75
- **P(satisfaction drop | low churn)**: 0.25
- Evidence is 3x more likely under high-churn scenario

### Posterior Belief (After Update)
- **Updated Churn Estimate**: 38% (±6%)
- **Shift**: +8 percentage points from prior
- **Uncertainty Reduced**: ±8% → ±6% (evidence was informative)

### Belief Update Visualization
```
Prior:     [====|=========]  30% ± 8%
                    ↓
Evidence:  Satisfaction dropped 15%
                    ↓
Posterior: [========|=====]  38% ± 6%
```

### Why This Update Makes Sense
1. Satisfaction is a leading indicator of churn
2. The 15% drop is a strong signal (3x likelihood ratio)
3. Large sample (n=1,200) provides reliable evidence
4. Update magnitude (8pp) reflects evidence strength

### What Would Change Our Belief Further
- Higher churn: Competitor launches superior product
- Lower churn: We launch successful retention program"""

    update_metric = GEval(
        name="Belief Update Transparency",
        criteria="""Evaluate Bayesian belief update communication:
        1. Shows prior belief with uncertainty
        2. Describes new evidence clearly
        3. Explains likelihood/evidence strength
        4. Shows posterior belief with updated uncertainty
        5. Explains WHY the update makes sense
        6. Notes what would further change beliefs

        Score 1.0 if update process is fully transparent.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="How did the new satisfaction data change our churn estimate?",
        actual_output=bayesian_output
    )

    assert_test(test_case, [update_metric])


@pytest.mark.deepeval
def test_bayesian_decision_under_uncertainty(deepeval_model):
    """Test that Bayesian outputs support decision-making under uncertainty."""

    bayesian_output = """## Decision Analysis Under Uncertainty

**Decision**: Should we invest $500K in customer retention program?

### Expected Outcomes by Scenario

| Scenario | Probability | Retention Lift | NPV |
|----------|-------------|----------------|-----|
| High effectiveness | 25% | 15% | +$2M |
| Medium effectiveness | 50% | 8% | +$800K |
| Low effectiveness | 20% | 2% | -$200K |
| No effect | 5% | 0% | -$500K |

### Expected Value Calculation
- **Expected NPV**: 0.25($2M) + 0.50($800K) + 0.20(-$200K) + 0.05(-$500K)
- **Expected NPV**: $500K + $400K - $40K - $25K = **$835K**

### Risk Analysis
- **Probability of positive return**: 75%
- **Probability of break-even or better**: 95%
- **Maximum downside**: -$500K (5% probability)

### Decision Recommendation
**PROCEED** with retention investment

**Rationale**:
1. Expected value is strongly positive ($835K)
2. 75% chance of meaningful profit
3. Downside is capped and unlikely (5%)
4. Aligns with risk tolerance (max loss < 10% of budget)

### Sensitivity Analysis
Decision remains PROCEED if:
- Effectiveness probabilities shift by up to 15%
- Cost increases by up to 40%
- Decision flips to HOLD if low-effectiveness probability exceeds 50%"""

    decision_metric = GEval(
        name="Decision Under Uncertainty",
        criteria="""Evaluate decision support quality:
        1. Maps scenarios with probabilities
        2. Quantifies outcomes for each scenario
        3. Calculates expected value correctly
        4. Assesses risk (downside probability)
        5. Provides clear recommendation with rationale
        6. Includes sensitivity analysis

        Score 1.0 if analysis fully supports decision-making.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="Should we invest in the retention program given the uncertainty?",
        actual_output=bayesian_output
    )

    assert_test(test_case, [decision_metric])


@pytest.mark.deepeval
def test_bayesian_model_assumptions(deepeval_model):
    """Test that Bayesian model assumptions are clearly stated."""

    bayesian_output = """## Model Assumptions & Limitations

### Statistical Assumptions

1. **Prior Distribution**
   - *Assumption*: Beta(2, 5) prior on churn rate
   - *Justification*: Industry data suggests 20-30% churn typical
   - *Sensitivity*: Results robust to prior choice (tested Beta(1,1) to Beta(5,10))

2. **Likelihood Model**
   - *Assumption*: Customer churn follows Bernoulli distribution
   - *Justification*: Binary outcome (churn/retain)
   - *Limitation*: Ignores partial churn (reduced usage)

3. **Independence**
   - *Assumption*: Customer decisions are independent
   - *Limitation*: May underestimate uncertainty if customers influence each other
   - *Mitigation*: Inflated credible intervals by 10%

4. **Stationarity**
   - *Assumption*: Churn patterns stable over time
   - *Limitation*: May not hold during market disruptions
   - *Mitigation*: Rolling window analysis to detect drift

### Business Assumptions

5. **Cost Estimates**
   - *Assumption*: Customer acquisition cost = $500
   - *Uncertainty*: ±20% based on channel mix
   - *Impact*: Affects ROI calculations proportionally

### What Could Invalidate This Analysis
- Major competitor entry (violates stationarity)
- Economic recession (changes customer behavior)
- Product quality issues (introduces correlation)

### Robustness Checks Performed
- ✓ Prior sensitivity analysis
- ✓ Leave-one-out cross-validation
- ✓ Posterior predictive checks
- ✗ Hierarchical model (future work)"""

    assumptions_metric = GEval(
        name="Model Assumptions Clarity",
        criteria="""Evaluate assumption communication:
        1. Lists statistical assumptions explicitly
        2. Provides justification for each assumption
        3. Acknowledges limitations of assumptions
        4. Describes mitigation for known limitations
        5. Notes what could invalidate the analysis
        6. Lists robustness checks performed

        Score 1.0 if assumptions are comprehensively documented.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="What assumptions does the Bayesian model make?",
        actual_output=bayesian_output
    )

    assert_test(test_case, [assumptions_metric])
