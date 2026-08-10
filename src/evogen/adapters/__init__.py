"""Replaceable boundaries for subjects, environments, coding agents, and workspaces."""

from .agents import JsonStdioRoleBackend, RoleBackend
from .protocols import EnvironmentInvestigator, ExperimentEvaluator, SubjectRunner
from .role_builder import RoleBackedDirectoryBuilder
from .workspace import GitWorkspaceAdapter

__all__ = [
    "EnvironmentInvestigator",
    "ExperimentEvaluator",
    "GitWorkspaceAdapter",
    "JsonStdioRoleBackend",
    "RoleBackend",
    "RoleBackedDirectoryBuilder",
    "SubjectRunner",
]
