---- MODULE EscalationProtocol ----
\* =========================================================================
\* CARF Escalation Protocol — TLA+ Formal Specification
\*
\* Verifies the escalation invariants of the CARF system:
\*   1. Every low-confidence decision reaches human review.
\*   2. No escalation request is silently dropped.
\*   3. Human resolution is bounded (timeout or explicit response).
\*   4. Chaotic domain always triggers immediate escalation.
\*   5. Guardian rejection at reflection limit triggers escalation.
\*
\* This spec focuses on the escalation sub-protocol, modeling:
\*   - Confidence thresholds triggering escalation
\*   - Guardian REQUIRES_ESCALATION verdicts
\*   - Reflection-limit forced escalation
\*   - Disorder domain auto-escalation
\*   - Chaotic domain emergency escalation
\*   - Human response lifecycle (PENDING → APPROVED/REJECTED/MODIFIED/TIMEOUT)
\*
\* =========================================================================
EXTENDS Naturals, FiniteSets

CONSTANTS
    ConfidenceThreshold,   \* e.g. 50 (represents 0.50, scaled to avoid reals)
    MaxReflections,        \* default 2
    HumanTimeoutBound      \* max ticks before human TIMEOUT

\* ---- State Variables ----
VARIABLES
    phase,                 \* workflow phase: "routing" | "domain" | "guardian" | "escalation" | "resolved"
    domain,                \* classified Cynefin domain
    confidence,            \* domain confidence (0-100 integer, representing 0.00-1.00)
    guardian_verdict,      \* "APPROVED" | "REJECTED" | "REQUIRES_ESCALATION" | "none"
    reflection_count,      \* current reflector iterations
    escalation_requested,  \* TRUE if escalation has been requested
    escalation_reason,     \* why escalation was requested
    human_response,        \* "PENDING" | "APPROVED" | "REJECTED" | "MODIFIED" | "TIMEOUT"
    human_timer,           \* ticks since escalation was requested
    resolved               \* TRUE when the escalation is fully resolved

vars == << phase, domain, confidence, guardian_verdict, reflection_count,
           escalation_requested, escalation_reason, human_response,
           human_timer, resolved >>

\* ---- Value Sets ----
Domains       == {"Clear", "Complicated", "Complex", "Chaotic", "Disorder"}
Verdicts      == {"APPROVED", "REJECTED", "REQUIRES_ESCALATION", "none"}
HumanStatuses == {"PENDING", "APPROVED", "REJECTED", "MODIFIED", "TIMEOUT"}
Reasons       == {"low_confidence", "chaotic_emergency", "disorder_ambiguity",
                  "guardian_escalation", "reflection_limit_exceeded", "none"}
Phases        == {"routing", "domain", "guardian", "escalation", "resolved"}

\* ---- Type Invariant ----
TypeOK ==
    /\ phase              \in Phases
    /\ domain             \in Domains \cup {"none"}
    /\ confidence         \in 0..100
    /\ guardian_verdict   \in Verdicts
    /\ reflection_count   \in 0..(MaxReflections+1)
    /\ escalation_requested \in BOOLEAN
    /\ escalation_reason  \in Reasons
    /\ human_response     \in HumanStatuses \cup {"IDLE"}
    /\ human_timer        \in 0..(HumanTimeoutBound+1)
    /\ resolved           \in BOOLEAN

\* ====================================================================
\* Initial state
\* ====================================================================
Init ==
    /\ phase              = "routing"
    /\ domain             = "none"
    /\ confidence         = 0
    /\ guardian_verdict   = "none"
    /\ reflection_count   = 0
    /\ escalation_requested = FALSE
    /\ escalation_reason  = "none"
    /\ human_response     = "IDLE"
    /\ human_timer        = 0
    /\ resolved           = FALSE

\* ====================================================================
\* Routing phase — classify domain and confidence
\* ====================================================================
RouteQuery ==
    /\ phase = "routing"
    /\ \E d \in Domains, c \in 0..100 :
        /\ domain' = d
        /\ confidence' = c
        \* Immediate escalation paths
        /\ IF d = "Chaotic"
           THEN /\ phase' = "escalation"
                /\ escalation_requested' = TRUE
                /\ escalation_reason' = "chaotic_emergency"
                /\ human_response' = "PENDING"
           ELSE IF d = "Disorder"
           THEN /\ phase' = "escalation"
                /\ escalation_requested' = TRUE
                /\ escalation_reason' = "disorder_ambiguity"
                /\ human_response' = "PENDING"
           ELSE IF c < ConfidenceThreshold
           THEN \* Low confidence → Disorder override → escalation
                /\ phase' = "escalation"
                /\ escalation_requested' = TRUE
                /\ escalation_reason' = "low_confidence"
                /\ human_response' = "PENDING"
           ELSE /\ phase' = "domain"
                /\ escalation_requested' = escalation_requested
                /\ escalation_reason' = escalation_reason
                /\ human_response' = human_response
    /\ UNCHANGED << guardian_verdict, reflection_count, human_timer, resolved >>

\* ====================================================================
\* Domain processing → Guardian
\* ====================================================================
DomainProcess ==
    /\ phase = "domain"
    /\ phase' = "guardian"
    /\ UNCHANGED << domain, confidence, guardian_verdict, reflection_count,
                    escalation_requested, escalation_reason, human_response,
                    human_timer, resolved >>

