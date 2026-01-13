"""Services module: Concrete implementations.

Contains integrations with external services:
- Causal Inference Engine - Active (Phase 2)
- HumanLayer (HITL) - Active
- Neo4j (Causal Graph) - Active (Phase 3)
- Redis (Short-term memory) - Phase 3+
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
]
