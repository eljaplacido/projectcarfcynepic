"""Evaluate TransparencyService output quality using DeepEval metrics.

Tests ensure transparency outputs:
- Clearly explain agent decision chains
- Provide complete audit trail information
- Meet EU AI Act transparency requirements
- Support human oversight effectively
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
def test_agent_decision_transparency(deepeval_model):
    """Test that agent decisions are transparently explained."""

    transparency_output = """## Agent Decision Trace

### Session: abc-123-def
### Query: "Why did sales increase last quarter?"

---

### Step 1: Cynefin Router
- **Agent**: cynefin_router
- **Input**: "Why did sales increase last quarter?"
- **Decision**: Route to COMPLICATED domain
- **Reasoning**: Query asks "why" about past event, suggesting causal analysis needed.
  Entropy score 0.23 indicates low ambiguity. Pattern match: "why did X increase"
  maps to causal investigation.
- **Confidence**: 89%
- **Alternatives Considered**:
  - CLEAR (rejected: not a simple lookup)
  - COMPLEX (rejected: past event, not emergent future)
- **Duration**: 145ms

---

### Step 2: Causal Analyst
- **Agent**: causal_analyst
- **Input**: Sales data (Q1-Q4), Marketing spend, Economic indicators
- **Decision**: Perform DoWhy causal analysis
- **Reasoning**: Multiple potential causes identified. Selected propensity score
  matching to control for confounders. Treatment: marketing spend.
- **Confidence**: 87%
- **Data Sources Used**:
  - sales_transactions.csv (n=2,500)
  - marketing_spend.csv (monthly aggregates)
  - consumer_confidence_index (Fed API)
- **Assumptions Made**:
  - No unmeasured confounders
  - Linear treatment effect
- **Duration**: 2,340ms

---

### Step 3: Guardian
- **Agent**: guardian
- **Input**: Causal analysis result, confidence=87%
- **Decision**: APPROVE (auto-approved)
- **Reasoning**: Confidence 87% exceeds threshold 75%. No policy violations.
  Financial impact within limits. Risk score: LOW.
- **Policies Evaluated**: 4/4 passed
- **Duration**: 12ms

---

### Total Pipeline Duration: 2,497ms
### Final Confidence: 87%"""

    transparency_metric = GEval(
        name="Agent Decision Transparency",
        criteria="""Evaluate agent decision chain transparency:
        1. Each step shows agent name and role
        2. Input/output clearly documented
        3. Reasoning explains WHY decision was made
        4. Confidence levels provided at each step
        5. Alternatives considered are listed
        6. Data sources and assumptions documented
        7. Timing information included

        Score 1.0 if fully transparent and auditable.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="Show me the decision trace for this analysis",
        actual_output=transparency_output
    )

    assert_test(test_case, [transparency_metric])


@pytest.mark.deepeval
def test_audit_trail_completeness(deepeval_model):
    """Test that audit trails contain all required compliance information."""

    transparency_output = """## Audit Trail Report

### Session Metadata
| Field | Value |
|-------|-------|
| Session ID | abc-123-def-456 |
| Timestamp | 2024-01-15T14:32:17Z |
| User ID | user@example.com (hashed) |
| Request Origin | API /v1/query |
| IP Address | [redacted for privacy] |

### Processing Record

**1. Input Received**
- Raw query: "Analyze marketing campaign effectiveness"
- Preprocessing: Tokenized, normalized
- Query hash: sha256:7f83b...

**2. Model Invocations**
| Step | Model | Version | Input Tokens | Output Tokens | Latency |
|------|-------|---------|--------------|---------------|---------|
| Router | gpt-4o-mini | 2024-01 | 156 | 89 | 234ms |
| Analyst | gpt-4o | 2024-01 | 2,340 | 512 | 1,890ms |

**3. Data Access Log**
| Dataset | Rows Accessed | Columns | Permission |
|---------|---------------|---------|------------|
| sales_2024 | 2,500 | 8 | read-only |
| marketing_spend | 12 | 4 | read-only |

**4. Decision Record**
- Domain Classification: COMPLICATED (confidence: 89%)
- Analysis Method: DoWhy Causal Inference
- Final Result: 15% effect (CI: 12-18%)
- Guardian Verdict: APPROVED
- Human Review: Not triggered

**5. Output Delivered**
- Response hash: sha256:3a2f1...
- Delivery timestamp: 2024-01-15T14:32:19Z
- Total latency: 2,497ms

### Compliance Attestation
- ✓ Art. 12 Record-keeping: Complete audit trail
- ✓ Art. 13 Transparency: Explanation provided
- ✓ Art. 14 Human Oversight: Escalation available
- ✓ Data minimization: Only required data accessed"""

    audit_metric = GEval(
        name="Audit Trail Completeness",
        criteria="""Evaluate audit trail completeness:
        1. Session metadata (ID, timestamp, origin)
        2. Input/output hashes for integrity
        3. All model invocations logged with versions
        4. Data access recorded
        5. Decisions documented with reasoning
        6. Timing/latency recorded
        7. Compliance attestation included

        Score 1.0 if audit trail is complete for regulatory review.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="Generate the audit trail for this session",
        actual_output=transparency_output
    )

    assert_test(test_case, [audit_metric])


