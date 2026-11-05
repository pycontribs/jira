from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_import():
    """Test import of jira module."""
    import jira  # noqa: F401
