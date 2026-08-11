"""Replaceable boundaries for subjects, environments, coding agents, and workspaces."""

from .agents import (
    JsonStdioRoleBackend,
    RawRoleExecution,
    RetainedRoleExecutor,
    RoleBackend,
    RoleInvocationError,
    RoleInvocationResult,
    RoleInvoker,
)
from .protocols import (
    CapabilityArchitectRole,
    Diagnostician,
    EnvironmentInvestigator,
    ExperimentEvaluator,
    ProbeBuilder,
    ProbeEvaluator,
    ProbePlanner,
    ProbeReviewer,
    ProbeRoleBundle,
    ReleaseRecommender,
    SubjectRunner,
    TraceAnalyst,
)
from .role_adapters import (
    AdversarialReviewerAdapter,
    CapabilityArchitectAdapter,
    DiagnosticianAdapter,
    InvestigatorAdapter,
    ReleaseStewardAdapter,
    TraceAnalystAdapter,
)
from .role_builder import RoleBackedDirectoryBuilder
from .workspace import GitWorkspaceAdapter

__all__ = [
    "EnvironmentInvestigator",
    "ExperimentEvaluator",
    "ProbeBuilder",
    "ProbeEvaluator",
    "ProbePlanner",
    "ProbeReviewer",
    "ProbeRoleBundle",
    "GitWorkspaceAdapter",
    "JsonStdioRoleBackend",
    "RoleBackend",
    "RoleInvoker",
    "RawRoleExecution",
    "RoleInvocationResult",
    "RetainedRoleExecutor",
    "RoleInvocationError",
    "TraceAnalyst",
    "Diagnostician",
    "CapabilityArchitectRole",
    "ReleaseRecommender",
    "TraceAnalystAdapter",
    "DiagnosticianAdapter",
    "InvestigatorAdapter",
    "CapabilityArchitectAdapter",
    "AdversarialReviewerAdapter",
    "ReleaseStewardAdapter",
    "RoleBackedDirectoryBuilder",
    "SubjectRunner",
]