@pytest.mark.deepeval
def test_eu_ai_act_compliance_report(deepeval_model):
    """Test that EU AI Act compliance reporting is comprehensive."""

    transparency_output = """## EU AI Act Compliance Assessment

### System Classification
- **AI System**: CARF - Complex Adaptive Reasoning Fabric
- **Risk Category**: LIMITED RISK (decision support, not autonomous)
- **Articles Applicable**: 12, 13, 14, 52

---

### Article-by-Article Compliance

#### Article 12: Record-Keeping ✓ COMPLIANT
**Requirement**: Automatic logging of events for traceability
**Evidence**:
- Kafka audit trail captures all decisions (retention: 7 years)
- Session IDs enable full trace reconstruction
- Immutable log storage with cryptographic integrity
**Score**: 95%

#### Article 13: Transparency ✓ COMPLIANT
**Requirement**: Users can interpret system outputs
**Evidence**:
- Every output includes confidence score and reasoning
- Transparency panel shows agent chain-of-thought
- Methodology documented and accessible
**Score**: 90%

#### Article 14: Human Oversight ✓ COMPLIANT
**Requirement**: Human oversight and intervention possible
**Evidence**:
- Guardian layer enforces escalation policies
- HumanLayer integration for Slack/email approval
- Override capability for authorized users
**Score**: 95%

#### Article 52: Transparency Obligations ⚠️ PARTIAL
**Requirement**: Users informed they are interacting with AI
**Evidence**:
- API responses include "ai_generated: true" flag
- UI shows "AI Analysis" badge
**Gap**: Verbal/chat interactions lack explicit AI disclosure
**Remediation**: Add disclosure to chat greeting
**Score**: 75%

---

### Overall Compliance Score: 89%
### Status: COMPLIANT with minor improvements recommended

### Priority Remediation
1. Add AI disclosure to chat interface (Article 52)
2. Implement user feedback mechanism (continuous improvement)
3. Document bias testing procedures (Article 10 readiness)"""

    compliance_metric = GEval(
        name="EU AI Act Compliance",
        criteria="""Evaluate EU AI Act compliance reporting:
        1. System correctly classified by risk level
        2. Applicable articles identified
        3. Each article assessed with evidence
        4. Gaps clearly identified
        5. Remediation steps provided
        6. Overall compliance score calculated

        Score 1.0 if report is comprehensive and audit-ready.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="Generate EU AI Act compliance report",
        actual_output=transparency_output
    )

    assert_test(test_case, [compliance_metric])


@pytest.mark.deepeval
def test_human_oversight_support(deepeval_model):
    """Test that transparency outputs support human oversight effectively."""

    transparency_output = """## Human Oversight Dashboard

### Current Analysis Summary
- **Query**: "Should we approve $500K marketing budget?"
- **AI Recommendation**: APPROVE
- **Confidence**: 82%
- **Risk Level**: MEDIUM

---

### Why You Should Review This

**Escalation Triggers**:
1. ⚠️ Amount exceeds $100K auto-approval limit
2. ⚠️ Confidence below 85% threshold
3. ✓ No policy violations detected

**Key Uncertainties**:
- Competitor response unknown (could reduce effectiveness)
- Q4 seasonality may inflate expected returns
- Model assumes linear scaling (not validated above $300K)

---

### Information for Your Decision

**What the AI Found**:
- Historical ROI on marketing: 15:1
- Proposed budget is 50% increase from current
- Expected revenue impact: +$7.5M (±$2M)

**What the AI Cannot Know**:
- Strategic fit with company priorities
- Political/organizational considerations
- Risk appetite of leadership

**Alternative Scenarios**:
| Decision | Expected Outcome | Risk |
|----------|------------------|------|
| Approve $500K | +$7.5M revenue | Medium |
| Approve $300K | +$4.5M revenue | Low |
| Reject | Status quo | None |

---

### Your Options

1. **Approve** - Accept AI recommendation
2. **Modify** - Adjust amount (suggest: $300K for lower risk)
3. **Reject** - Override AI recommendation
4. **Request More Info** - Ask for additional analysis

### Override Impact
If you reject AI recommendation:
- Decision logged for audit trail
- Feedback used to improve future recommendations
- No penalty - human judgment is valued"""

    oversight_metric = GEval(
        name="Human Oversight Support",
        criteria="""Evaluate human oversight facilitation:
        1. Clear summary of AI recommendation
        2. Escalation triggers explained
        3. Key uncertainties highlighted
        4. Distinguishes AI knowledge vs human judgment
        5. Presents alternatives, not just one option
        6. Makes override process clear and judgment-free

        Score 1.0 if human can make informed decision to accept/reject.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="Present this decision for human review",
        actual_output=transparency_output
    )

    assert_test(test_case, [oversight_metric])


