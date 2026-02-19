---- MODULE StateGraph ----
\* =========================================================================
\* CARF LangGraph StateGraph — TLA+ Formal Specification
\*
\* Verifies the workflow properties of the CARF cognitive architecture:
\*   1. LIVENESS  — Every request eventually reaches a terminal state (END).
\*   2. SAFETY    — No domain agent runs without prior router classification.
\*   3. BOUNDED   — Reflector loops stay within max_reflections (default 2).
\*   4. GUARDIAN   — Every domain-agent output passes through Guardian
\*                   (except Chaotic, which short-circuits to human).
\*
\* Graph topology (from src/workflows/graph.py):
\*
\*   Entry ──► router ──► { deterministic_runner | causal_analyst
\*                          | bayesian_explorer  | circuit_breaker
\*                          | human_escalation }
\*
\*   deterministic_runner ──► guardian
\*   causal_analyst       ──► guardian
\*   bayesian_explorer    ──► guardian
\*   circuit_breaker      ──► human_escalation        (always)
\*
\*   guardian ──► END             (APPROVED)
\*            ──► reflector       (REJECTED, if reflections < max)
\*            ──► human_escalation (REQUIRES_ESCALATION or REJECTED at limit)
\*
\*   reflector ──► router
\*
\*   human_escalation ──► router  (MODIFIED)
\*                    ──► END     (APPROVED | REJECTED | TIMEOUT)
\*
\* Model parameters:
\*   MaxReflections — maximum reflector attempts before escalation
\*   MaxHumanLoops  — bound on human→router re-entries (for model-checking)
\*
\* =========================================================================
EXTENDS Naturals, FiniteSets, Sequences

CONSTANTS MaxReflections,   \* default 2
          MaxHumanLoops     \* bound for model-checking (e.g. 3)

\* ---- State Variables ----
VARIABLES
    pc,                   \* program counter — current node
    cynefin_domain,       \* classified domain
    guardian_verdict,      \* APPROVED | REJECTED | REQUIRES_ESCALATION
    human_status,          \* APPROVED | REJECTED | MODIFIED | TIMEOUT
    reflection_count,      \* number of reflector iterations
    human_loop_count,      \* number of human→router re-entries
    terminated,            \* TRUE when workflow reached END
    router_ran             \* TRUE once the router has classified

vars == << pc, cynefin_domain, guardian_verdict, human_status,
           reflection_count, human_loop_count, terminated, router_ran >>

\* ---- Domain Values ----
Domains    == {"Clear", "Complicated", "Complex", "Chaotic", "Disorder"}
Verdicts   == {"APPROVED", "REJECTED", "REQUIRES_ESCALATION"}
HumanStats == {"APPROVED", "REJECTED", "MODIFIED", "TIMEOUT", "IDLE"}
Nodes      == {"entry", "router",
               "deterministic_runner", "causal_analyst",
               "bayesian_explorer", "circuit_breaker",
               "guardian", "reflector", "human_escalation", "end"}

\* ---- Type Invariant ----
TypeOK ==
    /\ pc              \in Nodes
    /\ cynefin_domain  \in Domains \cup {"none"}
    /\ guardian_verdict \in Verdicts \cup {"none"}
    /\ human_status    \in HumanStats
    /\ reflection_count \in 0..MaxReflections+1
    /\ human_loop_count \in 0..MaxHumanLoops+1
    /\ terminated      \in BOOLEAN
    /\ router_ran      \in BOOLEAN

\* ====================================================================
\* Initial state
\* ====================================================================
Init ==
    /\ pc              = "entry"
    /\ cynefin_domain  = "none"
    /\ guardian_verdict = "none"
    /\ human_status    = "IDLE"
    /\ reflection_count = 0
    /\ human_loop_count = 0
    /\ terminated      = FALSE
    /\ router_ran      = FALSE

\* ====================================================================
\* Transition actions
\* ====================================================================

\* Entry → router (only once, at start)
StartRouter ==
    /\ pc = "entry"
    /\ pc' = "router"
    /\ UNCHANGED << cynefin_domain, guardian_verdict, human_status,
                    reflection_count, human_loop_count, terminated, router_ran >>

\* Router classifies into one of the 5 Cynefin domains
RouterClassify ==
    /\ pc = "router"
    /\ \E d \in Domains :
        /\ cynefin_domain' = d
        /\ pc' = CASE d = "Clear"       -> "deterministic_runner"
                 []   d = "Complicated"  -> "causal_analyst"
                 []   d = "Complex"      -> "bayesian_explorer"
                 []   d = "Chaotic"      -> "circuit_breaker"
                 []   d = "Disorder"     -> "human_escalation"
    /\ router_ran' = TRUE
    /\ UNCHANGED << guardian_verdict, human_status,
                    reflection_count, human_loop_count, terminated >>

\* Domain agents (Clear, Complicated, Complex) → Guardian
DomainToGuardian ==
    /\ pc \in {"deterministic_runner", "causal_analyst", "bayesian_explorer"}
    /\ pc' = "guardian"
    /\ UNCHANGED << cynefin_domain, guardian_verdict, human_status,
                    reflection_count, human_loop_count, terminated, router_ran >>

