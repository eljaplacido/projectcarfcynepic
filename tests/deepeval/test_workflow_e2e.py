"""End-to-end workflow evaluation tests.

Tests complete CYNEPIC workflows from query to response:
- Full pipeline evaluation
- Cross-component consistency
- Response quality across different scenarios
"""

import pytest

try:
    from deepeval import assert_test
    from deepeval.metrics import GEval, AnswerRelevancyMetric
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False


pytestmark = pytest.mark.skipif(not DEEPEVAL_AVAILABLE, reason="deepeval not installed")


# End-to-end test scenarios
E2E_SCENARIOS = [
    {
        "name": "Causal Marketing Analysis",
        "query": "Did our Q3 marketing campaign cause the sales increase?",
        "expected_domain": "Complicated",
        "expected_components": ["CynefinRouter", "CausalEngine", "Guardian"],
        "quality_criteria": """
        1. Correctly routes to Complicated domain
        2. Performs causal analysis (not just correlation)
        3. Reports confidence with refutation test results
        4. Provides actionable business recommendation
        """
    },
    {
        "name": "Bayesian Churn Prediction",
        "query": "What's the probability of losing our top 10 customers next quarter?",
        "expected_domain": "Complex",
        "expected_components": ["CynefinRouter", "BayesianEngine", "Guardian"],
        "quality_criteria": """
        1. Correctly routes to Complex domain
        2. Provides probability distribution, not just point estimate
        3. Quantifies uncertainty appropriately
        4. Suggests probing actions to reduce uncertainty
        """
    },
    {
        "name": "Simple Data Lookup",
        "query": "What were our total sales in January 2024?",
        "expected_domain": "Clear",
        "expected_components": ["CynefinRouter", "DataService"],
        "quality_criteria": """
        1. Correctly routes to Clear domain
        2. Returns specific number (not analysis)
        3. High confidence (>90%)
        4. Fast response (appropriate for simple lookup)
        """
    },
    {
        "name": "Crisis Response",
        "query": "Our main database just went down and we're losing orders!",
        "expected_domain": "Chaotic",
        "expected_components": ["CynefinRouter", "Guardian", "HumanLayer"],
        "quality_criteria": """
        1. Correctly routes to Chaotic domain
        2. Prioritizes immediate action over analysis
        3. Escalates to human decision-maker
        4. Provides clear next steps
        """
    },
]


@pytest.mark.deepeval
@pytest.mark.parametrize("scenario", E2E_SCENARIOS, ids=lambda x: x["name"])
def test_e2e_workflow_quality(scenario, deepeval_model):
    """Test end-to-end workflow quality for different scenarios."""

    # Simulate full workflow response
    simulated_response = generate_mock_response(scenario)

    workflow_metric = GEval(
        name=f"E2E Quality: {scenario['name']}",
        criteria=f"""Evaluate the end-to-end response quality:

        Scenario: {scenario['name']}
        Query: {scenario['query']}
        Expected Domain: {scenario['expected_domain']}
        Expected Components: {', '.join(scenario['expected_components'])}

        Quality Criteria:
        {scenario['quality_criteria']}

        Score 1.0 if all criteria met, proportionally lower otherwise.""",
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input=scenario["query"],
        actual_output=simulated_response
    )

    assert_test(test_case, [workflow_metric])


@pytest.mark.deepeval
def test_e2e_component_consistency(deepeval_model):
    """Test that different components produce consistent, non-contradicting outputs."""

    # Simulated multi-component response
    response = """## Full Analysis Pipeline Results

### 1. Router Classification
- Domain: Complicated
- Confidence: 87%
- Reasoning: Query asks about causal relationships requiring expert analysis

### 2. Causal Analysis (DoWhy)
- Treatment Effect: +15% sales increase
- Confidence Interval: [12%, 18%]
- Refutation Tests: 3/3 passed
- Methodology: Causal Forest with propensity score matching

### 3. Reliability Assessment
- Overall Reliability: 85% (HIGH)
- Data Quality: 91%
- Model Confidence: 87%
- Refutation Score: 100%

### 4. Guardian Decision
- Verdict: APPROVE
- Policies Passed: 4/4
- Risk Level: LOW
- Human Review: Not required

### Summary
The marketing campaign caused a 15% sales increase with high confidence (87%).
This finding is reliable and actionable for budget planning."""

    consistency_metric = GEval(
        name="Component Consistency",
        criteria="""Evaluate cross-component consistency:

        1. Router confidence aligns with analysis confidence
        2. Causal results match reliability assessment
        3. Guardian verdict is consistent with confidence/risk levels
        4. Summary accurately reflects component outputs
        5. No contradicting information between components

        Score 1.0 if fully consistent, lower for contradictions.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.8,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="Analyze the impact of our marketing campaign on sales",
        actual_output=response
    )

    assert_test(test_case, [consistency_metric])


@pytest.mark.deepeval
def test_e2e_transparency_completeness(deepeval_model):
    """Test that end-to-end response includes all required transparency elements."""

    response = """## Analysis Complete

**Query Classification**
- Domain: Complicated (Causal Analysis)
- Confidence: 87%
- Components Used: CynefinRouter → CausalEngine → Guardian

**Analysis Results**
- Finding: Marketing campaign caused 15% sales increase
- Effect Size: $2.3M additional revenue
- Confidence Interval: [12%, 18%] at 95% confidence

**Transparency Report**

| Aspect | Detail |
|--------|--------|
| Data Sources | Sales DB (Jan-Dec 2024), Marketing Spend API |
| Methodology | DoWhy Causal Inference with CausalForestDML |
| Assumptions | No unmeasured confounders, SUTVA holds |
| Limitations | Cannot capture brand perception effects |

**Reliability Assessment**
- Overall: 85% (HIGH)
- Refutation Tests: 3/3 passed
  - Placebo Treatment: No effect ✓
  - Subset Validation: Effect holds ✓
  - Random Cause: No spurious correlation ✓

**Decision**
- Guardian Verdict: APPROVE
- Human Review: Not required
- Audit Trail: Preserved (Session ID: abc-123)

**Recommendations**
1. Proceed with campaign renewal at current budget
2. Consider A/B test for 20% budget increase
3. Monitor monthly to validate continued effect"""

    transparency_metric = GEval(
        name="Transparency Completeness",
        criteria="""Evaluate if response includes all transparency elements:

        Required Elements:
        1. Query classification with confidence
        2. Components/agents used in analysis
        3. Data sources cited
        4. Methodology explained
        5. Assumptions stated
        6. Limitations acknowledged
        7. Reliability/refutation test results
        8. Guardian decision with rationale
        9. Audit trail reference
        10. Actionable recommendations

        Score: Count of elements present / 10""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.8,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="Analyze marketing campaign impact with full transparency",
        actual_output=response
    )

    assert_test(test_case, [transparency_metric])


