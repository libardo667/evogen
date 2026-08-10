from __future__ import annotations

from enum import StrEnum


class Completeness(StrEnum):
    COMPLETE = "complete"
    TRUNCATED = "truncated"
    MISSING = "missing"
    UNKNOWN = "unknown"


class ProofClass(StrEnum):
    SYNTHETIC = "synthetic"
    PORTABLE = "portable"
    REPLAY = "replay"
    LIVE = "live"


class EventKind(StrEnum):
    RUN_STARTED = "run_started"
    OBSERVATION = "observation"
    OBSERVATION_DELTA = "observation_delta"
    AFFORDANCE_SET = "affordance_set"
    DECISION = "decision"
    BINDING = "binding"
    DISPATCH = "dispatch"
    EXECUTION_RECEIPT = "execution_receipt"
    OUTCOME_OBSERVATION = "outcome_observation"
    MEMORY_UPDATE = "memory_update"
    HUMAN_INTERVENTION = "human_intervention"
    RECOVERY = "recovery"
    ERROR = "error"
    GOAL_BLOCKED = "goal_blocked"
    GOAL_ACHIEVED = "goal_achieved"
    RUN_FINISHED = "run_finished"


class FailureLayer(StrEnum):
    PERCEPTION = "perception"
    OBSERVABILITY = "observability"
    WORLD_REPRESENTATION = "world_representation"
    IDENTITY_TOPOLOGY = "identity_topology"
    AFFORDANCE_DISCOVERY = "affordance_discovery"
    BINDING_PRECONDITIONS = "binding_preconditions"
    EXECUTION = "execution"
    OUTCOME_VERIFICATION = "outcome_verification"
    CAUSAL_ATTRIBUTION = "causal_attribution"
    MEMORY_CONTINUITY = "memory_continuity"
    PLANNING_STRATEGY = "planning_strategy"
    RECOVERY = "recovery"
    RUNTIME_INFRASTRUCTURE = "runtime_infrastructure"
    ENVIRONMENT_LIMITATION = "environment_limitation"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_REPRODUCIBLE = "not_reproducible"


class ResolutionKind(StrEnum):
    ADD_CAPABILITY = "add_capability"
    CORRECT_CAPABILITY = "correct_capability"
    REMOVE_CAPABILITY = "remove_unsafe_capability"
    ADD_OBSERVATION = "add_observation"
    ADD_OUTCOME_EVIDENCE = "add_outcome_evidence"
    ADD_RECOVERY = "add_recovery_path"
    CHANGE_MEMORY = "change_memory_representation"
    CHANGE_PLANNER_POLICY = "change_planner_policy"
    ADD_KNOWLEDGE = "add_knowledge"
    BUILD_PROBE = "build_probe"
    FIX_INFRASTRUCTURE = "fix_infrastructure"
    NO_CHANGE_ENVIRONMENT_REFUSED = "no_change_environment_refused"
    NO_CHANGE_EXISTING_CAPABILITY = "no_change_existing_capability"


class IssueStatus(StrEnum):
    OPEN = "open"
    SPECIFIED = "specified"
    IMPLEMENTED = "implemented"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class CandidateStatus(StrEnum):
    CREATED = "created"
    REVIEWED = "reviewed"
    EVALUATED = "evaluated"
    RETAINED = "retained"
    REJECTED = "rejected"


class GateVerdict(StrEnum):
    RETAIN = "retain"
    REVISE = "revise"
    REJECT = "reject"


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentRole(StrEnum):
    TRACE_ANALYST = "trace_analyst"
    DIAGNOSTICIAN = "diagnostician"
    INVESTIGATOR = "investigator"
    CAPABILITY_ARCHITECT = "capability_architect"
    IMPLEMENTER = "implementer"
    ADVERSARIAL_REVIEWER = "adversarial_reviewer"
    EVALUATOR = "evaluator"
    RELEASE_STEWARD = "release_steward"