\* Circuit breaker (Chaotic) → human_escalation (always)
ChaoticToHuman ==
    /\ pc = "circuit_breaker"
    /\ pc' = "human_escalation"
    /\ UNCHANGED << cynefin_domain, guardian_verdict, human_status,
                    reflection_count, human_loop_count, terminated, router_ran >>

\* Guardian issues a verdict
GuardianDecide ==
    /\ pc = "guardian"
    /\ \E v \in Verdicts :
        /\ guardian_verdict' = v
        /\ pc' = CASE v = "APPROVED"            -> "end"
                 []   v = "REJECTED" /\ reflection_count < MaxReflections
                                                 -> "reflector"
                 []   v = "REJECTED" /\ reflection_count >= MaxReflections
                                                 -> "human_escalation"
                 []   v = "REQUIRES_ESCALATION"  -> "human_escalation"
    /\ UNCHANGED << cynefin_domain, human_status,
                    reflection_count, human_loop_count, terminated, router_ran >>

\* Reflector increments count and loops back to router
ReflectorRetry ==
    /\ pc = "reflector"
    /\ reflection_count' = reflection_count + 1
    /\ pc' = "router"
    /\ guardian_verdict' = "none"
    /\ UNCHANGED << cynefin_domain, human_status,
                    human_loop_count, terminated, router_ran >>

\* Human escalation resolves
HumanResolve ==
    /\ pc = "human_escalation"
    /\ \E hs \in {"APPROVED", "REJECTED", "MODIFIED", "TIMEOUT"} :
        /\ human_status' = hs
        /\ IF hs = "MODIFIED" /\ human_loop_count < MaxHumanLoops
           THEN /\ pc' = "router"
                /\ human_loop_count' = human_loop_count + 1
           ELSE /\ pc' = "end"
                /\ human_loop_count' = human_loop_count
    /\ UNCHANGED << cynefin_domain, guardian_verdict,
                    reflection_count, terminated, router_ran >>

\* Terminal state
Terminate ==
    /\ pc = "end"
    /\ terminated' = TRUE
    /\ UNCHANGED << pc, cynefin_domain, guardian_verdict, human_status,
                    reflection_count, human_loop_count, router_ran >>

\* ====================================================================
\* Next-state relation
\* ====================================================================
Next ==
    \/ StartRouter
    \/ RouterClassify
    \/ DomainToGuardian
    \/ ChaoticToHuman
    \/ GuardianDecide
    \/ ReflectorRetry
    \/ HumanResolve
    \/ Terminate

\* ====================================================================
\* Fairness — ensure the system makes progress
\* ====================================================================
Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

\* ====================================================================
\* SAFETY PROPERTIES
\* ====================================================================

\* S1: No domain agent runs without router having classified first.
\*     If pc is a domain-agent node, router must have run.
SafetyNoAgentWithoutRouter ==
    pc \in {"deterministic_runner", "causal_analyst",
            "bayesian_explorer", "circuit_breaker"}
        => router_ran = TRUE

\* S2: Reflector count never exceeds MaxReflections+1
SafetyBoundedReflections ==
    reflection_count <= MaxReflections + 1

\* S3: Human loop count never exceeds MaxHumanLoops+1
SafetyBoundedHumanLoops ==
    human_loop_count <= MaxHumanLoops + 1

\* S4: Guardian invariant — every non-Chaotic/non-Disorder domain agent
\*     output passes through guardian before reaching end.
\*     (Chaotic goes to human_escalation directly; Disorder goes to human_escalation.)
\*     Verified by graph topology: deterministic_runner/causal_analyst/bayesian_explorer
\*     all have edges exclusively to "guardian".
\*     TLA+ check: if terminated and domain is non-Chaotic & non-Disorder,
\*     guardian_verdict must have been set.
SafetyGuardianMustRun ==
    (terminated = TRUE /\ cynefin_domain \in {"Clear", "Complicated", "Complex"})
        => guardian_verdict \in Verdicts

\* Combined safety invariant
SafetyInvariant ==
    /\ TypeOK
    /\ SafetyNoAgentWithoutRouter
    /\ SafetyBoundedReflections
    /\ SafetyBoundedHumanLoops
    /\ SafetyGuardianMustRun

\* ====================================================================
\* LIVENESS PROPERTIES
\* ====================================================================

\* L1: Every request eventually terminates
LivenessTermination == <>(terminated = TRUE)

\* L2: If router classifies, eventually the workflow terminates
LivenessPostRouter == (router_ran = TRUE) ~> (terminated = TRUE)

\* ====================================================================
\* Model-checking configuration (for TLC)
\* ====================================================================
\* SPECIFICATION Spec
\* INVARIANT     SafetyInvariant
\* PROPERTY      LivenessTermination
\* PROPERTY      LivenessPostRouter
\*
\* CONSTANTS
\*   MaxReflections = 2
\*   MaxHumanLoops  = 3

====
