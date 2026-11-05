"""The root of JIRA package namespace."""

from __future__ import annotations

try:
    import importlib.metadata

    __version__ = importlib.metadata.version("jira")
except Exception:
    __version__ = "unknown"

from jira.client import (
    JIRA,
    TEXT_FIELD_MAX_LENGTH,
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
    "__version__",
    "Issue",
    "JIRA",
    "JIRAError",
    "Priority",
    "Project",
    "Role",
    "TEXT_FIELD_MAX_LENGTH",
    "User",
    "Watchers",
    "Worklog",
    "get_jira",
)