\* ====================================================================
\* Guardian evaluation
\* ====================================================================
GuardianEvaluate ==
    /\ phase = "guardian"
    /\ \E v \in {"APPROVED", "REJECTED", "REQUIRES_ESCALATION"} :
        /\ guardian_verdict' = v
        /\ CASE v = "APPROVED" ->
                /\ phase' = "resolved"
                /\ resolved' = TRUE
                /\ UNCHANGED << escalation_requested, escalation_reason, human_response >>
           []   v = "REQUIRES_ESCALATION" ->
                /\ phase' = "escalation"
                /\ escalation_requested' = TRUE
                /\ escalation_reason' = "guardian_escalation"
                /\ human_response' = "PENDING"
                /\ resolved' = FALSE
           []   v = "REJECTED" /\ reflection_count < MaxReflections ->
                \* Reflector loop
                /\ reflection_count' = reflection_count + 1
                /\ phase' = "guardian"    \* simplified: retry guardian after reflection
                /\ resolved' = FALSE
                /\ UNCHANGED << escalation_requested, escalation_reason, human_response >>
           []   v = "REJECTED" /\ reflection_count >= MaxReflections ->
                \* Reflection limit → forced escalation
                /\ phase' = "escalation"
                /\ escalation_requested' = TRUE
                /\ escalation_reason' = "reflection_limit_exceeded"
                /\ human_response' = "PENDING"
                /\ resolved' = FALSE
    /\ UNCHANGED << domain, confidence, human_timer >>

\* ====================================================================
\* Human escalation lifecycle
\* ====================================================================

\* Human provides a response
HumanRespond ==
    /\ phase = "escalation"
    /\ human_response = "PENDING"
    /\ human_timer < HumanTimeoutBound
    /\ \E resp \in {"APPROVED", "REJECTED", "MODIFIED"} :
        /\ human_response' = resp
        /\ IF resp = "MODIFIED"
           THEN /\ phase' = "routing"     \* re-route with human guidance
                /\ resolved' = FALSE
           ELSE /\ phase' = "resolved"
                /\ resolved' = TRUE
    /\ human_timer' = human_timer + 1
    /\ UNCHANGED << domain, confidence, guardian_verdict, reflection_count,
                    escalation_requested, escalation_reason >>

\* Timeout — human didn't respond in time
HumanTimeout ==
    /\ phase = "escalation"
    /\ human_response = "PENDING"
    /\ human_timer >= HumanTimeoutBound
    /\ human_response' = "TIMEOUT"
    /\ phase' = "resolved"
    /\ resolved' = TRUE
    /\ human_timer' = human_timer
    /\ UNCHANGED << domain, confidence, guardian_verdict, reflection_count,
                    escalation_requested, escalation_reason >>

\* Timer tick while waiting
HumanWait ==
    /\ phase = "escalation"
    /\ human_response = "PENDING"
    /\ human_timer < HumanTimeoutBound
    /\ human_timer' = human_timer + 1
    /\ UNCHANGED << phase, domain, confidence, guardian_verdict, reflection_count,
                    escalation_requested, escalation_reason, human_response, resolved >>

\* ====================================================================
\* Next-state relation
\* ====================================================================
Next ==
    \/ RouteQuery
    \/ DomainProcess
    \/ GuardianEvaluate
    \/ HumanRespond
    \/ HumanTimeout
    \/ HumanWait

Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

\* ====================================================================
\* SAFETY PROPERTIES
\* ====================================================================

\* S1: If domain is Chaotic, escalation must have been requested
SafetyChaoticAlwaysEscalates ==
    (domain = "Chaotic" /\ phase # "routing")
        => escalation_requested = TRUE

\* S2: If domain is Disorder, escalation must have been requested
SafetyDisorderAlwaysEscalates ==
    (domain = "Disorder" /\ phase # "routing")
        => escalation_requested = TRUE

\* S3: Low confidence triggers escalation
SafetyLowConfidenceEscalates ==
    (confidence < ConfidenceThreshold /\ domain # "none" /\ phase # "routing")
        => escalation_requested = TRUE

\* S4: Reflection limit forces escalation
SafetyReflectionLimitEscalates ==
    (reflection_count >= MaxReflections /\ guardian_verdict = "REJECTED")
        => (phase = "escalation" \/ resolved = TRUE)

\* S5: No escalation is silently dropped — if requested, must eventually resolve
\*     (This is actually a liveness property; the safety part: if in escalation,
\*      human_response is PENDING until a response or timeout)
SafetyEscalationNotDropped ==
    (phase = "escalation") => (human_response = "PENDING" \/ resolved = TRUE)

\* S6: Reflection count bounded
SafetyBoundedReflections ==
    reflection_count <= MaxReflections + 1

\* Combined safety invariant
SafetyInvariant ==
    /\ TypeOK
    /\ SafetyChaoticAlwaysEscalates
    /\ SafetyDisorderAlwaysEscalates
    /\ SafetyLowConfidenceEscalates
    /\ SafetyBoundedReflections
    /\ SafetyEscalationNotDropped

\* ====================================================================
\* LIVENESS PROPERTIES
\* ====================================================================

\* L1: Every escalation request eventually resolves
LivenessEscalationResolves ==
    (escalation_requested = TRUE) ~> (resolved = TRUE)

\* L2: Every request eventually terminates
LivenessTermination == <>(resolved = TRUE)

\* L3: Pending human responses don't hang forever
LivenessHumanResolves ==
    (human_response = "PENDING") ~> (human_response # "PENDING")

\* ====================================================================
\* Model-checking configuration (for TLC)
\* ====================================================================
\* SPECIFICATION Spec
\* INVARIANT     SafetyInvariant
\* PROPERTY      LivenessTermination
\* PROPERTY      LivenessEscalationResolves
\* PROPERTY      LivenessHumanResolves
\*
\* CONSTANTS
\*   ConfidenceThreshold = 50
\*   MaxReflections      = 2
\*   HumanTimeoutBound   = 5

====
