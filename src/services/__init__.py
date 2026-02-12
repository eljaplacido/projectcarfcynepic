"""Services module: Concrete implementations.

Contains integrations with external services:
- Causal Inference Engine - Active
- HumanLayer (HITL) - Active
- Neo4j (Causal Graph) - Active
- CSL-Core Policy Verification - Active
- Policy Scaffolding - Active
- Transparency & Reliability - Active
- Simulation Framework - Active
- ChimeraOracle Fast Predictions - Active
- Kafka Audit Trail - Optional
- OPA Policy Engine - Optional
"""

from .human_layer import (
    HumanLayerService,
    get_human_layer_service,
    human_escalation_node,
    HumanResponse,
    NotificationContext,
)
from .causal import (
    CausalInferenceEngine,
    get_causal_engine,
    run_causal_analysis,
    CausalHypothesis,
    CausalAnalysisResult,
    CausalGraph,
)
from .bayesian import (
    ActiveInferenceEngine,
    get_bayesian_engine,
    run_active_inference,
    BayesianBelief,
    ExplorationProbe,
    ActiveInferenceResult,
)
from .neo4j_service import (
    Neo4jService,
    Neo4jConfig,
    get_neo4j_service,
    shutdown_neo4j,
)
from .kafka_audit import (
    KafkaAuditService,
    KafkaConfig,
    KafkaAuditEvent,
    get_kafka_audit_service,
    log_state_to_kafka,
)
from .opa_service import (
    OPAService,
    OPAConfig,
    OPAEvaluation,
    get_opa_service,
)
from .dataset_store import (
    DatasetStore,
    DatasetMetadata,
    get_dataset_store,
)
from .csl_policy_service import (
    CSLPolicyService,
    CSLConfig,
    CSLEvaluation,
    get_csl_service,
)
from .policy_scaffold_service import (
    PolicyScaffoldService,
    get_scaffold_service,
)
from .transparency import (
    TransparencyService,
    get_transparency_service,
)
from .simulation import (
    SimulationService,
    get_simulation_service,
)

__all__ = [
    # Human Layer
    "HumanLayerService",
    "get_human_layer_service",
    "human_escalation_node",
    "HumanResponse",
    "NotificationContext",
    # Causal Inference
    "CausalInferenceEngine",
    "get_causal_engine",
    "run_causal_analysis",
    "CausalHypothesis",
    "CausalAnalysisResult",
    "CausalGraph",
    # Bayesian Active Inference
    "ActiveInferenceEngine",
    "get_bayesian_engine",
    "run_active_inference",
    "BayesianBelief",
    "ExplorationProbe",
    "ActiveInferenceResult",
    # Neo4j Graph Database
    "Neo4jService",
    "Neo4jConfig",
    "get_neo4j_service",
    "shutdown_neo4j",
    # Kafka Audit Trail
    "KafkaAuditService",
    "KafkaConfig",
    "KafkaAuditEvent",
    "get_kafka_audit_service",
    "log_state_to_kafka",
    # OPA Policy Service
    "OPAService",
    "OPAConfig",
    "OPAEvaluation",
    "get_opa_service",
    # Dataset Store
    "DatasetStore",
    "DatasetMetadata",
    "get_dataset_store",
    # CSL-Core Policy Service
    "CSLPolicyService",
    "CSLConfig",
    "CSLEvaluation",
    "get_csl_service",
    # Policy Scaffolding
    "PolicyScaffoldService",
    "get_scaffold_service",
    # Transparency & Reliability
    "TransparencyService",
    "get_transparency_service",
    # Simulation Framework
    "SimulationService",
    "get_simulation_service",
]