@pytest.mark.deepeval
def test_reliability_assessment_clarity(deepeval_model):
    """Test that reliability assessments are clear and actionable."""

    transparency_output = """## Reliability Assessment

### Overall Reliability: 85% (HIGH)

---

### Factor Breakdown

| Factor | Weight | Score | Status |
|--------|--------|-------|--------|
| Model Confidence | 30% | 87% | ✓ Good |
| Data Quality | 25% | 91% | ✓ Excellent |
| Refutation Tests | 25% | 100% | ✓ All passed |
| Sample Size | 20% | 72% | ⚠️ Adequate |

---

### What's Strong
1. **Refutation Tests** (100%): All 3 validity tests passed
2. **Data Quality** (91%): Low missing values, consistent formats
3. **Model Confidence** (87%): High certainty in causal estimate

### What Could Be Better
1. **Sample Size** (72%): 2,500 samples is adequate but not ideal
   - Recommendation: Collect 2 more months of data
   - Impact: Would increase reliability to ~90%

---

### Reliability Interpretation

**85% reliability means**:
- This analysis is trustworthy for business decisions
- Results unlikely to change with more data
- Confidence intervals are well-calibrated

**When to be cautious**:
- Extrapolating beyond observed data range
- Applying to different market conditions
- Decisions with irreversible consequences (recommend human review)

---

### Improvement Roadmap
1. **Quick Win**: Add 500 more samples → +3% reliability
2. **Medium Term**: Implement cross-validation → +2% reliability
3. **Long Term**: A/B testing framework → Highest confidence"""

    reliability_metric = GEval(
        name="Reliability Assessment Clarity",
        criteria="""Evaluate reliability assessment communication:
        1. Overall score with clear interpretation
        2. Factors broken down with individual scores
        3. Strengths clearly identified
        4. Weaknesses with specific improvement suggestions
        5. Practical interpretation of reliability level
        6. Roadmap for improvement

        Score 1.0 if non-expert can understand and act on assessment.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=deepeval_model
    )

    test_case = LLMTestCase(
        input="Assess the reliability of this analysis",
        actual_output=transparency_output
    )

    assert_test(test_case, [reliability_metric])
