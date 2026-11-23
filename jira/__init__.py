"""The root of JIRA package namespace."""

from __future__ import annotations

try:
    import importlib.metadata

    __version__ = importlib.metadata.version("jira")
except Exception:
    __version__ = "unknown"

from jira.client import (
    DESCRIPTION_MAX_LENGTH,
    JIRA,
    Comment,
    Issue,
    Priority,
    Project,
    Role,
    User,
    Watchers,
    Worklog,
)
from jira.config import get_jira
from jira.exceptions import JIRAError

__all__ = (
    "Comment",
    "DESCRIPTION_MAX_LENGTH",
    "__version__",
    "Issue",
    "JIRA",
    "JIRAError",
    "Priority",
    "Project",
    "Role",
    "User",
    "Watchers",
    "Worklog",
    "get_jira",
)