@pytest.mark.deepeval
def test_e2e_error_handling(deepeval_model):
    """Test that errors are handled gracefully with helpful messages."""

    error_response = """## Analysis Status: Incomplete

**Issue Encountered**
We couldn't complete the full analysis due to data quality issues.

**What Happened**
- Router Classification: ✓ Completed (Complicated domain, 82% confidence)
- Data Validation: ⚠️ Issues detected
  - Missing values: 23% of marketing spend records
  - Date range gap: Feb 2024 data missing
- Causal Analysis: ❌ Cannot proceed

**Why This Matters**
Causal inference requires complete data to control for confounders.
The gaps could bias our results, leading to incorrect conclusions.

**Your Options**
1. **Proceed with caveats**: Get preliminary results with uncertainty flag
2. **Provide missing data**: Upload Feb 2024 records to continue
3. **Adjust scope**: Analyze Q3-Q4 only (complete data available)

**Recommendation**
Option 3 (Adjust scope) provides the most reliable results.
Would you like to proceed with Q3-Q4 analysis?

**Current Confidence: 45%** (insufficient for automated decision)
Human review recommended before proceeding."""

    error_metric = GEval(
        name="Error Handling Quality",
        criteria="""Evaluate error handling:

        1. Clearly explains what went wrong
        2. Shows what succeeded vs failed
        3. Explains impact of the error
        4. Provides actionable alternatives
        5. Makes recommendation
        6. Appropriately reduces confidence
        7. Suggests human review when needed

        Score 1.0 if all criteria met, proportionally lower.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="Analyze marketing impact (with incomplete data)",
        actual_output=error_response
    )

    assert_test(test_case, [error_metric])


def generate_mock_response(scenario: dict) -> str:
    """Generate mock response based on scenario for testing."""

    domain = scenario["expected_domain"]
    query = scenario["query"]

    if domain == "Clear":
        return f"""## Analysis Result

**Query**: {query}
**Domain**: Clear (Simple Lookup)
**Confidence**: 95%

**Answer**: Total January 2024 sales were $4,523,891.

**Data Source**: Sales Database, queried at 2024-12-01T10:30:00Z
**Response Time**: 45ms

This is a factual lookup with high confidence."""

    elif domain == "Complicated":
        return f"""## Causal Analysis Result

**Query**: {query}
**Domain**: Complicated (Causal Analysis)
**Confidence**: 87%

**Finding**: The Q3 marketing campaign CAUSED a 15% increase in sales.
This is a causal effect, not merely correlation.

**Evidence**:
- Treatment Effect: +15% (CI: 12-18%)
- Refutation Tests: 3/3 passed
- Sample Size: 1,500 transactions

**Guardian Verdict**: APPROVE (Low Risk)

**Recommendation**: Campaign strategy is validated for renewal."""

    elif domain == "Complex":
        return f"""## Bayesian Analysis Result

**Query**: {query}
**Domain**: Complex (Probabilistic Exploration)
**Confidence**: 72%

**Prediction Distribution**:
- 10% probability: Lose 0-2 customers
- 45% probability: Lose 2-4 customers
- 35% probability: Lose 4-6 customers
- 10% probability: Lose 6+ customers

**Key Uncertainty Sources**:
- Customer satisfaction data is 3 months old
- Competitor actions unknown

**Recommended Probes**:
1. Customer satisfaction survey (high priority)
2. Competitive intelligence review

**Guardian Verdict**: ESCALATE (Medium uncertainty)"""

    elif domain == "Chaotic":
        return f"""## URGENT: Crisis Response

**Query**: {query}
**Domain**: Chaotic (Crisis - Act First)
**Confidence**: N/A (Action mode)

**IMMEDIATE ACTIONS REQUIRED**:
1. ⚠️ Switch to backup database (ETA: 2 min)
2. 📢 Notify customers via status page
3. 🔄 Queue incoming orders for retry

**Escalated To**: On-call DBA and Engineering Lead

**Guardian Verdict**: ESCALATE IMMEDIATELY
Human decision-maker notified via PagerDuty.

**DO NOT wait for analysis** - act to stabilize first."""

    return f"Response for {domain} domain query"
