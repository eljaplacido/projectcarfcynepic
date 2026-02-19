# TLA+ Formal Specifications

Formal specifications for verifying critical CARF workflow invariants using TLA+ and the TLC model checker.

## Specifications

### StateGraph.tla

Models the complete LangGraph StateGraph workflow and verifies:

| Property | Type | Description |
|----------|------|-------------|
| **Liveness (L1)** | Temporal | Every request eventually reaches terminal state (END) |
| **Safety (S1)** | Invariant | No domain agent runs without prior router classification |
| **Safety (S2)** | Invariant | Reflector loops bounded by `MaxReflections` (default 2) |
| **Safety (S3)** | Invariant | Human loops bounded by `MaxHumanLoops` |
| **Safety (S4)** | Invariant | Every non-Chaotic/Disorder output passes through Guardian |

### EscalationProtocol.tla

Models the escalation sub-protocol and verifies:

| Property | Type | Description |
|----------|------|-------------|
| **Safety (S1-S2)** | Invariant | Chaotic/Disorder domains always trigger escalation |
| **Safety (S3)** | Invariant | Low-confidence decisions trigger escalation |
| **Safety (S4)** | Invariant | Reflection limit forces escalation |
| **Safety (S5)** | Invariant | No escalation request is silently dropped |
| **Liveness (L1)** | Temporal | Every escalation eventually resolves |
| **Liveness (L2)** | Temporal | Pending human responses don't hang forever |

## Running with TLC

### Prerequisites

Install the TLA+ Toolbox or use the command-line tools:

```bash
# Option 1: TLA+ Toolbox (GUI)
# Download from https://github.com/tlaplus/tlaplus/releases

# Option 2: Command-line TLC
# Download tla2tools.jar from the same releases page
```

### Model Checking StateGraph

```bash
# Create a model configuration file
cat > StateGraph.cfg << 'EOF'
SPECIFICATION Spec
INVARIANT SafetyInvariant
PROPERTY LivenessTermination
PROPERTY LivenessPostRouter
CONSTANTS
  MaxReflections = 2
  MaxHumanLoops = 3
EOF

# Run TLC
java -jar tla2tools.jar -config StateGraph.cfg StateGraph.tla
```

### Model Checking EscalationProtocol

```bash
# Create a model configuration file
cat > EscalationProtocol.cfg << 'EOF'
SPECIFICATION Spec
INVARIANT SafetyInvariant
PROPERTY LivenessTermination
PROPERTY LivenessEscalationResolves
PROPERTY LivenessHumanResolves
CONSTANTS
  ConfidenceThreshold = 50
  MaxReflections = 2
  HumanTimeoutBound = 5
EOF

# Run TLC
java -jar tla2tools.jar -config EscalationProtocol.cfg EscalationProtocol.tla
```

### Expected Results

With default constants, TLC should explore ~10k-50k states for each spec and report:

```
Model checking completed. No error has been found.
```

If a violation is found, TLC will produce a counterexample trace showing exactly which sequence of states leads to the invariant violation.

## Mapping to CARF Code

| TLA+ Concept | Code Location |
|--------------|---------------|
| `router` node | `src/workflows/router.py:cynefin_router_node()` |
| `route_by_domain` | `src/workflows/graph.py:route_by_domain()` |
| `guardian` node | `src/workflows/guardian.py:guardian_node()` |
| `route_after_guardian` | `src/workflows/graph.py:route_after_guardian()` |
| `reflector` node | `src/workflows/graph.py:reflector_node()` |
| `human_escalation` | `src/services/human_layer.py:human_escalation_node()` |
| `MaxReflections` | `src/core/state.py:EpistemicState.max_reflections` (default 2) |
| `ConfidenceThreshold` | `src/workflows/router.py:CynefinRouter.confidence_threshold` |
| `GuardianVerdict` | `src/core/state.py:GuardianVerdict` enum |
