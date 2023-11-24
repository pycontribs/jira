"""The root of jira_svc package namespace."""
from __future__ import annotations

try:
    import importlib.metadata

    __version__ = importlib.metadata.version("jira_svc")
except Exception:
    __version__ = "unknown"

from jira_svc.client import (
    jira_svc,
    Comment,
    Issue,
    Priority,
    Project,
    Role,
    User,
    Watchers,
    Worklog,
)
from jira_svc.config import get_jira_svc
from jira_svc.exceptions import jira_svcError

__all__ = (
    "Comment",
    "__version__",
    "Issue",
    "jira_svc",
    "jira_svcError",
    "Priority",
    "Project",
    "Role",
    "User",
    "Watchers",
    "Worklog",
    "get_jira_svc",
)
